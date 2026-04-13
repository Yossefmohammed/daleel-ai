"""
job_matcher.py  –  Career AI  (v2 – location-aware + source-diverse)
======================================================================
Fixes vs v1:
  • Candidate selection enforces source diversity (round-robin by source)
    so the AI always sees jobs from ALL scraped sources, not just RemoteOK.
  • Location-aware scoring: jobs matching the user's preferred location
    get a bonus so they rank higher.
  • AI prompt explicitly requests matches from multiple sources/locations.
  • _load_jobs() reads jobs_combined.csv first (populated by data_scraper),
    then falls back to the legacy paths.
"""

import os
import re
import json

import pandas as pd


# ── Groq helpers ──────────────────────────────────────────────────────────────

def _groq_client():
    from groq import Groq
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise ValueError("GROQ_API_KEY not set")
    return Groq(api_key=key)


def _call_llm(client, prompt: str, max_tokens: int = 1500) -> str:
    for model in ["llama-3.3-70b-versatile", "gemma2-9b-it"]:
        try:
            r = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=max_tokens,
            )
            return r.choices[0].message.content
        except Exception:
            continue
    raise RuntimeError("All Groq models failed.")


def _parse_json(text: str):
    text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for pat in [r"\[.*\]", r"\{.*\}"]:
        m = re.search(pat, text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except Exception:
                pass
    return []


# ── CSV column normaliser ─────────────────────────────────────────────────────

_COL_MAP = {
    "job_title": "title",        "title": "title",
    "position": "title",         "job_position": "title",     "role": "title",
    "company_name": "company",   "company": "company",        "employer": "company",
    "job_description": "description", "description": "description",
    "responsibilities": "description", "details": "description",
    "location": "location",      "job_location": "location",  "city": "location",
    "salary": "salary",          "salary_in_usd": "salary",
    "salary_estimate": "salary", "avg_salary": "salary",
    "experience_level": "level", "seniority_level": "level",  "level": "level",
    "employment_type": "type",
}


def _normalise(df: pd.DataFrame) -> pd.DataFrame:
    rename = {}
    for col in df.columns:
        low = col.lower().strip()
        if low in _COL_MAP and _COL_MAP[low] not in df.columns:
            rename[col] = _COL_MAP[low]
    return df.rename(columns=rename)


# ── Scoring helpers ───────────────────────────────────────────────────────────

def _score_row(row_text: str, skills: list[str], roles: list[str],
               location_pref: str = "") -> int:
    """
    Keyword match score.
      +2  per matching skill
      +1  per matching word from a desired role title
      +3  if the job location matches the preferred location   ← NEW
    """
    text = row_text.lower()
    score = 0

    for s in skills:
        if s.lower() in text:
            score += 2

    for r in roles:
        for word in r.lower().split():
            if len(word) > 3 and word in text:
                score += 1

    if location_pref:
        loc_lower = location_pref.lower()
        # Common Egypt synonyms
        egypt_aliases = {"egypt", "cairo", "giza", "alexandria", "مصر", "القاهرة"}
        if loc_lower in egypt_aliases:
            # Give bonus to any Egypt-located job
            if any(alias in text for alias in egypt_aliases):
                score += 3
        elif loc_lower in text:
            score += 3

    return score


def _diverse_candidates(
    jobs: list[dict],
    skills: list[str],
    roles: list[str],
    location_pref: str = "",
    n: int = 30,
) -> list[dict]:
    """
    Build a candidate shortlist that:
      1. Scores every job by skill/role/location relevance
      2. Picks the top-N/sources jobs from each source (round-robin)
         so the AI always sees multiple sources
      3. Back-fills with top-scored jobs if any source has fewer jobs

    This prevents RemoteOK (or any single source) from filling all 25 slots.
    """
    # Score all
    for j in jobs:
        blob  = (str(j.get("title", "")) + " " + str(j.get("description", ""))).lower()
        j["_score"] = _score_row(blob, skills, roles, location_pref)

    scored = sorted(jobs, key=lambda x: x.get("_score", 0), reverse=True)

    # Bucket by source
    buckets: dict[str, list] = {}
    for j in scored:
        src = j.get("source", "Unknown")
        buckets.setdefault(src, [])
        buckets[src].append(j)

    num_sources = max(len(buckets), 1)
    per_source  = max(3, n // num_sources)

    # Round-robin selection
    diverse: list[dict] = []
    seen: set            = set()
    max_rounds           = per_source

    for rnd in range(max_rounds):
        for src_jobs in buckets.values():
            if rnd < len(src_jobs):
                j = src_jobs[rnd]
                k = (j.get("title", "")[:40].lower(), j.get("company", "")[:30].lower())
                if k not in seen:
                    seen.add(k)
                    diverse.append(j)
                if len(diverse) >= n:
                    break
        if len(diverse) >= n:
            break

    # Back-fill from top-scored if we're short
    for j in scored:
        if len(diverse) >= n:
            break
        k = (j.get("title", "")[:40].lower(), j.get("company", "")[:30].lower())
        if k not in seen:
            seen.add(k)
            diverse.append(j)

    # Clean internal score field before returning
    for j in diverse:
        j.pop("_score", None)

    return diverse[:n]


# ── CSV loader ────────────────────────────────────────────────────────────────

def _load_jobs(limit: int = 2000) -> pd.DataFrame | None:
    # Prefer the live-scraped combined DB; fall back to legacy paths
    paths = [
        "data/jobs_combined.csv",
        "data/jobs.csv",
        "docs/ai_jobs_market_2025_2026.csv",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                df = pd.read_csv(p, nrows=limit, on_bad_lines="skip")
                df = _normalise(df)
                df = df.fillna("")
                return df
            except Exception as e:
                print(f"Warning loading {p}: {e}")
    return None


# ── Main class ────────────────────────────────────────────────────────────────

class JobMatcher:
    def __init__(self):
        self.client = _groq_client()

    def match_jobs(
        self,
        user_profile: dict,
        limit: int = 8,
        location_pref: str = "",
    ) -> dict:
        """
        Parameters
        ----------
        user_profile  : dict with keys skills, interested_roles, seniority_level,
                        experience_years
        limit         : how many matches to return
        location_pref : e.g. "Egypt", "Cairo", "Remote"  (new in v2)
        """
        df = _load_jobs()
        if df is None or df.empty:
            return {
                "success": False,
                "error": (
                    "Job database not found. "
                    "Download a Kaggle dataset and save it as data/jobs.csv"
                ),
            }

        skills     = user_profile.get("skills", [])
        roles      = user_profile.get("interested_roles", [])
        seniority  = user_profile.get("seniority_level", "")
        exp_years  = user_profile.get("experience_years", 0)

        text_cols = [c for c in ["title", "description", "company", "location", "level"]
                     if c in df.columns] or list(df.columns)

        df["_combined"] = df[text_cols].astype(str).agg(" ".join, axis=1)
        all_jobs = df.to_dict("records")

        # Source-diverse candidate selection (the key fix)
        candidates = _diverse_candidates(
            all_jobs, skills, roles, location_pref=location_pref, n=30
        )

        # Build compact payload for the LLM
        job_list = []
        for row in candidates:
            entry = {}
            for field in ["title", "company", "location", "level", "type",
                          "salary", "description", "source"]:
                if field in row and str(row[field]).strip():
                    val = str(row[field])
                    entry[field] = val[:200] if field == "description" else val
            job_list.append(entry)

        # Summarise sources present for the AI to know variety is available
        sources_present = sorted({j.get("source", "?") for j in job_list})

        prompt = f"""You are a career advisor. Given the user profile and job listings,
return ONLY a valid JSON array (no markdown, no explanation) of the top {limit} best-matching jobs.

IMPORTANT:
- Try to recommend jobs from DIFFERENT sources/companies when possible.
- If the user prefers a specific location ({location_pref or 'not specified'}), 
  prioritise jobs in or near that location, but also include relevant remote options.
- Sources available in this list: {', '.join(sources_present)}

Each object must have exactly these keys:
{{
  "title": "job title",
  "company": "company name",
  "location": "city, country or Remote",
  "source": "source website name",
  "match_score": <integer 0-100>,
  "matched_skills": ["skill1", "skill2"],
  "missing_skills": ["skill1"],
  "why_good_fit": "one or two sentences explaining the match",
  "salary": "salary info or N/A",
  "url": "application URL"
}}

User profile:
- Skills: {', '.join(skills)}
- Experience: {exp_years} years
- Seniority: {seniority}
- Interested roles: {', '.join(roles) if roles else 'any'}
- Preferred location: {location_pref or 'open to remote and on-site'}

Job listings (from {len(job_list)} pre-screened candidates across {len(sources_present)} sources):
{json.dumps(job_list, indent=2)[:4500]}

Return ONLY the JSON array.
"""

        try:
            raw     = _call_llm(self.client, prompt)
            matches = _parse_json(raw)

            if isinstance(matches, dict) and "jobs" in matches:
                matches = matches["jobs"]
            if not isinstance(matches, list):
                matches = []

            return {
                "success":              True,
                "matches":              matches,
                "total_in_db":          len(df),
                "candidates_evaluated": len(job_list),
                "sources_in_candidates": sources_present,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def explain_gap(self, user_skills: list, job: dict) -> dict:
        prompt = f"""You are a career advisor. Analyse the skill gap.

User skills: {', '.join(user_skills)}

Target job: {json.dumps(job)}

Return ONLY a valid JSON object:
{{
  "matching_skills": ["..."],
  "missing_skills": ["..."],
  "learning_path": ["step 1", "step 2"],
  "time_to_readiness": "e.g. 3 months",
  "resources": ["course or resource 1", "resource 2"]
}}
"""
        try:
            raw = _call_llm(self.client, prompt, max_tokens=800)
            return {"success": True, "gap_analysis": _parse_json(raw)}
        except Exception as e:
            return {"success": False, "error": str(e)}