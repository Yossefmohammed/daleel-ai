"""
Data Scraper Module
Sources:
  ✅ RemoteOK     — free public JSON API
  ✅ Arbeitnow    — free public JSON API
  ✅ The Muse     — free public JSON API
  ✅ Wuzzuf       — HTML scraping with BeautifulSoup (Egypt-focused)
  ⚠️  LinkedIn    — NOT supported (see note below)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LinkedIn Scraping — Why it is NOT included:
  1. ToS section 8.2 explicitly forbids automated data collection.
  2. Pages are JavaScript-rendered — requests/BS4 gets a login
     redirect, not job data.
  3. Aggressive bot detection (Cloudflare + proprietary layer).
  4. They have legally pursued scrapers (hiQ v LinkedIn, 2022).
  Legitimate option: LinkedIn Jobs API via a registered partner app:
  https://developer.linkedin.com/product-catalog/jobs
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import time
import logging
import requests
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/json,*/*",
}

OUTPUT_PATH = "data/jobs_combined.csv"
KAGGLE_FALLBACK_PATHS = ["data/jobs.csv", "docs/ai_jobs_market_2025_2026.csv"]


# ─────────────────────────────────────────────────────────────────────────────
# 1. RemoteOK
# ─────────────────────────────────────────────────────────────────────────────
class RemoteOKScraper:
    URL = "https://remoteok.com/api"

    def scrape(self, limit: int = 100) -> list:
        try:
            logger.info("📡 RemoteOK: fetching...")
            r = requests.get(self.URL, headers=HEADERS, timeout=15)
            r.raise_for_status()
            jobs = []
            for item in r.json()[1:limit + 1]:
                if not isinstance(item, dict):
                    continue
                jobs.append({
                    "job_title":   item.get("position", "Unknown"),
                    "company":     item.get("company", "Unknown"),
                    "description": item.get("description", "")[:600],
                    "location":    item.get("location", "Remote"),
                    "remote_work": "Fully Remote",
                    "tags":        ", ".join(item.get("tags", [])),
                    "url":         item.get("url", ""),
                    "salary_range": item.get("salary", "Not specified"),
                    "posted_date": item.get("date", datetime.now().isoformat()),
                    "source":      "RemoteOK",
                })
            logger.info(f"✅ RemoteOK: {len(jobs)} jobs")
            return jobs
        except Exception as e:
            logger.warning(f"⚠️  RemoteOK failed: {e}")
            return []


# ─────────────────────────────────────────────────────────────────────────────
# 2. Arbeitnow
# ─────────────────────────────────────────────────────────────────────────────
class ArbeitnowScraper:
    URL = "https://www.arbeitnow.com/api/job-board-api"

    def scrape(self, pages: int = 3) -> list:
        jobs = []
        try:
            for page in range(1, pages + 1):
                logger.info(f"📡 Arbeitnow page {page}...")
                r = requests.get(self.URL, params={"page": page}, headers=HEADERS, timeout=15)
                r.raise_for_status()
                data = r.json().get("data", [])
                if not data:
                    break
                for item in data:
                    jobs.append({
                        "job_title":   item.get("title", "Unknown"),
                        "company":     item.get("company_name", "Unknown"),
                        "description": item.get("description", "")[:600],
                        "location":    item.get("location", "Unknown"),
                        "remote_work": "Fully Remote" if item.get("remote") else "On-site / Hybrid",
                        "tags":        ", ".join(item.get("tags", [])),
                        "url":         item.get("url", ""),
                        "salary_range": "Not specified",
                        "posted_date": item.get("created_at", datetime.now().isoformat()),
                        "source":      "Arbeitnow",
                    })
                time.sleep(0.5)
        except Exception as e:
            logger.warning(f"⚠️  Arbeitnow failed: {e}")
        logger.info(f"✅ Arbeitnow: {len(jobs)} jobs")
        return jobs


# ─────────────────────────────────────────────────────────────────────────────
# 3. The Muse
# ─────────────────────────────────────────────────────────────────────────────
class TheMuseScraper:
    URL = "https://www.themuse.com/api/public/jobs"
    CATEGORIES = ["Software Engineer", "Data Science", "Product & UX"]

    def scrape(self, pages: int = 2) -> list:
        jobs = []
        try:
            for cat in self.CATEGORIES:
                for page in range(1, pages + 1):
                    logger.info(f"📡 The Muse: {cat} p{page}...")
                    r = requests.get(
                        self.URL, params={"category": cat, "page": page},
                        headers=HEADERS, timeout=15,
                    )
                    r.raise_for_status()
                    results = r.json().get("results", [])
                    if not results:
                        break
                    for item in results:
                        loc_list = item.get("locations", [{}])
                        location = loc_list[0].get("name", "Unknown") if loc_list else "Unknown"
                        jobs.append({
                            "job_title":   item.get("name", "Unknown"),
                            "company":     item.get("company", {}).get("name", "Unknown"),
                            "description": item.get("contents", "")[:600],
                            "location":    location,
                            "remote_work": "Remote" if "remote" in location.lower() else "On-site / Hybrid",
                            "tags":        ", ".join(c.get("name","") for c in item.get("categories",[])),
                            "url":         item.get("refs", {}).get("landing_page", ""),
                            "salary_range": "Not specified",
                            "posted_date": item.get("publication_date", datetime.now().isoformat()),
                            "source":      "The Muse",
                        })
                    time.sleep(0.5)
        except Exception as e:
            logger.warning(f"⚠️  The Muse failed: {e}")
        logger.info(f"✅ The Muse: {len(jobs)} jobs")
        return jobs


# ─────────────────────────────────────────────────────────────────────────────
# 4. Wuzzuf  🇪🇬
# ─────────────────────────────────────────────────────────────────────────────
class WuzzufScraper:
    """
    Scrapes Wuzzuf.net — Egypt's largest job board.
    Server-renders HTML so BeautifulSoup works fine.

    Wuzzuf uses minified/hashed CSS class names (e.g. css-m604qf) that can
    change on any deploy.  This scraper uses semantic / structural selectors
    (tag names, href patterns, text content) so it stays robust.
    """

    BASE_URL   = "https://wuzzuf.net"
    SEARCH_URL = "https://wuzzuf.net/search/jobs/"

    # Cast a wide net — Wuzzuf is Egypt-first
    KEYWORDS = [
        "software engineer",
        "python developer",
        "data scientist",
        "frontend developer",
        "backend developer",
        "full stack developer",
        "devops engineer",
        "mobile developer",
        "machine learning",
        "ui ux",
    ]

    EGYPT_CITIES = {
        "Cairo", "Giza", "Alexandria", "Maadi", "Nasr City",
        "Heliopolis", "Zamalek", "Smart Village", "New Cairo",
        "6th of October", "Mansoura", "Tanta", "Assiut",
        "Egypt", "Remote", "Hybrid",
    }

    def _fetch(self, keyword: str, page: int) -> BeautifulSoup | None:
        try:
            r = requests.get(
                self.SEARCH_URL,
                params={"q": keyword, "l": "Egypt", "start": page},
                headers=HEADERS,
                timeout=20,
            )
            if r.status_code == 200:
                return BeautifulSoup(r.text, "lxml")
            logger.warning(f"   Wuzzuf HTTP {r.status_code} for '{keyword}' p{page}")
        except Exception as e:
            logger.warning(f"   Wuzzuf fetch error: {e}")
        return None

    def _parse(self, soup: BeautifulSoup) -> list:
        jobs = []

        # Wuzzuf wraps each listing in <article> — the most stable selector
        cards = soup.find_all("article")

        # Fallback: any block with a /jobs/ link and an <h2>
        if not cards:
            cards = [h2.parent.parent for h2 in soup.find_all("h2") if h2.find("a", href=True)]

        for card in cards:
            try:
                # ── Title ───────────────────────────────────────────────
                h2 = card.find("h2")
                title_tag = h2.find("a") if h2 else card.find("a", href=lambda h: h and "/jobs/" in h)
                title = title_tag.get_text(strip=True) if title_tag else ""
                if not title:
                    continue

                # ── URL ─────────────────────────────────────────────────
                href = title_tag.get("href", "") if title_tag else ""
                job_url = href if href.startswith("http") else (self.BASE_URL + href if href else "")

                # ── Company ─────────────────────────────────────────────
                company_tag = card.find("a", href=lambda h: h and "/company/" in (h or "").lower())
                company = company_tag.get_text(strip=True) if company_tag else "Unknown"

                # ── Location ────────────────────────────────────────────
                location = "Egypt"
                for span in card.find_all("span"):
                    txt = span.get_text(strip=True)
                    if any(city.lower() in txt.lower() for city in self.EGYPT_CITIES) and len(txt) < 50:
                        location = txt
                        break

                # ── Skills / Tags ────────────────────────────────────────
                tag_links = card.select("a[href*='/a/']")  # Wuzzuf skill tags use /a/ path
                tags = ", ".join(t.get_text(strip=True) for t in tag_links[:8] if t.get_text(strip=True))

                # ── Posted date ──────────────────────────────────────────
                time_tag = card.find("time")
                posted = time_tag.get("datetime", datetime.now().isoformat()) if time_tag else datetime.now().isoformat()

                jobs.append({
                    "job_title":   title,
                    "company":     company,
                    "description": tags or title,
                    "location":    location,
                    "remote_work": "Remote" if "remote" in location.lower() else "On-site / Hybrid",
                    "tags":        tags,
                    "url":         job_url,
                    "salary_range": "Not specified",
                    "posted_date": posted,
                    "source":      "Wuzzuf",
                })
            except Exception:
                continue

        return jobs

    def scrape(self, keywords: list | None = None, pages_per_keyword: int = 2) -> list:
        keywords = keywords or self.KEYWORDS
        all_jobs = []

        for kw in keywords:
            logger.info(f"📡 Wuzzuf: '{kw}'")
            for page in range(0, pages_per_keyword):   # Wuzzuf paginates from 0
                soup = self._fetch(kw, page)
                if not soup:
                    break
                found = self._parse(soup)
                if not found:
                    break
                all_jobs.extend(found)
                logger.info(f"   page {page}: {len(found)} jobs")
                time.sleep(1.5)                        # respectful crawl delay

        # Deduplicate within source
        seen: set = set()
        unique = []
        for job in all_jobs:
            key = (job["job_title"].lower(), job["company"].lower())
            if key not in seen:
                seen.add(key)
                unique.append(job)

        logger.info(f"✅ Wuzzuf: {len(unique)} unique jobs")
        return unique


# ─────────────────────────────────────────────────────────────────────────────
# Main merge function
# ─────────────────────────────────────────────────────────────────────────────
def _load_existing() -> pd.DataFrame:
    for path in [OUTPUT_PATH] + KAGGLE_FALLBACK_PATHS:
        if os.path.exists(path):
            try:
                df = pd.read_csv(path)
                rename = {"title": "job_title", "position": "job_title",
                          "name": "job_title", "company_name": "company"}
                df.rename(columns={k: v for k, v in rename.items() if k in df.columns}, inplace=True)
                df.setdefault("job_title", "Unknown")
                df.setdefault("company",   "Unknown")
                df.setdefault("source",    "Kaggle")
                logger.info(f"✅ Loaded {len(df)} existing jobs from {path}")
                return df
            except Exception as e:
                logger.warning(f"⚠️  {path}: {e}")
    return pd.DataFrame()


def scrape_and_save(
    include_remoteok:  bool = True,
    include_arbeitnow: bool = True,
    include_muse:      bool = True,
    include_wuzzuf:    bool = True,
    remoteok_limit:    int  = 100,
    arbeitnow_pages:   int  = 3,
    muse_pages:        int  = 2,
    wuzzuf_keywords:   list | None = None,
    wuzzuf_pages:      int  = 2,
) -> pd.DataFrame:
    os.makedirs("data", exist_ok=True)
    existing = _load_existing()
    fresh = []

    if include_remoteok:
        fresh += RemoteOKScraper().scrape(limit=remoteok_limit)
    if include_arbeitnow:
        fresh += ArbeitnowScraper().scrape(pages=arbeitnow_pages)
    if include_muse:
        fresh += TheMuseScraper().scrape(pages=muse_pages)
    if include_wuzzuf:
        fresh += WuzzufScraper().scrape(keywords=wuzzuf_keywords, pages_per_keyword=wuzzuf_pages)

    logger.info(f"📊 Fresh scraped: {len(fresh)} | Existing: {len(existing)}")

    if not fresh and existing.empty:
        return pd.DataFrame()

    combined = pd.concat([existing, pd.DataFrame(fresh)], ignore_index=True)
    before = len(combined)
    combined.drop_duplicates(subset=["job_title", "company"], keep="first", inplace=True)
    logger.info(f"🗑️  {before - len(combined)} duplicates removed → {len(combined)} total")

    combined.to_csv(OUTPUT_PATH, index=False)
    logger.info(f"💾 Saved → {OUTPUT_PATH}")
    return combined


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    df = scrape_and_save()
    if not df.empty:
        print(f"\n✅ {len(df)} total jobs")
        print(df[["job_title", "company", "location", "source"]].head(15).to_string(index=False))
    else:
        print("❌ No jobs collected.")