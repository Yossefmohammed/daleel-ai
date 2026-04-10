"""
GitHub Analyzer Module
Analyzes GitHub profiles: languages, repos, followers, AI insights.
"""

import os
import json
from github import Github
from groq import Groq


class GitHubAnalyzer:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"

        github_token = os.getenv("GITHUB_TOKEN")
        self.github = Github(github_token) if github_token else Github()

    def get_user_profile(self, username: str) -> dict:
        try:
            user = self.github.get_user(username)
            languages: dict = {}
            for repo in user.get_repos(sort="updated")[:20]:
                if repo.language:
                    languages[repo.language] = languages.get(repo.language, 0) + 1

            return {
                "username": user.login,
                "name": user.name,
                "bio": user.bio,
                "followers": user.followers,
                "following": user.following,
                "public_repos": user.public_repos,
                "languages": languages,
                "company": user.company,
                "location": user.location,
                "blog": user.blog,
                "success": True,
            }
        except Exception as e:
            return {"success": False, "error": f"Error fetching profile: {e}"}

    def analyze_github_profile(self, username: str) -> dict:
        profile = self.get_user_profile(username)
        if not profile.get("success"):
            return profile

        prompt = f"""Analyze this GitHub profile and return ONLY a valid JSON object:
{{
  "profile_strength": "score 1-10",
  "top_skills": ["detected programming skills"],
  "contribution_level": "active or moderate or low",
  "project_quality": "short assessment",
  "recommendations": ["2-3 suggestions to improve the profile"],
  "career_readiness": "junior or mid or senior"
}}

Profile data:
{json.dumps(profile, default=str, indent=2)}

Return ONLY the JSON object, no markdown, no extra text."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=600,
            )
            raw = response.choices[0].message.content.strip()
            try:
                parsed = json.loads(raw)
                return {"success": True, "profile": profile, "analysis": parsed}
            except json.JSONDecodeError:
                return {"success": True, "profile": profile, "analysis": raw}
        except Exception as e:
            return {"success": False, "error": str(e)}