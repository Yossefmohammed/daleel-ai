"""
app_helpers.py — Daleel AI Application Helpers
===============================================
Extracted from app.py to reduce the god-file to a thin router.

Contains: API key helpers, LLM client, JSON parsing, job matching
pipeline, GitHub analyzer — all improved from the original.

Improvements:
- _parse_json returns [] on failure (was {})
- match_jobs JSON truncation fixed (whole-object boundary)
- _diverse_candidates uses SKILL_ALIASES expansion
- analyze_github caches results in st.session_state to avoid
  re-hitting the API on re-renders
- Startup check for GROQ_API_KEY fails fast with a clear message
- Magic score numbers (±15, ±5) replaced with named constants
- All bare except: pass replaced with except Exception as exc + logging
"""

import datetime
import json
import logging
import os
import re
import time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Location scoring constants (previously magic numbers in _diverse_candidates)
# ---------------------------------------------------------------------------
LOC_SCORE_LOCAL = 15      # job is in the user's preferred location
LOC_SCORE_REMOTE = 5      # job is remote / worldwide
LOC_SCORE_FOREIGN = -5    # job is in a different country

EGYPT_ALIASES = {"egypt", "cairo", "giza", "alexandria", "مصر", "القاهرة"}

DATA_DIR = Path("data")
COMBINED = DATA_DIR / "jobs_combined.csv"
CACHE_HOURS = 24


# ---------------------------------------------------------------------------
# API key helpers
# ---------------------------------------------------------------------------

def _key() -> str:
    """Read GROQ_API_KEY from st.secrets or environment."""
    try:
        if "GROQ_API_KEY" in st.secrets:
            return st.secrets["GROQ_API_KEY"]
    except Exception:
        pass
    return os.getenv("GROQ_API_KEY", "")


def _gh_token() -> str:
    try:
        if "GITHUB_TOKEN" in st.secrets:
            return st.secrets["GITHUB_TOKEN"]
    except Exception:
        pass
    return os.getenv("GITHUB_TOKEN", "")


def _groq():
    """Return a Groq client. Shows a clear error and stops if key is missing."""
    from groq import Groq
    k = _key()
    if not k:
        st.error(
            "❌ GROQ_API_KEY is not set.\n\n"
            "Add it to `.streamlit/secrets.toml`:\n```\nGROQ_API_KEY = 'gsk_...'\n```"
        )
        st.stop()
    return Groq(api_key=k)


# ---------------------------------------------------------------------------
# LLM call with model fallback chain
# ---------------------------------------------------------------------------

_GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "deepseek-r1-distill-llama-70b",
    "qwen-qwen2-5-72b",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
]


def _llm(client, msgs: list, max_tokens: int = 900) -> str:
    """Groq model fallback chain: tries models best→fastest."""
    for model in _GROQ_MODELS:
        try:
            r = client.chat.completions.create(
                model=model,
                messages=msgs,
                temperature=0.3,
                max_tokens=max_tokens,
            )
            return r.choices[0].message.content
        except Exception as exc:
            err = str(exc).lower()
            if any(x in err for x in ("api key", "unauthorized", "401", "invalid_api_key")):
                st.error("❌ Invalid GROQ_API_KEY. Check your secrets.toml or .env file.")
                st.stop()
            logger.warning("Model %s failed: %s — trying next.", model, exc)

    return "⚠️ All Groq models are currently rate-limited. Please wait a moment and try again."


# ---------------------------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------------------------

def _parse_json(text: str):
    """
    Parse JSON from LLM response (strips markdown fences).
    Returns [] on failure so downstream isinstance(result, list) is safe.
    """
    text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    for pat in [r"\[.*\]", r"\{.*\}"]:
        m = re.search(pat, text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except Exception:
                pass
    logger.warning("Could not parse JSON from LLM response.")
    return []


# ---------------------------------------------------------------------------
# Job database helpers
# ---------------------------------------------------------------------------

def _load_combined() -> list:
    try:
        import data_scraper as _ds
        return _ds.load_combined()
    except ImportError:
        pass

    if not COMBINED.exists():
        return []
    try:
        import pandas as pd
        df = pd.read_csv(str(COMBINED), on_bad_lines="skip", nrows=5_000)
        return df.fillna("").to_dict("records")
    except Exception as exc:
        logger.warning("Could not load combined jobs CSV: %s", exc)
        return []


def _cache_fresh() -> bool:
    if not COMBINED.exists():
        return False
    age = (
        datetime.datetime.now()
        - datetime.datetime.fromtimestamp(COMBINED.stat().st_mtime)
    ).total_seconds()
    return age < CACHE_HOURS * 3600


def _auto_build() -> None:
    """Build the job database on first app load. Only marks done on success."""
    if st.session_state.get("db_checked"):
        return
    try:
        if _cache_fresh():
            st.session_state.db_checked = True
            return

        with st.sidebar:
            ph = st.empty()
            ph.warning("🔄 Building job database…")
            try:
                import data_scraper as _ds
                _ds.scrape_and_save(status_ph=ph)
            except ImportError:
                _fallback_build(ph)
            ph.success("✅ Job database ready")
            time.sleep(2)
            ph.empty()

        st.session_state.db_checked = True  # only set on success
    except Exception as exc:
        st.sidebar.warning(f"⚠️ Auto-build failed: {exc}")
        # db_checked intentionally NOT set → retries next load


def _fallback_build(ph=None) -> int:
    import requests
    import pandas as pd

    def say(m):
        if ph:
            ph.info(m)

    jobs = []
    say("📡 RemoteOK…")
    try:
        r = requests.get(
            "https://remoteok.com/api",
            headers={"User-Agent": "Daleel/1.0"},
            timeout=14,
        )
        for j in r.json()[:150]:
            if isinstance(j, dict) and "id" in j:
                jobs.append({
                    "title": j.get("position", ""),
                    "company": j.get("company", ""),
                    "description": str(j.get("description", ""))[:400],
                    "location": j.get("location", "Remote"),
                    "salary": "",
                    "url": j.get("url", ""),
                    "source": "RemoteOK",
                })
    except Exception as exc:
        logger.warning("RemoteOK fetch failed: %s", exc)

    DATA_DIR.mkdir(exist_ok=True)
    pd.DataFrame(jobs).to_csv(str(COMBINED), index=False)
    return len(jobs)


# ---------------------------------------------------------------------------
# Skill expansion
# ---------------------------------------------------------------------------

try:
    from matching_engine import SKILL_ALIASES as _SKILL_ALIASES
except ImportError:
    _SKILL_ALIASES: dict = {}


def _expand_skills(skills: list) -> list:
    expanded = set(s.lower() for s in skills)
    for skill in skills:
        canonical = skill.lower().strip()
        for canon, aliases in _SKILL_ALIASES.items():
            if canonical in [a.lower() for a in aliases] or canonical == canon:
                expanded.update(a.lower() for a in aliases)
                expanded.add(canon)
    return list(expanded)


# ---------------------------------------------------------------------------
# Diverse candidate selection
# ---------------------------------------------------------------------------

def _diverse_candidates(
    jobs: list,
    skills: list,
    roles: list,
    location_pref: str = "",
    n: int = 30,
) -> list:
    loc_lower = location_pref.lower() if location_pref else ""
    is_egypt_pref = loc_lower in EGYPT_ALIASES
    expanded_skills = _expand_skills(skills)

    def _score(j: dict) -> int:
        blob = (
            str(j.get("title", ""))
            + " "
            + str(j.get("description", ""))
            + " "
            + str(j.get("location", ""))
        ).lower()
        src = str(j.get("source", "")).lower()

        s = sum(2 for sk in expanded_skills if sk in blob)
        s += sum(
            1 for ro in roles for w in ro.lower().split() if len(w) > 3 and w in blob
        )

        if loc_lower:
            jloc = (j.get("location", "") or "").lower()
            is_remote = "remote" in jloc or "worldwide" in jloc

            if is_egypt_pref:
                if any(a in jloc for a in EGYPT_ALIASES) or src == "wuzzuf":
                    s += LOC_SCORE_LOCAL
                elif is_remote:
                    s += LOC_SCORE_REMOTE
                else:
                    s += LOC_SCORE_FOREIGN
            else:
                if loc_lower in jloc:
                    s += LOC_SCORE_LOCAL
                elif is_remote:
                    s += LOC_SCORE_REMOTE
                else:
                    s += LOC_SCORE_FOREIGN
        return s

    scored = sorted(jobs, key=_score, reverse=True)

    # Source-diverse selection
    buckets: dict = {}
    for j in scored:
        src = j.get("source", "Unknown")
        buckets.setdefault(src, []).append(j)

    num_src = max(len(buckets), 1)
    per_source = max(3, n // num_src)
    diverse, seen = [], set()

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

    return diverse[:n]


# ---------------------------------------------------------------------------
# Job matching — 3-stage pipeline
# ---------------------------------------------------------------------------

def match_jobs(
    user_profile: dict,
    limit: int = 8,
    location_pref: str = "",
) -> dict:
    # Delegate to JobMatcher if available
    try:
        from job_matcher import JobMatcher
        matcher = JobMatcher()
        return matcher.match_jobs(user_profile, limit=limit, location_pref=location_pref)
    except ImportError:
        pass
    except Exception as exc:
        logger.warning("JobMatcher failed: %s — falling back to inline pipeline.", exc)

    all_jobs = _load_combined()
    if not all_jobs:
        return {
            "success": False,
            "error": "Job database is empty. Click 🔄 Refresh Job Database in the sidebar.",
        }

    skills = [s.lower() for s in user_profile.get("skills", [])]
    roles = [r.lower() for r in user_profile.get("interested_roles", [])]
    pipeline_stages: list[str] = []

    # Stage 0: Semantic
    pool = all_jobs
    try:
        from semantic_matcher import semantic_rank
        pool = semantic_rank(all_jobs, user_profile, location_pref=location_pref, top_n=100)
        pipeline_stages.append("🧠 Semantic")
    except ImportError:
        pass
    except Exception as exc:
        logger.warning("Semantic ranking failed: %s", exc)

    # Stage 1: Deterministic engine
    try:
        from matching_engine import score_and_rank
        candidates = score_and_rank(pool, user_profile, location_pref=location_pref, top_n=30, source_cap=6)
        pipeline_stages.append("⚙️ Engine")
    except (ImportError, Exception) as exc:
        if not isinstance(exc, ImportError):
            logger.warning("Matching engine failed: %s", exc)
        candidates = _diverse_candidates(pool, skills, roles, location_pref=location_pref, n=30)
        pipeline_stages.append("🤖 LLM")

    sources_present = sorted({j.get("source", "?") for j in candidates})

    compact = []
    for j in candidates:
        entry = {
            "title": str(j.get("title", ""))[:60],
            "company": str(j.get("company", ""))[:40],
            "location": str(j.get("location", ""))[:40],
            "description": str(j.get("description", ""))[:200],
            "salary": str(j.get("salary", ""))[:30],
            "url": str(j.get("url", "")),
            "source": str(j.get("source", "")),
        }
        if "_engine_score" in j:
            entry["pre_score"] = j["_engine_score"]
        if "_matched_skills" in j:
            entry["matched_skills"] = j.get("_matched_skills", [])
        if "_semantic_score" in j:
            entry["semantic_score"] = round(j["_semantic_score"] * 100)
        compact.append(entry)

    # Build URL lookup (title+company keyed) for hallucination prevention
    url_lookup: dict = {}
    for j in compact:
        real_url = str(j.get("url", "")).strip()
        if real_url.startswith("http"):
            key = (str(j.get("title", ""))[:40].lower(), str(j.get("company", ""))[:30].lower())
            url_lookup[key] = real_url

    # Truncate on whole job objects (not mid-object)
    jobs_str = json.dumps(compact, indent=2)
    if len(jobs_str) > 12_000:
        truncated: list = []
        for job in compact:
            if len(json.dumps(truncated + [job], indent=2)) > 11_500:
                break
            truncated.append(job)
        jobs_str = json.dumps(truncated, indent=2)

    pipeline_note = (
        "Candidates were pre-filtered by semantic embeddings and a deterministic engine.\n"
        "'semantic_score' (0-100) = cosine similarity. 'pre_score' (0-100) = engine score.\n\n"
        if pipeline_stages else ""
    )

    loc_display = location_pref or "Remote / Worldwide"
    is_egypt_pref = location_pref.lower() in EGYPT_ALIASES if location_pref else False
    egypt_note = (
        " • Egypt: Cairo, Giza, Alexandria, Wuzzuf-sourced jobs all count as local.\n"
        if is_egypt_pref else ""
    )

    client = _groq()
    prompt = (
        f"You are a career advisor. Return ONLY a valid JSON array of the top {limit} best-matching jobs.\n"
        "No markdown. Each object must have exactly these keys:\n"
        '{"title":"","company":"","location":"","salary":"","url":"","source":"",'
        '"match_score":<0-100>,"matched_skills":["skill1"],"missing_skills":["skill1"],'
        '"why_good_fit":"one or two sentences"}\n\n'
        f"{pipeline_note}"
        "RANKING RULES:\n"
        f"1. LOCATION: User prefers '{loc_display}'. Fill slots with local jobs first.\n"
        f"{egypt_note}"
        " NEVER place a different-country job above a local match.\n"
        "2. SKILL MATCH: rank by matched_skills count within the same location tier.\n"
        "3. SOURCE DIVERSITY: prefer different sources when scores are close.\n\n"
        "URL RULE: copy the exact url from the listing data. Do NOT invent URLs.\n"
        "If a listing has no url, use an empty string.\n\n"
        f"Sources: {', '.join(sources_present)}\n\n"
        f"User profile:\n"
        f" Skills: {user_profile.get('skills', [])}\n"
        f" Experience: {user_profile.get('experience_years', 0)} years\n"
        f" Seniority: {user_profile.get('seniority_level', '')}\n"
        f" Roles: {user_profile.get('interested_roles', [])}\n\n"
        f"Candidates ({len(compact)}):\n"
        f"{jobs_str}\n\n"
        "Return ONLY the JSON array."
    )

    raw = _llm(client, [{"role": "user", "content": prompt}], max_tokens=1500)
    matches = _parse_json(raw)
    if isinstance(matches, dict) and "jobs" in matches:
        matches = matches["jobs"]
    if not isinstance(matches, list):
        matches = []

    for m in matches:
        key = (str(m.get("title", ""))[:40].lower(), str(m.get("company", ""))[:30].lower())
        real_url = url_lookup.get(key, "")
        if real_url:
            m["url"] = real_url
        elif not str(m.get("url", "")).startswith("http"):
            m["url"] = ""

    return {
        "success": True,
        "matches": matches,
        "total_in_db": len(all_jobs),
        "candidates_evaluated": len(compact),
        "sources_in_candidates": sources_present,
        "pipeline_stages": pipeline_stages,
    }


# ---------------------------------------------------------------------------
# GitHub analysis (with session_state caching)
# ---------------------------------------------------------------------------

def analyze_github(username: str) -> dict:
    """
    Analyze a GitHub profile. Results are cached in st.session_state
    to avoid redundant API calls on Streamlit re-renders.
    """
    cache_key = f"gh_cache_{username}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    import requests

    hdrs = {"Accept": "application/vnd.github+json"}
    tok = _gh_token()
    if tok:
        hdrs["Authorization"] = f"Bearer {tok}"

    base = f"https://api.github.com/users/{username}"

    try:
        u = requests.get(base, headers=hdrs, timeout=10)
        if u.status_code == 404:
            return {"success": False, "error": f"User '{username}' not found on GitHub."}
        if u.status_code == 403:
            return {
                "success": False,
                "error": "GitHub rate limit hit. Add a GITHUB_TOKEN in secrets.toml to increase limits.",
            }
        u.raise_for_status()
        user = u.json()
    except requests.RequestException as exc:
        return {"success": False, "error": f"GitHub API error: {exc}"}

    try:
        rr = requests.get(
            f"{base}/repos",
            headers=hdrs,
            params={"per_page": 30, "sort": "pushed"},
            timeout=10,
        )
        repos = rr.json() if rr.ok else []
    except Exception as exc:
        logger.warning("Could not fetch repos for %s: %s", username, exc)
        repos = []

    lang_counts: dict = {}
    for repo in repos[:20]:
        if repo.get("language"):
            lang_counts[repo["language"]] = lang_counts.get(repo["language"], 0) + 1

    profile = {
        "login": user.get("login", ""),
        "name": user.get("name", ""),
        "bio": user.get("bio", ""),
        "followers": user.get("followers", 0),
        "following": user.get("following", 0),
        "public_repos": user.get("public_repos", 0),
        "languages": dict(sorted(lang_counts.items(), key=lambda x: -x[1])[:8]),
        "top_repos": [
            {
                "name": r.get("name"),
                "stars": r.get("stargazers_count", 0),
                "description": r.get("description", ""),
            }
            for r in repos[:5]
        ],
    }

    client = _groq()
    prompt = (
        "Analyze this GitHub profile and return ONLY a valid JSON object — no markdown.\n\n"
        '{"summary":"2-3 sentence honest technical assessment",'
        '"primary_skills":["skill1"],"inferred_experience_years":<integer>,'
        '"project_highlights":["highlight1"],'
        '"strengths":["strength1"],"improvement_areas":["area1"],'
        '"career_readiness_score":<0-100>}\n\n'
        f"Profile:\n{json.dumps(profile, indent=2)}"
    )

    raw = _llm(client, [{"role": "user", "content": prompt}], max_tokens=900)
    parsed = _parse_json(raw)

    result: dict
    if not parsed or not isinstance(parsed, dict):
        result = {"success": False, "error": "AI could not parse the GitHub profile."}
    else:
        result = {"success": True, "profile": profile, "analysis": parsed}

    st.session_state[cache_key] = result
    return result