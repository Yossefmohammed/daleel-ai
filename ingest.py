"""
ingest.py  (Graph RAG version)
==============================
Loads PDFs → splits into chunks → creates:
  1. ChromaDB vector store  (unchanged, in ./db/)
  2. Knowledge graph        (new,       in ./db/knowledge_graph.json)

Run standalone:
    python ingest.py
"""

import os
import time
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

from graph_builder import KnowledgeGraphBuilder


# ── Config ─────────────────────────────────────────────────────────────────────

DOCS_DIR   = "docs"
DB_DIR     = "db"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
EMBED_MODEL = "sentence-transformers/all-mpnet-base-v2"


# ── Main ───────────────────────────────────────────────────────────────────────

def ingest(progress_callback=None):
    """
    Full ingestion pipeline. Returns (n_chunks, graph_stats) or raises.

    progress_callback(stage: str, pct: int) is called if provided.
    Stages: 'loading', 'splitting', 'embedding', 'graph', 'done'
    """

    def _cb(stage, pct):
        if progress_callback:
            progress_callback(stage, pct)

    # 1. Discover PDFs
    _cb("loading", 0)
    docs_path = Path(DOCS_DIR)
    docs_path.mkdir(exist_ok=True)
    pdf_files = list(docs_path.glob("**/*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in '{DOCS_DIR}' folder.")

    # 2. Load
    all_documents = []
    for i, pdf in enumerate(pdf_files):
        loader = PyPDFLoader(str(pdf))
        all_documents.extend(loader.load())
        _cb("loading", int(20 * (i + 1) / len(pdf_files)))

    _cb("splitting", 20)

    # 3. Split
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    chunks = splitter.split_documents(all_documents)

    _cb("embedding", 40)

    # 4. Embeddings + ChromaDB
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBED_MODEL, model_kwargs={"device": "cpu"}
    )
    db_path = Path(DB_DIR)
    db_path.mkdir(exist_ok=True)

    db = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(db_path),
    )
    db.persist()

    _cb("graph", 70)

    # 5. Knowledge graph
    builder = KnowledgeGraphBuilder()

    def _graph_progress(done, total):
        pct = 70 + int(25 * done / total)
        _cb("graph", pct)

    builder.build_from_documents(chunks, progress_callback=_graph_progress)

    _cb("done", 100)

    return len(chunks), builder.stats()


# ── CLI entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("📚 Starting Graph RAG ingestion…")
    t0 = time.time()

    def cli_progress(stage, pct):
        print(f"  [{pct:3d}%] {stage}")

    try:
        n_chunks, stats = ingest(progress_callback=cli_progress)
        elapsed = time.time() - t0
        print(f"\n✅ Done in {elapsed:.1f}s")
        print(f"   Chunks : {n_chunks}")
        print(f"   Nodes  : {stats['nodes']}")
        print(f"   Edges  : {stats['edges']}")
    except Exception as e:
        print(f"❌ Error: {e}")