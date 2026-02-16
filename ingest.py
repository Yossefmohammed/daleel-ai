import shutil
import sqlite3
import time
import sys
import os
import gc
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from constant import CHROMA_SETTINGS

BASE_DIR = Path(__file__).parent
DOCS_DIR = BASE_DIR / "docs"

# Persistent location (outside /tmp, safe for restarts)
PERSISTENT_CHROMA_DIR = BASE_DIR / "chroma_db"

# =========================
# LOAD DOCUMENTS
# =========================
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

# =========================
# SPLIT DOCUMENTS INTO CHUNKS
# =========================
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

# =========================
# CREATE EMBEDDINGS
# =========================
def create_embeddings():
    print("🧠 Creating embeddings model...")
    sys.stdout.flush()
    return HuggingFaceEmbeddings(
        model_name="BAAI/bge-base-en-v1.5",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )

# =========================
# BUILD VECTORSTORE WITH TEMP SAFETY
# =========================
def build_vectorstore(chunks, embeddings, retries=3):
    PERSISTENT_CHROMA_DIR.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(retries):
        temp_dir = PERSISTENT_CHROMA_DIR.parent / f"temp_build_{int(time.time())}_{attempt}"
        temp_dir.mkdir(parents=True, exist_ok=False)

        try:
            print(f"🛠 Building vectorstore in temp directory: {temp_dir}")
            sys.stdout.flush()

            vectordb = Chroma.from_documents(
                documents=chunks,
                embedding=embeddings,
                persist_directory=str(temp_dir),
                collection_name="company_docs"
            )
            vectordb.persist()
            print("💾 Persisted temp vectorstore.")
            sys.stdout.flush()

            # Verify temp database
            import chromadb
            from chromadb.config import Settings
            client = chromadb.PersistentClient(
                path=str(temp_dir),
                settings=Settings(anonymized_telemetry=False)
            )
            collection = client.get_collection("company_docs")
            final_count = collection.count()
            print(f"📊 Temp document count: {final_count}")
            sys.stdout.flush()

            if final_count == 0:
                raise RuntimeError("❌ Temp database has zero documents!")

            # Remove old persistent database
            if PERSISTENT_CHROMA_DIR.exists():
                print(f"⚠️ Removing old persistent database at {PERSISTENT_CHROMA_DIR}")
                sys.stdout.flush()
                shutil.rmtree(PERSISTENT_CHROMA_DIR)
                time.sleep(1)

            # Move temp DB to persistent location
            print(f"📦 Moving temp DB to persistent location: {PERSISTENT_CHROMA_DIR}")
            sys.stdout.flush()
            shutil.move(str(temp_dir), str(PERSISTENT_CHROMA_DIR))

            # Verify persistent DB
            client_final = chromadb.PersistentClient(
                path=str(PERSISTENT_CHROMA_DIR),
                settings=Settings(anonymized_telemetry=False)
            )
            collection_final = client_final.get_collection("company_docs")
            final_count2 = collection_final.count()
            print(f"✅ Final persistent document count: {final_count2}")
            sys.stdout.flush()

            # Cleanup
            try:
                vectordb._client.close()
            except:
                pass
            del vectordb
            gc.collect()
            time.sleep(1)
            return  # success

        except Exception as e:
            print(f"⚠️ Build attempt {attempt+1} failed: {e}")
            sys.stdout.flush()
            shutil.rmtree(temp_dir, ignore_errors=True)
            if attempt < retries - 1:
                print("⏳ Retrying...")
                time.sleep(2)
            else:
                raise

# =========================
# INGESTION PIPELINE
# =========================
def ingest_documents():
    print("🚀🚀🚀 INGESTION STARTED 🚀🚀🚀")
    sys.stdout.flush()
    documents = load_documents()
    chunks = split_documents(documents)
    embeddings = create_embeddings()
    build_vectorstore(chunks, embeddings)
    print("\n🎉 Ingestion completed successfully.")
    sys.stdout.flush()

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    ingest_documents()
