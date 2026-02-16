import shutil
import tempfile
import sqlite3
import time
import sys
import os
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from constant import CHROMA_SETTINGS

# ===============================
# PATHS
# ===============================

BASE_DIR = Path(__file__).parent
DOCS_DIR = BASE_DIR / "docs"

def get_writable_chroma_dir():
    primary_dir = Path(CHROMA_SETTINGS.persist_directory)
    try:
        primary_dir.mkdir(parents=True, exist_ok=True)
        test_db = primary_dir / "test_writable.sqlite"
        conn = sqlite3.connect(str(test_db))
        conn.execute("CREATE TABLE test (id integer)")
        conn.close()
        test_db.unlink()
        print(f"✅ Primary directory is writable: {primary_dir}")
        sys.stdout.flush()
        return primary_dir
    except Exception as e:
        print(f"⚠️ Primary directory not fully writable: {e}")
        sys.stdout.flush()
        fallback = Path(tempfile.gettempdir()) / "wasla_chroma_fallback"
        fallback.mkdir(parents=True, exist_ok=True)
        print(f"ℹ️ Using fallback directory: {fallback}")
        sys.stdout.flush()
        return fallback

CHROMA_DIR = get_writable_chroma_dir()

def load_documents():
    print("\n" + "="*60)
    print("🔍 DEBUG: Starting load_documents()")
    print(f"🔍 Current working directory: {os.getcwd()}")
    print(f"🔍 DOCS_DIR absolute path: {DOCS_DIR.absolute()}")
    print(f"🔍 DOCS_DIR exists? {DOCS_DIR.exists()}")
    sys.stdout.flush()

    if not DOCS_DIR.exists():
        raise FileNotFoundError(f"❌ 'docs' folder not found at {DOCS_DIR}")

    pdf_files = list(DOCS_DIR.rglob("*.pdf"))
    print(f"📄 Found {len(pdf_files)} PDF file(s):")
    for pdf in pdf_files:
        print(f"   - {pdf.name}")
    sys.stdout.flush()

    if not pdf_files:
        raise ValueError("❌ No PDF files found in docs/")

    documents = []
    for pdf_file in pdf_files:
        print(f"\n📂 Loading: {pdf_file.name}")
        sys.stdout.flush()
        loader = PyPDFLoader(str(pdf_file))
        docs = loader.load()
        for doc in docs:
            doc.metadata["source_file"] = pdf_file.name
        documents.extend(docs)
        print(f"   → {len(docs)} pages loaded")
        sys.stdout.flush()

    print(f"\n✅ Total documents loaded: {len(documents)}")
    sys.stdout.flush()
    if len(documents) == 0:
        raise RuntimeError("No pages were loaded from PDFs.")
    return documents

def split_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ".", "!", "?", " ", ""]
    )
    chunks = splitter.split_documents(documents)
    print(f"🔹 Created {len(chunks)} chunks.")
    sys.stdout.flush()
    return chunks

def create_embeddings():
    return HuggingFaceEmbeddings(
        model_name="BAAI/bge-base-en-v1.5",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )

def build_vectorstore(chunks, embeddings, retries=3):
    for attempt in range(retries):
        temp_dir = Path(tempfile.mkdtemp(prefix="wasla_build_"))
        try:
            print(f"🛠 Building in temporary directory: {temp_dir}")
            sys.stdout.flush()
            vectordb = Chroma.from_documents(
                documents=chunks,
                embedding=embeddings,
                persist_directory=str(temp_dir),
                collection_name="company_docs"
            )
            count_before = vectordb._collection.count()
            print(f"📊 Document count in temp collection (before persist): {count_before}")
            sys.stdout.flush()

            vectordb.persist()
            count_after = vectordb._collection.count()
            print(f"📊 Document count in temp collection (after persist): {count_after}")
            sys.stdout.flush()

            if count_after > 0:
                sample = vectordb._collection.get(limit=1)
                print(f"📄 Sample content (first 100 chars): {sample['documents'][0][:100]}")
                sys.stdout.flush()

            if CHROMA_DIR.exists():
                print("⚠️ Removing old Chroma database...")
                sys.stdout.flush()
                shutil.rmtree(CHROMA_DIR)
            shutil.move(str(temp_dir), str(CHROMA_DIR))
            print("✅ Chroma DB built and moved successfully.")
            print(f"📂 Stored at: {CHROMA_DIR}")
            sys.stdout.flush()
            return  # <-- No final verification that causes tenant error
        except Exception as e:
            print(f"⚠️ Build attempt {attempt+1} failed: {e}")
            sys.stdout.flush()
            shutil.rmtree(temp_dir, ignore_errors=True)
            if attempt < retries - 1:
                time.sleep(2)
            else:
                raise

def ingest_documents():
    print("🚀🚀🚀 INGESTION STARTED 🚀🚀🚀")
    sys.stdout.flush()
    documents = load_documents()
    chunks = split_documents(documents)
    embeddings = create_embeddings()
    build_vectorstore(chunks, embeddings)
    print("\n🎉 Ingestion completed successfully.")
    sys.stdout.flush()

if __name__ == "__main__":
    ingest_documents()