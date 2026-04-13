"""
semantic_matcher.py  –  Career AI  (v2 – stronger location signal)
===================================================================
Fix vs v1:
  • Location boost raised from +0.10 → +0.30 for matching location.
  • Egypt alias set used consistently (Cairo, Giza, Alexandria all match).
  • Wuzzuf source gets Egypt boost automatically (it only lists Egypt jobs).
  • Non-matching physical locations now receive a -0.10 penalty so they
    genuinely rank below local and remote options.
  • Remote/worldwide jobs get a +0.08 nudge (was +0.06).

Pipeline position
-----------------
Stage 0  SemanticMatcher.rank()         → semantic top-100  (this file)
Stage 1  matching_engine.score_and_rank() → diverse top-30
Stage 2  Groq LLM                       → explanation top-8
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger("semantic_matcher")

DATA_DIR     = Path("data")
CACHE_VECS   = DATA_DIR / "embed_cache.npz"
CACHE_INDEX  = DATA_DIR / "embed_index.json"
COMBINED_CSV = DATA_DIR / "jobs_combined.csv"

MODEL_NAME   = "all-MiniLM-L6-v2"
EMBED_DIM    = 384
BATCH_SIZE   = 64

EGYPT_ALIASES = {"egypt", "cairo", "giza", "alexandria", "مصر", "القاهرة"}


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _job_key(job: dict) -> str:
    raw = f"{job.get('title','')[:60]}|{job.get('company','')[:40]}"
    return hashlib.md5(raw.encode()).hexdigest()


def _job_text(job: dict) -> str:
    title = str(job.get("title",       "") or "")
    desc  = str(job.get("description", "") or "")[:400]
    loc   = str(job.get("location",    "") or "")
    src   = str(job.get("source",      "") or "")
    return f"{title}. {title}. {desc} Location: {loc}. Source: {src}".strip()


def _profile_text(user_profile: dict, location_pref: str = "") -> str:
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
    sims = matrix @ query_vec
    return sims.astype(np.float32)


# ══════════════════════════════════════════════════════════════════════════════
# Embedding cache
# ══════════════════════════════════════════════════════════════════════════════

class _EmbedCache:
    def __init__(self):
        self.keys:    list[str]  = []
        self.vectors: np.ndarray = np.empty((0, EMBED_DIM), dtype=np.float32)
        self._loaded = False

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
        key_idx  = {k: i for i, k in enumerate(self.keys)}
        idxs     = [key_idx[k] for k in keys if k in key_idx]
        ordered  = [k for k in keys if k in key_idx]
        if not idxs:
            return [], np.empty((0, EMBED_DIM), dtype=np.float32)
        return ordered, self.vectors[idxs]


# ══════════════════════════════════════════════════════════════════════════════
# Main class
# ══════════════════════════════════════════════════════════════════════════════

class SemanticMatcher:
    def __init__(self, model_name: str = MODEL_NAME):
        self._model      = None
        self._model_name = model_name
        self._cache      = _EmbedCache()
        self._cache.load()

    def _load_model(self):
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
        self._load_model()
        vecs = self._model.encode(
            texts,
            batch_size=BATCH_SIZE,
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return vecs.astype(np.float32)

    def _ensure_cached(self, jobs: list[dict]) -> None:
        all_keys = [_job_key(j) for j in jobs]
        missing  = self._cache.missing_keys(all_keys)
        if not missing:
            return
        missing_set = set(missing)
        new_jobs    = [j for j in jobs if _job_key(j) in missing_set]
        new_texts   = [_job_text(j) for j in new_jobs]
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
        location_pref: str = "",
        top_n:         int = 100,
        source_cap:    int = 15,
    ) -> list[dict]:
        """
        Rank all jobs by semantic similarity, then apply location boost/penalty.

        FIX v2: location scoring is now meaningful:
          +0.30  for exact location match (was +0.10)
          +0.30  for Egypt alias match OR Wuzzuf source when pref is Egypt
          +0.08  for remote/worldwide (was +0.06)
          -0.10  for non-matching physical location (NEW — creates separation)
        """
        if not jobs:
            return []

        self._ensure_cached(jobs)

        profile_text = _profile_text(user_profile, location_pref)
        query_vec    = self._embed([profile_text])[0]

        all_keys             = [_job_key(j) for j in jobs]
        ordered_keys, matrix = self._cache.get_vectors_for_keys(all_keys)

        if matrix.size == 0:
            logger.warning("No cached vectors found — returning jobs unsorted")
            return jobs[:top_n]

        sims = _cosine_similarity(query_vec, matrix)

        # ── Location boost / penalty  ─────────────────────────────────────
        # FIX: boost is now 3× larger (+0.30 vs old +0.10) so it can
        # actually reorder results when two jobs have similar semantic scores.
        # A penalty for non-matching physical locations is new — it creates
        # clear separation between local, remote, and irrelevant jobs.
        loc_lower    = location_pref.lower() if location_pref else ""
        is_egypt_pref = loc_lower in EGYPT_ALIASES
        key_to_sim   = dict(zip(ordered_keys, sims))

        for job in jobs:
            k    = _job_key(job)
            if k not in key_to_sim:
                continue
            jloc = (job.get("location", "") or "").lower()
            jsrc = (job.get("source",   "") or "").lower()
            curr = key_to_sim[k]

            if not loc_lower:
                # No preference set — small remote bonus, no penalties
                if "remote" in jloc or "worldwide" in jloc:
                    key_to_sim[k] = min(curr + 0.08, 1.0)
                continue

            if is_egypt_pref:
                if any(a in jloc for a in EGYPT_ALIASES) or jsrc == "wuzzuf":
                    # Strong Egypt match
                    key_to_sim[k] = min(curr + 0.30, 1.0)
                elif "remote" in jloc or "worldwide" in jloc:
                    # Remote is acceptable when Egypt is preferred
                    key_to_sim[k] = min(curr + 0.08, 1.0)
                else:
                    # Different country/city — push down
                    key_to_sim[k] = max(curr - 0.10, 0.0)
            else:
                if loc_lower in jloc:
                    # Exact city/country match
                    key_to_sim[k] = min(curr + 0.30, 1.0)
                elif "remote" in jloc or "worldwide" in jloc:
                    key_to_sim[k] = min(curr + 0.08, 1.0)
                else:
                    # Non-matching physical location — penalise
                    key_to_sim[k] = max(curr - 0.10, 0.0)

        # ── Sort and diversify  ───────────────────────────────────────────
        sorted_jobs = sorted(
            jobs,
            key=lambda j: key_to_sim.get(_job_key(j), 0.0),
            reverse=True,
        )

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

        for j in sorted_jobs:
            if len(diverse) >= top_n:
                break
            k = (_job_key(j),)
            if k not in seen:
                seen.add(k)
                diverse.append(j)

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
        self._load_model()
        profile_text = _profile_text(user_profile, location_pref)
        job_t        = _job_text(job)
        vecs = self._embed([profile_text, job_t])
        sim  = float(np.dot(vecs[0], vecs[1]))
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
# Singleton + convenience wrapper
# ══════════════════════════════════════════════════════════════════════════════

_singleton: Optional[SemanticMatcher] = None


def get_matcher() -> SemanticMatcher:
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
    return get_matcher().rank(jobs, user_profile, location_pref, top_n=top_n)


if __name__ == "__main__":
    sample_jobs = [
        {"title": "Machine Learning Engineer",  "company": "OpenAI",  "description": "Build LLMs, PyTorch, Python",     "location": "Remote",      "source": "RemoteOK"},
        {"title": "Computer Vision Researcher", "company": "NVIDIA",  "description": "Deep learning, OpenCV, C++",      "location": "Cairo, Egypt", "source": "Wuzzuf"},
        {"title": "Frontend Developer",         "company": "Acme",    "description": "React, TypeScript, CSS",          "location": "Remote",      "source": "Remotive"},
        {"title": "Backend Engineer",           "company": "Stripe",  "description": "Python, FastAPI, PostgreSQL",     "location": "Remote",      "source": "Himalayas"},
        {"title": "Data Scientist",             "company": "Google",  "description": "ML, statistics, Python, sklearn", "location": "Remote",      "source": "The Muse"},
        {"title": "NLP Scientist",              "company": "HF",      "description": "Transformers, BERT, NLP, Python", "location": "Paris",       "source": "Arbeitnow"},
        {"title": "React Native Developer",     "company": "Startup", "description": "Mobile, JS, React, Redux",       "location": "Alexandria",  "source": "Wuzzuf"},
        {"title": "Sales Manager",              "company": "Corp",    "description": "CRM, targets, B2B sales",        "location": "Dubai",       "source": "Jobicy"},
    ]
    profile = {
        "skills": ["Python", "PyTorch", "CV", "OpenCV", "machine learning"],
        "interested_roles": ["ML engineer", "computer vision engineer"],
        "seniority_level": "Senior",
        "experience_years": 4,
    }
    print("=== Semantic rank test (location=Egypt) ===")
    matcher = SemanticMatcher()
    results = matcher.rank(sample_jobs, profile, location_pref="Egypt", top_n=8)
    for i, j in enumerate(results, 1):
        score = j.get("_semantic_score", 0)
        print(f"  {i}. [{score:.3f}] {j['title']:35} @ {j['company']:10}  ({j['location']})")