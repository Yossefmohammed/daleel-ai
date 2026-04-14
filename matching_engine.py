"""
matching_engine.py  –  Career AI  (Stage 1: Deterministic Keyword Scorer)
==========================================================================
Sits between the semantic embeddings (Stage 0) and the Groq LLM (Stage 2).

score_and_rank(jobs, user_profile, location_pref, top_n, source_cap)
  → returns top_n jobs with _engine_score and _matched_skills injected,
    diverse across sources (max source_cap per source).

Scoring breakdown (0-100 scale):
  • Skill match      – up to 50 pts  (weighted by seniority & exact/partial)
  • Role relevance   – up to 20 pts
  • Experience fit   – up to 15 pts
  • Location match   – up to 15 pts  (same boosts/penalties as semantic_matcher)
"""

from __future__ import annotations

import re
from typing import Optional

EGYPT_ALIASES = {"egypt", "cairo", "giza", "alexandria", "مصر", "القاهرة"}

# Seniority keyword sets used to detect job level from description/title
_JUNIOR_KW  = {"junior", "entry", "graduate", "intern", "trainee", "jr"}
_MID_KW     = {"mid", "mid-level", "midlevel", "intermediate"}
_SENIOR_KW  = {"senior", "lead", "staff", "principal", "sr", "sr.", "architect"}


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _blob(job: dict) -> str:
    """Single lowercase string of all searchable job text."""
    return " ".join([
        str(job.get("title",       "") or ""),
        str(job.get("description", "") or ""),
        str(job.get("location",    "") or ""),
        str(job.get("company",     "") or ""),
    ]).lower()


def _skill_score(blob: str, skills: list[str]) -> tuple[float, list[str]]:
    """
    Returns (raw_score 0-1, matched_skill_names).
    Exact whole-word match → 1.0 weight per skill.
    Partial (skill appears as substring) → 0.5 weight.
    Max possible = len(skills).
    """
    if not skills:
        return 0.0, []

    total  = 0.0
    matched: list[str] = []

    for skill in skills:
        s = skill.lower().strip()
        if not s:
            continue
        # Exact word-boundary match
        if re.search(rf"\b{re.escape(s)}\b", blob):
            total += 1.0
            matched.append(skill)
        elif s in blob:  # partial / compound word
            total += 0.5
            matched.append(skill)

    raw = total / len(skills)
    return min(raw, 1.0), matched


def _role_score(blob: str, roles: list[str]) -> float:
    """0-1: fraction of role keywords found in blob."""
    if not roles:
        return 0.0
    hits = 0
    for role in roles:
        for word in role.lower().split():
            if len(word) > 3 and word in blob:
                hits += 1
                break
    return min(hits / len(roles), 1.0)


def _exp_score(blob: str, user_exp: int, seniority: str) -> float:
    """
    Heuristic: penalise if the job's apparent seniority band is far from the user's.
    Returns 0-1.
    """
    job_level = "mid"
    title_desc = blob[:300]
    if any(k in title_desc for k in _SENIOR_KW):
        job_level = "senior"
    elif any(k in title_desc for k in _JUNIOR_KW):
        job_level = "junior"

    user_level = seniority.lower()
    if "senior" in user_level or "lead" in user_level or "principal" in user_level:
        user_band = "senior"
    elif "junior" in user_level or "entry" in user_level or "intern" in user_level:
        user_band = "junior"
    else:
        user_band = "mid"

    if user_band == job_level:
        return 1.0
    # One band away
    if abs(["junior","mid","senior"].index(user_band) -
           ["junior","mid","senior"].index(job_level)) == 1:
        return 0.55
    # Two bands away (junior ↔ senior)
    return 0.15


def _loc_score(job: dict, loc_lower: str) -> float:
    """
    Returns 0-1 representing how well the job location matches the preference.
    Mirrors the v2 boosts in semantic_matcher:
      1.0  → exact local match
      0.55 → remote / worldwide
      0.0  → non-matching physical location
    """
    if not loc_lower:
        return 0.65  # neutral when no preference

    jloc = (job.get("location", "") or "").lower()
    jsrc = (job.get("source",   "") or "").lower()
    is_remote = "remote" in jloc or "worldwide" in jloc

    is_egypt_pref = loc_lower in EGYPT_ALIASES

    if is_egypt_pref:
        if any(a in jloc for a in EGYPT_ALIASES) or jsrc == "wuzzuf":
            return 1.0
        if is_remote:
            return 0.55
        return 0.0
    else:
        if loc_lower in jloc:
            return 1.0
        if is_remote:
            return 0.55
        return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def score_job(
    job: dict,
    user_profile: dict,
    location_pref: str = "",
) -> tuple[float, list[str]]:
    """
    Score a single job against the user profile.

    Returns
    -------
    (engine_score_0_to_100, matched_skills_list)
    """
    skills    = [s.strip() for s in user_profile.get("skills",           []) if s.strip()]
    roles     = [r.strip() for r in user_profile.get("interested_roles", []) if r.strip()]
    exp_years = int(user_profile.get("experience_years", 0) or 0)
    seniority = str(user_profile.get("seniority_level", "mid-level") or "mid-level")
    loc_lower = (location_pref or "").lower().strip()

    blob = _blob(job)

    sk_raw,  matched = _skill_score(blob, skills)
    ro_raw           = _role_score(blob, roles)
    ex_raw           = _exp_score(blob, exp_years, seniority)
    lc_raw           = _loc_score(job, loc_lower)

    # Weighted sum → 0-100
    score = (
        sk_raw * 50 +   # skill match: most important
        ro_raw * 20 +   # role match
        ex_raw * 15 +   # experience / seniority fit
        lc_raw * 15     # location
    )

    return round(score, 2), matched


def score_and_rank(
    jobs: list[dict],
    user_profile: dict,
    location_pref: str = "",
    top_n: int = 30,
    source_cap: int = 6,
) -> list[dict]:
    """
    Score every job, then return the top_n with source diversity.

    Injects into each returned job dict:
      _engine_score   – float 0-100
      _matched_skills – list[str]

    Parameters
    ----------
    jobs          : pre-filtered job list (typically semantic top-100)
    user_profile  : dict with skills, interested_roles, experience_years, seniority_level
    location_pref : plain string e.g. "Egypt", "Remote", "Cairo"
    top_n         : how many to return
    source_cap    : max jobs per source (diversity guard)
    """
    if not jobs:
        return []

    # Score all
    scored: list[tuple[float, list[str], dict]] = []
    for job in jobs:
        s, matched = score_job(job, user_profile, location_pref)
        scored.append((s, matched, job))

    # Sort descending by engine score
    scored.sort(key=lambda x: x[0], reverse=True)

    # Source-diversity pass
    buckets: dict[str, list] = {}
    for s, matched, job in scored:
        src = job.get("source", "Unknown")
        buckets.setdefault(src, [])
        if len(buckets[src]) < source_cap:
            buckets[src].append((s, matched, job))

    diverse: list[dict] = []
    seen:    set         = set()
    per_src  = max(source_cap, top_n // max(len(buckets), 1))

    # Round-robin across sources
    for rnd in range(per_src):
        for src_list in buckets.values():
            if rnd < len(src_list):
                s, matched, job = src_list[rnd]
                key = (
                    str(job.get("title",   ""))[:40].lower(),
                    str(job.get("company", ""))[:30].lower(),
                )
                if key not in seen:
                    seen.add(key)
                    out = dict(job)
                    out["_engine_score"]   = round(s, 2)
                    out["_matched_skills"] = matched
                    diverse.append(out)
            if len(diverse) >= top_n:
                break
        if len(diverse) >= top_n:
            break

    # Fill remainder from global sorted list if needed
    for s, matched, job in scored:
        if len(diverse) >= top_n:
            break
        key = (
            str(job.get("title",   ""))[:40].lower(),
            str(job.get("company", ""))[:30].lower(),
        )
        if key not in seen:
            seen.add(key)
            out = dict(job)
            out["_engine_score"]   = round(s, 2)
            out["_matched_skills"] = matched
            diverse.append(out)

    return diverse[:top_n]


# ─────────────────────────────────────────────────────────────────────────────
# Quick smoke-test
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sample_jobs = [
        {"title": "Senior Python Developer",   "company": "TechCorp",  "description": "Python, FastAPI, PostgreSQL, Docker", "location": "Cairo, Egypt",  "source": "Wuzzuf"},
        {"title": "Junior React Developer",    "company": "StartupEG", "description": "React, JavaScript, CSS, TypeScript",  "location": "Alexandria",    "source": "Wuzzuf"},
        {"title": "ML Engineer",               "company": "OpenAI",    "description": "PyTorch, Python, machine learning",   "location": "Remote",        "source": "RemoteOK"},
        {"title": "Backend Engineer",          "company": "Stripe",    "description": "Python, Go, Kubernetes, AWS",         "location": "New York",      "source": "The Muse"},
        {"title": "Data Scientist",            "company": "Google",    "description": "Python, sklearn, pandas, statistics", "location": "Worldwide",     "source": "Remotive"},
        {"title": "Sales Manager",             "company": "Corp",      "description": "CRM, B2B, targets, negotiation",     "location": "Dubai",         "source": "Jobicy"},
    ]
    profile = {
        "skills":           ["Python", "FastAPI", "PostgreSQL", "Docker"],
        "interested_roles": ["Backend Engineer", "Python Developer"],
        "seniority_level":  "Senior",
        "experience_years": 5,
    }
    print("=== matching_engine smoke test (location=Egypt) ===")
    results = score_and_rank(sample_jobs, profile, location_pref="Egypt", top_n=6)
    for j in results:
        print(f"  [{j['_engine_score']:5.1f}]  {j['title']:<35}  {j['location']:<20}  matched={j['_matched_skills']}")