"""
Job Matcher  –  fixed
======================
• Uses groq package directly (langchain_community.llms.Groq does not exist)
• Keyword-filters the CSV first, then sends top candidates to the LLM
• Returns a parsed list of job dicts, not a raw string
• Handles multiple Kaggle CSV column formats automatically
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
        m = re.search(r"\[.*\]", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except Exception:
                pass
        m2 = re.search(r"\{.*\}", text, re.DOTALL)
        if m2:
            try:
                return json.loads(m2.group())
            except Exception:
                pass
    return []


# ── CSV column normaliser ─────────────────────────────────────────────────────

# Maps known Kaggle column names → our internal names
_COL_MAP = {
    # job title
    "job_title":        "title",
    "title":            "title",
    "position":         "title",
    "job_position":     "title",
    "role":             "title",
    # company
    "company_name":     "company",
    "company":          "company",
    "employer":         "company",
    # description
    "job_description":  "description",
    "description":      "description",
    "responsibilities": "description",
    "details":          "description",
    # location
    "location":         "location",
    "job_location":     "location",
    "city":             "location",
    # salary
    "salary":           "salary",
    "salary_in_usd":    "salary",
    "salary_estimate":  "salary",
    "avg_salary":       "salary",
    # experience / level
    "experience_level": "level",
    "seniority_level":  "level",
    "level":            "level",
    "employment_type":  "type",
}


def _normalise(df: pd.DataFrame) -> pd.DataFrame:
    rename = {}
    for col in df.columns:
        low = col.lower().strip()
        if low in _COL_MAP and _COL_MAP[low] not in df.columns:
            rename[col] = _COL_MAP[low]
    return df.rename(columns=rename)


# ── Keyword pre-filter ────────────────────────────────────────────────────────

def _score_row(row_text: str, skills: list[str], roles: list[str]) -> int:
    """Quick keyword match score — no LLM needed for pre-filtering."""
    text = row_text.lower()
    score = 0
    for s in skills:
        if s.lower() in text:
            score += 2
    for r in roles:
        # match any word from a role title
        for word in r.lower().split():
            if len(word) > 3 and word in text:
                score += 1
    return score


def _load_jobs(limit: int = 500) -> pd.DataFrame | None:
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

    def match_jobs(self, user_profile: dict, limit: int = 8) -> dict:
        df = _load_jobs()
        if df is None or df.empty:
            return {
                "success": False,
                "error": (
                    "Job database not found. "
                    "Download a Kaggle dataset and save it as data/jobs.csv"
                ),
            }

        skills  = user_profile.get("skills", [])
        roles   = user_profile.get("interested_roles", [])
        seniority = user_profile.get("seniority_level", "")
        exp_years = user_profile.get("experience_years", 0)

        # Build a combined text column for scoring
        text_cols = [c for c in ["title", "description", "company", "level"] if c in df.columns]
        if not text_cols:
            # fallback: use all columns
            text_cols = list(df.columns)

        df["_combined"] = df[text_cols].astype(str).agg(" ".join, axis=1)
        df["_score"] = df["_combined"].apply(lambda t: _score_row(t, skills, roles))

        # Take top candidates (scored > 0 first, then random sample as fallback)
        candidates = df[df["_score"] > 0].nlargest(20, "_score")
        if len(candidates) < 5:
            candidates = df.sample(min(20, len(df)), random_state=42)

        # Prepare a compact list for the LLM
        job_list = []
        for _, row in candidates.iterrows():
            entry = {}
            for field in ["title", "company", "location", "level", "type", "salary", "description"]:
                if field in row and str(row[field]).strip():
                    val = str(row[field])
                    entry[field] = val[:200] if field == "description" else val
            job_list.append(entry)

        prompt = f"""You are a career advisor. Given the user profile and job listings below,
return ONLY a valid JSON array (no markdown, no explanation) of the top {limit} best-matching jobs.

Each object in the array must have exactly these keys:
{{
  "title": "job title",
  "company": "company name",
  "location": "city or remote",
  "match_score": <integer 0-100>,
  "matched_skills": ["skill1", "skill2"],
  "missing_skills": ["skill1"],
  "why_good_fit": "one or two sentences explaining the match",
  "salary": "salary info or N/A"
}}

User profile:
- Skills: {', '.join(skills)}
- Experience: {exp_years} years
- Seniority: {seniority}
- Interested roles: {', '.join(roles) if roles else 'any'}

Job listings:
{json.dumps(job_list, indent=2)[:4000]}

Return ONLY the JSON array.
"""

        try:
            raw     = _call_llm(self.client, prompt)
            matches = _parse_json(raw)

            # Ensure it's a list
            if isinstance(matches, dict) and "jobs" in matches:
                matches = matches["jobs"]
            if not isinstance(matches, list):
                matches = []

            return {
                "success":  True,
                "matches":  matches,
                "total_in_db": len(df),
                "candidates_evaluated": len(job_list),
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