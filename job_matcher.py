"""
Job Matcher Module
Matches user profiles with jobs from Kaggle CSV datasets.
"""

import os
import json
import pandas as pd
from groq import Groq


class JobMatcher:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"
        self.job_database = self._load_job_database()

    def _load_job_database(self) -> list:
        paths = [
            "data/jobs_combined.csv",
            "data/jobs.csv",
            "docs/ai_jobs_market_2025_2026.csv",
        ]
        for path in paths:
            if os.path.exists(path):
                try:
                    df = pd.read_csv(path)
                    jobs = df.to_dict("records")
                    print(f"✅ Loaded {len(jobs)} jobs from {path}")
                    return jobs
                except Exception as e:
                    print(f"⚠️ Error loading {path}: {e}")
        print("⚠️ No job database found. See README for Kaggle dataset setup.")
        return []

    def match_jobs(self, user_profile: dict, limit: int = 10) -> dict:
        if not self.job_database:
            return {
                "success": False,
                "error": (
                    "Job database not loaded. "
                    "Download a CSV from Kaggle and place it at data/jobs.csv"
                ),
            }

        # Send only a sample to avoid token limits
        sample = json.dumps(self.job_database[:8], indent=2)

        prompt = f"""Match this user profile with jobs from the database.

User Profile:
{json.dumps(user_profile, indent=2)}

Job Database Sample:
{sample}

Return ONLY a valid JSON object:
{{
  "jobs": [
    {{
      "job_title": "title",
      "company": "company name",
      "match_score": 85,
      "reason": "why this is a good match",
      "required_skills": ["skill1", "skill2"],
      "nice_to_have": ["skill3"]
    }}
  ],
  "summary": "2-3 sentence overall insight"
}}

Return ONLY the JSON object, no markdown, no extra text."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1200,
            )
            raw = response.choices[0].message.content.strip()
            try:
                parsed = json.loads(raw)
                return {"success": True, "matches": parsed}
            except json.JSONDecodeError:
                return {"success": True, "matches": raw}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def explain_gap(self, user_skills: list, job_requirements: dict) -> dict:
        prompt = f"""Analyze the skill gap between user and job requirements.

User Skills: {json.dumps(user_skills)}
Job Requirements: {json.dumps(job_requirements)}

Return ONLY a valid JSON object:
{{
  "matching_skills": ["skills they already have"],
  "missing_skills": ["skills to learn"],
  "learning_path": ["step-by-step progression"],
  "time_to_readiness": "estimated months",
  "resources": ["courses or resources"]
}}

Return ONLY the JSON object, no markdown, no extra text."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=800,
            )
            raw = response.choices[0].message.content.strip()
            try:
                parsed = json.loads(raw)
                return {"success": True, "gap_analysis": parsed}
            except json.JSONDecodeError:
                return {"success": True, "gap_analysis": raw}
        except Exception as e:
            return {"success": False, "error": str(e)}