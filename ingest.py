import os
import shutil
import gc
import time
import threading
import streamlit as st
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
import chromadb
from chromadb.config import Settings as ChromaSettings
from constant import CHROMA_SETTINGS
import sqlite3  # for explicit db check

rebuild_lock = threading.Lock()

load_dotenv()
st.set_page_config(page_title="Company AI Assistant", page_icon="🤖")
st.title("🤖 Company AI Assistant")

with st.sidebar:
    st.header("Controls")
    if st.button("🗑️ Force Rebuild Database"):
        try:
            shutil.rmtree(CHROMA_SETTINGS.persist_directory, ignore_errors=True)
            st.success("Database cleared. Please ask a question to rebuild.")
            st.rerun()
        except Exception as e:
            st.error(f"Error clearing database: {e}")
    show_debug = st.checkbox("Show debug info", value=False)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    st.error("❌ GROQ_API_KEY not found in .env file")
    st.stop()

def create_chroma_client(persist_dir):
    """Create a persistent Chroma client with telemetry disabled."""
    return chromadb.PersistentClient(
        path=persist_dir,
        settings=ChromaSettings(anonymized_telemetry=False)
    )

def verify_db(persist_dir, embeddings, collection_name="company_docs"):
    """Verify that the database exists and is queryable."""
    client = create_chroma_client(persist_dir)
    db = Chroma(
        client=client,
        collection_name=collection_name,
        embedding_function=embeddings
    )
    # Test a simple query
    test = db.similarity_search("test", k=1)
    if len(test) == 0:
        raise ValueError("Database exists but returned no documents")
    return db

@st.cache_resource(show_spinner="Loading knowledge base...")
def load_vectorstore():
    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-base-en-v1.5",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )
    persist_dir = CHROMA_SETTINGS.persist_directory
    os.makedirs(persist_dir, exist_ok=True)

    # First attempt to load existing DB
    try:
        db = verify_db(persist_dir, embeddings)
        if st.session_state.get("show_debug", False):
            client = create_chroma_client(persist_dir)
            collections = client.list_collections()
            st.write(f"📚 Collections: {[c.name for c in collections]}")
            count = db._collection.count()
            st.write(f"📊 Document count: {count}")
        return db
    except Exception as e:
        st.warning(f"Database not usable: {e}. Rebuilding...")
        # Clean up any stale objects
        gc.collect()
        time.sleep(1)

        with rebuild_lock:
            # Double-check after acquiring lock (another thread might have rebuilt)
            try:
                db = verify_db(persist_dir, embeddings)
                return db
            except Exception:
                pass

            # Remove any corrupted database files
            if os.path.exists(persist_dir):
                shutil.rmtree(persist_dir, ignore_errors=True)
                time.sleep(1)

            # Run ingestion
            from ingest import ingest_documents
            ingest_documents()

            # Give the filesystem a moment
            time.sleep(2)

            # Verify the newly built database
            try:
                db = verify_db(persist_dir, embeddings)
                return db
            except Exception as e:
                # If verification still fails, raise a clear error
                raise RuntimeError(f"Database rebuild succeeded but verification failed: {e}")

@st.cache_resource
def load_llm():
    return ChatGroq(
        groq_api_key=GROQ_API_KEY,
        model_name="llama-3.1-8b-instant",
        temperature=0.4
    )

def build_prompt(context, chat_history, question):
    system_template = """
You are a professional, friendly AI assistant for a company website.

Your job:
- Answer using ONLY the provided context
- If answer is not in context, say:
  "I'm sorry, I couldn't find that information in our documents."
- Be natural and conversational
- Do NOT mention internal processing or retrieval
- Keep answers clear and helpful

Context:
{context}

Chat History:
{chat_history}

User Question:
{question}
"""
    return ChatPromptTemplate.from_template(system_template).format(
        context=context, chat_history=chat_history, question=question
    )

def retrieve_docs(db, query):
    retriever = db.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 6, "fetch_k": 20, "lambda_mult": 0.5}
    )
    try:
        return retriever.invoke(query)
    except sqlite3.OperationalError as e:
        # If we get a database error, suggest a rebuild
        st.error(f"Database error: {e}. Try the 'Force Rebuild' button.")
        raise

def format_context(docs):
    context_parts = []
    for doc in docs:
        source = doc.metadata.get("source_file", "Unknown")
        content = doc.page_content[:1000]
        context_parts.append(f"[{source}]\n{content}")
    return "\n\n".join(context_parts)

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

user_input = st.chat_input("Ask something about our company...")

if user_input:
    st.chat_message("user").write(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    try:
        st.session_state["show_debug"] = show_debug
        db = load_vectorstore()
        llm = load_llm()

        with st.spinner("Searching documents..."):
            docs = retrieve_docs(db, user_input)

        if show_debug:
            st.write(f"**Retrieved {len(docs)} documents**")
            for i, doc in enumerate(docs):
                with st.expander(f"Chunk {i+1} – Source: {doc.metadata.get('source_file', 'Unknown')}"):
                    st.write(doc.page_content)

        context = format_context(docs)
        history_text = "\n".join(
            f"{'User' if m['role']=='user' else 'Assistant'}: {m['content']}"
            for m in st.session_state.messages[-6:]
        )

        final_prompt = build_prompt(context, history_text, user_input)

        with st.spinner("Thinking..."):
            response = llm.invoke(final_prompt)
            answer = response.content

        st.chat_message("assistant").write(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})

    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        st.exception(e)