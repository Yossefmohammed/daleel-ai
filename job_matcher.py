"""
job_matcher.py — PathIQ Job Matching Engine
============================================
Matches a user profile against a jobs CSV database and uses Groq
to generate ranked matches with explanation and gap analysis.
"""

import os
import json
import re
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

JOBS_PATH = Path("data/jobs.csv")

SYSTEM_PROMPT = """You are PathIQ's Job Matching Engine — a precision career placement AI.
Given a user profile and job listings, return ONLY a valid JSON object. No markdown, no fences.

Required structure:
{
  "matches": [
    {
      "rank": 1,
      "title": "Job title",
      "company": "Company name",
      "match_score": 1-100,
      "why_fit": "2-sentence explanation of why they fit",
      "skill_gaps": ["gap 1", "gap 2"],
      "gap_fix": "How to close the main gap in < 30 days",
      "salary_est_usd": {"min": 100000, "max": 145000},
      "apply_priority": "high|medium|low"
    }
  ],
  "overall_market_fit": 1-100,
  "strongest_profile_aspect": "One sentence",
  "top_recommendation": "The single best next step for this candidate",
  "search_keywords": ["keyword1", "keyword2", "keyword3"]
}"""


class JobMatcher:
    """Matches user skills/experience against a jobs database."""

    def __init__(self, jobs_path: str = None):
        self.jobs_path = Path(jobs_path) if jobs_path else JOBS_PATH
        self._llm_client = None
        self._df = None

    def _get_llm(self):
        if self._llm_client:
            return self._llm_client
        try:
            from groq import Groq
        except ImportError:
            raise ImportError("Install groq: pip install groq")

        key = None
        try:
            import streamlit as st
            key = st.secrets.get("GROQ_API_KEY")
        except Exception:
            pass
        if not key:
            key = os.getenv("GROQ_API_KEY")
        if not key:
            raise ValueError("GROQ_API_KEY not found")

        self._llm_client = Groq(api_key=key)
        return self._llm_client

    def _load_jobs(self) -> pd.DataFrame:
        if self._df is not None:
            return self._df

        if not self.jobs_path.exists():
            raise FileNotFoundError(
                f"Jobs database not found at {self.jobs_path}. "
                "Download a dataset from Kaggle and save as data/jobs.csv. "
                "See README for dataset options."
            )

        df = pd.read_csv(self.jobs_path)

        # Normalize column names (handle different Kaggle dataset formats)
        df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]

        # Map known column aliases to standard names
        col_map = {
            "job_title": ["job_title", "title", "position", "role", "job_name"],
            "company":   ["company", "company_name", "employer", "organization"],
            "description": ["description", "job_description", "requirements", "details"],
            "location":  ["location", "city", "country", "work_location"],
            "salary":    ["salary", "salary_usd", "salary_in_usd", "average_salary", "pay"],
        }
        rename = {}
        for std, aliases in col_map.items():
            if std not in df.columns:
                for alias in aliases:
                    if alias in df.columns:
                        rename[alias] = std
                        break
        if rename:
            df = df.rename(columns=rename)

        # Ensure required columns exist
        for col in ["job_title", "company", "description"]:
            if col not in df.columns:
                df[col] = "Unknown"

        self._df = df
        return df

    def _candidate_keyword_filter(self, df: pd.DataFrame, profile: dict) -> pd.DataFrame:
        """Pre-filter jobs by keyword match before sending to LLM."""
        skills = [s.lower() for s in profile.get("skills", [])]
        roles  = [r.lower() for r in profile.get("interested_roles", [])]
        keywords = skills + roles

        if not keywords:
            return df.head(50)

        def row_score(row):
            text = " ".join([
                str(row.get("job_title", "")),
                str(row.get("description", "")),
            ]).lower()
            return sum(1 for kw in keywords if kw in text)

        df = df.copy()
        df["_score"] = df.apply(row_score, axis=1)
        filtered = df[df["_score"] > 0].sort_values("_score", ascending=False).head(20)
        if len(filtered) < 5:
            filtered = df.head(20)
        return filtered.drop(columns=["_score"])

    def match_jobs(self, user_profile: dict) -> dict:
        """
        Match user profile against job database.

        Args:
            user_profile: {
                "skills": ["Python", "FastAPI", ...],
                "experience_years": 4,
                "seniority_level": "mid",
                "interested_roles": ["Backend Engineer", ...]
            }

        Returns:
            {"success": bool, "matches": list, "analysis": dict, "error": str}
        """
        try:
            df = self._load_jobs()
        except FileNotFoundError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"Failed to load jobs database: {e}"}

        try:
            candidates = self._candidate_keyword_filter(df, user_profile)
        except Exception:
            candidates = df.head(20)

        # Build compact job list for LLM
        job_list = []
        for _, row in candidates.iterrows():
            job_list.append({
                "title":       str(row.get("job_title", ""))[:80],
                "company":     str(row.get("company", ""))[:50],
                "description": str(row.get("description", ""))[:300],
                "location":    str(row.get("location", ""))[:50],
                "salary":      str(row.get("salary", "N/A"))[:30],
            })

        prompt = f"""Match this candidate profile against the job listings and return the top 5 matches.

CANDIDATE PROFILE:
{json.dumps(user_profile, indent=2)}

JOB LISTINGS:
{json.dumps(job_list[:20], indent=2)}

Return ONLY the JSON object with the top 5 best matches."""

        try:
            client   = self._get_llm()
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1200,
            )
            raw_json = response.choices[0].message.content.strip()
            raw_json = re.sub(r"```(?:json)?\s*", "", raw_json).strip().strip("`")
            result   = json.loads(raw_json)
            return {"success": True, **result}

        except json.JSONDecodeError as e:
            return {"success": False, "error": f"JSON parse error: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}