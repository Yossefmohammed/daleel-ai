"""
ingest.py — PathIQ Document Ingestion Pipeline
===============================================
Processes PDFs in docs/ folder, builds ChromaDB vector store
and knowledge graph. Run once before starting the app.

Usage:
    python ingest.py
    python ingest.py --docs-dir /path/to/pdfs --chunk-size 600
"""

import os
import sys
import time
import argparse
from pathlib import Path

# ── Config ───────────────────────────────────────────────────────────────────
DB_DIR        = "db"
DOCS_DIR      = "docs"
EMBED_MODEL   = "sentence-transformers/all-mpnet-base-v2"
CHUNK_SIZE    = 500
CHUNK_OVERLAP = 100


def print_step(msg: str, icon: str = "→"):
    print(f"\n{icon}  {msg}", flush=True)


def print_ok(msg: str):
    print(f"   ✓  {msg}", flush=True)


def print_err(msg: str):
    print(f"   ✗  {msg}", flush=True)


def run_ingestion(docs_dir: str = DOCS_DIR, chunk_size: int = CHUNK_SIZE):
    start = time.time()

    print("\n" + "═" * 55)
    print("  PathIQ — Document Ingestion Pipeline")
    print("═" * 55)

    # ── Check imports ────────────────────────────────────────
    print_step("Checking dependencies…")
    try:
        from langchain_community.document_loaders import PyPDFLoader
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from langchain_community.vectorstores import Chroma
        from langchain_community.embeddings import HuggingFaceEmbeddings
        from graph_builder import KnowledgeGraphBuilder, GRAPH_PATH
        print_ok("All dependencies available")
    except ImportError as e:
        print_err(f"Missing dependency: {e}")
        print("\n  Run: pip install -r requirements.txt")
        sys.exit(1)

    # ── Scan for PDFs ────────────────────────────────────────
    print_step(f"Scanning {docs_dir}/ for PDFs…")
    docs_path = Path(docs_dir)
    docs_path.mkdir(exist_ok=True)
    pdf_files = list(docs_path.glob("**/*.pdf"))

    if not pdf_files:
        print_err(f"No PDF files found in {docs_dir}/")
        print("\n  Add PDF files to the docs/ folder and re-run.")
        sys.exit(1)

    print_ok(f"Found {len(pdf_files)} PDF(s): {[f.name for f in pdf_files]}")

    # ── Load PDFs ────────────────────────────────────────────
    print_step("Loading and parsing PDFs…")
    all_docs = []
    for i, pdf in enumerate(pdf_files):
        try:
            loader = PyPDFLoader(str(pdf))
            pages  = loader.load()
            all_docs.extend(pages)
            print_ok(f"{pdf.name} → {len(pages)} pages")
        except Exception as e:
            print_err(f"Failed to load {pdf.name}: {e}")

    if not all_docs:
        print_err("No content extracted from PDFs")
        sys.exit(1)

    # ── Chunk ────────────────────────────────────────────────
    print_step(f"Splitting into chunks (size={chunk_size}, overlap={CHUNK_OVERLAP})…")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(all_docs)

    # Tag each chunk with an ID for graph retrieval
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = f"chunk_{i}"

    print_ok(f"{len(chunks)} chunks created")

    # ── Embeddings + ChromaDB ────────────────────────────────
    print_step(f"Building embeddings ({EMBED_MODEL})…")
    print("  (This may take a few minutes on first run — model downloads ~420MB)")

    try:
        embeddings = HuggingFaceEmbeddings(
            model_name=EMBED_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    except Exception as e:
        print_err(f"Embedding model error: {e}")
        sys.exit(1)

    print_step("Storing in ChromaDB vector store…")
    try:
        Path(DB_DIR).mkdir(exist_ok=True)
        db = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=DB_DIR,
            collection_metadata={"hnsw:space": "cosine"},
        )
        db.persist()
        print_ok(f"ChromaDB: {len(chunks)} chunks stored in {DB_DIR}/")
    except Exception as e:
        print_err(f"ChromaDB error: {e}")
        sys.exit(1)

    # ── Knowledge graph ──────────────────────────────────────
    print_step("Building knowledge graph…")
    try:
        builder = KnowledgeGraphBuilder()

        processed = [0]
        def progress(done, total):
            if done % max(1, total // 10) == 0:
                pct = round(done / total * 100)
                print(f"  {pct}% ({done}/{total} chunks)", end="\r", flush=True)
            processed[0] = done

        builder.build_from_documents(chunks, progress_callback=progress)
        stats = builder.stats()
        print()
        print_ok(f"Graph: {stats['nodes']} nodes, {stats['edges']} edges → {GRAPH_PATH}")
    except Exception as e:
        print_err(f"Graph build error: {e}")
        print("  Vector store is ready — graph expansion disabled.")

    # ── Done ─────────────────────────────────────────────────
    elapsed = round(time.time() - start, 1)
    print("\n" + "═" * 55)
    print(f"  Ingestion complete in {elapsed}s")
    print("  Run: streamlit run app.py")
    print("═" * 55 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PathIQ Document Ingestion")
    parser.add_argument("--docs-dir",   default=DOCS_DIR,     help="PDF directory")
    parser.add_argument("--chunk-size", default=CHUNK_SIZE, type=int, help="Chunk size")
    args = parser.parse_args()
    run_ingestion(docs_dir=args.docs_dir, chunk_size=args.chunk_size)