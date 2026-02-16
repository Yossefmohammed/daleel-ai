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
from constant import CHROMA_SETTINGS

rebuild_lock = threading.Lock()

load_dotenv()
st.set_page_config(page_title="Company AI Assistant", page_icon="🤖")
st.title("🤖 Company AI Assistant")

# ===== FORCE REBUILD BUTTON =====
if st.sidebar.button("🗑️ Force Rebuild Database"):
    try:
        shutil.rmtree(CHROMA_SETTINGS["persist_directory"], ignore_errors=True)  # <-- dict access
        st.success("Database cleared. Please ask a question to rebuild.")
        st.rerun()
    except Exception as e:
        st.error(f"Error clearing database: {e}")
# =================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    st.error("❌ GROQ_API_KEY not found in .env file")
    st.stop()

def load_vectorstore():
    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-base-en-v1.5",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )
    persist_dir = CHROMA_SETTINGS["persist_directory"]  # <-- dict access
    os.makedirs(persist_dir, exist_ok=True)

    try:
        db = Chroma(
            persist_directory=persist_dir,
            embedding_function=embeddings,
            collection_name="company_docs",
            client_settings=CHROMA_SETTINGS  # this stays as dict
        )
        test = db.similarity_search("test", k=1)
        if len(test) == 0:
            raise ValueError("Empty database")
        return db
    except Exception as e:
        st.warning(f"Rebuilding vector database... Reason: {e}")
        if 'db' in locals():
            del db
        gc.collect()
        time.sleep(1)

        with rebuild_lock:
            try:
                db = Chroma(
                    persist_directory=persist_dir,
                    embedding_function=embeddings,
                    collection_name="company_docs",
                    client_settings=CHROMA_SETTINGS
                )
                test = db.similarity_search("test", k=1)
                if len(test) > 0:
                    return db
            except Exception:
                pass

            if os.path.exists(persist_dir):
                shutil.rmtree(persist_dir, ignore_errors=True)
                time.sleep(1)

            from ingest import ingest_documents
            ingest_documents()

        db = Chroma(
            persist_directory=persist_dir,
            embedding_function=embeddings,
            collection_name="company_docs",
            client_settings=CHROMA_SETTINGS
        )
        return db

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
    return retriever.invoke(query)

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
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    else:
        st.chat_message("assistant").write(msg["content"])

user_input = st.chat_input("Ask something about our company...")

if user_input:
    st.chat_message("user").write(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    try:
        db = load_vectorstore()
        llm = load_llm()

        docs = retrieve_docs(db, user_input)

        # Debug display
        st.write(f"**Retrieved {len(docs)} documents**")
        if len(docs) == 0:
            st.warning("No relevant documents found. The database might be empty or the query doesn't match.")
        else:
            for i, doc in enumerate(docs):
                with st.expander(f"Chunk {i+1} – Source: {doc.metadata.get('source_file', 'Unknown')}"):
                    st.write(doc.page_content)

        context = format_context(docs)

        history_text = ""
        for msg in st.session_state.messages[-6:]:
            role = "User" if msg["role"] == "user" else "Assistant"
            history_text += f"{role}: {msg['content']}\n"

        final_prompt = build_prompt(context, history_text, user_input)

        try:
            response = llm.invoke(final_prompt)
            answer = response.content
        except Exception as e:
            st.error(f"LLM error: {e}")
            st.exception(e)
            st.stop()

        st.chat_message("assistant").write(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})

    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        st.exception(e)