"""github_analyzer.py — 5-dimension GitHub profile scoring + salary band."""
import os, json, re
from groq import Groq
from constant import GROQ_MODEL, GROQ_MODEL_FALLBACK, GH_REPO_LIMIT

def _parse_json(raw: str) -> dict:
    raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`")
    try:    return json.loads(raw)
    except Exception: pass
    m = re.search(r'\{[\s\S]+\}', raw)
    if m:
        try: return json.loads(m.group())
        except Exception: pass
    return {}

class GitHubAnalyzer:
    def __init__(self):
        key = os.getenv("GROQ_API_KEY", "")
        if not key:
            raise ValueError("GROQ_API_KEY not set")
        self.client  = Groq(api_key=key)
        gh_token     = os.getenv("GITHUB_TOKEN")
        from github import Github
        self.github  = Github(gh_token) if gh_token else Github()

    def _fetch_profile(self, username: str) -> dict:
        user  = self.github.get_user(username)
        langs: dict = {}
        stars = 0; forks = 0; has_readme = 0; total_repos = 0
        for repo in user.get_repos(sort="updated")[:GH_REPO_LIMIT]:
            total_repos += 1
            if repo.language:
                langs[repo.language] = langs.get(repo.language, 0) + 1
            stars += repo.stargazers_count
            forks += repo.forks_count
            try:
                repo.get_readme()
                has_readme += 1
            except Exception:
                pass

        return {
            "username":      user.login,
            "name":          user.name or "",
            "bio":           user.bio  or "",
            "followers":     user.followers,
            "following":     user.following,
            "public_repos":  user.public_repos,
            "languages":     langs,
            "company":       user.company  or "",
            "location":      user.location or "",
            "blog":          user.blog     or "",
            "total_stars":   stars,
            "total_forks":   forks,
            "readme_ratio":  round(has_readme / max(total_repos, 1), 2),
            "created_year":  user.created_at.year,
        }

    def analyze_github_profile(self, username: str) -> dict:
        try:
            profile = self._fetch_profile(username)
        except Exception as e:
            return {"success": False, "error": str(e)}

        prompt = (
            "You are a senior engineering recruiter. Analyze this GitHub profile.\n"
            "Return ONLY valid JSON — no markdown, no prose.\n\n"
            f"PROFILE DATA:\n{json.dumps(profile, indent=2)}\n\n"
            "JSON SCHEMA:\n"
            "{\n"
            '  "scores": {\n'
            '    "consistency":     <1-10, regularity of commits/repos>,\n'
            '    "depth":           <1-10, project complexity>,\n'
            '    "visibility":      <1-10, stars/followers/forks>,\n'
            '    "documentation":   <1-10, README quality/ratio>,\n'
            '    "collaboration":   <1-10, forks/community signals>\n'
            "  },\n"
            '  "overall_score":     <1-100 integer>,\n'
            '  "top_skills":        ["detected tech skills"],\n'
            '  "career_readiness":  "junior|mid|senior",\n'
            '  "recruiter_verdict": "2-sentence honest recruiter opinion",\n'
            '  "salary_band_usd":   "e.g. $60k-$90k",\n'
            '  "recommendations":   ["3 specific improvements"]\n'
            "}"
        )

        for model in [GROQ_MODEL, GROQ_MODEL_FALLBACK]:
            try:
                r = self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2, max_tokens=800,
                )
                parsed = _parse_json(r.choices[0].message.content)
                if parsed:
                    return {"success": True, "profile": profile, "analysis": parsed}
            except Exception:
                continue
        return {"success": False, "error": "All models failed."}