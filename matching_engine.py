"""
matching_engine.py  –  Career AI  (Stage 1: Deterministic Keyword Scorer - FIXED)
=================================================================================
"""

from __future__ import annotations

import re

EGYPT_ALIASES = {"egypt", "cairo", "giza", "alexandria", "مصر", "القاهرة"}

# ─────────────────────────────────────────────────────────────────────────────
# Skill aliases (FIX #1)
# ─────────────────────────────────────────────────────────────────────────────

SKILL_ALIASES = {
    "python": ["python", "python3", "py"],
    "c++": ["c++", "cpp"],
    "sql": ["sql", "mysql", "postgresql", "mssql", "sql server"],
    "machine learning": ["machine learning", "ml"],
    "deep learning": ["deep learning", "dl"],
    "object detection": ["object detection", "yolo", "detection"],
    "data cleaning": ["data cleaning", "data preprocessing"],
}

# Seniority keywords
_JUNIOR_KW  = {"junior", "entry", "graduate", "intern", "trainee", "jr"}
_SENIOR_KW  = {"senior", "lead", "staff", "principal", "sr", "sr.", "architect"}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _blob(job: dict) -> str:
    return " ".join([
        str(job.get("title", "")),
        str(job.get("description", "")),
        str(job.get("location", "")),
        str(job.get("company", "")),
    ]).lower()


# ─────────────────────────────────────────────────────────────────────────────
# Skill matching (FIXED)
# ─────────────────────────────────────────────────────────────────────────────

def _match_skill(blob: str, skill: str) -> float:
    s = skill.lower().strip()
    if not s:
        return 0.0

    aliases = SKILL_ALIASES.get(s, [s])

    for alias in aliases:
        # strong exact match
        if re.search(rf"\b{re.escape(alias)}\b", blob):
            if s == "python":
                return 2.0  # boost Python
            return 1.5

        # partial match
        if alias in blob:
            return 0.75

    return 0.0


def _skill_score(blob: str, skills: list[str]) -> tuple[float, list[str]]:
    if not skills:
        return 0.0, []

    total = 0.0
    matched = []

    for skill in skills:
        score = _match_skill(blob, skill)
        if score > 0:
            total += score
            matched.append(skill)

    # FIX #2: prevent dilution
    norm = max(min(len(skills), 10), 1)
    raw = total / norm

    return min(raw, 1.0), matched


# ─────────────────────────────────────────────────────────────────────────────
# Other scoring
# ─────────────────────────────────────────────────────────────────────────────

def _role_score(blob: str, roles: list[str]) -> float:
    if not roles:
        return 0.0

    hits = 0
    for role in roles:
        for word in role.lower().split():
            if len(word) > 3 and word in blob:
                hits += 1
                break

    return min(hits / len(roles), 1.0)


def _exp_score(blob: str, seniority: str) -> float:
    job_level = "mid"
    text = blob[:300]

    if any(k in text for k in _SENIOR_KW):
        job_level = "senior"
    elif any(k in text for k in _JUNIOR_KW):
        job_level = "junior"

    user_level = seniority.lower()

    if "senior" in user_level:
        user_band = "senior"
    elif "junior" in user_level:
        user_band = "junior"
    else:
        user_band = "mid"

    levels = ["junior", "mid", "senior"]

    if user_band == job_level:
        return 1.0

    if abs(levels.index(user_band) - levels.index(job_level)) == 1:
        return 0.55

    return 0.15


def _loc_score(job: dict, loc_lower: str) -> float:
    if not loc_lower:
        return 0.65

    jloc = (job.get("location", "") or "").lower()
    jsrc = (job.get("source", "") or "").lower()
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
# Main scoring
# ─────────────────────────────────────────────────────────────────────────────

def score_job(job: dict, user_profile: dict, location_pref: str = ""):
    skills    = [s.strip() for s in user_profile.get("skills", []) if s.strip()]
    roles     = [r.strip() for r in user_profile.get("interested_roles", []) if r.strip()]
    seniority = str(user_profile.get("seniority_level", "mid-level"))

    blob = _blob(job)

    sk_raw, matched = _skill_score(blob, skills)
    missing = [s for s in skills if s not in matched]  # FIX #3

    ro_raw = _role_score(blob, roles)
    ex_raw = _exp_score(blob, seniority)
    lc_raw = _loc_score(job, location_pref.lower())

    score = (
        sk_raw * 50 +
        ro_raw * 20 +
        ex_raw * 15 +
        lc_raw * 15
    )

    return round(score, 2), matched, missing


# ─────────────────────────────────────────────────────────────────────────────
# Ranking
# ─────────────────────────────────────────────────────────────────────────────

def score_and_rank(
    jobs: list[dict],
    user_profile: dict,
    location_pref: str = "",
    top_n: int = 30,
    source_cap: int = 6,
) -> list[dict]:

    if not jobs:
        return []

    scored = []

    for job in jobs:
        s, matched, missing = score_job(job, user_profile, location_pref)
        scored.append((s, matched, missing, job))

    scored.sort(key=lambda x: x[0], reverse=True)

    buckets = {}
    for s, matched, missing, job in scored:
        src = job.get("source", "Unknown")
        buckets.setdefault(src, [])
        if len(buckets[src]) < source_cap:
            buckets[src].append((s, matched, missing, job))

    diverse = []
    seen = set()

    for rnd in range(source_cap):
        for src_list in buckets.values():
            if rnd < len(src_list):
                s, matched, missing, job = src_list[rnd]

                key = (
                    job.get("title", "").lower()[:40],
                    job.get("company", "").lower()[:30],
                )

                if key not in seen:
                    seen.add(key)

                    out = dict(job)
                    out["_engine_score"] = s
                    out["_matched_skills"] = matched
                    out["_missing_skills"] = missing

                    diverse.append(out)

            if len(diverse) >= top_n:
                break

    return diverse[:top_n]