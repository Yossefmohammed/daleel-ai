"""
data_scraper.py  –  Career AI  (v3 – Real jobs, real URLs, 7 sources)
======================================================================
Sources scraped (all free, no API key needed):
  1. RemoteOK      – remote tech jobs
  2. Arbeitnow     – European + remote jobs
  3. Remotive      – curated remote jobs
  4. Jobicy        – remote jobs
  5. The Muse      – US + remote jobs
  6. Himalayas     – remote tech jobs
  7. Wuzzuf        – Egypt jobs (Cairo, Giza, Alexandria)

All jobs are stored in data/jobs_combined.csv with a real, working URL.
"""

from __future__ import annotations

import time
import datetime
import re
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

DATA_DIR = Path("data")
COMBINED = DATA_DIR / "jobs_combined.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
}

EGYPT_ALIASES = {"egypt", "cairo", "giza", "alexandria"}


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _get(url: str, params: dict | None = None, timeout: int = 15) -> requests.Response | None:
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=timeout)
        r.raise_for_status()
        return r
    except Exception as e:
        print(f"  ⚠️  GET {url} failed: {e}")
        return None


def _clean(text: str) -> str:
    """Strip HTML tags and normalise whitespace."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", str(text))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:500]


def _job(title, company, description, location, salary, url, source) -> dict:
    return {
        "title":       _clean(title)       or "",
        "company":     _clean(company)     or "",
        "description": _clean(description) or "",
        "location":    _clean(location)    or "",
        "salary":      _clean(salary)      or "",
        "url":         str(url).strip()    or "",
        "source":      source,
        "scraped_at":  datetime.datetime.now().isoformat(timespec="seconds"),
    }


# ══════════════════════════════════════════════════════════════════════════════
# Source 1 – RemoteOK  (JSON API)
# ══════════════════════════════════════════════════════════════════════════════

def scrape_remoteok(skills: list[str] | None = None, limit: int = 80) -> list[dict]:
    """https://remoteok.com/api — returns JSON array, first item is metadata."""
    print("  📡 RemoteOK…")
    r = _get("https://remoteok.com/api")
    if not r:
        return []
    try:
        data = r.json()
    except Exception:
        return []

    jobs = []
    for item in data[1:]:  # skip metadata object
        if not isinstance(item, dict) or not item.get("id"):
            continue
        tags = " ".join(item.get("tags", []))
        if skills:
            blob = (item.get("position", "") + " " + tags + " " + item.get("description", "")).lower()
            if not any(s.lower() in blob for s in skills):
                continue
        jobs.append(_job(
            title=item.get("position", ""),
            company=item.get("company", ""),
            description=item.get("description", "")[:400],
            location=item.get("location", "Remote"),
            salary=item.get("salary", ""),
            url=item.get("url", f"https://remoteok.com/remote-jobs/{item.get('slug', '')}"),
            source="RemoteOK",
        ))
        if len(jobs) >= limit:
            break

    print(f"     ✅ {len(jobs)} jobs")
    return jobs


# ══════════════════════════════════════════════════════════════════════════════
# Source 2 – Arbeitnow  (JSON API)
# ══════════════════════════════════════════════════════════════════════════════

def scrape_arbeitnow(skills: list[str] | None = None, limit: int = 80) -> list[dict]:
    """https://arbeitnow.com/api/job-board-api"""
    print("  📡 Arbeitnow…")
    jobs = []
    page = 1
    while len(jobs) < limit:
        r = _get("https://arbeitnow.com/api/job-board-api", params={"page": page})
        if not r:
            break
        try:
            data = r.json().get("data", [])
        except Exception:
            break
        if not data:
            break
        for item in data:
            blob = (item.get("title", "") + " " + " ".join(item.get("tags", []))).lower()
            if skills and not any(s.lower() in blob for s in skills):
                continue
            jobs.append(_job(
                title=item.get("title", ""),
                company=item.get("company_name", ""),
                description=item.get("description", "")[:400],
                location=item.get("location", "Remote"),
                salary="",
                url=item.get("url", ""),
                source="Arbeitnow",
            ))
            if len(jobs) >= limit:
                break
        page += 1
        if page > 5:
            break
        time.sleep(0.3)

    print(f"     ✅ {len(jobs)} jobs")
    return jobs


# ══════════════════════════════════════════════════════════════════════════════
# Source 3 – Remotive  (JSON API)
# ══════════════════════════════════════════════════════════════════════════════

def scrape_remotive(skills: list[str] | None = None, limit: int = 80) -> list[dict]:
    """https://remotive.com/api/remote-jobs"""
    print("  📡 Remotive…")
    params = {}
    if skills:
        params["search"] = " ".join(skills[:3])
    r = _get("https://remotive.com/api/remote-jobs", params=params)
    if not r:
        return []
    try:
        data = r.json().get("jobs", [])
    except Exception:
        return []

    jobs = []
    for item in data[:limit]:
        jobs.append(_job(
            title=item.get("title", ""),
            company=item.get("company_name", ""),
            description=_clean(item.get("description", ""))[:400],
            location=item.get("candidate_required_location", "Remote"),
            salary=item.get("salary", ""),
            url=item.get("url", ""),
            source="Remotive",
        ))

    print(f"     ✅ {len(jobs)} jobs")
    return jobs


# ══════════════════════════════════════════════════════════════════════════════
# Source 4 – Jobicy  (JSON API)
# ══════════════════════════════════════════════════════════════════════════════

def scrape_jobicy(skills: list[str] | None = None, limit: int = 60) -> list[dict]:
    """https://jobicy.com/api/v2/remote-jobs"""
    print("  📡 Jobicy…")
    params = {"count": min(limit, 50), "geo": "worldwide", "industry": "tech"}
    if skills:
        params["tag"] = skills[0].lower()
    r = _get("https://jobicy.com/api/v2/remote-jobs", params=params)
    if not r:
        return []
    try:
        data = r.json().get("jobs", [])
    except Exception:
        return []

    jobs = []
    for item in data[:limit]:
        jobs.append(_job(
            title=item.get("jobTitle", ""),
            company=item.get("companyName", ""),
            description=_clean(item.get("jobDescription", ""))[:400],
            location=item.get("jobGeo", "Remote"),
            salary=item.get("annualSalaryMin", "") and
                   f"${item['annualSalaryMin']:,}–${item.get('annualSalaryMax', item['annualSalaryMin']):,}",
            url=item.get("url", ""),
            source="Jobicy",
        ))

    print(f"     ✅ {len(jobs)} jobs")
    return jobs


# ══════════════════════════════════════════════════════════════════════════════
# Source 5 – The Muse  (JSON API)
# ══════════════════════════════════════════════════════════════════════════════

def scrape_themuse(skills: list[str] | None = None, limit: int = 60) -> list[dict]:
    """https://www.themuse.com/api/public/jobs"""
    print("  📡 The Muse…")
    params = {"page": 1, "descending": "true"}
    if skills:
        params["category"] = "Software Engineer"  # broad category
    r = _get("https://www.themuse.com/api/public/jobs", params=params)
    if not r:
        return []
    try:
        data = r.json().get("results", [])
    except Exception:
        return []

    jobs = []
    for item in data[:limit]:
        # Location: list of location dicts
        locs = item.get("locations", [])
        loc_str = ", ".join(l.get("name", "") for l in locs) if locs else "Remote"
        # URL
        ref_url = item.get("refs", {}).get("landing_page", "")
        if not ref_url:
            ref_url = f"https://www.themuse.com/jobs/{item.get('id', '')}"
        blob = item.get("name", "") + " " + _clean(item.get("contents", ""))
        if skills and not any(s.lower() in blob.lower() for s in skills):
            continue
        jobs.append(_job(
            title=item.get("name", ""),
            company=item.get("company", {}).get("name", ""),
            description=_clean(item.get("contents", ""))[:400],
            location=loc_str,
            salary="",
            url=ref_url,
            source="The Muse",
        ))
        if len(jobs) >= limit:
            break

    print(f"     ✅ {len(jobs)} jobs")
    return jobs


# ══════════════════════════════════════════════════════════════════════════════
# Source 6 – Himalayas  (JSON API)
# ══════════════════════════════════════════════════════════════════════════════

def scrape_himalayas(skills: list[str] | None = None, limit: int = 60) -> list[dict]:
    """https://himalayas.app/jobs/api"""
    print("  📡 Himalayas…")
    params = {"limit": min(limit, 100)}
    if skills:
        params["q"] = " ".join(skills[:3])
    r = _get("https://himalayas.app/jobs/api", params=params)
    if not r:
        return []
    try:
        data = r.json().get("jobs", [])
    except Exception:
        return []

    jobs = []
    for item in data[:limit]:
        jobs.append(_job(
            title=item.get("title", ""),
            company=item.get("companyName", ""),
            description=_clean(item.get("description", ""))[:400],
            location=item.get("locationRestrictions", ["Remote"])[0]
                     if item.get("locationRestrictions") else "Remote",
            salary=item.get("salary", ""),
            url=item.get("applicationLink", item.get("url", "")),
            source="Himalayas",
        ))

    print(f"     ✅ {len(jobs)} jobs")
    return jobs


# ══════════════════════════════════════════════════════════════════════════════
# Source 7 – Wuzzuf  (HTML scraper — Egypt jobs)
# ══════════════════════════════════════════════════════════════════════════════

def scrape_wuzzuf(skills: list[str] | None = None, limit: int = 60) -> list[dict]:
    """
    Scrapes https://wuzzuf.net/search/jobs/ for Egypt-based jobs.
    Uses BeautifulSoup to parse the HTML listing page.
    """
    print("  📡 Wuzzuf (Egypt)…")
    query = " ".join(skills[:3]) if skills else "software developer"
    params = {"q": query, "a[]": "Egypt--Egypt", "start": 0}
    url = "https://wuzzuf.net/search/jobs/"

    r = _get(url, params=params)
    if not r:
        return []

    soup = BeautifulSoup(r.text, "lxml")
    cards = soup.select("div.css-pkv5jc")  # job card container

    if not cards:
        # fallback selector
        cards = soup.select("article") or soup.select("[data-id]")

    jobs = []
    for card in cards[:limit]:
        # Title + link
        title_el = card.select_one("h2 a, h3 a, a.css-o171kl, a[data-tag='job-title']")
        title    = title_el.get_text(strip=True) if title_el else ""
        href     = title_el.get("href", "") if title_el else ""
        if href and not href.startswith("http"):
            href = "https://wuzzuf.net" + href

        # Company
        comp_el = card.select_one("a.css-17s97q8, a[data-tag='company-name'], span.css-1f89vj5")
        company = comp_el.get_text(strip=True) if comp_el else ""

        # Location
        loc_el = card.select_one("span.css-5wys0k, [data-tag='job-location']")
        location = loc_el.get_text(strip=True) if loc_el else "Egypt"
        if not location:
            location = "Egypt"

        # Description / tags
        tags_els = card.select("a.css-o171kl span, span.css-1ve4b75")
        desc = " · ".join(t.get_text(strip=True) for t in tags_els) if tags_els else ""

        if not title or not href:
            continue

        jobs.append(_job(
            title=title,
            company=company,
            description=desc,
            location=location,
            salary="",
            url=href,
            source="Wuzzuf",
        ))

    # If CSS selectors changed, try JSON-LD embedded in the page
    if not jobs:
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, list):
                    items = data
                elif data.get("@type") == "ItemList":
                    items = data.get("itemListElement", [])
                else:
                    items = [data]
                for item in items:
                    job = item.get("item", item)
                    if job.get("@type") != "JobPosting":
                        continue
                    org  = job.get("hiringOrganization", {})
                    loc  = job.get("jobLocation", {})
                    addr = loc.get("address", {}) if isinstance(loc, dict) else {}
                    city = addr.get("addressLocality", "Egypt") if isinstance(addr, dict) else "Egypt"
                    jobs.append(_job(
                        title=job.get("title", ""),
                        company=org.get("name", "") if isinstance(org, dict) else "",
                        description=_clean(job.get("description", ""))[:400],
                        location=city,
                        salary="",
                        url=job.get("url", "https://wuzzuf.net"),
                        source="Wuzzuf",
                    ))
            except Exception:
                continue

    print(f"     ✅ {len(jobs)} jobs from Wuzzuf Egypt")
    return jobs


# ══════════════════════════════════════════════════════════════════════════════
# Database helpers
# ══════════════════════════════════════════════════════════════════════════════

def load_combined() -> list[dict]:
    """Load all saved jobs as a list of dicts."""
    if not COMBINED.exists():
        return []
    try:
        df = pd.read_csv(str(COMBINED), on_bad_lines="skip", nrows=8000)
        return df.fillna("").to_dict("records")
    except Exception as e:
        print(f"load_combined error: {e}")
        return []


def source_counts() -> dict[str, int]:
    """Return {source: count} from the saved CSV."""
    if not COMBINED.exists():
        return {}
    try:
        df = pd.read_csv(str(COMBINED), usecols=["source"], on_bad_lines="skip")
        return df["source"].value_counts().to_dict()
    except Exception:
        return {}


def save_jobs(new_jobs: list[dict]) -> int:
    """
    Merge new_jobs into jobs_combined.csv.
    Deduplicates on (title_lower, company_lower).
    Returns total job count after save.
    """
    DATA_DIR.mkdir(exist_ok=True)

    existing: list[dict] = load_combined()

    seen: set[tuple] = set()
    merged: list[dict] = []

    for j in existing:
        k = (str(j.get("title", ""))[:40].lower(), str(j.get("company", ""))[:30].lower())
        if k not in seen:
            seen.add(k)
            merged.append(j)

    added = 0
    for j in new_jobs:
        k = (str(j.get("title", ""))[:40].lower(), str(j.get("company", ""))[:30].lower())
        if k not in seen:
            seen.add(k)
            merged.append(j)
            added += 1

    df = pd.DataFrame(merged)
    df.to_csv(str(COMBINED), index=False)
    print(f"  💾 Saved: {added} new + {len(existing)} existing = {len(merged)} total jobs")
    return len(merged)


# ══════════════════════════════════════════════════════════════════════════════
# scrape_by_skills — used by app.py "Find My Best Jobs" button
# ══════════════════════════════════════════════════════════════════════════════

def scrape_by_skills(
    skills: list[str],
    limit: int = 60,
    location: str = "",
) -> list[dict]:
    """
    Scrape fresh jobs matching the given skills.
    If location is Egypt / Cairo / etc, always include Wuzzuf results.
    Returns combined list (not yet saved — caller decides when to save).
    """
    loc_lower     = location.lower() if location else ""
    is_egypt_pref = loc_lower in EGYPT_ALIASES or loc_lower == "egypt"

    per_source = max(limit // 6, 10)
    all_jobs: list[dict] = []

    scrapers = [
        scrape_remoteok,
        scrape_arbeitnow,
        scrape_remotive,
        scrape_jobicy,
        scrape_themuse,
        scrape_himalayas,
    ]

    for fn in scrapers:
        try:
            jobs = fn(skills=skills, limit=per_source)
            all_jobs.extend(jobs)
        except Exception as e:
            print(f"  ⚠️  {fn.__name__} error: {e}")
        time.sleep(0.5)

    # Always scrape Wuzzuf when Egypt preferred, or if no location pref
    if is_egypt_pref or not loc_lower:
        try:
            wuzzuf_jobs = scrape_wuzzuf(skills=skills, limit=per_source)
            all_jobs.extend(wuzzuf_jobs)
        except Exception as e:
            print(f"  ⚠️  scrape_wuzzuf error: {e}")

    return all_jobs


# ══════════════════════════════════════════════════════════════════════════════
# scrape_and_save — used by sidebar "Refresh Job Database" button
# ══════════════════════════════════════════════════════════════════════════════

def scrape_and_save(
    skills: list[str] | None = None,
    status_ph=None,
    limit_per_source: int = 80,
) -> int:
    """
    Full scrape of all sources → save to CSV.
    status_ph: optional Streamlit placeholder for live progress messages.
    """
    def say(msg: str):
        print(msg)
        if status_ph:
            try:
                status_ph.info(msg)
            except Exception:
                pass

    say("🔄 Starting full job database refresh…")
    all_jobs: list[dict] = []

    scraper_fns = [
        ("RemoteOK",  scrape_remoteok),
        ("Arbeitnow", scrape_arbeitnow),
        ("Remotive",  scrape_remotive),
        ("Jobicy",    scrape_jobicy),
        ("The Muse",  scrape_themuse),
        ("Himalayas", scrape_himalayas),
        ("Wuzzuf 🇪🇬", scrape_wuzzuf),
    ]

    for name, fn in scraper_fns:
        say(f"📡 Scraping {name}…")
        try:
            jobs = fn(skills=skills, limit=limit_per_source)
            all_jobs.extend(jobs)
            say(f"  ✅ {name}: {len(jobs)} jobs")
        except Exception as e:
            say(f"  ⚠️ {name} failed: {e}")
        time.sleep(0.8)

    total = save_jobs(all_jobs)
    say(f"✅ Done! {total:,} total jobs in database.")
    return total


# ══════════════════════════════════════════════════════════════════════════════
# CLI test
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=== data_scraper smoke test ===")
    jobs = scrape_by_skills(["Python", "FastAPI", "React"], limit=30, location="Egypt")
    print(f"\nTotal scraped: {len(jobs)}")
    for j in jobs[:5]:
        print(f"  [{j['source']:10}] {j['title'][:40]:<40} | {j['location']:<20} | {j['url'][:60]}")
    n = save_jobs(jobs)
    print(f"\nSaved. Total in DB: {n}")