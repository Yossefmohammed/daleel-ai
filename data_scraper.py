"""
data_scraper.py  –  updated
============================
Key change: scrape_by_skills(skills, limit) lets the app pass user skills
as RemoteOK keyword queries, so scraped jobs are targeted to the user.
Still falls back gracefully if scraping fails.
"""

import requests
import pandas as pd
from datetime import datetime
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
COMBINED = DATA_DIR / "jobs_combined.csv"


# ── Normalise any CSV into standard columns ────────────────────────────────
COL_MAP = {
    "job_title":          "title",
    "position":           "title",
    "role":               "title",
    "company_name":       "company",
    "employer":           "company",
    "job_description":    "description",
    "responsibilities":   "description",
    "required_skills":    "description",   # kaggle column
    "job_location":       "location",
    "city":               "location",
    "salary_in_usd":      "salary",
    "salary_estimate":    "salary",
    "annual_salary_usd":  "salary",
    "avg_salary":         "salary",
    "salary_range":       "salary",
}


def _normalise(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.lower().strip() for c in df.columns]
    return df.rename(columns={k: v for k, v in COL_MAP.items()
                               if k in df.columns and v not in df.columns})


def _to_standard(jobs: list) -> list:
    """Ensure every job dict has title/company/description/location/salary/url/source."""
    out = []
    for j in jobs:
        out.append({
            "title":       str(j.get("title","") or j.get("job_title",""))[:100],
            "company":     str(j.get("company","") or j.get("company_name",""))[:80],
            "description": str(j.get("description",""))[:400],
            "location":    str(j.get("location","") or j.get("city","") or "Remote")[:60],
            "salary":      str(j.get("salary","") or j.get("salary_range","") or "")[:40],
            "url":         str(j.get("url",""))[:200],
            "source":      str(j.get("source","Unknown")),
        })
    return out


# ── RemoteOK ───────────────────────────────────────────────────────────────
def scrape_remoteok(keywords: str = "", limit: int = 150) -> list:
    """
    Scrape RemoteOK.  Pass skill keywords to search for targeted jobs.
    keywords can be a single skill like "python" or comma-joined "python,react".
    """
    try:
        params = {}
        if keywords:
            params["tags"] = keywords.lower()
        r = requests.get(
            "https://remoteok.com/api",
            params=params,
            headers={"User-Agent": "CareerAI/1.0"},
            timeout=14,
        )
        r.raise_for_status()
        jobs = []
        for j in r.json()[:limit]:
            if not isinstance(j, dict) or "id" not in j:
                continue
            tags = j.get("tags", [])
            desc = j.get("description", "") or (", ".join(tags) if tags else "")
            jobs.append({
                "title":       j.get("position") or j.get("title", ""),
                "company":     j.get("company", ""),
                "description": str(desc)[:400],
                "location":    j.get("location", "Remote"),
                "salary":      str(j.get("salary", "")),
                "url":         j.get("url", ""),
                "source":      "RemoteOK",
            })
        logger.info(f"RemoteOK: {len(jobs)} jobs (keywords={keywords!r})")
        return jobs
    except Exception as e:
        logger.warning(f"RemoteOK failed: {e}")
        return []


# ── Arbeitnow ─────────────────────────────────────────────────────────────
def scrape_arbeitnow(limit: int = 150) -> list:
    jobs = []
    try:
        for page in range(1, 4):
            r = requests.get(
                "https://www.arbeitnow.com/api/job-board-api",
                params={"page": page},
                headers={"Accept": "application/json"},
                timeout=14,
            )
            r.raise_for_status()
            data = r.json().get("data", [])
            if not data:
                break
            for j in data:
                jobs.append({
                    "title":       j.get("title", ""),
                    "company":     j.get("company_name", ""),
                    "description": str(j.get("description") or "")[:400],
                    "location":    j.get("location", ""),
                    "salary":      "",
                    "url":         j.get("url", ""),
                    "source":      "Arbeitnow",
                })
            if len(jobs) >= limit:
                break
        logger.info(f"Arbeitnow: {len(jobs)} jobs")
        return jobs[:limit]
    except Exception as e:
        logger.warning(f"Arbeitnow failed: {e}")
        return []


# ── Local Kaggle CSV ───────────────────────────────────────────────────────
def load_local_csv() -> list:
    candidates = [
        DATA_DIR / "jobs.csv",
        Path("docs") / "ai_jobs_market_2025_2026.csv",
    ] + list(Path("docs").glob("*.csv"))

    for p in candidates:
        if not p.exists():
            continue
        try:
            df = pd.read_csv(str(p), on_bad_lines="skip", nrows=2000)
            df = _normalise(df).fillna("")
            for col in ["title", "company", "description", "location", "salary"]:
                if col not in df.columns:
                    df[col] = ""
            df["source"] = "Local CSV"
            df["url"] = ""
            records = df[["title","company","description","location",
                           "salary","url","source"]].to_dict("records")
            logger.info(f"Local CSV: {len(records)} jobs from {p.name}")
            return records
        except Exception as e:
            logger.warning(f"Local CSV {p}: {e}")
    return []


# ── Dedup + save ──────────────────────────────────────────────────────────
def _dedup(jobs: list) -> list:
    seen, unique = set(), []
    for j in jobs:
        k = (str(j.get("title","")).lower()[:40],
             str(j.get("company","")).lower()[:30])
        if k not in seen:
            seen.add(k)
            unique.append(j)
    return unique

def save_jobs(jobs: list) -> int:
    DATA_DIR.mkdir(exist_ok=True)
    unique = _dedup(jobs)
    pd.DataFrame(unique).to_csv(str(COMBINED), index=False)
    logger.info(f"Saved {len(unique)} unique jobs to {COMBINED}")
    return len(unique)


# ══════════════════════════════════════════════════════════════════════════════
# Public API used by app.py
# ══════════════════════════════════════════════════════════════════════════════
def scrape_and_save(skills: list = None, status_ph=None) -> pd.DataFrame:
    """
    Main entry point.

    Parameters
    ----------
    skills : list of str, optional
        User skills from CV analysis.  When provided, RemoteOK is queried with
        each skill as a keyword so results are relevant to this specific user.
    status_ph : streamlit placeholder, optional
        If provided, progress messages are sent here.

    Returns
    -------
    pd.DataFrame  –  the combined job dataset.
    """
    def say(m):
        if status_ph:
            status_ph.info(m)
        logger.info(m)

    all_jobs = []

    if skills:
        say(f"📡 Scraping RemoteOK for your skills: {', '.join(skills[:4])}…")
        for sk in skills[:4]:
            all_jobs.extend(scrape_remoteok(keywords=sk, limit=60))
        # combined query
        all_jobs.extend(scrape_remoteok(keywords=",".join(skills[:4]), limit=80))
    else:
        say("📡 Scraping RemoteOK (general search)…")
        all_jobs.extend(scrape_remoteok(limit=150))

    say(f"✅ RemoteOK done ({len(all_jobs)} so far). Fetching Arbeitnow…")
    all_jobs.extend(scrape_arbeitnow())
    say(f"✅ Arbeitnow done. Loading local CSV…")
    all_jobs.extend(load_local_csv())

    all_jobs = _to_standard(all_jobs)
    n = save_jobs(all_jobs)
    say(f"✅ Database built — {n:,} unique jobs saved.")
    return pd.read_csv(str(COMBINED))


# ── Legacy compat (old app.py called get_combined_jobs) ───────────────────
def get_combined_jobs(kaggle_path: str = "docs/ai_jobs_market_2025_2026.csv",
                      output_path: str = "data/jobs_combined.csv") -> pd.DataFrame:
    """Backward-compatible wrapper."""
    return scrape_and_save()


if __name__ == "__main__":
    df = scrape_and_save()
    print(f"Total jobs: {len(df)}")
    print(df[["title","company","location","source"]].head(10).to_string())