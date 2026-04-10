"""
app.py  –  Wasla AI  ·  Graph RAG Edition
==========================================
Drop-in replacement for the original app.py.

What changed vs the classic RAG version
────────────────────────────────────────
• Ingestion now builds BOTH a ChromaDB vector store AND a knowledge graph
  (entity co-occurrence graph stored as JSON in db/knowledge_graph.json).
• Retrieval uses GraphRetriever: vector similarity search PLUS graph-based
  neighbour expansion, so multi-hop questions get much richer context.
• The sidebar shows graph stats (nodes / edges).
• Everything else (Groq LLM, dark theme, conversation tracker, feedback CSV)
  is kept exactly as before.
"""

import streamlit as st
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.prompts import PromptTemplate
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

import os, csv, re, random, datetime, time
from pathlib import Path

# ── Graph RAG modules ──────────────────────────────────────────────────────────
from graph_builder import KnowledgeGraphBuilder, GRAPH_PATH
from graph_retriever import GraphRetriever

# ── Constants ──────────────────────────────────────────────────────────────────
DB_DIR      = "db"
EMBED_MODEL = "sentence-transformers/all-mpnet-base-v2"
CHUNK_SIZE  = 500
CHUNK_OVERLAP = 100


# ══════════════════════════════════════════════════════════════════════════════
# Theme
# ══════════════════════════════════════════════════════════════════════════════

def set_dark_theme():
    st.markdown("""
    <style>
    .stApp { background-color: #0B1020; color: #EAEAF2; }
    section.main > div { max-width: 900px; margin: auto; }
    h1 { text-align:center; font-size:42px; font-weight:700; color:#FFF; margin-bottom:0; }
    .stChatMessage { background-color:#1E1E2E; border-radius:10px; padding:10px;
                     margin:5px 0; border:1px solid #2D3748; }
    [data-testid="chatMessageContent"] { color:#E5E7EB !important; }
    textarea { background-color:#111827 !important; color:#E5E7EB !important;
               border-radius:10px !important; border:1px solid #2D3748 !important; }
    button { background-color:#2563EB !important; color:white !important;
             border-radius:10px !important; width:100%; transition:all .3s ease; }
    button:hover { background-color:#1D4ED8 !important;
                   box-shadow:0 4px 6px rgba(37,99,235,.3); }
    .stExpander { background-color:#1E1E2E; border:1px solid #2D3748; border-radius:10px; }
    footer { visibility:hidden; }
    div[data-testid="column"] button {
        background-color:#2D3748 !important; color:#E5E7EB !important;
        border:1px solid #4A5568 !important; margin:2px !important; }
    div[data-testid="column"] button:hover { background-color:#4A5568 !important; }
    </style>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Helpers (kept from original)
# ══════════════════════════════════════════════════════════════════════════════

def is_greeting(query: str) -> bool:
    patterns = [r'\b(hi|hello|hey|greetings|howdy|sup|yo)\b',
                r'how are you', r"how's it going", r"what's up",
                r'good (morning|afternoon|evening)', r'nice to meet you']
    q = query.lower().strip()
    if len(q.split()) <= 3:
        for p in patterns:
            if re.search(p, q):
                return True
    return False


def get_greeting_response() -> str:
    opts = [
        "Hi there! 👋 I'm Wasla AI. How can I help you explore Wasla Solutions today?",
        "Hello! Great to have you here. What would you like to know about Wasla?",
        "Hey! I'm here to assist with any questions about Wasla Solutions. What's on your mind?",
    ]
    return random.choice(opts)


def save_to_csv(question, answer):
    path = "chat_history.csv"
    exists = os.path.isfile(path)
    try:
        with open(path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if not exists:
                w.writerow(["Question", "Answer", "Time", "Date"])
            w.writerow([question, answer,
                        datetime.datetime.now().strftime("%H:%M:%S"),
                        datetime.datetime.now().strftime("%Y-%m-%d")])
    except Exception:
        pass


def save_feedback(question, response, feedback):
    path = "feedback.csv"
    exists = os.path.isfile(path)
    try:
        with open(path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if not exists:
                w.writerow(["Question", "Response", "Feedback", "Time", "Date"])
            w.writerow([question, response, feedback,
                        datetime.datetime.now().strftime("%H:%M:%S"),
                        datetime.datetime.now().strftime("%Y-%m-%d")])
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# Conversation tracker
# ══════════════════════════════════════════════════════════════════════════════

class ConversationTracker:
    def __init__(self):
        self.topics_discussed = []
        self.message_count = 0

    def add_topic(self, topic):
        if topic and topic not in self.topics_discussed:
            self.topics_discussed.append(topic)
            if len(self.topics_discussed) > 5:
                self.topics_discussed = self.topics_discussed[-5:]

    def increment_count(self):
        self.message_count += 1

    def get_context(self):
        return {
            "msg_count": self.message_count,
            "previous_topics": ", ".join(self.topics_discussed) or "none yet",
        }


# ══════════════════════════════════════════════════════════════════════════════
# Prompt
# ══════════════════════════════════════════════════════════════════════════════

WASLA_PROMPT = PromptTemplate(
    template="""You are Wasla AI, a knowledgeable and friendly assistant for Wasla Solutions.

**CONVERSATION CONTEXT:**
Message #{msg_count} in conversation. Previous topics: {previous_topics}

**RETRIEVED CONTEXT (vector + graph-expanded):**
{context}

**USER QUESTION:**
{question}

**GUIDELINES:**
- Vary your openings; never repeat the same phrase twice.
- Use bullet points for lists; be specific and quote document details.
- If information is missing, say so politely and suggest related topics.
- Professional, warm tone. End with a natural follow-up question.

**YOUR RESPONSE:**""",
    input_variables=["context", "question", "msg_count", "previous_topics"],
)


def get_system_prompt() -> str:
    return (
        "You are Wasla AI, a knowledgeable and friendly assistant for Wasla Solutions. "
        "Be professional, warm, and vary your responses naturally. "
        "Only share information from the provided document context; never invent facts."
    )


# ══════════════════════════════════════════════════════════════════════════════
# LLM  (Groq – unchanged from original)
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_resource(ttl=3600)
def load_llm():
    try:
        from groq import Groq
    except ImportError:
        st.sidebar.error("❌ Install groq: pip install groq")
        return None

    if "GROQ_API_KEY" not in st.secrets:
        st.sidebar.error("❌ GROQ_API_KEY not in secrets!")
        return None

    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    models = [
        "llama-3.3-70b-versatile",
        "deepseek-r1-distill-llama-70b",
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "gemma2-9b-it",
    ]

    class GroqLLM:
        def __init__(self, client, model):
            self.client = client
            self.model = model

        def invoke(self, prompt):
            try:
                r = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": get_system_prompt()},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.8,
                    max_tokens=600,
                    top_p=0.9,
                )
                return r.choices[0].message.content
            except Exception as e:
                return f"Error: {e}"

    placeholder = st.sidebar.empty()
    for model in models:
        try:
            placeholder.info(f"🔄 Testing {model}…")
            llm = GroqLLM(client, model)
            test = llm.invoke("Reply with 'ready'")
            if test and "Error" not in test:
                placeholder.success(f"✅ AI ready  ({model.split('/')[-1]})")
                return llm
        except Exception:
            continue

    placeholder.error("❌ Could not start AI – check API key.")
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Vector store init
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_resource(ttl=3600)
def init_vectorstore():
    try:
        embeddings = HuggingFaceEmbeddings(
            model_name=EMBED_MODEL, model_kwargs={"device": "cpu"}
        )
        if os.path.exists(os.path.join(DB_DIR, "chroma.sqlite3")):
            db = Chroma(embedding_function=embeddings, persist_directory=DB_DIR)
            try:
                count = db._collection.count()
                st.sidebar.success(f"✅ Vector DB: {count} chunks")
            except Exception:
                st.sidebar.warning("⚠️ Vector DB loaded (count unavailable)")
            return db
        st.sidebar.warning("📁 No vector DB found – run ingestion first.")
        return None
    except Exception as e:
        st.sidebar.error(f"❌ Vector store error: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# Knowledge graph init
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_resource(ttl=3600)
def init_graph():
    builder = KnowledgeGraphBuilder()
    ok = builder.load()
    if ok:
        stats = builder.stats()
        st.sidebar.success(
            f"🕸️ Graph: {stats['nodes']} nodes · {stats['edges']} edges"
        )
        return builder.G
    st.sidebar.warning("🕸️ No graph found – run ingestion first.")
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Ingestion (Graph RAG version)
# ══════════════════════════════════════════════════════════════════════════════

def run_ingestion():
    progress_bar = st.progress(0)
    status = st.empty()

    try:
        status.text("📁 Scanning for PDFs…")
        docs_path = Path("docs")
        docs_path.mkdir(exist_ok=True)
        pdf_files = list(docs_path.glob("**/*.pdf"))
        if not pdf_files:
            status.text("❌ No PDFs in docs/ folder.")
            progress_bar.progress(100)
            time.sleep(2)
            return False

        # Load
        all_docs = []
        for i, pdf in enumerate(pdf_files):
            status.text(f"📄 Loading {pdf.name} ({i+1}/{len(pdf_files)})…")
            all_docs.extend(PyPDFLoader(str(pdf)).load())
            progress_bar.progress(int(20 * (i + 1) / len(pdf_files)))

        # Split
        status.text("✂️ Splitting into chunks…")
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
        )
        chunks = splitter.split_documents(all_docs)
        progress_bar.progress(30)

        # Embed + ChromaDB
        status.text("🔤 Creating embeddings & vector store…")
        embeddings = HuggingFaceEmbeddings(
            model_name=EMBED_MODEL, model_kwargs={"device": "cpu"}
        )
        Path(DB_DIR).mkdir(exist_ok=True)
        db = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=DB_DIR,
        )
        db.persist()
        progress_bar.progress(65)

        # Knowledge graph
        status.text("🕸️ Building knowledge graph…")

        def _gp(done, total):
            progress_bar.progress(65 + int(30 * done / total))

        builder = KnowledgeGraphBuilder()
        builder.build_from_documents(chunks, progress_callback=_gp)
        stats = builder.stats()

        progress_bar.progress(100)
        status.text(
            f"✅ Done!  {len(chunks)} chunks · "
            f"{stats['nodes']} graph nodes · {stats['edges']} edges"
        )
        time.sleep(2)
        status.empty()
        progress_bar.empty()
        return True

    except Exception as e:
        status.text(f"❌ Error: {e}")
        progress_bar.progress(100)
        time.sleep(3)
        status.empty()
        progress_bar.empty()
        return False


# ══════════════════════════════════════════════════════════════════════════════
# Question processing (Graph RAG)
# ══════════════════════════════════════════════════════════════════════════════

def process_question(prompt, vectorstore, graph, llm):
    """
    Run Graph RAG retrieval + LLM generation.
    Returns (response_text, retrieved_docs).
    """
    conv = st.session_state.conversation_tracker

    # Greeting shortcut
    if is_greeting(prompt) and conv.get_context()["msg_count"] <= 2:
        conv.increment_count()
        return get_greeting_response(), []

    # Build Graph Retriever
    retriever = GraphRetriever(
        vectorstore=vectorstore,
        graph=graph,
        k=5,
        graph_k=5,
        hop_depth=2,
    )

    docs = retriever.get_relevant_documents(prompt)
    conv.increment_count()

    # Build context string
    context = "\n\n".join(
        f"[Doc {i+1}]: {d.page_content}" for i, d in enumerate(docs)
    )

    ctx = conv.get_context()
    formatted = WASLA_PROMPT.format(
        context=context,
        question=prompt,
        msg_count=ctx["msg_count"],
        previous_topics=ctx["previous_topics"],
    )

    response = llm.invoke(formatted)
    save_to_csv(prompt, response)
    return response, docs


# ══════════════════════════════════════════════════════════════════════════════
# Welcome message
# ══════════════════════════════════════════════════════════════════════════════

def get_welcome_message() -> str:
    return random.choice([
        "👋 **Hi there! I'm Wasla AI** – now powered by **Graph RAG** for smarter, multi-hop answers.\n\nI can help with:\n- 📋 Services & solutions\n- 🕸️ Connected insights across your documents\n- 💡 Specific questions\n\nReady when you are! 🚀",
        "**Hello! I'm Wasla AI** – upgraded with a **knowledge graph** so I can connect related information across documents.\n\nAsk me anything about Wasla Solutions!",
    ])


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main():
    st.set_page_config(
        page_title="Wasla AI – Graph RAG",
        page_icon="🕸️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    set_dark_theme()

    # ── Session state ──────────────────────────────────────────────────────────
    for key, default in [
        ("messages", []),
        ("llm", None),
        ("vectorstore", None),
        ("graph", None),
        ("conversation_tracker", ConversationTracker()),
        ("welcome_shown", False),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    if not st.session_state.welcome_shown:
        st.session_state.welcome_shown = True
        st.session_state.messages.append({
            "role": "assistant",
            "content": get_welcome_message(),
            "sources": [],
            "feedback": None,
        })

    # ── Sidebar ────────────────────────────────────────────────────────────────
    with st.sidebar:
        st.title("🕸️ Wasla AI – Graph RAG")
        st.markdown("---")

        # API
        st.subheader("🔑 API Configuration")
        if "GROQ_API_KEY" in st.secrets:
            st.success("✅ Groq API key found")
            if st.button("🔄 Initialize AI", use_container_width=True):
                with st.spinner("Loading…"):
                    st.session_state.llm = load_llm()
                if st.session_state.llm:
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": "✅ **Graph RAG AI ready!** Ask me anything.",
                        "sources": [], "feedback": None,
                    })
        else:
            st.error("❌ GROQ_API_KEY not in secrets")

        st.markdown("---")

        # Knowledge base
        st.subheader("📚 Knowledge Base (Graph RAG)")
        db_exists = os.path.exists(os.path.join(DB_DIR, "chroma.sqlite3"))
        graph_exists = os.path.exists(GRAPH_PATH)

        if db_exists and graph_exists:
            if st.session_state.vectorstore is None:
                with st.spinner("Loading vector store…"):
                    st.session_state.vectorstore = init_vectorstore()
            if st.session_state.graph is None:
                with st.spinner("Loading knowledge graph…"):
                    st.session_state.graph = init_graph()
        else:
            if not db_exists:
                st.warning("❌ Vector store not found")
            if not graph_exists:
                st.warning("❌ Knowledge graph not found")

        docs_path = Path("docs")
        pdf_files = list(docs_path.glob("**/*.pdf")) if docs_path.exists() else []
        if pdf_files:
            st.info(f"📄 {len(pdf_files)} PDF(s) in docs/")
            if st.button("🚀 Build Graph RAG Index", type="primary", use_container_width=True):
                ok = run_ingestion()
                if ok:
                    # Reload caches
                    st.cache_resource.clear()
                    st.session_state.vectorstore = None
                    st.session_state.graph = None
                    st.rerun()
        else:
            st.warning("📁 No PDFs in docs/ folder")

        st.markdown("---")

        # Controls
        st.subheader("🎮 Controls")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔄 Reset AI", use_container_width=True):
                st.cache_resource.clear()
                st.session_state.llm = None
                st.rerun()
        with c2:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                first = st.session_state.messages[:1]
                st.session_state.messages = first
                st.session_state.conversation_tracker = ConversationTracker()
                st.rerun()

        with st.expander("ℹ️ System Status"):
            vs = st.session_state.vectorstore
            g  = st.session_state.graph
            lines = [
                f"🔑 Groq key : {'✅' if 'GROQ_API_KEY' in st.secrets else '❌'}",
                f"🤖 AI model : {'✅' if st.session_state.llm else '❌'}",
                f"📚 Vector DB: {'✅' if vs else '❌'}",
                f"🕸️ Graph    : {'✅ ' + str(g.number_of_nodes()) + ' nodes' if g else '❌'}",
                f"💬 Messages : {len(st.session_state.messages)}",
            ]
            st.write("\n".join(lines))

        if os.path.exists("chat_history.csv"):
            with open("chat_history.csv") as f:
                st.download_button("📥 Export Chat", f, "chat_history.csv",
                                   use_container_width=True)
        if os.path.exists("feedback.csv"):
            with open("feedback.csv") as f:
                st.download_button("📥 Export Feedback", f, "feedback.csv",
                                   use_container_width=True)

    # ── Chat UI ────────────────────────────────────────────────────────────────
    st.title("💬 Wasla AI  ·  Graph RAG")
    st.markdown("*Vector similarity + knowledge graph expansion for richer answers*")

    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

            if msg.get("sources"):
                with st.expander("📚 View Sources"):
                    for j, src in enumerate(msg["sources"], 1):
                        preview = src[:200] + "…" if len(src) > 200 else src
                        st.write(f"**Source {j}:**")
                        st.write(preview)

            # Feedback buttons on last assistant message
            if (msg["role"] == "assistant"
                    and i == len(st.session_state.messages) - 1
                    and msg.get("feedback") is None):
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("👍 Helpful", key=f"pos_{i}"):
                        st.session_state.messages[i]["feedback"] = "positive"
                        if i > 0 and st.session_state.messages[i-1]["role"] == "user":
                            save_feedback(st.session_state.messages[i-1]["content"],
                                          msg["content"], "positive")
                        st.rerun()
                with c2:
                    if st.button("👎 Not helpful", key=f"neg_{i}"):
                        st.session_state.messages[i]["feedback"] = "negative"
                        if i > 0 and st.session_state.messages[i-1]["role"] == "user":
                            save_feedback(st.session_state.messages[i-1]["content"],
                                          msg["content"], "negative")
                        st.rerun()

    # ── Input ──────────────────────────────────────────────────────────────────
    if prompt := st.chat_input("Ask a question about your documents…"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking (Graph RAG)…"):
                try:
                    db_ok    = os.path.exists(os.path.join(DB_DIR, "chroma.sqlite3"))
                    graph_ok = os.path.exists(GRAPH_PATH)

                    if not db_ok or not graph_ok:
                        resp = ("⚠️ **Knowledge base / graph not found.** "
                                "Please add PDFs to `docs/` and click *Build Graph RAG Index*.")
                        st.markdown(resp)
                        st.session_state.messages.append({
                            "role": "assistant", "content": resp,
                            "sources": [], "feedback": None})
                        st.stop()

                    if st.session_state.vectorstore is None:
                        st.session_state.vectorstore = init_vectorstore()
                    if st.session_state.graph is None:
                        st.session_state.graph = init_graph()
                    if st.session_state.llm is None:
                        with st.spinner("Starting AI…"):
                            st.session_state.llm = load_llm()

                    vs  = st.session_state.vectorstore
                    g   = st.session_state.graph
                    llm = st.session_state.llm

                    if not vs or not g or not llm:
                        resp = ("⚠️ **System not ready.** "
                                "Please initialise AI and rebuild the index.")
                        st.markdown(resp)
                        st.session_state.messages.append({
                            "role": "assistant", "content": resp,
                            "sources": [], "feedback": None})
                        st.stop()

                    response, docs = process_question(prompt, vs, g, llm)
                    st.markdown(response)

                    if docs:
                        with st.expander("📚 View Sources"):
                            for j, doc in enumerate(docs, 1):
                                preview = (doc.page_content[:200] + "…"
                                           if len(doc.page_content) > 200
                                           else doc.page_content)
                                st.write(f"**Source {j}:**")
                                st.write(preview)

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response,
                        "sources": [d.page_content for d in docs],
                        "feedback": None,
                    })

                except Exception as e:
                    err = f"❌ **Error:** {e}"
                    st.error(err)
                    st.session_state.messages.append({
                        "role": "assistant", "content": err,
                        "sources": [], "feedback": None})


if __name__ == "__main__":
    main()