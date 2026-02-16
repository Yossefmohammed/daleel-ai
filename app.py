import os
import shutil
import gc
import time
import threading
import logging
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
import chromadb
from chromadb.config import Settings as ChromaSettings
from constant import CHROMA_SETTINGS
import sqlite3

# -------------------- Logging Setup --------------------
logging.basicConfig(
    filename='chatbot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# -------------------- Global Lock --------------------
rebuild_lock = threading.Lock()

# -------------------- Streamlit Page Config --------------------
load_dotenv()
st.set_page_config(page_title="Wasla AI Assistant", page_icon="🤖")
st.title("🤖 Wasla AI Assistant")

# -------------------- Sidebar Controls --------------------
with st.sidebar:
    st.header("Controls")
    if st.button("🗑️ Force Rebuild Database"):
        try:
            shutil.rmtree(CHROMA_SETTINGS.persist_directory, ignore_errors=True)
            st.success("Database cleared. Please ask a question to rebuild.")
            st.rerun()
        except Exception as e:
            st.error(f"Error clearing database: {e}")
            logging.error(f"Force rebuild failed: {e}")

    if st.button("🧹 Clear chat history"):
        st.session_state.messages = []
        st.session_state.feedback_given = {}
        st.rerun()

    show_debug = st.checkbox("Show debug info", value=False)

# -------------------- API Key Check --------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    st.error("❌ GROQ_API_KEY not found in .env file")
    st.stop()

# -------------------- Chroma Client Helper --------------------
def create_chroma_client(persist_dir):
    """Create a persistent Chroma client with telemetry disabled."""
    return chromadb.PersistentClient(
        path=persist_dir,
        settings=ChromaSettings(anonymized_telemetry=False)
    )

# -------------------- Database Verification --------------------
def verify_db(persist_dir, embeddings, collection_name="company_docs"):
    """Verify that the database exists and is queryable."""
    client = create_chroma_client(persist_dir)
    db = Chroma(
        client=client,
        collection_name=collection_name,
        embedding_function=embeddings
    )
    test = db.similarity_search("test", k=1)
    if len(test) == 0:
        raise ValueError("Database exists but returned no documents")
    return db

# -------------------- Load Vector Store (cached) --------------------
@st.cache_resource(show_spinner="Loading knowledge base...")
def load_vectorstore():
    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-base-en-v1.5",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )
    persist_dir = CHROMA_SETTINGS.persist_directory
    os.makedirs(persist_dir, exist_ok=True)

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
        logging.warning(f"Database unusable, rebuilding: {e}")
        gc.collect()
        time.sleep(1)

        with rebuild_lock:
            # Double-check after acquiring lock
            try:
                db = verify_db(persist_dir, embeddings)
                return db
            except Exception:
                pass

            # Remove corrupted database
            if os.path.exists(persist_dir):
                shutil.rmtree(persist_dir, ignore_errors=True)
                time.sleep(1)

            # Run ingestion
            from ingest import ingest_documents
            ingest_documents()
            time.sleep(2)  # Let filesystem settle

            # Verify newly built database
            try:
                db = verify_db(persist_dir, embeddings)
                return db
            except Exception as e:
                logging.error(f"Rebuild verification failed: {e}")
                raise RuntimeError(f"Database rebuild succeeded but verification failed: {e}")

# -------------------- Load LLM (cached) --------------------
@st.cache_resource
def load_llm():
    return ChatGroq(
        groq_api_key=GROQ_API_KEY,
        model_name="llama-3.1-8b-instant",
        temperature=0.4
    )

# -------------------- Build Prompt (Improved) --------------------
def build_prompt(context, chat_history, question):
    system_template = """
You are Wasla's AI assistant — professional, friendly, and knowledgeable about our company.

Guidelines:
- Always speak as Wasla, using "we" and "us". Never refer to yourself as a chatbot.
- Answer using ONLY the provided context.
- If the answer is not in the context, say: "I'm sorry, I couldn't find that information in our documents."
- Be natural, conversational, and concise.
- If the user asks a yes/no question, first answer clearly (yes/no), then provide additional relevant information or ask a follow‑up question.
- Do NOT mention internal processes like retrieval, vector databases, or "according to my training".
- Keep responses helpful and aligned with Wasla's tone: quietly powerful, precise, and focused on long‑term solutions.

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

# -------------------- Retrieve Documents --------------------
def retrieve_docs(db, query):
    retriever = db.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 6, "fetch_k": 20, "lambda_mult": 0.5}
    )
    try:
        return retriever.invoke(query)
    except sqlite3.OperationalError as e:
        st.error("⚠️ Database error. Please try the 'Force Rebuild' button in the sidebar.")
        logging.error(f"Database error on query '{query}': {e}")
        raise

# -------------------- Format Context --------------------
def format_context(docs):
    context_parts = []
    for doc in docs:
        source = doc.metadata.get("source_file", "Unknown")
        content = doc.page_content[:1000]
        context_parts.append(f"[{source}]\n{content}")
    return "\n\n".join(context_parts)

# -------------------- Log Unanswered Questions --------------------
def log_unanswered(question, answer):
    if "I couldn't find that information" in answer:
        logging.info(f"UNANSWERED: {question}")

# -------------------- Initialize Session State --------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "feedback_given" not in st.session_state:
    st.session_state.feedback_given = {}  # maps message index to 'up' or 'down'

# -------------------- Display Chat History --------------------
for idx, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        # If this is an assistant message, show feedback buttons (unless already given)
        if msg["role"] == "assistant" and idx not in st.session_state.feedback_given:
            col1, col2 = st.columns([0.1, 0.1])
            with col1:
                if st.button("👍", key=f"up_{idx}"):
                    st.session_state.feedback_given[idx] = "up"
                    logging.info(f"Feedback positive for message {idx}")
                    st.rerun()
            with col2:
                if st.button("👎", key=f"down_{idx}"):
                    st.session_state.feedback_given[idx] = "down"
                    logging.info(f"Feedback negative for message {idx}")
                    st.rerun()

# -------------------- User Input --------------------
user_input = st.chat_input("Ask something about Wasla...")

if user_input:
    # Add user message
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

        # Log unanswered questions
        log_unanswered(user_input, answer)

        # Display assistant response
        st.chat_message("assistant").write(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})

        # Rerun to show feedback buttons for the new message
        st.rerun()

    except Exception as e:
        st.error("😓 An unexpected error occurred. Our team has been notified.")
        logging.error(f"Unhandled exception: {e}", exc_info=True)
        st.exception(e)  # Still show full error in dev; you may remove in production