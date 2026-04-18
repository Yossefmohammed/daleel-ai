"""
ingest.py — Daleel AI Document Ingestion Pipeline
==================================================
Processes PDFs in docs/ → builds ChromaDB vector store + knowledge graph.
Run once before starting the app, or whenever you add new documents.

Usage:
    python ingest.py
    python ingest.py --docs-dir /path/to/pdfs --chunk-size 600
    python ingest.py --force          # re-ingest even if DB already exists

Improvements over original:
- Incremental ingestion: skips PDFs already in the DB (hash-based)
  so adding one new PDF doesn't re-process the entire docs/ folder.
- --force flag to override incremental behaviour.
- Configurable embedding model via --embed-model argument.
- Proper logging (not just print) so log level can be controlled.
- graph_builder now receives custom_keywords from CLI if provided.
- All sys.exit() calls replaced with raised exceptions in run_ingestion()
  so the function can be called programmatically from app.py.
"""

import argparse
import hashlib
import json
import logging
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Defaults ──────────────────────────────────────────────────────────────────
DB_DIR = "db"
DOCS_DIR = "docs"
EMBED_MODEL = "sentence-transformers/all-mpnet-base-v2"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
INGEST_MANIFEST = Path(DB_DIR) / "ingested_files.json"


# ── Manifest helpers (incremental ingestion) ──────────────────────────────────

def _file_hash(path: Path) -> str:
    """SHA-256 of file contents — used to detect unchanged files."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _load_manifest() -> dict:
    if INGEST_MANIFEST.exists():
        try:
            return json.loads(INGEST_MANIFEST.read_text())
        except Exception:
            pass
    return {}


def _save_manifest(manifest: dict) -> None:
    INGEST_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    INGEST_MANIFEST.write_text(json.dumps(manifest, indent=2))


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run_ingestion(
    docs_dir: str = DOCS_DIR,
    chunk_size: int = CHUNK_SIZE,
    embed_model: str = EMBED_MODEL,
    force: bool = False,
    custom_keywords: list | None = None,
) -> dict:
    """
    Run the full ingestion pipeline.

    Args:
        docs_dir: directory containing PDF files
        chunk_size: token/char size of each text chunk
        embed_model: HuggingFace sentence-transformer model name
        force: if True, re-ingest all files even if already processed
        custom_keywords: extra tech keywords for the knowledge graph

    Returns:
        {"chunks": int, "nodes": int, "edges": int, "skipped": int}

    Raises:
        SystemExit on unrecoverable errors (missing deps, no PDFs).
    """
    start = time.time()

    logger.info("=" * 55)
    logger.info("  Daleel AI — Document Ingestion Pipeline")
    logger.info("=" * 55)

    # ── Check imports ─────────────────────────────────────────────────
    logger.info("Checking dependencies…")
    try:
        from langchain_community.document_loaders import PyPDFLoader
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from langchain_community.vectorstores import Chroma
        from langchain_community.embeddings import HuggingFaceEmbeddings
        from graph_builder import KnowledgeGraphBuilder, GRAPH_PATH
        logger.info("  ✓ All dependencies available")
    except ImportError as exc:
        logger.error("Missing dependency: %s\nRun: pip install -r requirements.txt", exc)
        sys.exit(1)

    # ── Scan for PDFs ─────────────────────────────────────────────────
    logger.info("Scanning %s/ for PDFs…", docs_dir)
    docs_path = Path(docs_dir)
    docs_path.mkdir(exist_ok=True)
    pdf_files = sorted(docs_path.glob("**/*.pdf"))

    if not pdf_files:
        logger.error("No PDF files found in %s/  — add PDFs and re-run.", docs_dir)
        sys.exit(1)

    logger.info("  Found %d PDF(s): %s", len(pdf_files), [f.name for f in pdf_files])

    # ── Incremental check ─────────────────────────────────────────────
    manifest = {} if force else _load_manifest()
    new_files = []
    skipped = 0
    for pdf in pdf_files:
        fhash = _file_hash(pdf)
        if not force and manifest.get(str(pdf)) == fhash:
            logger.info("  ⊘  Skipping (unchanged): %s", pdf.name)
            skipped += 1
        else:
            new_files.append((pdf, fhash))

    if not new_files and not force:
        logger.info("All PDFs already ingested. Use --force to re-ingest.")
        return {"chunks": 0, "nodes": 0, "edges": 0, "skipped": skipped}

    # ── Load new PDFs ─────────────────────────────────────────────────
    logger.info("Loading %d new/changed PDF(s)…", len(new_files))
    all_docs = []
    successfully_loaded: list[tuple[Path, str]] = []

    for pdf, fhash in new_files:
        try:
            loader = PyPDFLoader(str(pdf))
            pages = loader.load()
            all_docs.extend(pages)
            successfully_loaded.append((pdf, fhash))
            logger.info("  ✓  %s → %d page(s)", pdf.name, len(pages))
        except Exception as exc:
            logger.warning("  ✗  Failed to load %s: %s", pdf.name, exc)

    if not all_docs:
        logger.error("No content extracted from new PDFs.")
        sys.exit(1)

    # ── Chunk ─────────────────────────────────────────────────────────
    logger.info(
        "Splitting into chunks (size=%d, overlap=%d)…",
        chunk_size, CHUNK_OVERLAP,
    )
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(all_docs)

    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = f"chunk_{i}"

    logger.info("  ✓  %d chunks created", len(chunks))

    # ── Embeddings + ChromaDB ─────────────────────────────────────────
    logger.info("Building embeddings (%s)…", embed_model)
    logger.info("  (First run may download ~420MB model weights)")
    try:
        embeddings = HuggingFaceEmbeddings(
            model_name=embed_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    except Exception as exc:
        logger.error("Embedding model error: %s", exc)
        sys.exit(1)

    logger.info("Storing in ChromaDB vector store…")
    try:
        Path(DB_DIR).mkdir(exist_ok=True)
        db = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=DB_DIR,
            collection_metadata={"hnsw:space": "cosine"},
        )
        db.persist()
        logger.info("  ✓  ChromaDB: %d chunks stored in %s/", len(chunks), DB_DIR)
    except Exception as exc:
        logger.error("ChromaDB error: %s", exc)
        sys.exit(1)

    # ── Knowledge graph ───────────────────────────────────────────────
    logger.info("Building knowledge graph…")
    graph_stats = {"nodes": 0, "edges": 0}
    try:
        builder = KnowledgeGraphBuilder(custom_keywords=custom_keywords)

        def progress(done: int, total: int) -> None:
            if done % max(1, total // 10) == 0 or done == total:
                pct = round(done / total * 100)
                print(f"  {pct:3d}%  ({done}/{total} chunks)", end="\r", flush=True)

        builder.build_from_documents(chunks, progress_callback=progress)
        print()  # clear the \r line
        graph_stats = builder.stats()
        logger.info(
            "  ✓  Graph: %d nodes, %d edges → %s",
            graph_stats["nodes"], graph_stats["edges"], GRAPH_PATH,
        )
    except Exception as exc:
        logger.warning("Graph build error: %s  — vector store is ready, graph disabled.", exc)

    # ── Update manifest ───────────────────────────────────────────────
    for pdf, fhash in successfully_loaded:
        manifest[str(pdf)] = fhash
    _save_manifest(manifest)

    # ── Done ──────────────────────────────────────────────────────────
    elapsed = round(time.time() - start, 1)
    logger.info("=" * 55)
    logger.info("  Ingestion complete in %ss", elapsed)
    logger.info("  Run: streamlit run app.py")
    logger.info("=" * 55)

    return {
        "chunks": len(chunks),
        "nodes": graph_stats.get("nodes", 0),
        "edges": graph_stats.get("edges", 0),
        "skipped": skipped,
    }


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Daleel AI Document Ingestion")
    parser.add_argument("--docs-dir", default=DOCS_DIR, help="PDF directory (default: docs/)")
    parser.add_argument("--chunk-size", default=CHUNK_SIZE, type=int, help="Chunk size in chars")
    parser.add_argument(
        "--embed-model",
        default=EMBED_MODEL,
        help="HuggingFace embedding model name",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-ingest all files even if already processed",
    )
    parser.add_argument(
        "--keywords",
        nargs="*",
        metavar="KEYWORD",
        help="Extra domain keywords for entity extraction (e.g. --keywords MyCompany MyProduct)",
    )
    args = parser.parse_args()

    run_ingestion(
        docs_dir=args.docs_dir,
        chunk_size=args.chunk_size,
        embed_model=args.embed_model,
        force=args.force,
        custom_keywords=args.keywords,
    )