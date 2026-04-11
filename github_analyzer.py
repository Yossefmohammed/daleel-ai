"""
github_analyzer.py — PathIQ Code Profile Engine
=================================================
Fetches GitHub profile data via API and scores it with Groq LLaMA.
"""

import os
import json
import re
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()


class GitHubAnalyzer:
    """
    Analyzes a GitHub profile and returns a scored developer profile
    with actionable improvement recommendations.
    """

    GITHUB_API = "https://api.github.com"

    SYSTEM_PROMPT = """You are PathIQ's Code Profile Engine — a senior engineering recruiter 
who evaluates developer GitHub profiles. 
Return ONLY a valid JSON object. No markdown, no code fences.

Required structure:
{
  "overall_score": 1-100,
  "subscores": {
    "consistency": 1-100,
    "depth": 1-100,
    "visibility": 1-100,
    "documentation": 1-100,
    "collaboration": 1-100
  },
  "seniority_signal": "junior|mid|senior|staff",
  "primary_speciality": "Backend | Frontend | Full Stack | Data | DevOps | ML | etc",
  "top_languages": ["lang1", "lang2", "lang3"],
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "gaps": ["gap 1", "gap 2"],
  "quick_wins": [
    {"action": "Pin 3 best repositories", "impact": "high", "effort": "low"},
    {"action": "Write README for top repo", "impact": "high", "effort": "medium"}
  ],
  "recruiter_verdict": "One sentence summary a recruiter would write about this profile",
  "target_roles": ["Role A", "Role B", "Role C"],
  "salary_band_usd": {"min": 90000, "max": 140000}
}"""

    def __init__(self):
        self._token = os.getenv("GITHUB_TOKEN")
        self._llm_client = None

    def _headers(self):
        h = {"Accept": "application/vnd.github.v3+json"}
        if self._token:
            h["Authorization"] = f"token {self._token}"
        return h

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

    def _fetch_user(self, username: str) -> dict:
        r = requests.get(f"{self.GITHUB_API}/users/{username}", headers=self._headers(), timeout=10)
        r.raise_for_status()
        return r.json()

    def _fetch_repos(self, username: str, limit: int = 30) -> list:
        r = requests.get(
            f"{self.GITHUB_API}/users/{username}/repos",
            headers=self._headers(),
            params={"per_page": limit, "sort": "updated"},
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

    def _aggregate_languages(self, repos: list) -> dict:
        langs = {}
        for repo in repos[:15]:  # limit API calls
            if repo.get("language"):
                langs[repo["language"]] = langs.get(repo["language"], 0) + 1
        return dict(sorted(langs.items(), key=lambda x: x[1], reverse=True))

    def _contribution_stats(self, repos: list) -> dict:
        total_stars   = sum(r.get("stargazers_count", 0) for r in repos)
        total_forks   = sum(r.get("forks_count", 0) for r in repos)
        has_readme    = sum(1 for r in repos if r.get("description"))
        forked        = sum(1 for r in repos if r.get("fork"))
        original      = len(repos) - forked
        avg_stars     = round(total_stars / max(len(repos), 1), 1)
        return {
            "total_stars":   total_stars,
            "total_forks":   total_forks,
            "repos_with_desc": has_readme,
            "original_repos": original,
            "forked_repos":  forked,
            "avg_stars":     avg_stars,
        }

    def analyze_github_profile(self, username: str) -> dict:
        """
        Analyze a GitHub profile and return a scored intelligence report.

        Returns:
            {
              "success": bool,
              "profile": dict,    # raw GitHub data summary
              "analysis": dict,   # AI-scored analysis
              "error": str        # only if success=False
            }
        """
        try:
            user_data = self._fetch_user(username)
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return {"success": False, "error": f"GitHub user '{username}' not found. Check the username spelling."}
            return {"success": False, "error": f"GitHub API error: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Network error: {e}"}

        try:
            repos = self._fetch_repos(username)
        except Exception:
            repos = []

        languages   = self._aggregate_languages(repos)
        stats       = self._contribution_stats(repos)
        account_age = ""
        created     = user_data.get("created_at", "")
        if created:
            try:
                dt = datetime.strptime(created, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                years = (datetime.now(timezone.utc) - dt).days // 365
                account_age = f"{years} years"
            except Exception:
                account_age = created[:4]

        profile_summary = {
            "username":       username,
            "name":           user_data.get("name") or username,
            "bio":            user_data.get("bio") or "",
            "location":       user_data.get("location") or "Unknown",
            "followers":      user_data.get("followers", 0),
            "following":      user_data.get("following", 0),
            "public_repos":   user_data.get("public_repos", 0),
            "account_age":    account_age,
            "blog":           bool(user_data.get("blog")),
            "hireable":       user_data.get("hireable"),
            "languages":      languages,
            "top_repos": [
                {
                    "name":        r.get("name"),
                    "description": r.get("description") or "",
                    "stars":       r.get("stargazers_count", 0),
                    "forks":       r.get("forks_count", 0),
                    "language":    r.get("language") or "N/A",
                    "has_readme":  bool(r.get("description")),
                    "updated":     (r.get("updated_at") or "")[:10],
                }
                for r in sorted(repos, key=lambda x: x.get("stargazers_count", 0), reverse=True)[:8]
            ],
            **stats,
        }

        # AI analysis
        prompt = f"""Analyze this GitHub profile and return a JSON score report:

PROFILE DATA:
{json.dumps(profile_summary, indent=2)}

Return ONLY the JSON object."""

        try:
            client  = self._get_llm()
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system",  "content": self.SYSTEM_PROMPT},
                    {"role": "user",    "content": prompt},
                ],
                temperature=0.2,
                max_tokens=900,
            )
            raw_json = response.choices[0].message.content.strip()
            raw_json = re.sub(r"```(?:json)?\s*", "", raw_json).strip().strip("`")
            analysis = json.loads(raw_json)
        except Exception as e:
            analysis = {"error": str(e), "overall_score": 0}

        return {
            "success":  True,
            "profile":  profile_summary,
            "analysis": analysis,
        }