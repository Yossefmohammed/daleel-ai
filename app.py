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
    /* Modern gradient background */
    .stApp { 
        background: linear-gradient(135deg, #0F0F1E 0%, #1A1A2E 50%, #16213E 100%);
        color: #E8E8F0;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Main content area */
    section.main > div { 
        max-width: 950px; 
        margin: auto;
        padding: 20px;
    }
    
    /* Headers */
    h1 { 
        text-align: center; 
        font-size: 48px; 
        font-weight: 800; 
        background: linear-gradient(135deg, #00D9FF, #0091FF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 5px;
        letter-spacing: -1px;
    }
    
    h2, h3 { color: #00D9FF; font-weight: 700; }
    
    /* Chat messages */
    .stChatMessage {
        background: linear-gradient(135deg, rgba(30,30,46,0.9) 0%, rgba(24,24,40,0.9) 100%);
        border-radius: 15px; 
        padding: 16px;
        margin: 12px 0; 
        border: 1px solid rgba(0, 217, 255, 0.2);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease;
    }
    
    .stChatMessage:hover {
        border-color: rgba(0, 217, 255, 0.4);
        box-shadow: 0 6px 20px rgba(0, 217, 255, 0.1);
    }
    
    [data-testid="chatMessageContent"] { 
        color: #E8E8F0 !important;
        font-size: 15px;
        line-height: 1.6;
    }
    
    /* Input area */
    .stChatInputContainer { margin-top: 20px; }
    
    textarea { 
        background-color: #1A1A2E !important; 
        color: #E8E8F0 !important;
        border-radius: 12px !important; 
        border: 1px solid rgba(0, 217, 255, 0.3) !important;
        font-size: 15px !important;
        transition: all 0.3s ease !important;
    }
    
    textarea:focus { 
        border-color: #00D9FF !important;
        box-shadow: 0 0 10px rgba(0, 217, 255, 0.2) !important;
    }
    
    /* Buttons */
    button {
        background: linear-gradient(135deg, #00D9FF, #0091FF) !important; 
        color: #000 !important;
        border-radius: 10px !important; 
        width: 100%; 
        transition: all 0.3s ease !important;
        font-weight: 600 !important;
        font-size: 14px !important;
    }
    
    button:hover { 
        background: linear-gradient(135deg, #00E5FF, #0099FF) !important;
        box-shadow: 0 6px 20px rgba(0, 217, 255, 0.3) !important;
        transform: translateY(-2px);
    }
    
    button:active {
        transform: translateY(0);
    }
    
    /* Expanders */
    .stExpander { 
        background: rgba(30,30,46,0.6); 
        border: 1px solid rgba(0, 217, 255, 0.2); 
        border-radius: 12px;
        transition: all 0.3s ease;
    }
    
    .stExpander:hover {
        border-color: rgba(0, 217, 255, 0.4);
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(135deg, #0F0F1E 0%, #1A1A2E 100%);
        border-right: 1px solid rgba(0, 217, 255, 0.2);
    }
    
    /* Status messages */
    .stSuccess {
        background-color: rgba(34, 197, 94, 0.15) !important;
        border: 1px solid rgba(34, 197, 94, 0.5) !important;
        border-radius: 10px !important;
    }
    
    .stWarning {
        background-color: rgba(251, 191, 36, 0.15) !important;
        border: 1px solid rgba(251, 191, 36, 0.5) !important;
        border-radius: 10px !important;
    }
    
    .stError {
        background-color: rgba(239, 68, 68, 0.15) !important;
        border: 1px solid rgba(239, 68, 68, 0.5) !important;
        border-radius: 10px !important;
    }
    
    .stInfo {
        background-color: rgba(59, 130, 246, 0.15) !important;
        border: 1px solid rgba(59, 130, 246, 0.5) !important;
        border-radius: 10px !important;
    }
    
    /* Control buttons */
    div[data-testid="column"] button {
        background: rgba(45, 55, 72, 0.8) !important; 
        color: #00D9FF !important;
        border: 1px solid rgba(0, 217, 255, 0.3) !important; 
        margin: 3px !important;
        transition: all 0.3s ease !important;
    }
    
    div[data-testid="column"] button:hover { 
        background: rgba(0, 217, 255, 0.1) !important;
        border-color: rgba(0, 217, 255, 0.6) !important;
    }
    
    /* Hide footer */
    footer { visibility: hidden; }
    
    /* Markdown styling */
    [data-testid="stMarkdownContainer"] { color: #E8E8F0; }
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
        "👋 **Welcome to Wasla AI!** I'm your intelligent assistant powered by Graph RAG technology.\n\n✨ **What I can help with:**\n• 📋 Document analysis and insights\n• 🕸️ Connected information across your knowledge base\n• 💡 Detailed answers to your questions\n• 🔗 Relationship discovery between topics\n\n💬 Ask me anything!",
        "🚀 **Hello! I'm Wasla AI** – leveraging advanced graph-based retrieval to provide you with the most relevant and connected answers.\n\n📊 Ready to explore your knowledge base...\n\n💭 What would you like to know?",
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
        ("auto_ingest_done", False),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    # ── Auto-ingestion on startup ──────────────────────────────────────────────
    if not st.session_state.auto_ingest_done:
        docs_path = Path("docs")
        docs_path.mkdir(exist_ok=True)
        pdf_files = list(docs_path.glob("**/*.pdf"))
        db_exists = os.path.exists(os.path.join(DB_DIR, "chroma.sqlite3"))
        graph_exists = os.path.exists(GRAPH_PATH)
        
        # Auto-ingest if PDFs exist but DB/graph don't
        if pdf_files and (not db_exists or not graph_exists):
            with st.spinner("🚀 Setting up knowledge base... (This runs once)"):
                try:
                    run_ingestion()
                    st.cache_resource.clear()
                except Exception as e:
                    st.warning(f"⚠️ Auto-ingestion encountered an issue: {e}")
        
        st.session_state.auto_ingest_done = True

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
        st.title("🕸️ Wasla AI")
        st.caption("🚀 Graph RAG Engine")
        st.markdown("---")

        # API Configuration
        st.subheader("🔑 API Configuration")
        if "GROQ_API_KEY" in st.secrets:
            st.success("✅ Groq API ready")
            if st.button("▶️ Start AI", use_container_width=True, key="btn_start_ai"):
                with st.spinner("Loading AI…"):
                    st.session_state.llm = load_llm()
                st.rerun()
        else:
            st.error("❌ GROQ_API_KEY missing")

        st.markdown("---")

        # Knowledge Base
        st.subheader("📚 Knowledge Base")
        db_exists = os.path.exists(os.path.join(DB_DIR, "chroma.sqlite3"))
        graph_exists = os.path.exists(GRAPH_PATH)

        if db_exists and graph_exists:
            st.success("✅ Ready")
            if st.session_state.vectorstore is None:
                with st.spinner("Loading…"):
                    st.session_state.vectorstore = init_vectorstore()
            if st.session_state.graph is None:
                with st.spinner("Loading…"):
                    st.session_state.graph = init_graph()
        else:
            st.info("⏳ Building...")

        docs_path = Path("docs")
        pdf_files = list(docs_path.glob("**/*.pdf")) if docs_path.exists() else []
        if pdf_files:
            st.info(f"📄 {len(pdf_files)} PDF(s) found")
            if not db_exists or not graph_exists:
                if st.button("🔨 Build Now", use_container_width=True, key="btn_build_manual"):
                    ok = run_ingestion()
                    if ok:
                        st.cache_resource.clear()
                        st.rerun()

        st.markdown("---")

        # Quick Controls
        st.subheader("⚙️ Controls")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔄 Reset", use_container_width=True, key="btn_reset"):
                st.cache_resource.clear()
                st.session_state.llm = None
                st.rerun()
        with c2:
            if st.button("🗑️ Clear", use_container_width=True, key="btn_clear"):
                first = st.session_state.messages[:1]
                st.session_state.messages = first
                st.session_state.conversation_tracker = ConversationTracker()
                st.rerun()

        st.markdown("---")

        # System Status
        with st.expander("ℹ️ System Status", expanded=True):
            vs = st.session_state.vectorstore
            g = st.session_state.graph
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Groq", "🟢" if "GROQ_API_KEY" in st.secrets else "🔴")
                st.metric("AI", "🟢" if st.session_state.llm else "🔴")
            with col2:
                st.metric("Vector DB", "🟢" if vs else "🔴")
                st.metric("Graph", "🟢" if g else "🔴")
            
            st.divider()
            st.caption(f"📊 Messages: {len(st.session_state.messages)}")
            if g:
                st.caption(f"🕸️ Nodes: {g.number_of_nodes()} | Edges: {g.number_of_edges()}")

        st.markdown("---")

        # Export Data
        st.subheader("📥 Export")
        if os.path.exists("chat_history.csv"):
            with open("chat_history.csv") as f:
                st.download_button(
                    "💬 Chat History",
                    f,
                    "chat_history.csv",
                    use_container_width=True,
                    key="btn_export_chat"
                )
        if os.path.exists("feedback.csv"):
            with open("feedback.csv") as f:
                st.download_button(
                    "👍 Feedback Data",
                    f,
                    "feedback.csv",
                    use_container_width=True,
                    key="btn_export_feedback"
                )

    # ── Chat UI ────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style='text-align: center; margin-bottom: 30px;'>
        <h1 style='margin: 0;'>🕸️ Wasla AI Assistant</h1>
        <p style='color: #00D9FF; font-size: 16px; margin-top: 8px;'>💬 Intelligent Conversations Powered by Graph RAG</p>
    </div>
    """, unsafe_allow_html=True)

    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

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