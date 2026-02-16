import shutil
import tempfile
import sqlite3
import time
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
    """Return a Path that is writable by both the OS and SQLite."""
    primary_dir = Path(CHROMA_SETTINGS.persist_directory)
    try:
        primary_dir.mkdir(parents=True, exist_ok=True)
        # Test with a real SQLite file – catches read‑only filesystem issues
        test_db = primary_dir / "test_writable.sqlite"
        conn = sqlite3.connect(str(test_db))
        conn.execute("CREATE TABLE test (id integer)")
        conn.close()
        test_db.unlink()
        print(f"✅ Primary directory is writable: {primary_dir}")
        return primary_dir
    except Exception as e:
        print(f"⚠️ Primary directory not fully writable: {e}")
        fallback = Path(tempfile.gettempdir()) / "wasla_chroma_fallback"
        fallback.mkdir(parents=True, exist_ok=True)
        print(f"ℹ️ Using fallback directory: {fallback}")
        return fallback

CHROMA_DIR = get_writable_chroma_dir()

# ===============================
# LOAD DOCUMENTS
# ===============================

def load_documents():
    if not DOCS_DIR.exists():
        raise FileNotFoundError("❌ 'docs' folder not found.")

    documents = []
    for pdf_file in DOCS_DIR.rglob("*.pdf"):
        print(f"📄 Loading: {pdf_file.name}")
        loader = PyPDFLoader(str(pdf_file))
        docs = loader.load()
        for doc in docs:
            doc.metadata["source_file"] = pdf_file.name
        documents.extend(docs)

    if not documents:
        raise ValueError("❌ No PDF files found in docs/")
    return documents

# ===============================
# SPLIT DOCUMENTS
# ===============================

def split_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ".", "!", "?", " ", ""]
    )
    chunks = splitter.split_documents(documents)
    print(f"🔹 Created {len(chunks)} chunks.")
    return chunks

# ===============================
# CREATE EMBEDDINGS
# ===============================

def create_embeddings():
    return HuggingFaceEmbeddings(
        model_name="BAAI/bge-base-en-v1.5",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )

# ===============================
# BUILD VECTOR DATABASE (with retry)
# ===============================

def build_vectorstore(chunks, embeddings, retries=3):
    for attempt in range(retries):
        try:
            if CHROMA_DIR.exists():
                print("⚠️ Resetting existing Chroma database...")
                shutil.rmtree(CHROMA_DIR)

            vectordb = Chroma.from_documents(
                documents=chunks,
                embedding=embeddings,
                persist_directory=str(CHROMA_DIR)
            )
            vectordb.persist()
            print("✅ Chroma DB built successfully.")
            print(f"📂 Stored at: {CHROMA_DIR}")
            return
        except Exception as e:
            print(f"⚠️ Build attempt {attempt+1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(2)  # wait before retrying
            else:
                raise  # re-raise the last exception

# ===============================
# MAIN INGEST FUNCTION
# ===============================

def ingest_documents():
    print("🚀 Starting ingestion process...\n")
    documents = load_documents()
    chunks = split_documents(documents)
    embeddings = create_embeddings()
    build_vectorstore(chunks, embeddings)
    print("\n🎉 Ingestion completed successfully.")

if __name__ == "__main__":
    ingest_documents()