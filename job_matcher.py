"""
job_matcher.py  –  Career AI  (v5 – synonym-aware LLM prompts)
================================================================
Fixes:
  - LLM now knows skill aliases (imported from matching_engine)
  - Prompt instructs to treat "NLP" = "Natural Language Processing"
  - explain_gap() no longer falsely reports missing synonyms
  - BUG #3 FIX: _parse_json() returns [] on failure (not {})
"""

import os
import re
import json

import pandas as pd

try:
    from matching_engine import SKILL_ALIASES
except ImportError:
    SKILL_ALIASES = {}

EGYPT_ALIASES = {"egypt", "cairo", "giza", "alexandria", "مصر", "القاهرة"}


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


# ── BUG #3 FIX: return [] instead of {} on parse failure ─────────────────────
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
    return []   # ← was implicitly {}, now explicitly [] for safer downstream handling


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
    text  = row_text.lower()
    score = 0

    for s in skills:
        if s.lower() in text:
            score += 2

    for r in roles:
        for word in r.lower().split():
            if len(word) > 3 and word in text:
                score += 1

    if location_pref:
        loc_lower     = location_pref.lower()
        is_egypt_pref = loc_lower in EGYPT_ALIASES
        is_remote_job = "remote" in text or "worldwide" in text

        if is_egypt_pref:
            if any(alias in text for alias in EGYPT_ALIASES):
                score += 15
            elif is_remote_job:
                score += 5
            else:
                score -= 5
        else:
            if loc_lower in text:
                score += 15
            elif is_remote_job:
                score += 5
            else:
                score -= 5

    return score


def _diverse_candidates(
    jobs: list[dict],
    skills: list[str],
    roles: list[str],
    location_pref: str = "",
    n: int = 30,
) -> list[dict]:
    for j in jobs:
        blob  = (str(j.get("title", "")) + " " + str(j.get("description", "")) +
                 " " + str(j.get("location", ""))).lower()
        j["_score"] = _score_row(blob, skills, roles, location_pref)

    scored = sorted(jobs, key=lambda x: x.get("_score", 0), reverse=True)

    buckets: dict[str, list] = {}
    for j in scored:
        src = j.get("source", "Unknown")
        buckets.setdefault(src, [])
        buckets[src].append(j)

    num_sources = max(len(buckets), 1)
    per_source  = max(3, n // num_sources)

    diverse: list[dict] = []
    seen: set            = set()

    for rnd in range(per_source):
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

    for j in scored:
        if len(diverse) >= n:
            break
        k = (j.get("title", "")[:40].lower(), j.get("company", "")[:30].lower())
        if k not in seen:
            seen.add(k)
            diverse.append(j)

    for j in diverse:
        j.pop("_score", None)

    return diverse[:n]


# ── CSV loader ────────────────────────────────────────────────────────────────

def _load_jobs(limit: int = 2000) -> pd.DataFrame | None:
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


# ── Helper to build synonym prompt text ──────────────────────────────────────

def _build_synonym_instruction() -> str:
    if not SKILL_ALIASES:
        return ""
    examples = []
    for canonical, aliases in list(SKILL_ALIASES.items())[:10]:
        if len(aliases) > 1:
            examples.append(f'"{canonical}" (also known as {", ".join(aliases[:3])})')
    if not examples:
        return ""
    return (
        "IMPORTANT – Skill synonyms: The following skills are considered IDENTICAL for matching:\n"
        + "\n".join(f"  • {ex}" for ex in examples) +
        "\nFor example, if the user has 'NLP' and the job asks for 'Natural Language Processing', it's a perfect match.\n"
        "Do NOT mark a skill as 'missing' if the user has a synonym.\n"
    )


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
        df = _load_jobs()
        if df is None or df.empty:
            return {
                "success": False,
                "error": (
                    "Job database not found. "
                    "Download a Kaggle dataset and save it as data/jobs.csv, "
                    "or click 'Scrape Fresh Jobs Now' in the Job Matcher tab."
                ),
            }

        skills    = user_profile.get("skills", [])
        roles     = user_profile.get("interested_roles", [])
        seniority = user_profile.get("seniority_level", "")
        exp_years = user_profile.get("experience_years", 0)

        text_cols = [c for c in ["title", "description", "company", "location", "level"]
                     if c in df.columns] or list(df.columns)

        df["_combined"] = df[text_cols].astype(str).agg(" ".join, axis=1)
        all_jobs = df.to_dict("records")

        candidates = _diverse_candidates(
            all_jobs, skills, roles, location_pref=location_pref, n=30
        )

        job_list = []
        for row in candidates:
            entry = {}
            for field in ["title", "company", "location", "level", "type",
                          "salary", "description", "source", "url"]:
                if field in row and str(row[field]).strip():
                    val = str(row[field])
                    entry[field] = val[:200] if field == "description" else val
            job_list.append(entry)

        # Build URL lookup
        url_lookup: dict[tuple, str] = {}
        for row in candidates:
            real_url = str(row.get("url", "")).strip()
            if real_url.startswith("http"):
                key = (
                    str(row.get("title", ""))[:40].lower(),
                    str(row.get("company", ""))[:30].lower(),
                )
                url_lookup[key] = real_url

        sources_present = sorted({j.get("source", "?") for j in job_list})

        loc_display   = location_pref or "Remote/Worldwide"
        is_egypt_pref = location_pref.lower() in EGYPT_ALIASES if location_pref else False
        egypt_note    = (
            "For Egypt: Cairo, Giza, Alexandria, and 'Egypt' in the location field "
            "all count as a match.\n" if is_egypt_pref else ""
        )

        synonym_instruction = _build_synonym_instruction()

        # ── BUG #2 FIX: truncate on whole job objects only ────────────────
        jobs_str = json.dumps(job_list, indent=2)
        if len(jobs_str) > 4500:
            truncated = []
            for job in job_list:
                candidate_str = json.dumps(truncated + [job], indent=2)
                if len(candidate_str) > 4200:
                    break
                truncated.append(job)
            jobs_str = json.dumps(truncated, indent=2)

        prompt = f"""You are a career advisor. Given the user profile and job listings,
return ONLY a valid JSON array (no markdown, no explanation) of the top {limit} best-matching jobs.

{synonym_instruction}

LOCATION REQUIREMENT — this is the most important ranking rule:
- The user is based in / prefers: '{loc_display}'.
- FIRST, fill as many of the {limit} slots as possible with jobs IN that location.
- ONLY use remote or other-location jobs if fewer than {limit // 2} strong local matches exist.
- {egypt_note}- NEVER include a job from a different physical country at the expense of a matching local one.
- Sources available: {', '.join(sources_present)}

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
  "url": "copy the url field exactly from the job listing below, or empty string if not present"
}}

IMPORTANT for url: do NOT invent URLs. Copy the exact url value from the job listing data.
If a listing has no url field, use an empty string "".

User profile:
- Skills: {', '.join(skills)}
- Experience: {exp_years} years
- Seniority: {seniority}
- Interested roles: {', '.join(roles) if roles else 'any'}
- Preferred location: {loc_display}

Job listings ({len(job_list)} pre-screened candidates across {len(sources_present)} sources):
{jobs_str}

Return ONLY the JSON array.
"""

        try:
            raw     = _call_llm(self.client, prompt)
            matches = _parse_json(raw)

            if isinstance(matches, dict) and "jobs" in matches:
                matches = matches["jobs"]
            if not isinstance(matches, list):
                matches = []

            # Replace hallucinated / missing URLs
            for m in matches:
                key = (
                    str(m.get("title", ""))[:40].lower(),
                    str(m.get("company", ""))[:30].lower(),
                )
                real_url = url_lookup.get(key, "")
                if real_url:
                    m["url"] = real_url
                elif not str(m.get("url", "")).startswith("http"):
                    m["url"] = ""

            return {
                "success":               True,
                "matches":               matches,
                "total_in_db":           len(df),
                "candidates_evaluated":  len(job_list),
                "sources_in_candidates": sources_present,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def explain_gap(self, user_skills: list, job: dict) -> dict:
        """Fixed to understand skill synonyms."""
        synonym_instruction = _build_synonym_instruction()

        prompt = f"""You are a career advisor. Analyse the skill gap between the user and the job.

{synonym_instruction}

User skills: {', '.join(user_skills)}

Target job: {json.dumps(job, indent=2)}

IMPORTANT RULES:
- If the user has a skill that is a synonym of a job requirement, consider it MATCHED, not missing.
- For example, "NLP" equals "Natural Language Processing", "JS" equals "JavaScript".
- Only list a skill as "missing_skills" if the user has no equivalent skill.

Return ONLY a valid JSON object with these exact keys:
{{
  "matching_skills": ["list of user skills that match job requirements (including synonyms)"],
  "missing_skills": ["only skills truly absent from user's skill set"],
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