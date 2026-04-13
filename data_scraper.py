"""
data_scraper.py  –  Career AI  (upgraded)
==========================================
Sources:
  1. RemoteOK      – remote tech jobs        (free JSON API, no key)
  2. Arbeitnow     – European + remote jobs  (free JSON API, no key)
  3. The Muse      – culture-first jobs      (free JSON API, no key)
  4. Remotive      – remote-only jobs        (free JSON API, no key)
  5. JobIcyAPI     – broad tech jobs         (free JSON API, no key)
  6. Local CSV     – any CSV in data/ or docs/

Public API (called by app.py):
    scrape_by_skills(skills, limit=60)   → list[dict]   (targeted)
    scrape_and_save(skills, status_ph)   → pd.DataFrame (full rebuild)
    save_jobs(jobs)                      → int           (dedup + persist)
    load_combined()                      → list[dict]
"""

from __future__ import annotations

import re
import time
import logging
from pathlib import Path

import pandas as pd
import requests

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger("data_scraper")

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_DIR = Path("data")
COMBINED = DATA_DIR / "jobs_combined.csv"

_UA = {"User-Agent": "CareerAI/2.0 (+github.com/Yossefmohammed/wasla-chatbot)",
       "Accept": "application/json"}

# ── Column aliases used by local CSVs ─────────────────────────────────────────
COL_MAP = {
    "job_title": "title", "position": "title", "role": "title",
    "company_name": "company", "employer": "company",
    "job_description": "description", "responsibilities": "description",
    "required_skills": "description",
    "job_location": "location", "city": "location",
    "salary_in_usd": "salary", "salary_estimate": "salary",
    "annual_salary_usd": "salary", "avg_salary": "salary", "salary_range": "salary",
}

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", str(text or "")).strip()

def _norm(j: dict) -> dict:
    """Ensure every job dict has exactly the 7 required keys."""
    return {
        "title":       str(j.get("title",       "") or "")[:120].strip(),
        "company":     str(j.get("company",     "") or "")[:80].strip(),
        "description": str(j.get("description", "") or "")[:500].strip(),
        "location":    str(j.get("location",    "") or "Remote")[:80].strip(),
        "salary":      str(j.get("salary",      "") or "")[:60].strip(),
        "url":         str(j.get("url",         "") or "")[:300].strip(),
        "source":      str(j.get("source",      "Unknown")).strip(),
    }

def _dedup(jobs: list) -> list:
    seen, unique = set(), []
    for j in jobs:
        k = (j.get("title", "").lower()[:40], j.get("company", "").lower()[:30])
        if k not in seen:
            seen.add(k)
            unique.append(j)
    return unique


# ══════════════════════════════════════════════════════════════════════════════
# Source 1 – RemoteOK
# ══════════════════════════════════════════════════════════════════════════════
def scrape_remoteok(keywords: str = "", limit: int = 150) -> list:
    """
    Scrape RemoteOK remote jobs.
    keywords: comma-joined skill tags e.g. "python,react"
    """
    try:
        params = {}
        if keywords:
            params["tags"] = keywords.lower().replace(" ", ",")
        r = requests.get("https://remoteok.com/api", params=params,
                         headers=_UA, timeout=15)
        r.raise_for_status()
        jobs = []
        for j in r.json()[:limit]:
            if not isinstance(j, dict) or "id" not in j:
                continue
            tags = j.get("tags", [])
            desc = _strip_html(j.get("description", "")) or ", ".join(tags)
            jobs.append(_norm({
                "title":       j.get("position") or j.get("title", ""),
                "company":     j.get("company", ""),
                "description": desc[:500],
                "location":    j.get("location", "Remote"),
                "salary":      str(j.get("salary") or ""),
                "url":         j.get("url", ""),
                "source":      "RemoteOK",
            }))
        logger.info(f"RemoteOK       → {len(jobs):>4} jobs  (kw={keywords!r})")
        return jobs
    except Exception as e:
        logger.warning(f"RemoteOK failed: {e}")
        return []


# ══════════════════════════════════════════════════════════════════════════════
# Source 2 – Arbeitnow
# ══════════════════════════════════════════════════════════════════════════════
def scrape_arbeitnow(limit: int = 150) -> list:
    """European + remote jobs — free paginated JSON API."""
    jobs = []
    try:
        for page in range(1, 5):
            r = requests.get(
                "https://www.arbeitnow.com/api/job-board-api",
                params={"page": page}, headers=_UA, timeout=15)
            r.raise_for_status()
            data = r.json().get("data", [])
            if not data:
                break
            for j in data:
                jobs.append(_norm({
                    "title":       j.get("title", ""),
                    "company":     j.get("company_name", ""),
                    "description": _strip_html(j.get("description", ""))[:500],
                    "location":    j.get("location", ""),
                    "salary":      "",
                    "url":         j.get("url", ""),
                    "source":      "Arbeitnow",
                }))
            if len(jobs) >= limit:
                break
            time.sleep(0.3)
        logger.info(f"Arbeitnow      → {len(jobs):>4} jobs")
        return jobs[:limit]
    except Exception as e:
        logger.warning(f"Arbeitnow failed: {e}")
        return []


# ══════════════════════════════════════════════════════════════════════════════
# Source 3 – The Muse  (https://www.themuse.com/api/public/jobs)
# ══════════════════════════════════════════════════════════════════════════════
_MUSE_CATEGORIES = {
    "python": "Engineering", "javascript": "Engineering", "js": "Engineering",
    "react": "Engineering",  "vue": "Engineering",         "node": "Engineering",
    "java": "Engineering",   "kotlin": "Engineering",      "swift": "Engineering",
    "php": "Engineering",    "ruby": "Engineering",         "go": "Engineering",
    "rust": "Engineering",   "c++": "Engineering",          "scala": "Engineering",
    "data": "Data Science",  "ml": "Data Science",          "ai": "Data Science",
    "machine learning": "Data Science",                      "nlp": "Data Science",
    "design": "Design & UX", "figma": "Design & UX",        "ux": "Design & UX",
    "product": "Product",    "devops": "DevOps",             "cloud": "DevOps",
    "aws": "DevOps",         "docker": "DevOps",             "kubernetes": "DevOps",
    "mobile": "Engineering", "android": "Engineering",       "ios": "Engineering",
    "marketing": "Marketing & PR", "sales": "Sales",
}

def scrape_themuse(keywords: str = "", limit: int = 100) -> list:
    """
    The Muse public API — free, no key required.
    Picks the best matching category from your skills.
    """
    category = "Engineering"
    if keywords:
        kw_lower = keywords.lower()
        for kw, cat in _MUSE_CATEGORIES.items():
            if kw in kw_lower:
                category = cat
                break

    jobs, page = [], 1
    try:
        while len(jobs) < limit:
            r = requests.get(
                "https://www.themuse.com/api/public/jobs",
                params={"category": category, "page": page, "descending": "true"},
                headers=_UA, timeout=15)
            r.raise_for_status()
            payload = r.json()
            items = payload.get("results", [])
            if not items:
                break
            for item in items:
                locs = item.get("locations", [])
                loc = ", ".join(l.get("name", "") for l in locs) or "Remote"
                levels = item.get("levels", [])
                lvl = ", ".join(l.get("name", "") for l in levels)
                desc = _strip_html(item.get("contents", ""))
                jobs.append(_norm({
                    "title":       item.get("name", ""),
                    "company":     item.get("company", {}).get("name", ""),
                    "description": (f"[{lvl}] " if lvl else "") + desc[:490],
                    "location":    loc,
                    "salary":      "",
                    "url":         item.get("refs", {}).get("landing_page", ""),
                    "source":      "The Muse",
                }))
            if page >= payload.get("page_count", 1) or len(jobs) >= limit:
                break
            page += 1
            time.sleep(0.3)
    except Exception as e:
        logger.warning(f"The Muse failed: {e}")

    logger.info(f"The Muse       → {len(jobs):>4} jobs  (cat={category!r})")
    return jobs[:limit]


# ══════════════════════════════════════════════════════════════════════════════
# Source 4 – Remotive  (https://remotive.com/api/remote-jobs)
# ══════════════════════════════════════════════════════════════════════════════
_REMOTIVE_CATS = {
    "python": "software-dev", "javascript": "software-dev", "react": "software-dev",
    "java": "software-dev",   "php": "software-dev",         "ruby": "software-dev",
    "go": "software-dev",     "node": "software-dev",         "typescript": "software-dev",
    "data": "data",           "ml": "data",                   "machine learning": "data",
    "ai": "data",             "analyst": "data",
    "devops": "devops-sysadmin", "aws": "devops-sysadmin",   "docker": "devops-sysadmin",
    "design": "design",       "ux": "design",                 "figma": "design",
    "product": "product",     "marketing": "marketing",       "sales": "sales",
    "mobile": "mobile-dev",   "android": "mobile-dev",        "ios": "mobile-dev",
    "qa": "qa",               "testing": "qa",
}

def scrape_remotive(keywords: str = "", limit: int = 100) -> list:
    """Remotive.com free JSON API — remote-only jobs."""
    category = ""
    if keywords:
        kw_lower = keywords.lower()
        for kw, cat in _REMOTIVE_CATS.items():
            if kw in kw_lower:
                category = cat
                break
    try:
        params = {"limit": min(limit, 100)}
        if category:
            params["category"] = category
        if keywords:
            params["search"] = keywords
        r = requests.get("https://remotive.com/api/remote-jobs",
                         params=params, headers=_UA, timeout=15)
        r.raise_for_status()
        items = r.json().get("jobs", [])
        jobs = []
        for j in items[:limit]:
            tags = ", ".join(j.get("tags", []))
            desc = _strip_html(j.get("description", ""))
            if tags:
                desc = f"Skills: {tags}. {desc}"
            jobs.append(_norm({
                "title":       j.get("title", ""),
                "company":     j.get("company_name", ""),
                "description": desc[:500],
                "location":    j.get("candidate_required_location", "Remote"),
                "salary":      j.get("salary", ""),
                "url":         j.get("url", ""),
                "source":      "Remotive",
            }))
        logger.info(f"Remotive       → {len(jobs):>4} jobs  (kw={keywords!r})")
        return jobs
    except Exception as e:
        logger.warning(f"Remotive failed: {e}")
        return []


# ══════════════════════════════════════════════════════════════════════════════
# Source 5 – Jobicy  (https://jobicy.com/api/v2/remote-jobs)
# ══════════════════════════════════════════════════════════════════════════════
def scrape_jobicy(keywords: str = "", limit: int = 50) -> list:
    """Jobicy free JSON API — remote jobs."""
    try:
        params = {"count": min(limit, 50), "geo": "worldwide"}
        if keywords:
            # use first keyword as tag
            params["tag"] = keywords.split(",")[0].strip().lower()
        r = requests.get("https://jobicy.com/api/v2/remote-jobs",
                         params=params, headers=_UA, timeout=15)
        r.raise_for_status()
        items = r.json().get("jobs", [])
        jobs = []
        for j in items:
            desc = _strip_html(j.get("jobDescription", ""))
            salary = ""
            lo = j.get("annualSalaryMin", "")
            hi = j.get("annualSalaryMax", "")
            if lo or hi:
                salary = f"${lo}–${hi}" if (lo and hi) else f"${lo or hi}"
            jobs.append(_norm({
                "title":       j.get("jobTitle", ""),
                "company":     j.get("companyName", ""),
                "description": desc[:500],
                "location":    j.get("jobGeo", "Remote"),
                "salary":      salary,
                "url":         j.get("url", ""),
                "source":      "Jobicy",
            }))
        logger.info(f"Jobicy         → {len(jobs):>4} jobs  (kw={keywords!r})")
        return jobs
    except Exception as e:
        logger.warning(f"Jobicy failed: {e}")
        return []


# ══════════════════════════════════════════════════════════════════════════════
# Source 6 – Local CSV (data/jobs.csv or docs/*.csv)
# ══════════════════════════════════════════════════════════════════════════════
def load_local_csv() -> list:
    candidates = [DATA_DIR / "jobs.csv"]
    if Path("docs").exists():
        candidates += list(Path("docs").glob("*.csv"))

    for p in candidates:
        if not p.exists():
            continue
        try:
            df = pd.read_csv(str(p), on_bad_lines="skip", nrows=2000)
            df.columns = [c.lower().strip() for c in df.columns]
            # rename known aliases
            df = df.rename(columns={k: v for k, v in COL_MAP.items()
                                     if k in df.columns and v not in df.columns})
            df = df.fillna("")
            for col in ["title", "company", "description", "location", "salary"]:
                if col not in df.columns:
                    df[col] = ""
            df["source"] = "Local CSV"
            df["url"]    = ""
            records = df[["title","company","description","location",
                           "salary","url","source"]].to_dict("records")
            logger.info(f"Local CSV      → {len(records):>4} jobs  ({p.name})")
            return [_norm(r) for r in records]
        except Exception as e:
            logger.warning(f"Local CSV {p}: {e}")
    return []


# ══════════════════════════════════════════════════════════════════════════════
# Persist / load
# ══════════════════════════════════════════════════════════════════════════════
def save_jobs(jobs: list) -> int:
    """Dedup, save to CSV, return number of unique jobs saved."""
    DATA_DIR.mkdir(exist_ok=True)
    unique = _dedup([_norm(j) for j in jobs])

    # Merge with existing DB so we never lose previously scraped jobs
    if COMBINED.exists():
        try:
            existing = pd.read_csv(str(COMBINED), on_bad_lines="skip").fillna("").to_dict("records")
            unique = _dedup(existing + unique)
        except Exception:
            pass

    pd.DataFrame(unique).to_csv(str(COMBINED), index=False)
    logger.info(f"Saved {len(unique):,} unique jobs → {COMBINED}")
    return len(unique)


def load_combined() -> list:
    """Load current job database as list of dicts."""
    if not COMBINED.exists():
        return []
    try:
        df = pd.read_csv(str(COMBINED), on_bad_lines="skip", nrows=5000)
        return df.fillna("").to_dict("records")
    except Exception as e:
        logger.warning(f"load_combined failed: {e}")
        return []


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════
def scrape_by_skills(skills: list, limit: int = 60) -> list:
    """
    Targeted scrape based on a user's skill list.
    Called by app.py when the user clicks "Find My Best Jobs".

    For each skill we query RemoteOK, Remotive, and Jobicy.
    The Muse is queried once with the combined keyword string.
    Results are deduped and returned as a list of normalised job dicts.

    Parameters
    ----------
    skills : list of str
        User's skills, e.g. ["Python", "React", "SQL"].
    limit : int
        Max jobs to scrape per source per skill.

    Returns
    -------
    list[dict]  – jobs with keys: title, company, description,
                  location, salary, url, source
    """
    if not skills:
        return []

    all_jobs: list = []
    top_skills = skills[:5]   # use top 5 skills to keep requests reasonable
    combined_kw = ",".join(top_skills)

    # ── per-skill queries (most targeted) ────────────────────────────────────
    for skill in top_skills:
        all_jobs.extend(scrape_remoteok(keywords=skill, limit=limit))
        all_jobs.extend(scrape_remotive(keywords=skill, limit=limit // 2))
        all_jobs.extend(scrape_jobicy(keywords=skill,   limit=limit // 2))
        time.sleep(0.4)    # polite between skills

    # ── combined keyword query ────────────────────────────────────────────────
    all_jobs.extend(scrape_remoteok(keywords=combined_kw, limit=limit))
    all_jobs.extend(scrape_themuse(keywords=combined_kw,  limit=limit))

    deduped = _dedup([_norm(j) for j in all_jobs])
    logger.info(f"scrape_by_skills → {len(deduped)} unique jobs for {top_skills}")
    return deduped


def scrape_and_save(skills: list = None, status_ph=None) -> pd.DataFrame:
    """
    Full database rebuild.  Called by the sidebar Refresh button and on first load.

    Parameters
    ----------
    skills : list[str] | None
        When provided, targeted scraping is performed first.
    status_ph : Streamlit placeholder | None
        Progress messages are written here if supplied.

    Returns
    -------
    pd.DataFrame — the combined job database after saving.
    """
    def say(msg: str):
        logger.info(msg)
        if status_ph:
            status_ph.info(msg)

    all_jobs: list = []

    # ── Targeted scrape (skill-based) ─────────────────────────────────────
    if skills:
        say(f"🎯 Targeted scrape for: {', '.join(skills[:5])}")
        all_jobs.extend(scrape_by_skills(skills))

    # ── General scrape (always) ───────────────────────────────────────────
    say("📡 RemoteOK general…")
    all_jobs.extend(scrape_remoteok(limit=150))

    say("📡 Arbeitnow…")
    all_jobs.extend(scrape_arbeitnow(limit=150))

    say("📡 Remotive general…")
    all_jobs.extend(scrape_remotive(limit=100))

    say("📡 Jobicy general…")
    all_jobs.extend(scrape_jobicy(limit=50))

    say("📡 The Muse…")
    all_jobs.extend(scrape_themuse(limit=100))

    say("📂 Local CSV…")
    all_jobs.extend(load_local_csv())

    say("🔧 Deduplicating and saving…")
    n = save_jobs(all_jobs)
    say(f"✅ Done — {n:,} unique jobs in database.")
    return pd.read_csv(str(COMBINED))


# ── Backward-compat alias ─────────────────────────────────────────────────
def get_combined_jobs(*args, **kwargs) -> pd.DataFrame:
    return scrape_and_save()


# ── CLI test ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Targeted test (Python, React) ===")
    jobs = scrape_by_skills(["Python", "React", "SQL"])
    print(f"scrape_by_skills returned {len(jobs)} jobs")
    if jobs:
        for j in jobs[:3]:
            print(f"  [{j['source']}] {j['title']} @ {j['company']} — {j['location']}")

    print("\n=== Full DB build ===")
    df = scrape_and_save(skills=["Python", "React"])
    print(f"Database: {len(df)} rows")
    print(df[["title","company","location","source"]].head(8).to_string())