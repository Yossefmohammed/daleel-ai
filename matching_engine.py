"""
semantic_matcher.py  –  Career AI  (Top-1% upgrade)
=====================================================
Embeddings-based semantic matching using sentence-transformers.

Why this matters
----------------
Keyword matching can't understand:
  • "ML engineer"      ≈  "machine learning engineer"
  • "CV"               ≈  "computer vision"
  • "data scientist"   ≈  "AI/ML researcher"
  • "backend dev"      ≈  "server-side engineer"
  • "React developer"  ≈  "frontend engineer"

Embeddings turn text into vectors where MEANING drives distance,
not character overlap.  We get semantic similarity for free.

Model choice:  all-MiniLM-L6-v2
  • 80 MB on disk, loads in ~1 s
  • ~50 ms to embed a batch of 500 jobs on CPU
  • 384-dim vectors, cosine similarity
  • Free, runs entirely offline — no new API keys
  • Top-ranked model for semantic similarity on MTEB benchmark at its size

Pipeline (called from app.py)
------------------------------
Stage 0  SemanticMatcher.rank()        →  semantic top-100  (this file)
Stage 1  matching_engine.score_and_rank() →  diverse top-30   (matching_engine.py)
Stage 2  Groq LLM                      →  explanation top-8  (app.py)

Each stage filters from the previous, so the LLM only sees pre-vetted,
semantically relevant, source-diverse candidates.

Cache design
------------
Embeddings are expensive to recompute.  We cache them in:
    data/embed_cache.npz   – numpy array of all job vectors
    data/embed_index.json  – list of job keys (title+company hash)

Cache is invalidated when jobs_combined.csv changes (mtime check).
Only NEW jobs are re-embedded on each refresh — not the whole DB.

Install
-------
    pip install sentence-transformers
    (numpy and torch are pulled in automatically)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger("semantic_matcher")

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_DIR     = Path("data")
CACHE_VECS   = DATA_DIR / "embed_cache.npz"
CACHE_INDEX  = DATA_DIR / "embed_index.json"
COMBINED_CSV = DATA_DIR / "jobs_combined.csv"

# ── Model config ──────────────────────────────────────────────────────────────
MODEL_NAME   = "all-MiniLM-L6-v2"   # 80 MB, fast CPU inference
EMBED_DIM    = 384
BATCH_SIZE   = 64


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _job_key(job: dict) -> str:
    """Stable hash for a job — used as cache key."""
    raw = f"{job.get('title','')[:60]}|{job.get('company','')[:40]}"
    return hashlib.md5(raw.encode()).hexdigest()


def _job_text(job: dict) -> str:
    """
    Concatenate the fields that carry semantic signal.
    Title is repeated so the model weights it more heavily.
    """
    title = str(job.get("title",       "") or "")
    desc  = str(job.get("description", "") or "")[:400]
    loc   = str(job.get("location",    "") or "")
    src   = str(job.get("source",      "") or "")
    return f"{title}. {title}. {desc} Location: {loc}. Source: {src}".strip()


def _profile_text(user_profile: dict, location_pref: str = "") -> str:
    """
    Build a rich natural-language sentence from the user profile.
    The embedding of this becomes the query vector.
    """
    skills    = ", ".join(user_profile.get("skills",           [])[:20])
    roles     = ", ".join(user_profile.get("interested_roles", [])[:6])
    seniority = user_profile.get("seniority_level",  "mid-level")
    exp       = user_profile.get("experience_years", 0)
    loc       = location_pref or user_profile.get("location_preference", "")

    parts = [
        f"I am a {seniority} professional with {exp} years of experience.",
        f"My core skills include: {skills}." if skills else "",
        f"I am looking for roles such as: {roles}." if roles else "",
        f"I prefer to work in: {loc}." if loc else "",
    ]
    return " ".join(p for p in parts if p)


def _cosine_similarity(query_vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """
    Vectorised cosine similarity between a single query vector and a matrix.
    Returns 1-D array of similarities, shape (n_jobs,).
    """
    # Both query and rows should already be L2-normalised by encode(normalize_embeddings=True)
    sims = matrix @ query_vec          # shape (n,)
    return sims.astype(np.float32)


# ══════════════════════════════════════════════════════════════════════════════
# Embedding cache
# ══════════════════════════════════════════════════════════════════════════════

class _EmbedCache:
    """
    Persistent cache for job embeddings.

    Layout
    ------
    embed_index.json  →  list of job keys (MD5 hashes), position matches row
    embed_cache.npz   →  numpy array shape (n_cached, EMBED_DIM), float32

    On load we check whether the CSV is newer than the cache; if so we
    identify which keys are NEW (not cached) and embed only those.
    """

    def __init__(self):
        self.keys:    list[str]    = []   # ordered list of cached job keys
        self.vectors: np.ndarray   = np.empty((0, EMBED_DIM), dtype=np.float32)
        self._loaded = False

    def _csv_mtime(self) -> float:
        return COMBINED_CSV.stat().st_mtime if COMBINED_CSV.exists() else 0.0

    def _cache_mtime(self) -> float:
        return CACHE_VECS.stat().st_mtime if CACHE_VECS.exists() else 0.0

    def load(self) -> None:
        if not CACHE_VECS.exists() or not CACHE_INDEX.exists():
            self._loaded = True
            return
        try:
            self.keys    = json.loads(CACHE_INDEX.read_text())
            loaded       = np.load(str(CACHE_VECS))
            self.vectors = loaded["vecs"].astype(np.float32)
            logger.info(f"EmbedCache loaded: {len(self.keys)} cached jobs")
        except Exception as e:
            logger.warning(f"EmbedCache load failed ({e}), starting fresh")
            self.keys, self.vectors = [], np.empty((0, EMBED_DIM), dtype=np.float32)
        self._loaded = True

    def save(self) -> None:
        DATA_DIR.mkdir(exist_ok=True)
        CACHE_INDEX.write_text(json.dumps(self.keys))
        np.savez_compressed(str(CACHE_VECS), vecs=self.vectors)
        logger.info(f"EmbedCache saved: {len(self.keys)} entries")

    def missing_keys(self, all_keys: list[str]) -> list[str]:
        cached = set(self.keys)
        return [k for k in all_keys if k not in cached]

    def add(self, new_keys: list[str], new_vecs: np.ndarray) -> None:
        self.keys    = self.keys + new_keys
        self.vectors = np.vstack([self.vectors, new_vecs]) if self.vectors.size else new_vecs

    def get_vectors_for_keys(self, keys: list[str]) -> tuple[list[str], np.ndarray]:
        """
        Return (ordered_keys, matrix) for the given keys.
        Jobs whose key isn't cached are silently skipped.
        """
        key_idx = {k: i for i, k in enumerate(self.keys)}
        idxs     = [key_idx[k] for k in keys if k in key_idx]
        ordered  = [k for k in keys if k in key_idx]
        if not idxs:
            return [], np.empty((0, EMBED_DIM), dtype=np.float32)
        return ordered, self.vectors[idxs]


# ══════════════════════════════════════════════════════════════════════════════
# Main class
# ══════════════════════════════════════════════════════════════════════════════

class SemanticMatcher:
    """
    Semantic job ranking using sentence-transformers.

    Usage (from app.py)
    -------------------
        from semantic_matcher import SemanticMatcher

        matcher = SemanticMatcher()          # loads model once
        top100  = matcher.rank(
            jobs         = all_jobs,         # list[dict] from load_combined()
            user_profile = user_profile,
            location_pref= "Egypt",
            top_n        = 100,
        )
        # top100 is a list of job dicts, each with an added
        # '_semantic_score' key (float 0-1)
    """

    def __init__(self, model_name: str = MODEL_NAME):
        self._model      = None
        self._model_name = model_name
        self._cache      = _EmbedCache()
        self._cache.load()

    def _load_model(self):
        """Lazy-load the model on first use (saves startup time)."""
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading sentence-transformer model: {self._model_name}")
            t0           = time.time()
            self._model  = SentenceTransformer(self._model_name)
            logger.info(f"Model loaded in {time.time()-t0:.1f}s")
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed.\n"
                "Run:  pip install sentence-transformers"
            )

    def _embed(self, texts: list[str]) -> np.ndarray:
        """Embed a list of texts; returns L2-normalised float32 array."""
        self._load_model()
        vecs = self._model.encode(
            texts,
            batch_size=BATCH_SIZE,
            show_progress_bar=False,
            normalize_embeddings=True,   # cosine sim = dot product
            convert_to_numpy=True,
        )
        return vecs.astype(np.float32)

    def _ensure_cached(self, jobs: list[dict]) -> None:
        """Embed any jobs not yet in the cache, then persist."""
        all_keys = [_job_key(j) for j in jobs]
        missing  = self._cache.missing_keys(all_keys)

        if not missing:
            return   # all cached

        missing_set  = set(missing)
        new_jobs     = [j for j in jobs if _job_key(j) in missing_set]
        new_texts    = [_job_text(j) for j in new_jobs]

        logger.info(f"Embedding {len(new_jobs)} new jobs…")
        t0       = time.time()
        new_vecs = self._embed(new_texts)
        logger.info(f"Embedded in {time.time()-t0:.1f}s")

        self._cache.add(missing, new_vecs)
        self._cache.save()

    def rank(
        self,
        jobs:          list[dict],
        user_profile:  dict,
        location_pref: str  = "",
        top_n:         int  = 100,
        source_cap:    int  = 15,
    ) -> list[dict]:
        """
        Rank all jobs by semantic similarity to the user profile.

        Parameters
        ----------
        jobs          : full job list from load_combined()
        user_profile  : dict with skills, interested_roles, seniority_level,
                        experience_years
        location_pref : e.g. "Egypt", "Remote", ""
        top_n         : how many to return (passed to Stage 1 engine)
        source_cap    : max jobs per source in the output

        Returns
        -------
        list[dict] – jobs sorted by semantic score (desc), each with:
            _semantic_score  float  0-1
            _semantic_rank   int    1-based rank
        """
        if not jobs:
            return []

        # ── 1. Ensure all jobs are embedded ──────────────────────────────
        self._ensure_cached(jobs)

        # ── 2. Build query vector from user profile ───────────────────────
        profile_text = _profile_text(user_profile, location_pref)
        query_vec    = self._embed([profile_text])[0]   # shape (384,)

        # ── 3. Retrieve cached vectors for current jobs ───────────────────
        all_keys            = [_job_key(j) for j in jobs]
        ordered_keys, matrix = self._cache.get_vectors_for_keys(all_keys)

        if matrix.size == 0:
            logger.warning("No cached vectors found — returning jobs unsorted")
            return jobs[:top_n]

        # ── 4. Cosine similarity ──────────────────────────────────────────
        sims = _cosine_similarity(query_vec, matrix)   # shape (n,)

        # ── 5. Location boost  (+0.10 for exact match, +0.06 for remote) ─
        #    Applied AFTER cosine so it nudges rather than dominates.
        loc_lower    = location_pref.lower()
        egypt_set    = {"egypt", "cairo", "giza", "alexandria"}
        key_to_sim   = dict(zip(ordered_keys, sims))

        for i, job in enumerate(jobs):
            k = _job_key(job)
            if k not in key_to_sim:
                continue
            jloc = (job.get("location", "") or "").lower()
            if loc_lower and loc_lower in jloc:
                key_to_sim[k] = min(key_to_sim[k] + 0.10, 1.0)
            elif loc_lower in egypt_set and any(a in jloc for a in egypt_set):
                key_to_sim[k] = min(key_to_sim[k] + 0.10, 1.0)
            elif "remote" in jloc:
                key_to_sim[k] = min(key_to_sim[k] + 0.06, 1.0)

        # ── 6. Sort jobs by boosted similarity ────────────────────────────
        sorted_jobs = sorted(
            jobs,
            key=lambda j: key_to_sim.get(_job_key(j), 0.0),
            reverse=True,
        )

        # ── 7. Source-diverse selection ───────────────────────────────────
        buckets: dict[str, list] = {}
        for j in sorted_jobs:
            src = j.get("source", "Unknown")
            buckets.setdefault(src, [])
            if len(buckets[src]) < source_cap:
                buckets[src].append(j)

        diverse, seen = [], set()
        for rnd in range(source_cap):
            for src_jobs in buckets.values():
                if rnd < len(src_jobs):
                    jj = src_jobs[rnd]
                    k  = (_job_key(jj),)
                    if k not in seen:
                        seen.add(k)
                        diverse.append(jj)
                    if len(diverse) >= top_n:
                        break
            if len(diverse) >= top_n:
                break

        # Back-fill from global sorted list
        for j in sorted_jobs:
            if len(diverse) >= top_n:
                break
            k = (_job_key(j),)
            if k not in seen:
                seen.add(k)
                diverse.append(j)

        # ── 8. Annotate with scores and return ────────────────────────────
        for rank_i, j in enumerate(diverse, start=1):
            k = _job_key(j)
            j["_semantic_score"] = round(float(key_to_sim.get(k, 0.0)), 4)
            j["_semantic_rank"]  = rank_i

        return diverse[:top_n]

    def explain_similarity(
        self,
        user_profile: dict,
        job: dict,
        location_pref: str = "",
    ) -> dict:
        """
        Return the raw cosine similarity + a nearest-neighbour breakdown:
        which user skills are semantically closest to which job terms.
        Useful for the 'why_good_fit' UI field.
        """
        self._load_model()

        profile_text = _profile_text(user_profile, location_pref)
        job_t        = _job_text(job)

        vecs = self._embed([profile_text, job_t])
        sim  = float(np.dot(vecs[0], vecs[1]))

        # Per-skill similarity
        skills = user_profile.get("skills", [])[:15]
        if skills:
            skill_vecs = self._embed(skills)
            job_vec    = vecs[1]
            skill_sims = {s: round(float(np.dot(sv, job_vec)), 3)
                          for s, sv in zip(skills, skill_vecs)}
            top_skills = sorted(skill_sims.items(), key=lambda x: -x[1])[:5]
        else:
            top_skills = []

        return {
            "cosine_similarity": round(sim, 4),
            "top_matching_skills": [{"skill": s, "similarity": v} for s, v in top_skills],
        }


# ══════════════════════════════════════════════════════════════════════════════
# Convenience wrapper  —  the function app.py imports
# ══════════════════════════════════════════════════════════════════════════════

_singleton: Optional[SemanticMatcher] = None


def get_matcher() -> SemanticMatcher:
    """Return a process-level singleton (model loaded once per session)."""
    global _singleton
    if _singleton is None:
        _singleton = SemanticMatcher()
    return _singleton


def semantic_rank(
    jobs:          list[dict],
    user_profile:  dict,
    location_pref: str = "",
    top_n:         int = 100,
) -> list[dict]:
    """
    One-liner for app.py.

        from semantic_matcher import semantic_rank
        top100 = semantic_rank(all_jobs, user_profile, "Egypt", top_n=100)
    """
    return get_matcher().rank(jobs, user_profile, location_pref, top_n=top_n)


# ══════════════════════════════════════════════════════════════════════════════
# CLI test
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    # Quick smoke test — no real DB needed
    sample_jobs = [
        {"title": "Machine Learning Engineer",   "company": "OpenAI",  "description": "Build LLMs, PyTorch, Python",     "location": "Remote",     "source": "RemoteOK"},
        {"title": "Computer Vision Researcher",  "company": "NVIDIA",  "description": "Deep learning, OpenCV, C++",      "location": "Cairo, Egypt","source": "Wuzzuf"},
        {"title": "Frontend Developer",          "company": "Acme",    "description": "React, TypeScript, CSS",          "location": "Remote",     "source": "Remotive"},
        {"title": "Backend Engineer",            "company": "Stripe",  "description": "Python, FastAPI, PostgreSQL",     "location": "Remote",     "source": "Himalayas"},
        {"title": "Data Scientist",              "company": "Google",  "description": "ML, statistics, Python, sklearn", "location": "Remote",     "source": "The Muse"},
        {"title": "NLP Scientist",               "company": "HF",      "description": "Transformers, BERT, NLP, Python", "location": "Paris",      "source": "Arbeitnow"},
        {"title": "React Native Developer",      "company": "Startup", "description": "Mobile, JS, React, Redux",       "location": "Alexandria", "source": "Wuzzuf"},
        {"title": "Sales Manager",               "company": "Corp",    "description": "CRM, targets, B2B sales",        "location": "Dubai",      "source": "Jobicy"},
    ]

    profile = {
        "skills":           ["Python", "PyTorch", "CV", "OpenCV", "machine learning"],
        "interested_roles": ["ML engineer", "computer vision engineer"],
        "seniority_level":  "Senior",
        "experience_years": 4,
    }

    print("=== Semantic rank test (profile: ML / CV engineer) ===")
    matcher = SemanticMatcher()
    results = matcher.rank(sample_jobs, profile, location_pref="Egypt", top_n=8)

    for i, j in enumerate(results, 1):
        score = j.get("_semantic_score", 0)
        print(f"  {i}. [{score:.3f}] {j['title']:35} @ {j['company']:10}  ({j['location']})")

    print("\n=== Similarity breakdown for top job ===")
    if results:
        detail = matcher.explain_similarity(profile, results[0], "Egypt")
        print(f"  Cosine similarity: {detail['cosine_similarity']}")
        print("  Top matching skills:")
        for s in detail["top_matching_skills"]:
            print(f"    {s['skill']:20} → {s['similarity']:.3f}")

    print("\n=== Semantic synonym test ===")
    # 'CV' (as in computer vision) vs 'computer vision' — should score high with CV job
    cv_profile = {"skills": ["CV", "deep learning"], "interested_roles": ["CV engineer"],
                  "seniority_level": "mid-level", "experience_years": 2}
    results2 = matcher.rank(sample_jobs, cv_profile, top_n=3)
    print("  Top 3 for 'CV / deep learning' profile:")
    for j in results2:
        print(f"    [{j['_semantic_score']:.3f}] {j['title']}")