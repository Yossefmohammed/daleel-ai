"""
matching_engine.py – Career AI (Stage 1: Deterministic Keyword Scorer - IMPROVED)
=====================================================================================
FIXES:
- BUG 2 FIX: _loc_score now correctly handles Remote preference as PRIMARY target
             (previously "remote" was treated the same as a city name, giving wrong results)
- Expanded skill alias dictionary (50+ common tech synonyms)
- Bidirectional alias resolution (user skill → canonical form)
- Fuzzy matching fallback (catches typos & abbreviations)
- Correct "missing skills" detection (no more false positives)
"""

from __future__ import annotations

import re
import difflib
from typing import Tuple, List

EGYPT_ALIASES = {"egypt", "cairo", "giza", "alexandria", "مصر", "القاهرة"}

# ─────────────────────────────────────────────────────────────────────────────
# Skill aliases – EXTENDED
# Format: canonical_skill -> [list of synonyms, including acronyms, common typos]
# ─────────────────────────────────────────────────────────────────────────────

SKILL_ALIASES = {
    # Programming languages
    "python": ["python", "python3", "py", "python 3"],
    "c++": ["c++", "cpp", "cplusplus"],
    "c#": ["c#", "csharp", "c sharp"],
    "java": ["java", "java8", "java11", "j2ee"],
    "javascript": ["javascript", "js", "ecmascript", "nodejs", "node.js"],
    "typescript": ["typescript", "ts"],
    "go": ["go", "golang"],
    "rust": ["rust", "rustlang"],
    "php": ["php", "php7", "php8"],
    "ruby": ["ruby", "ruby on rails", "rails"],
    "swift": ["swift", "swiftui"],
    "kotlin": ["kotlin", "kt"],
    "r": ["r", "r language", "rstudio"],
    "matlab": ["matlab", "octave"],
    "sql": ["sql", "mysql", "postgresql", "postgres", "mssql", "sql server", "pl/sql", "tsql"],
    "nosql": ["nosql", "mongodb", "cassandra", "dynamodb", "firestore"],

    # Data Science & ML
    "machine learning": ["machine learning", "ml", "predictive modeling", "supervised learning", "unsupervised learning"],
    "deep learning": ["deep learning", "dl", "neural networks", "cnn", "rnn", "lstm", "transformers"],
    "natural language processing": ["natural language processing", "nlp", "text mining", "text analytics", "nlu", "nlg"],
    "computer vision": ["computer vision", "cv", "image recognition", "object detection", "image segmentation"],
    "object detection": ["object detection", "yolo", "detection", "faster r-cnn", "ssd"],
    "data cleaning": ["data cleaning", "data preprocessing", "data wrangling", "data munging", "etl"],
    "data visualization": ["data visualization", "dataviz", "tableau", "power bi", "matplotlib", "seaborn", "plotly"],
    "statistics": ["statistics", "statistical analysis", "hypothesis testing", "anova", "regression"],
    "pandas": ["pandas", "python pandas", "pd"],
    "numpy": ["numpy", "np", "numeric python"],
    "scikit-learn": ["scikit-learn", "sklearn", "scikit learn"],
    "tensorflow": ["tensorflow", "tf", "keras", "tf2"],
    "pytorch": ["pytorch", "torch", "py torch"],
    "spark": ["spark", "apache spark", "pyspark", "spark sql"],

    # Web & Cloud
    "react": ["react", "reactjs", "react.js"],
    "angular": ["angular", "angularjs", "angular 2+"],
    "vue": ["vue", "vuejs", "vue.js"],
    "django": ["django", "django rest", "django framework"],
    "flask": ["flask", "flask python"],
    "fastapi": ["fastapi", "fast api"],
    "docker": ["docker", "container", "dockerfile", "docker compose"],
    "kubernetes": ["kubernetes", "k8s", "kube"],
    "aws": ["aws", "amazon web services", "ec2", "s3", "lambda", "cloudformation"],
    "azure": ["azure", "microsoft azure", "azure devops"],
    "gcp": ["gcp", "google cloud platform", "google cloud"],
    "git": ["git", "github", "gitlab", "bitbucket", "version control"],

    # Soft & Other
    "communication": ["communication", "verbal communication", "written communication", "interpersonal skills"],
    "teamwork": ["teamwork", "collaboration", "team player", "cooperation"],
    "problem solving": ["problem solving", "analytical skills", "critical thinking", "troubleshooting"],
    "leadership": ["leadership", "team lead", "mentoring", "coaching"],
    "agile": ["agile", "scrum", "kanban", "sprint", "jira", "agile methodology"],
}

# Seniority keywords
_JUNIOR_KW = {"junior", "entry", "graduate", "intern", "trainee", "jr"}
_SENIOR_KW = {"senior", "lead", "staff", "principal", "sr", "sr.", "architect"}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _blob(job: dict) -> str:
    return " ".join([
        str(job.get("title", "")),
        str(job.get("description", "")),
        str(job.get("location", "")),
        str(job.get("company", "")),
    ]).lower()


# ─────────────────────────────────────────────────────────────────────────────
# Skill normalization (bidirectional alias resolution)
# ─────────────────────────────────────────────────────────────────────────────

def _canonical_skill(skill: str) -> str:
    """Convert any skill to its canonical form. Example: 'NLP' -> 'natural language processing'"""
    skill_lower = skill.lower().strip()
    if skill_lower in SKILL_ALIASES:
        return skill_lower
    for canonical, aliases in SKILL_ALIASES.items():
        if skill_lower in aliases:
            return canonical
    return skill_lower


# ─────────────────────────────────────────────────────────────────────────────
# Fuzzy matching helper
# ─────────────────────────────────────────────────────────────────────────────

def _fuzzy_match(word1: str, word2: str, threshold: float = 0.85) -> bool:
    return difflib.SequenceMatcher(None, word1, word2).ratio() >= threshold


# ─────────────────────────────────────────────────────────────────────────────
# Improved skill matching
# ─────────────────────────────────────────────────────────────────────────────

def _match_skill(blob: str, skill: str) -> float:
    if not skill:
        return 0.0

    canonical = _canonical_skill(skill)
    aliases = list(SKILL_ALIASES.get(canonical, [canonical]))

    if canonical not in aliases:
        aliases.append(canonical)
    original_lower = skill.lower().strip()
    if original_lower not in aliases:
        aliases.append(original_lower)

    blob_words = blob.split()

    for alias in aliases:
        if re.search(rf"\b{re.escape(alias)}\b", blob):
            if canonical == "python":
                return 2.0
            return 1.5
        if alias in blob:
            return 0.75

    for alias in aliases:
        for blob_word in blob_words:
            if len(alias) > 3 and len(blob_word) > 3 and _fuzzy_match(alias, blob_word):
                return 0.6

    return 0.0


def _skill_score(blob: str, skills: List[str]) -> Tuple[float, List[str]]:
    if not skills:
        return 0.0, []

    total = 0.0
    matched = []
    for skill in skills:
        score = _match_skill(blob, skill)
        if score > 0:
            total += score
            matched.append(skill)

    norm = max(min(len(skills), 10), 1)
    raw = total / norm
    return min(raw, 1.0), matched


# ─────────────────────────────────────────────────────────────────────────────
# Other scoring functions
# ─────────────────────────────────────────────────────────────────────────────

def _role_score(blob: str, roles: List[str]) -> float:
    if not roles:
        return 0.0
    hits = 0
    for role in roles:
        for word in role.lower().split():
            if len(word) > 3 and word in blob:
                hits += 1
                break
    return min(hits / len(roles), 1.0)


def _exp_score(blob: str, seniority: str) -> float:
    job_level = "mid"
    text = blob[:300]
    if any(k in text for k in _SENIOR_KW):
        job_level = "senior"
    elif any(k in text for k in _JUNIOR_KW):
        job_level = "junior"

    user_level = seniority.lower()
    if "senior" in user_level:
        user_band = "senior"
    elif "junior" in user_level:
        user_band = "junior"
    else:
        user_band = "mid"

    levels = ["junior", "mid", "senior"]
    if user_band == job_level:
        return 1.0
    if abs(levels.index(user_band) - levels.index(job_level)) == 1:
        return 0.55
    return 0.15


def _loc_score(job: dict, loc_lower: str) -> float:
    if not loc_lower:
        return 0.65

    jloc = (job.get("location", "") or "").lower()
    jsrc = (job.get("source", "") or "").lower()
    is_remote_job = "remote" in jloc or "worldwide" in jloc or "work from home" in jloc

    is_egypt_pref = loc_lower in EGYPT_ALIASES
    # ── BUG 2 FIX: explicit remote preference detection ──────────────────────
    is_remote_pref = "remote" in loc_lower or "worldwide" in loc_lower

    if is_remote_pref:
        # Remote is the PRIMARY goal — remote jobs score 1.0, on-site score 0.0
        if is_remote_job:
            return 1.0
        return 0.0

    if is_egypt_pref:
        if any(a in jloc for a in EGYPT_ALIASES) or jsrc == "wuzzuf":
            return 1.0
        if is_remote_job:
            return 0.55   # remote acceptable as secondary for Egypt preference
        return 0.0

    # Physical city / country preference
    if loc_lower in jloc:
        return 1.0
    if is_remote_job:
        return 0.55
    return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Main scoring function
# ─────────────────────────────────────────────────────────────────────────────

def score_job(job: dict, user_profile: dict, location_pref: str = ""):
    skills = [s.strip() for s in user_profile.get("skills", []) if s.strip()]
    roles = [r.strip() for r in user_profile.get("interested_roles", []) if r.strip()]
    seniority = str(user_profile.get("seniority_level", "mid-level"))

    blob = _blob(job)
    sk_raw, matched = _skill_score(blob, skills)

    # missing skills = skills NOT matched (correct — no false positives)
    missing = [s for s in skills if s not in matched]

    ro_raw = _role_score(blob, roles)
    ex_raw = _exp_score(blob, seniority)
    lc_raw = _loc_score(job, location_pref.lower())

    score = (sk_raw * 50) + (ro_raw * 20) + (ex_raw * 15) + (lc_raw * 15)
    return round(score, 2), matched, missing


# ─────────────────────────────────────────────────────────────────────────────
# Ranking
# ─────────────────────────────────────────────────────────────────────────────

def score_and_rank(
    jobs: List[dict],
    user_profile: dict,
    location_pref: str = "",
    top_n: int = 30,
    source_cap: int = 6,
) -> List[dict]:
    if not jobs:
        return []

    scored = []
    for job in jobs:
        s, matched, missing = score_job(job, user_profile, location_pref)
        scored.append((s, matched, missing, job))

    scored.sort(key=lambda x: x[0], reverse=True)

    buckets = {}
    for s, matched, missing, job in scored:
        src = job.get("source", "Unknown")
        buckets.setdefault(src, [])
        if len(buckets[src]) < source_cap:
            buckets[src].append((s, matched, missing, job))

    diverse = []
    seen = set()

    for rnd in range(source_cap):
        for src_list in buckets.values():
            if rnd < len(src_list):
                s, matched, missing, job = src_list[rnd]
                key = (job.get("title", "").lower()[:40], job.get("company", "").lower()[:30])
                if key not in seen:
                    seen.add(key)
                    out = dict(job)
                    out["_engine_score"] = s
                    out["_matched_skills"] = matched
                    out["_missing_skills"] = missing
                    diverse.append(out)
            if len(diverse) >= top_n:
                break

    return diverse[:top_n]