import shutil
import tempfile
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

# Ensure a writable path for Chroma DB
try:
    CHROMA_DIR = Path(CHROMA_SETTINGS.persist_directory)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    test_file = CHROMA_DIR / "test.txt"
    test_file.write_text("test")  # test write
    test_file.unlink()  # remove test file
except Exception:
    # If the original path is not writable, fallback to temp
    CHROMA_DIR = Path(tempfile.gettempdir()) / "wasla_chroma"
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"⚠️ Original CHROMA_DIR not writable. Using temp dir: {CHROMA_DIR}")


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
# BUILD VECTOR DATABASE
# ===============================

def build_vectorstore(chunks, embeddings):
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

    except PermissionError:
        raise PermissionError(
            f"❌ Cannot write to Chroma directory: {CHROMA_DIR}. "
            "Make sure the folder is writable or use a temp directory."
        )


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


# ===============================
# RUN
# ===============================

if __name__ == "__main__":
    ingest_documents()
