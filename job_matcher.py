"""job_matcher.py — keyword pre-filter + LLM matching with gap/priority."""
import os, json, re
import pandas as pd
from groq import Groq
from constant import (GROQ_MODEL, GROQ_MODEL_FALLBACK,
                      JOB_CSV_PATHS, JOB_SAMPLE_ROWS, JOB_MATCH_RESULTS)

def _parse_json(raw: str) -> dict:
    raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`")
    try:    return json.loads(raw)
    except Exception: pass
    m = re.search(r'\{[\s\S]+\}', raw)
    if m:
        try: return json.loads(m.group())
        except Exception: pass
    return {}

class JobMatcher:
    def __init__(self):
        key = os.getenv("GROQ_API_KEY", "")
        if not key:
            raise ValueError("GROQ_API_KEY not set")
        self.client = Groq(api_key=key)
        self.df     = self._load()

    def _load(self) -> pd.DataFrame:
        for path in JOB_CSV_PATHS:
            if os.path.exists(path):
                try:
                    df = pd.read_csv(path).fillna("")
                    # normalise column names
                    df.rename(columns={"title": "job_title", "position": "job_title",
                                       "company_name": "company"}, inplace=True)
                    if "job_title" not in df.columns:
                        df["job_title"] = "Unknown"
                    return df
                except Exception:
                    pass
        return pd.DataFrame()

    def _keyword_filter(self, skills: list, n: int) -> list:
        """Pre-filter CSV rows that mention at least one skill keyword."""
        if self.df.empty:
            return []
        mask = pd.Series([False] * len(self.df))
        text_cols = [c for c in ["job_title","tags","description","required_skills"] if c in self.df.columns]
        for col in text_cols:
            for skill in skills:
                mask |= self.df[col].str.lower().str.contains(skill.lower(), na=False)
        filtered = self.df[mask] if mask.any() else self.df
        return filtered.head(n).to_dict("records")

    def match_jobs(self, user_profile: dict) -> dict:
        if self.df.empty:
            return {"success": False,
                    "error": "No job database. Scrape jobs first (🌐 Scrape Jobs tab)."}

        skills   = user_profile.get("skills", [])
        sample   = self._keyword_filter(skills, JOB_SAMPLE_ROWS)
        prompt   = (
            "You are a career coach. Match this user to the best jobs.\n"
            "Return ONLY valid JSON — no markdown, no prose.\n\n"
            f"USER PROFILE:\n{json.dumps(user_profile, indent=2)}\n\n"
            f"JOB DATABASE SAMPLE ({len(sample)} jobs):\n{json.dumps(sample, indent=2)}\n\n"
            f"Return top {JOB_MATCH_RESULTS} matches as JSON:\n"
            "{\n"
            '  "jobs": [\n'
            "    {\n"
            '      "job_title":      "title",\n'
            '      "company":        "company",\n'
            '      "fit_score":      <1-100 integer>,\n'
            '      "why_fit":        "2-sentence explanation",\n'
            '      "skill_gaps":     ["missing skills"],\n'
            '      "how_to_close":   ["concrete steps to close each gap"],\n'
            '      "apply_priority": "high|medium|low",\n'
            '      "url":            "job url or empty"\n'
            "    }\n"
            "  ],\n"
            '  "summary": "2-sentence overall career insight"\n'
            "}"
        )

        for model in [GROQ_MODEL, GROQ_MODEL_FALLBACK]:
            try:
                r = self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.25, max_tokens=1400,
                )
                parsed = _parse_json(r.choices[0].message.content)
                if parsed:
                    return {"success": True, "matches": parsed}
            except Exception:
                continue
        return {"success": False, "error": "All models failed."}