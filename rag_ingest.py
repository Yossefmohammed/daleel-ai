"""
RAG Ingest Module
Builds two indexes from your data:
  1. ChromaDB vector store  (semantic similarity search)
  2. NetworkX knowledge graph (entity co-occurrence, multi-hop traversal)

Sources ingested:
  - data/jobs_combined.csv  (or data/jobs.csv fallback)
  - docs/*.pdf              (any PDF documents you drop in)
"""

import os
import re
import json
import time
import logging
import pandas as pd
import networkx as nx
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
DB_DIR        = "db"
GRAPH_PATH    = "db/knowledge_graph.json"
EMBED_MODEL   = "sentence-transformers/all-MiniLM-L6-v2"   # small & fast
CHUNK_SIZE    = 400
CHUNK_OVERLAP = 80

JOB_CSV_PATHS = [
    "data/jobs_combined.csv",
    "data/jobs.csv",
    "docs/ai_jobs_market_2025_2026.csv",
]


# ── Text chunker (no LangChain needed) ────────────────────────────────────────
def _chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    words = text.split()
    chunks, start = [], 0
    while start < len(words):
        end = min(start + size, len(words))
        chunks.append(" ".join(words[start:end]))
        start += size - overlap
    return [c for c in chunks if len(c.strip()) > 30]


# ── Entity extractor (regex-based, no spaCy required) ─────────────────────────
SKILL_KEYWORDS = {
    "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust",
    "react", "vue", "angular", "node", "django", "flask", "fastapi", "spring",
    "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "docker", "kubernetes", "aws", "azure", "gcp", "terraform", "ci/cd",
    "machine learning", "deep learning", "nlp", "data science", "ai",
    "devops", "backend", "frontend", "full stack", "mobile", "ios", "android",
    "remote", "cairo", "egypt", "giza", "alexandria",
    "junior", "senior", "mid-level", "manager", "lead", "intern",
}

def extract_entities(text: str) -> list[str]:
    """Pull skills, locations, seniority levels from text."""
    text_lower = text.lower()
    found = set()

    # Match known keywords
    for kw in SKILL_KEYWORDS:
        if kw in text_lower:
            found.add(kw)

    # Match capitalized words (likely company/job names)
    caps = re.findall(r'\b[A-Z][a-zA-Z]{2,}\b', text)
    for word in caps:
        if len(word) <= 20:
            found.add(word.lower())

    return list(found)[:15]   # cap to 15 per chunk


# ── CSV → documents ───────────────────────────────────────────────────────────
def _load_jobs_as_docs() -> list[dict]:
    """Convert job CSV rows into text documents."""
    for path in JOB_CSV_PATHS:
        if os.path.exists(path):
            try:
                df = pd.read_csv(path).fillna("")
                docs = []
                for _, row in df.iterrows():
                    title    = str(row.get("job_title", row.get("title", "Job")))
                    company  = str(row.get("company", row.get("company_name", "")))
                    location = str(row.get("location", row.get("city", "")))
                    tags     = str(row.get("tags", row.get("required_skills", "")))
                    desc     = str(row.get("description", ""))
                    remote   = str(row.get("remote_work", ""))
                    salary   = str(row.get("salary_range", row.get("annual_salary_usd", "")))
                    source   = str(row.get("source", ""))
                    url      = str(row.get("url", ""))

                    text = (
                        f"Job Title: {title}\n"
                        f"Company: {company}\n"
                        f"Location: {location} {remote}\n"
                        f"Skills/Tags: {tags}\n"
                        f"Description: {desc[:300]}\n"
                        f"Salary: {salary}\n"
                        f"Source: {source}\n"
                        f"URL: {url}"
                    ).strip()

                    docs.append({
                        "text": text,
                        "metadata": {
                            "source": source or "jobs_csv",
                            "job_title": title,
                            "company": company,
                            "location": location,
                            "url": url,
                            "type": "job_listing",
                        }
                    })
                logger.info(f"✅ Loaded {len(docs)} job docs from {path}")
                return docs
            except Exception as e:
                logger.warning(f"⚠️  Could not load {path}: {e}")
    return []


# ── PDF → documents ───────────────────────────────────────────────────────────
def _load_pdfs_as_docs() -> list[dict]:
    docs = []
    docs_path = Path("docs")
    if not docs_path.exists():
        return docs
    try:
        from pypdf import PdfReader
    except ImportError:
        return docs

    for pdf_file in docs_path.glob("**/*.pdf"):
        try:
            reader = PdfReader(str(pdf_file))
            text = "\n".join(p.extract_text() or "" for p in reader.pages)
            for chunk in _chunk_text(text):
                docs.append({
                    "text": chunk,
                    "metadata": {
                        "source": pdf_file.name,
                        "type": "pdf_document",
                    }
                })
            logger.info(f"✅ Loaded PDF: {pdf_file.name}")
        except Exception as e:
            logger.warning(f"⚠️  PDF {pdf_file.name}: {e}")
    return docs


# ── Build everything ──────────────────────────────────────────────────────────
def build_index(progress_callback=None) -> dict:
    """
    Build ChromaDB vector store + NetworkX knowledge graph.
    Returns stats dict.
    """
    import chromadb
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

    os.makedirs(DB_DIR, exist_ok=True)

    def _progress(pct: int, msg: str):
        logger.info(f"  [{pct}%] {msg}")
        if progress_callback:
            progress_callback(pct, msg)

    # ── 1. Load data ──────────────────────────────────────────────────────────
    _progress(5, "Loading job listings...")
    job_docs = _load_jobs_as_docs()

    _progress(15, "Loading PDF documents...")
    pdf_docs = _load_pdfs_as_docs()

    all_raw = job_docs + pdf_docs
    if not all_raw:
        raise ValueError("No data found! Scrape jobs first or add PDFs to docs/ folder.")

    _progress(20, f"Loaded {len(all_raw)} documents total")

    # ── 2. Chunk job docs (PDFs already chunked) ──────────────────────────────
    _progress(25, "Chunking documents...")
    chunks = []
    for doc in all_raw:
        if doc["metadata"].get("type") == "job_listing":
            # Job listings are short — keep as single chunk
            chunks.append(doc)
        else:
            for chunk_text in _chunk_text(doc["text"]):
                chunks.append({"text": chunk_text, "metadata": doc["metadata"]})

    _progress(30, f"{len(chunks)} chunks ready")

    # ── 3. ChromaDB vector store ──────────────────────────────────────────────
    _progress(35, "Initializing embedding model...")
    embed_fn = SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)

    _progress(40, "Building ChromaDB vector store...")
    client = chromadb.PersistentClient(path=DB_DIR)

    # Delete old collection if exists
    try:
        client.delete_collection("career_rag")
    except Exception:
        pass

    collection = client.create_collection(
        name="career_rag",
        embedding_function=embed_fn,
        metadata={"hnsw:space": "cosine"},
    )

    # Batch insert (ChromaDB handles up to 5461 per batch)
    BATCH = 500
    total_batches = (len(chunks) + BATCH - 1) // BATCH
    for i in range(0, len(chunks), BATCH):
        batch = chunks[i:i + BATCH]
        collection.add(
            ids=[f"chunk_{i + j}" for j in range(len(batch))],
            documents=[c["text"] for c in batch],
            metadatas=[c["metadata"] for c in batch],
        )
        pct = 40 + int(30 * (i / len(chunks)))
        _progress(pct, f"Embedded batch {i // BATCH + 1}/{total_batches}")

    _progress(70, f"✅ Vector store: {collection.count()} chunks")

    # ── 4. Knowledge graph ────────────────────────────────────────────────────
    _progress(72, "Building knowledge graph...")
    G = nx.Graph()

    for idx, chunk in enumerate(chunks):
        chunk_id = f"chunk_{idx}"
        G.add_node(chunk_id, type="chunk", text=chunk["text"][:100])

        entities = extract_entities(chunk["text"])
        for entity in entities:
            if not G.has_node(entity):
                G.add_node(entity, type="entity")
            G.add_edge(chunk_id, entity, weight=1)

        # Connect entities that co-occur in same chunk
        for i in range(len(entities)):
            for j in range(i + 1, len(entities)):
                e1, e2 = entities[i], entities[j]
                if G.has_edge(e1, e2):
                    G[e1][e2]["weight"] += 1
                else:
                    G.add_edge(e1, e2, weight=1)

        if idx % 500 == 0:
            pct = 72 + int(20 * idx / len(chunks))
            _progress(pct, f"Graph: {idx}/{len(chunks)} chunks processed")

    # ── 5. Save graph ─────────────────────────────────────────────────────────
    _progress(93, "Saving knowledge graph...")
    graph_data = nx.node_link_data(G)
    with open(GRAPH_PATH, "w", encoding="utf-8") as f:
        json.dump(graph_data, f)

    stats = {
        "chunks": len(chunks),
        "vector_count": collection.count(),
        "graph_nodes": G.number_of_nodes(),
        "graph_edges": G.number_of_edges(),
        "job_docs": len(job_docs),
        "pdf_docs": len(pdf_docs),
        "built_at": datetime.now().isoformat(),
    }

    _progress(100, f"✅ Done — {stats['chunks']} chunks, {stats['graph_nodes']} nodes, {stats['graph_edges']} edges")
    logger.info(f"RAG index stats: {stats}")
    return stats


def load_graph() -> nx.Graph | None:
    """Load saved knowledge graph from disk."""
    if not os.path.exists(GRAPH_PATH):
        return None
    try:
        with open(GRAPH_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        G = nx.node_link_graph(data)
        logger.info(f"✅ Graph loaded: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
        return G
    except Exception as e:
        logger.warning(f"⚠️  Could not load graph: {e}")
        return None


def get_collection():
    """Load ChromaDB collection."""
    import chromadb
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
    client = chromadb.PersistentClient(path=DB_DIR)
    embed_fn = SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
    return client.get_collection("career_rag", embedding_function=embed_fn)


def index_exists() -> bool:
    chroma_ok = os.path.exists(os.path.join(DB_DIR, "chroma.sqlite3"))
    graph_ok  = os.path.exists(GRAPH_PATH)
    return chroma_ok and graph_ok