"""
constant.py — PathIQ Global Configuration
==========================================
Central place for all configurable constants.
"""

import os
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT_DIR  = Path(__file__).parent
DB_DIR    = ROOT_DIR / "db"
DOCS_DIR  = ROOT_DIR / "docs"
DATA_DIR  = ROOT_DIR / "data"
JOBS_PATH = DATA_DIR / "jobs.csv"

# ── Embedding model ──────────────────────────────────────────────────────────
EMBED_MODEL   = "sentence-transformers/all-mpnet-base-v2"
CHUNK_SIZE    = 500
CHUNK_OVERLAP = 100

# ── Graph RAG ────────────────────────────────────────────────────────────────
GRAPH_PATH   = str(DB_DIR / "knowledge_graph.json")
GRAPH_K      = 5     # max extra chunks from graph expansion
VECTOR_K     = 5     # top-k from vector search
HOP_DEPTH    = 2     # BFS depth in knowledge graph

# ── LLM ─────────────────────────────────────────────────────────────────────
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "deepseek-r1-distill-llama-70b",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "gemma2-9b-it",
]
LLM_TEMPERATURE = 0.75
LLM_MAX_TOKENS  = 700

# ── App identity ─────────────────────────────────────────────────────────────
APP_NAME    = "PathIQ"
APP_TAGLINE = "Career Intelligence Platform"
APP_VERSION = "2.0.0"

# ── Services ─────────────────────────────────────────────────────────────────
SERVICES = {
    "cv":     {"label": "CV Analyzer",     "icon": "📄", "color": "#7c6af5"},
    "github": {"label": "Code Profile",    "icon": "💻", "color": "#2dd4c4"},
    "jobs":   {"label": "Job Matcher",     "icon": "🎯", "color": "#f5a623"},
    "assess": {"label": "Full Assessment", "icon": "📊", "color": "#f56c6c"},
    "rag":    {"label": "Knowledge Chat",  "icon": "🧠", "color": "#56d19e"},
}

# ── History ──────────────────────────────────────────────────────────────────
CHAT_HISTORY_PATH = ROOT_DIR / "chat_history.csv"
FEEDBACK_PATH     = ROOT_DIR / "feedback.csv"