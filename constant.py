"""
constant.py — single source of truth for all config values.
Import from here instead of scattering magic strings/numbers across files.
"""

# ── Paths ──────────────────────────────────────────────────────────────────────
DB_DIR        = "db"
EMBED_PATH    = "db/embeddings.npy"
CHUNKS_PATH   = "db/chunks.json"
GRAPH_PATH    = "db/knowledge_graph.json"
DOCS_DIR      = "docs"
DATA_DIR      = "data"

JOB_CSV_PATHS = [
    "data/jobs_combined.csv",
    "data/jobs.csv",
    "docs/ai_jobs_market_2025_2026.csv",
]

# ── Models ─────────────────────────────────────────────────────────────────────
EMBED_MODEL   = "sentence-transformers/all-MiniLM-L6-v2"   # 80 MB, fast CPU
GROQ_MODEL    = "llama-3.3-70b-versatile"
GROQ_MODEL_FALLBACK = "gemma2-9b-it"

# ── RAG tuning ─────────────────────────────────────────────────────────────────
CHUNK_SIZE    = 400        # words per chunk
CHUNK_OVERLAP = 80
VECTOR_K      = 7          # top-k from vector search
GRAPH_K       = 6          # max extra chunks from graph BFS
HOP_DEPTH     = 2          # BFS hops in knowledge graph
EMBED_BATCH   = 256        # embedding batch size
MAX_CONTEXT   = 4500       # chars of RAG context sent to LLM

# ── LLM generation ────────────────────────────────────────────────────────────
MAX_TOKENS    = 1400
TEMPERATURE   = 0.72
HISTORY_TURNS = 14         # message turns kept in prompt context

# ── Scraper ────────────────────────────────────────────────────────────────────
REMOTEOK_LIMIT    = 100
ARBEITNOW_PAGES   = 3
MUSE_PAGES        = 2
WUZZUF_PAGES      = 2
CRAWL_DELAY       = 1.5    # seconds between Wuzzuf page requests

WUZZUF_DEFAULT_KEYWORDS = [
    "software engineer", "python developer", "data scientist",
    "frontend developer", "backend developer", "full stack developer",
    "devops engineer", "machine learning", "mobile developer",
]

# ── CV analyzer ────────────────────────────────────────────────────────────────
CV_TEXT_LIMIT = 3500       # chars of CV text sent to LLM

# ── GitHub analyzer ───────────────────────────────────────────────────────────
GH_REPO_LIMIT = 20         # repos to scan for language aggregation

# ── Job matcher ────────────────────────────────────────────────────────────────
JOB_SAMPLE_ROWS   = 10     # rows from CSV pre-filtered before LLM call
JOB_MATCH_RESULTS = 5      # number of matches to return

# ── Skills keyword set (shared by ingest + retriever) ─────────────────────────
SKILL_KEYWORDS = {
    "python","javascript","typescript","java","c++","c#","go","rust","kotlin","swift",
    "react","vue","angular","node","django","flask","fastapi","spring","laravel","rails",
    "sql","postgresql","mysql","mongodb","redis","elasticsearch","cassandra","firebase",
    "docker","kubernetes","aws","azure","gcp","terraform","ci/cd","jenkins","github actions",
    "machine learning","deep learning","nlp","computer vision","data science","ai","llm","rag",
    "devops","sre","backend","frontend","full stack","mobile","ios","android","flutter","react native",
    "remote","hybrid","on-site","cairo","egypt","giza","alexandria","maadi","heliopolis","new cairo",
    "junior","mid-level","senior","lead","staff","principal","manager","director","intern","fresher",
    "agile","scrum","kanban","jira","figma","photoshop","linux","bash","git",
}