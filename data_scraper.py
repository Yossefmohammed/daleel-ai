"""
data_scraper.py  –  Career AI  (v4 – location-aware across ALL sources)
========================================================================
Fix vs v3:
  • scrape_by_skills() now passes location context to EVERY source, not just Wuzzuf.
  • New _scrape_remotive_located() helper uses Remotive's search param with location.
  • Arbeitnow and Himalayas receive location-enriched keyword strings.
  • Location penalty applied at save time: non-matching physical jobs ranked lower.

Sources:
  1. RemoteOK      – remote tech jobs        (free JSON API, no key)
  2. Arbeitnow     – European + remote jobs  (free JSON API, no key)
  3. The Muse      – culture-first jobs      (free JSON API, no key)
  4. Remotive      – remote-only jobs        (free JSON API, no key)
  5. Jobicy        – broad tech jobs         (free JSON API, no key)
  6. Wuzzuf        – Egypt + MENA jobs       (RSS feed, no key)
  7. Himalayas     – remote tech jobs        (free JSON API, no key)
  8. Local CSV     – any CSV in data/ or docs/
"""

from __future__ import annotations

import re
import time
import logging
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger("data_scraper")

DATA_DIR = Path("data")
COMBINED = DATA_DIR / "jobs_combined.csv"

_UA = {
    "User-Agent": "CareerAI/4.0 (+github.com/Yossefmohammed/wasla-chatbot)",
    "Accept":     "application/json",
}
_UA_RSS = {
    "User-Agent": "CareerAI/4.0 (+github.com/Yossefmohammed/wasla-chatbot)",
    "Accept":     "application/rss+xml, application/xml, text/xml",
}

COL_MAP = {
    "job_title": "title", "position": "title", "role": "title",
    "company_name": "company", "employer": "company",
    "job_description": "description", "responsibilities": "description",
    "required_skills": "description",
    "job_location": "location", "city": "location",
    "salary_in_usd": "salary", "salary_estimate": "salary",
    "annual_salary_usd": "salary", "avg_salary": "salary", "salary_range": "salary",
}

EGYPT_ALIASES = {"egypt", "cairo", "giza", "alexandria", "مصر", "القاهرة"}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", str(text or "")).strip()


def _norm(j: dict) -> dict:
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


def _ensure_source_diversity(jobs: list, max_per_source: int = 120) -> list:
    buckets: dict[str, list] = {}
    for j in jobs:
        src = j.get("source", "Unknown")
        buckets.setdefault(src, [])
        if len(buckets[src]) < max_per_source:
            buckets[src].append(j)

    combined, max_len = [], max((len(v) for v in buckets.values()), default=0)
    sources_list = list(buckets.values())
    for i in range(max_len):
        for src_jobs in sources_list:
            if i < len(src_jobs):
                combined.append(src_jobs[i])
    return combined


# ══════════════════════════════════════════════════════════════════════════════
# Source 1 – RemoteOK
# ══════════════════════════════════════════════════════════════════════════════
def scrape_remoteok(keywords: str = "", limit: int = 100) -> list:
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
def scrape_arbeitnow(keywords: str = "", limit: int = 150) -> list:
    jobs = []
    try:
        for page in range(1, 5):
            params: dict = {"page": page}
            if keywords:
                params["search"] = keywords
            r = requests.get(
                "https://www.arbeitnow.com/api/job-board-api",
                params=params, headers=_UA, timeout=15)
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
        logger.info(f"Arbeitnow      → {len(jobs):>4} jobs  (kw={keywords!r})")
        return jobs[:limit]
    except Exception as e:
        logger.warning(f"Arbeitnow failed: {e}")
        return []


# ══════════════════════════════════════════════════════════════════════════════
# Source 3 – The Muse
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
                locs   = item.get("locations", [])
                loc    = ", ".join(l.get("name", "") for l in locs) or "Remote"
                levels = item.get("levels", [])
                lvl    = ", ".join(l.get("name", "") for l in levels)
                desc   = _strip_html(item.get("contents", ""))
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
# Source 4 – Remotive  (standard + location-aware variant)
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
    return _scrape_remotive_located(keywords=keywords, location="", limit=limit)


def _scrape_remotive_located(keywords: str = "", location: str = "", limit: int = 100) -> list:
    """
    Remotive with optional location filter.
    Remotive's /api/remote-jobs supports a free-text 'search' param —
    appending the location city/country nudges results toward that area.
    """
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
        search = f"{keywords} {location}".strip() if location else keywords
        if search:
            params["search"] = search
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
        logger.info(f"Remotive       → {len(jobs):>4} jobs  (kw={keywords!r}, loc={location!r})")
        return jobs
    except Exception as e:
        logger.warning(f"Remotive failed: {e}")
        return []


# ══════════════════════════════════════════════════════════════════════════════
# Source 5 – Jobicy
# ══════════════════════════════════════════════════════════════════════════════
def scrape_jobicy(keywords: str = "", limit: int = 50) -> list:
    try:
        params = {"count": min(limit, 50), "geo": "worldwide"}
        if keywords:
            params["tag"] = keywords.split(",")[0].strip().lower()
        r = requests.get("https://jobicy.com/api/v2/remote-jobs",
                         params=params, headers=_UA, timeout=15)
        r.raise_for_status()
        items = r.json().get("jobs", [])
        jobs = []
        for j in items:
            desc = _strip_html(j.get("jobDescription", ""))
            lo = j.get("annualSalaryMin", "")
            hi = j.get("annualSalaryMax", "")
            salary = f"${lo}–${hi}" if (lo and hi) else (f"${lo or hi}" if (lo or hi) else "")
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
# Source 6 – Wuzzuf  (Egypt + MENA — RSS feed)
# ══════════════════════════════════════════════════════════════════════════════
def scrape_wuzzuf(keywords: str = "", location: str = "Egypt", limit: int = 60) -> list:
    try:
        params: dict = {}
        if keywords:
            params["q"] = keywords
        if location and location.lower() not in ("remote", "worldwide", ""):
            params["l"] = location

        r = requests.get(
            "https://wuzzuf.net/search/jobs/rss",
            params=params, headers=_UA_RSS, timeout=18,
        )
        r.raise_for_status()

        root = ET.fromstring(r.content)
        jobs = []

        for item in root.findall(".//item")[:limit]:
            title_raw = (item.findtext("title") or "").strip()
            link      = (item.findtext("link")  or "").strip()
            desc_raw  = (item.findtext("description") or "")

            company, loc = "", location or "Egypt"
            if " at " in title_raw:
                head, tail = title_raw.split(" at ", 1)
                title_raw  = head.strip()
                if " – " in tail:
                    company, loc = [p.strip() for p in tail.split(" – ", 1)]
                elif " - " in tail:
                    company, loc = [p.strip() for p in tail.split(" - ", 1)]
                else:
                    company = tail.strip()

            jobs.append(_norm({
                "title":       title_raw,
                "company":     company,
                "description": _strip_html(desc_raw)[:500],
                "location":    loc,
                "salary":      "",
                "url":         link,
                "source":      "Wuzzuf",
            }))

        logger.info(f"Wuzzuf         → {len(jobs):>4} jobs  (kw={keywords!r}, loc={location!r})")
        return jobs

    except ET.ParseError as e:
        logger.warning(f"Wuzzuf RSS parse error: {e}")
        return []
    except Exception as e:
        logger.warning(f"Wuzzuf failed: {e}")
        return []


# ══════════════════════════════════════════════════════════════════════════════
# Source 7 – Himalayas
# ══════════════════════════════════════════════════════════════════════════════
def scrape_himalayas(keywords: str = "", limit: int = 50) -> list:
    """
    Himalayas.app free public API.
    The 'q' param accepts free text — appending location to keywords
    surfaces jobs that mention that region in their description.
    """
    try:
        params: dict = {"limit": min(limit, 100)}
        if keywords:
            params["q"] = keywords
        r = requests.get(
            "https://himalayas.app/jobs/api",
            params=params, headers=_UA, timeout=15,
        )
        r.raise_for_status()
        items = r.json().get("jobs", [])
        jobs = []
        for j in items[:limit]:
            salary = ""
            lo = j.get("salaryMin", "")
            hi = j.get("salaryMax", "")
            cur = j.get("salaryCurrency", "USD")
            if lo or hi:
                salary = f"{cur} {lo}–{hi}" if (lo and hi) else f"{cur} {lo or hi}"

            reqs = j.get("requirements", [])
            desc = _strip_html(j.get("description", ""))
            if reqs:
                desc = "Requirements: " + "; ".join(reqs[:5]) + ". " + desc

            jobs.append(_norm({
                "title":       j.get("title", ""),
                "company":     j.get("companyName", ""),
                "description": desc[:500],
                "location":    j.get("locationRestrictions") or j.get("location", "Remote"),
                "salary":      salary,
                "url":         j.get("applicationLink", "") or j.get("url", ""),
                "source":      "Himalayas",
            }))
        logger.info(f"Himalayas      → {len(jobs):>4} jobs  (kw={keywords!r})")
        return jobs
    except Exception as e:
        logger.warning(f"Himalayas failed: {e}")
        return []


# ══════════════════════════════════════════════════════════════════════════════
# Source 8 – Local CSV
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
            df = df.rename(columns={k: v for k, v in COL_MAP.items()
                                     if k in df.columns and v not in df.columns})
            df = df.fillna("")
            for col in ["title", "company", "description", "location", "salary"]:
                if col not in df.columns:
                    df[col] = ""
            df["source"] = "Local CSV"
            df["url"]    = ""
            records = df[["title", "company", "description", "location",
                           "salary", "url", "source"]].to_dict("records")
            logger.info(f"Local CSV      → {len(records):>4} jobs  ({p.name})")
            return [_norm(r) for r in records]
        except Exception as e:
            logger.warning(f"Local CSV {p}: {e}")
    return []


# ══════════════════════════════════════════════════════════════════════════════
# Persist / load
# ══════════════════════════════════════════════════════════════════════════════
def save_jobs(jobs: list) -> int:
    DATA_DIR.mkdir(exist_ok=True)
    normalised = [_norm(j) for j in jobs]

    if COMBINED.exists():
        try:
            existing = pd.read_csv(str(COMBINED), on_bad_lines="skip").fillna("").to_dict("records")
            normalised = existing + normalised
        except Exception:
            pass

    deduped   = _dedup(normalised)
    balanced  = _ensure_source_diversity(deduped, max_per_source=150)
    pd.DataFrame(balanced).to_csv(str(COMBINED), index=False)
    logger.info(f"Saved {len(balanced):,} unique jobs → {COMBINED}")
    return len(balanced)


def load_combined() -> list:
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
def scrape_by_skills(
    skills: list,
    limit: int   = 60,
    location: str = "",
) -> list:
    """
    Balanced multi-source scrape based on user skills + location.

    location is now passed to ALL sources that support text search,
    not only to Wuzzuf.  This ensures the raw candidate pool already contains
    location-relevant jobs before the scoring/LLM stages run.

    Strategy:
      • location is appended to keyword strings for text-search APIs
        (Arbeitnow, Himalayas, Remotive) so their results skew local.
      • Wuzzuf is always queried with location=Egypt plus any specific city.
      • RemoteOK / The Muse / Jobicy don't support location params but are
        still included for remote-friendly roles.
    """
    if not skills:
        return []

    all_jobs: list = []
    top_skills     = skills[:5]
    combined_kw    = ",".join(s.lower() for s in top_skills[:3])
    search_str     = " ".join(top_skills[:3])

    is_local = location and location.lower() not in ("remote", "worldwide", "")

    location_kw = f"{search_str} {location}".strip() if is_local else search_str

    # ── 1. RemoteOK ───────────────────────────────────────────────────────
    all_jobs.extend(scrape_remoteok(keywords=combined_kw, limit=limit))
    time.sleep(0.4)

    # ── 2. Remotive ───────────────────────────────────────────────────────
    all_jobs.extend(_scrape_remotive_located(
        keywords=search_str,
        location=location if is_local else "",
        limit=limit,
    ))
    time.sleep(0.3)

    # ── 3. Jobicy ─────────────────────────────────────────────────────────
    all_jobs.extend(scrape_jobicy(keywords=top_skills[0], limit=limit))
    time.sleep(0.3)

    # ── 4. The Muse ───────────────────────────────────────────────────────
    all_jobs.extend(scrape_themuse(keywords=search_str, limit=limit))
    time.sleep(0.3)

    # ── 5. Arbeitnow ─────────────────────────────────────────────────────
    all_jobs.extend(scrape_arbeitnow(keywords=location_kw, limit=limit))
    time.sleep(0.3)

    # ── 6. Himalayas ─────────────────────────────────────────────────────
    all_jobs.extend(scrape_himalayas(keywords=location_kw, limit=limit))
    time.sleep(0.3)

    # ── 7. Wuzzuf (Egypt always, plus specific city if given) ─────────────
    all_jobs.extend(scrape_wuzzuf(keywords=search_str, location="Egypt", limit=limit))
    time.sleep(0.3)
    if is_local and location.lower() not in EGYPT_ALIASES:
        all_jobs.extend(
            scrape_wuzzuf(keywords=search_str, location=location, limit=limit // 2)
        )
        time.sleep(0.2)

    deduped = _dedup([_norm(j) for j in all_jobs])
    by_src: dict[str, int] = {}
    for j in deduped:
        by_src[j.get("source", "?")] = by_src.get(j.get("source", "?"), 0) + 1
    logger.info(
        f"scrape_by_skills → {len(deduped)} unique jobs | "
        + " | ".join(f"{s}:{n}" for s, n in sorted(by_src.items()))
    )
    return deduped


def scrape_and_save(skills: list = None, status_ph=None) -> pd.DataFrame:
    def say(msg: str):
        logger.info(msg)
        if status_ph:
            status_ph.info(msg)

    all_jobs: list = []

    if skills:
        say(f"🎯 Targeted scrape for: {', '.join(skills[:5])}")
        all_jobs.extend(scrape_by_skills(skills))

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

    say("📡 Himalayas…")
    all_jobs.extend(scrape_himalayas(limit=80))

    say("🌍 Wuzzuf (Egypt)…")
    all_jobs.extend(scrape_wuzzuf(limit=100))

    say("📂 Local CSV…")
    all_jobs.extend(load_local_csv())

    say("🔧 Balancing sources and saving…")
    n = save_jobs(all_jobs)
    say(f"✅ Done — {n:,} unique jobs in database.")
    return pd.read_csv(str(COMBINED))


def get_combined_jobs(*args, **kwargs) -> pd.DataFrame:
    return scrape_and_save()


def source_counts() -> dict[str, int]:
    jobs = load_combined()
    counts: dict[str, int] = {}
    for j in jobs:
        src = j.get("source", "Unknown")
        counts[src] = counts.get(src, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: -x[1]))


if __name__ == "__main__":
    print("=== Targeted test (Python, React) with location=Egypt ===")
    jobs = scrape_by_skills(["Python", "React", "SQL"], location="Egypt")
    print(f"scrape_by_skills returned {len(jobs)} jobs")
    by_src: dict[str, int] = {}
    for j in jobs:
        by_src[j["source"]] = by_src.get(j["source"], 0) + 1
    print("Source breakdown:", dict(sorted(by_src.items(), key=lambda x: -x[1])))
    for j in jobs[:5]:
        print(f"  [{j['source']:10}] {j['title'][:45]} @ {j['company'][:25]} — {j['location']} — {j['url'][:60]}")