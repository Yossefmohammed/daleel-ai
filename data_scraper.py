"""data_scraper.py — multi-source job scraper (RemoteOK · Arbeitnow · The Muse · Wuzzuf)."""
import os, time, logging, requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
REMOTEOK_LIMIT = 120
ARBEITNOW_PAGES = 3
MUSE_PAGES = 3
WUZZUF_PAGES = 3
CRAWL_DELAY = 0.5
WUZZUF_DEFAULT_KEYWORDS = ["AI", "Data Scientist", "Python", "ML Engineer"]
JOB_CSV_PATHS = []

logger = logging.getLogger(__name__)
OUTPUT = "data/jobs_combined.csv"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"),
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
}

def _now(): return datetime.now().isoformat()

# ── RemoteOK ───────────────────────────────────────────────────────────────────
class RemoteOKScraper:
    URL = "https://remoteok.com/api"
    def scrape(self, limit=REMOTEOK_LIMIT) -> list:
        try:
            data = requests.get(self.URL, headers=HEADERS, timeout=15).json()
            jobs = []
            for item in data[1:limit+1]:
                if not isinstance(item, dict): continue
                jobs.append({"job_title": item.get("position","Unknown"),
                             "company":   item.get("company","Unknown"),
                             "description": item.get("description","")[:500],
                             "location":  item.get("location","Remote"),
                             "remote_work":"Fully Remote",
                             "tags":      ", ".join(item.get("tags",[])),
                             "url":       item.get("url",""),
                             "salary_range": item.get("salary","Not specified"),
                             "posted_date":  item.get("date",_now()),
                             "source":    "RemoteOK"})
            logger.info(f"✅ RemoteOK: {len(jobs)}")
            return jobs
        except Exception as e:
            logger.warning(f"⚠️ RemoteOK: {e}"); return []

# ── Arbeitnow ──────────────────────────────────────────────────────────────────
class ArbeitnowScraper:
    URL = "https://www.arbeitnow.com/api/job-board-api"
    def scrape(self, pages=ARBEITNOW_PAGES) -> list:
        jobs = []
        for pg in range(1, pages+1):
            try:
                data = requests.get(self.URL, params={"page": pg},
                                    headers=HEADERS, timeout=15).json().get("data",[])
                if not data: break
                for item in data:
                    jobs.append({"job_title": item.get("title","Unknown"),
                                 "company":   item.get("company_name","Unknown"),
                                 "description": item.get("description","")[:500],
                                 "location":  item.get("location","Unknown"),
                                 "remote_work": "Fully Remote" if item.get("remote") else "On-site",
                                 "tags":      ", ".join(item.get("tags",[])),
                                 "url":       item.get("url",""),
                                 "salary_range": "Not specified",
                                 "posted_date":  item.get("created_at",_now()),
                                 "source":    "Arbeitnow"})
                time.sleep(0.5)
            except Exception as e:
                logger.warning(f"⚠️ Arbeitnow p{pg}: {e}"); break
        logger.info(f"✅ Arbeitnow: {len(jobs)}"); return jobs

# ── The Muse ───────────────────────────────────────────────────────────────────
class TheMuseScraper:
    URL  = "https://www.themuse.com/api/public/jobs"
    CATS = ["Software Engineer","Data Science","Product & UX"]
    def scrape(self, pages=MUSE_PAGES) -> list:
        jobs = []
        for cat in self.CATS:
            for pg in range(1, pages+1):
                try:
                    res = requests.get(self.URL, params={"category":cat,"page":pg},
                                       headers=HEADERS, timeout=15).json().get("results",[])
                    if not res: break
                    for item in res:
                        loc_list = item.get("locations",[{}])
                        loc = loc_list[0].get("name","Unknown") if loc_list else "Unknown"
                        jobs.append({
                            "job_title": item.get("name","Unknown"),
                            "company":   item.get("company",{}).get("name","Unknown"),
                            "description": item.get("contents","")[:500],
                            "location":  loc,
                            "remote_work": "Remote" if "remote" in loc.lower() else "On-site",
                            "tags":      ", ".join(c.get("name","") for c in item.get("categories",[])),
                            "url":       item.get("refs",{}).get("landing_page",""),
                            "salary_range": "Not specified",
                            "posted_date":  item.get("publication_date",_now()),
                            "source":    "The Muse"})
                    time.sleep(0.5)
                except Exception as e:
                    logger.warning(f"⚠️ Muse {cat} p{pg}: {e}"); break
        logger.info(f"✅ The Muse: {len(jobs)}"); return jobs

# ── Wuzzuf ─────────────────────────────────────────────────────────────────────
class WuzzufScraper:
    BASE   = "https://wuzzuf.net"
    SEARCH = "https://wuzzuf.net/search/jobs/"
    CITIES = {"Cairo","Giza","Alexandria","Maadi","Nasr City","Heliopolis",
               "Zamalek","Smart Village","New Cairo","6th of October",
               "Egypt","Remote","Hybrid"}

    def _fetch(self, kw, page):
        try:
            r = requests.get(self.SEARCH, params={"q":kw,"l":"Egypt","start":page},
                             headers=HEADERS, timeout=20)
            if r.status_code == 200:
                return BeautifulSoup(r.text, "lxml")
        except Exception as e:
            logger.warning(f"   Wuzzuf fetch: {e}")
        return None

    def _parse(self, soup) -> list:
        jobs, cards = [], soup.find_all("article") or []
        if not cards:
            cards = [h2.parent.parent for h2 in soup.find_all("h2") if h2.find("a", href=True)]
        for card in cards:
            try:
                h2  = card.find("h2")
                ta  = (h2.find("a") if h2 else None) or card.find("a", href=lambda h: h and "/jobs/" in (h or ""))
                if not ta: continue
                title   = ta.get_text(strip=True)
                href    = ta.get("href","")
                url     = href if href.startswith("http") else (self.BASE + href if href else "")
                co_tag  = card.find("a", href=lambda h: h and "/company/" in (h or "").lower())
                company = co_tag.get_text(strip=True) if co_tag else "Unknown"
                location = "Egypt"
                for sp in card.find_all("span"):
                    txt = sp.get_text(strip=True)
                    if any(c.lower() in txt.lower() for c in self.CITIES) and len(txt)<50:
                        location = txt; break
                tag_els = card.select("a[href*='/a/']")
                tags    = ", ".join(t.get_text(strip=True) for t in tag_els[:8])
                time_el = card.find("time")
                posted  = time_el.get("datetime", _now()) if time_el else _now()
                if title and title != "Unknown":
                    jobs.append({"job_title": title, "company": company,
                                 "description": tags or title, "location": location,
                                 "remote_work": "Remote" if "remote" in location.lower() else "On-site",
                                 "tags": tags, "url": url, "salary_range": "Not specified",
                                 "posted_date": posted, "source": "Wuzzuf"})
            except Exception: continue
        return jobs

    def scrape(self, keywords=None, pages_per_keyword=WUZZUF_PAGES) -> list:
        keywords  = keywords or WUZZUF_DEFAULT_KEYWORDS
        all_jobs  = []
        for kw in keywords:
            logger.info(f"📡 Wuzzuf: '{kw}'")
            for pg in range(0, pages_per_keyword):
                soup = self._fetch(kw, pg)
                if not soup: break
                found = self._parse(soup)
                if not found: break
                all_jobs.extend(found)
                time.sleep(CRAWL_DELAY)
        seen, unique = set(), []
        for j in all_jobs:
            key = (j["job_title"].lower(), j["company"].lower())
            if key not in seen: seen.add(key); unique.append(j)
        logger.info(f"✅ Wuzzuf: {len(unique)} unique"); return unique

# ── LinkedIn note ──────────────────────────────────────────────────────────────
# LinkedIn scraping is NOT implemented:
#   1. ToS §8.2 explicitly forbids automated data collection
#   2. Pages are JS-rendered — requests gets a login wall
#   3. Cloudflare + proprietary bot detection
#   4. Legal precedent (hiQ v LinkedIn 2022)
# Use the official LinkedIn Jobs API: https://developer.linkedin.com/product-catalog/jobs

# ── Merge & save ───────────────────────────────────────────────────────────────
def _load_existing() -> pd.DataFrame:
    for path in [OUTPUT] + JOB_CSV_PATHS:
        if os.path.exists(path):
            try:
                df = pd.read_csv(path).fillna("")
                df.rename(columns={"title":"job_title","position":"job_title",
                                   "company_name":"company"}, inplace=True)
                df.setdefault = lambda k,v: None  # no-op, just flag
                logger.info(f"✅ Loaded {len(df)} existing from {path}")
                return df
            except Exception: pass
    return pd.DataFrame()

def scrape_and_save(include_remoteok=True, include_arbeitnow=True,
                    include_muse=True, include_wuzzuf=True,
                    remoteok_limit=REMOTEOK_LIMIT, arbeitnow_pages=ARBEITNOW_PAGES,
                    muse_pages=MUSE_PAGES, wuzzuf_keywords=None,
                    wuzzuf_pages=WUZZUF_PAGES) -> pd.DataFrame:
    os.makedirs("data", exist_ok=True)
    existing = _load_existing()
    fresh = []
    if include_remoteok:  fresh += RemoteOKScraper().scrape(limit=remoteok_limit)
    if include_arbeitnow: fresh += ArbeitnowScraper().scrape(pages=arbeitnow_pages)
    if include_muse:      fresh += TheMuseScraper().scrape(pages=muse_pages)
    if include_wuzzuf:    fresh += WuzzufScraper().scrape(keywords=wuzzuf_keywords,
                                                          pages_per_keyword=wuzzuf_pages)
    combined = pd.concat([existing, pd.DataFrame(fresh)], ignore_index=True)
    before   = len(combined)
    combined.drop_duplicates(subset=["job_title","company"], keep="first", inplace=True)
    logger.info(f"🗑️ {before-len(combined)} dupes removed → {len(combined)} total")
    combined.to_csv(OUTPUT, index=False)
    logger.info(f"💾 Saved → {OUTPUT}")
    return combined

if __name__ == "__main__":
    df = scrape_and_save()
    print(f"✅ {len(df)} jobs total")