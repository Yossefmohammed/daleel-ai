"""
Wasla AI – Graph RAG Chatbot  (Redesigned UI)
==============================================
Key fixes vs original:
  • st.chat_input  →  Enter key sends the message (was broken with st.text_area)
  • Full dark UI redesign: deep navy, cyan accents, Plus Jakarta Sans font
  • Proper message bubbles, source pills, feedback buttons
  • All Graph RAG / LLM logic kept exactly as-is
"""

import os
import csv
import re
import random
import datetime
import time
from pathlib import Path

import streamlit as st
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from graph_builder import KnowledgeGraphBuilder, GRAPH_PATH
from graph_retriever import GraphRetriever

# ── Constants ──────────────────────────────────────────────────────────────
DB_DIR        = "db"
EMBED_MODEL   = "sentence-transformers/all-mpnet-base-v2"
CHUNK_SIZE    = 500
CHUNK_OVERLAP = 100

# ── Page config (must be first Streamlit call) ─────────────────────────────
st.set_page_config(
    page_title="Wasla AI",
    page_icon="🕸️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════════════════
def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --navy:    #080c18;
  --navy2:   #0d1326;
  --navy3:   #111829;
  --navy4:   #172035;
  --navy5:   #1e2d47;
  --line:    rgba(255,255,255,0.06);
  --line2:   rgba(255,255,255,0.10);
  --t1:      #e8eeff;
  --t2:      #7a8ab0;
  --t3:      #3d4a6a;
  --cyan:    #00d9ff;
  --cyan2:   #00b3d4;
  --cyan-d:  rgba(0,217,255,0.08);
  --cyan-b:  rgba(0,217,255,0.20);
  --sage:    #34d399;
  --ff: 'Plus Jakarta Sans', system-ui, sans-serif;
  --fm: 'JetBrains Mono', monospace;
  --r: 14px; --rs: 9px;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body,
[data-testid="stApp"],
[data-testid="stAppViewContainer"],
.main { background: var(--navy) !important; font-family: var(--ff) !important; }

#MainMenu, header, footer,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"] { display: none !important; }

.block-container { padding: 0 !important; max-width: 100% !important; }
section.main > div { padding: 0 !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
  background: var(--navy2) !important;
  border-right: 1px solid var(--line) !important;
  min-width: 268px !important; max-width: 268px !important;
}
[data-testid="stSidebar"] > div:first-child { padding: 0 !important; }
[data-testid="stSidebar"] .stButton > button {
  background: transparent !important;
  border: 1px solid var(--line2) !important;
  border-radius: var(--rs) !important;
  color: var(--t2) !important;
  font-family: var(--ff) !important;
  font-size: 12.5px !important;
  font-weight: 500 !important;
  padding: 9px 14px !important;
  transition: all 0.18s !important;
  width: 100% !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
  background: var(--navy4) !important;
  border-color: var(--cyan-b) !important;
  color: var(--t1) !important;
  transform: none !important;
  box-shadow: none !important;
}
[data-testid="stExpander"] {
  background: var(--navy3) !important;
  border: 1px solid var(--line) !important;
  border-radius: var(--r) !important;
}
[data-testid="stExpander"] summary { color: var(--t2) !important; font-size: 12px !important; }
[data-testid="stAlert"] {
  background: var(--navy3) !important;
  border-radius: var(--r) !important;
  border: 1px solid var(--line2) !important;
  color: var(--t2) !important; font-size: 12.5px !important;
}
[data-testid="stMetricLabel"] { color: var(--t3) !important; font-size: 11px !important; }
[data-testid="stMetricValue"] { color: var(--t1) !important; font-size: 18px !important; }
[data-testid="stDownloadButton"] > button {
  background: transparent !important;
  border: 1px solid var(--line2) !important;
  border-radius: var(--rs) !important;
  color: var(--t2) !important; font-size: 12px !important;
}
[data-testid="stDownloadButton"] > button:hover {
  border-color: var(--cyan-b) !important;
  color: var(--cyan) !important; transform: none !important;
}

/* ── Header ── */
.wasla-hdr {
  background: var(--navy2);
  border-bottom: 1px solid var(--line);
  padding: 0 28px; height: 60px;
  display: flex; align-items: center; justify-content: space-between;
  flex-shrink: 0;
}
.hdr-left { display: flex; align-items: center; gap: 14px; }
.hdr-gem  {
  width: 38px; height: 38px; border-radius: 11px;
  background: linear-gradient(135deg,#007acc,#00d9ff);
  display: flex; align-items: center; justify-content: center; font-size: 18px;
  box-shadow: 0 4px 14px rgba(0,217,255,0.25);
}
.hdr-title { font-size: 16px; font-weight: 800; color: var(--t1); letter-spacing: -.3px; }
.hdr-sub   { font-size: 11px; color: var(--t3); margin-top: 2px; }
.hdr-right { display: flex; gap: 8px; }
.hdr-badge {
  font-size: 10px; font-weight: 600; padding: 4px 10px;
  border-radius: 20px; border: 1px solid var(--line2);
  color: var(--t3); background: var(--navy3);
}
.hdr-badge.live {
  background: rgba(52,211,153,.10); border-color: rgba(52,211,153,.25); color: var(--sage);
}

/* ── Feed ── */
.wasla-feed {
  flex: 1; overflow-y: auto; padding: 26px 0 10px;
  scrollbar-width: thin; scrollbar-color: var(--line2) transparent;
}
.wasla-feed::-webkit-scrollbar { width: 3px; }
.wasla-feed::-webkit-scrollbar-thumb { background: var(--line2); border-radius: 3px; }

/* ── Messages ── */
.msg  { display: flex; gap: 13px; padding: 0 28px; margin-bottom: 22px; animation: fu .22s ease; }
.msg.u { flex-direction: row-reverse; }
@keyframes fu { from{opacity:0;transform:translateY(5px)} to{opacity:1;transform:translateY(0)} }
.av {
  width: 36px; height: 36px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700; flex-shrink: 0; margin-top: 2px;
}
.av.b { background: linear-gradient(135deg,#007acc,#00d9ff); color:#fff; box-shadow:0 3px 10px rgba(0,217,255,.25); }
.av.u { background: var(--navy5); border: 1px solid var(--line2); color: var(--t2); }
.bub  { max-width: 74%; }
.bi   { padding: 13px 17px; font-size: 13.5px; line-height: 1.72; color: var(--t1); border-radius: 18px; }
.bot .bi { background: var(--navy3); border: 1px solid var(--line); border-top-left-radius: 4px; }
.usr .bi { background: linear-gradient(135deg,#00527a,#007cc2); border-top-right-radius: 4px; color:#fff; }
.bm  { font-size: 10px; color: var(--t3); margin-top: 5px; padding: 0 4px; display:flex; gap:5px; align-items:center; }
.usr .bm { justify-content: flex-end; }
.bmd { width:3px;height:3px;border-radius:50%;background:var(--t3); }

/* Source pills */
.srcs { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.spill {
  font-size: 10px; font-weight: 600; padding: 3px 9px; border-radius: 20px;
  background: var(--cyan-d); color: var(--cyan); border: 1px solid var(--cyan-b);
  font-family: var(--fm);
}

/* ── Starter chips ── */
.chips-wrap { padding: 0 28px 20px; }
.chip-row   { display: flex; flex-wrap: wrap; gap: 8px; }

/* Chips rendered via st.button — override in main content area */
div[class*="stHorizontalBlock"] .stButton > button {
  background: var(--navy3) !important;
  border: 1px solid var(--line2) !important;
  border-radius: 30px !important;
  color: var(--t2) !important;
  font-size: 12px !important;
  font-weight: 500 !important;
  padding: 7px 15px !important;
  transition: all .18s !important;
  white-space: nowrap !important;
}
div[class*="stHorizontalBlock"] .stButton > button:hover {
  border-color: var(--cyan-b) !important;
  color: var(--cyan) !important;
  background: var(--cyan-d) !important;
  transform: translateY(-1px) !important;
  box-shadow: none !important;
}

/* ── Input ── */
.input-meta {
  display: flex; align-items: center; gap: 10px;
  padding: 12px 28px 8px;
  background: var(--navy2); border-top: 1px solid var(--line);
  flex-shrink: 0;
}
.im-tag {
  font-size: 10px; font-weight: 700; letter-spacing: .06em;
  text-transform: uppercase; padding: 3px 10px; border-radius: 20px;
  background: var(--cyan-d); color: var(--cyan); border: 1px solid var(--cyan-b);
}
.im-hint { font-size: 11px; color: var(--t3); }

/* st.chat_input */
[data-testid="stChatInput"] {
  background: var(--navy3) !important;
  border: 1px solid var(--line2) !important;
  border-radius: var(--r) !important;
  margin: 0 28px 16px !important;
  transition: border-color .18s, box-shadow .18s !important;
}
[data-testid="stChatInput"]:focus-within {
  border-color: var(--cyan) !important;
  box-shadow: 0 0 0 2px var(--cyan-d) !important;
}
[data-testid="stChatInput"] textarea {
  background: transparent !important;
  border: none !important;
  color: var(--t1) !important;
  font-family: var(--ff) !important;
  font-size: 13.5px !important;
  caret-color: var(--cyan) !important;
}
[data-testid="stChatInput"] textarea::placeholder { color: var(--t3) !important; }
[data-testid="stChatInput"] button {
  background: linear-gradient(135deg,#007acc,#00d9ff) !important;
  border: none !important; border-radius: 9px !important;
  color: var(--navy) !important;
}

.stProgress > div > div { background: var(--cyan) !important; }

/* Feedback row buttons */
.fb-row .stButton > button {
  background: transparent !important;
  border: 1px solid var(--line) !important;
  border-radius: var(--rs) !important;
  color: var(--t3) !important;
  padding: 4px 10px !important;
  font-size: 12px !important;
  transition: all .15s !important;
}
.fb-row .stButton > button:hover {
  border-color: var(--cyan-b) !important;
  color: var(--cyan) !important;
  transform: none !important;
}

.sb-div { height: 1px; background: var(--line); margin: 14px 0; }
.sb-lbl {
  font-size: 10px; font-weight: 700; letter-spacing: .09em;
  text-transform: uppercase; color: var(--t3); padding-bottom: 8px;
}
.sb-stat { display:flex; align-items:center; gap:8px; font-size:11px; color:var(--t3); }
.sb-dot  { width:7px;height:7px;border-radius:50%;animation:blink 2.4s ease-in-out infinite; }
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════
def ts():
    return datetime.datetime.now().strftime("%H:%M")


def is_greeting(q: str) -> bool:
    patterns = [r'\b(hi|hello|hey|greetings|howdy|sup|yo)\b',
                r'how are you', r"how's it going", r"what's up",
                r'good (morning|afternoon|evening)']
    q = q.lower().strip()
    if len(q.split()) <= 4:
        for p in patterns:
            if re.search(p, q):
                return True
    return False


def get_greeting() -> str:
    return random.choice([
        "Hi there! 👋 I'm **Wasla AI**. What would you like to know about Wasla Solutions today?",
        "Hello! Great to have you here. How can I help you explore Wasla's services?",
        "Hey! I'm here to help with any questions about Wasla Solutions. What's on your mind?",
    ])


def save_csv(question, answer):
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


def save_feedback(question, response, fb):
    path = "feedback.csv"
    exists = os.path.isfile(path)
    try:
        with open(path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if not exists:
                w.writerow(["Question", "Response", "Feedback", "Time", "Date"])
            w.writerow([question, response, fb,
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
        self.message_count    = 0

    def add_topic(self, t):
        if t and t not in self.topics_discussed:
            self.topics_discussed.append(t)
            if len(self.topics_discussed) > 5:
                self.topics_discussed = self.topics_discussed[-5:]

    def increment_count(self):
        self.message_count += 1

    def get_context(self):
        return {
            "msg_count":       self.message_count,
            "previous_topics": ", ".join(self.topics_discussed) or "none yet",
        }


# ══════════════════════════════════════════════════════════════════════════════
# Prompt
# ══════════════════════════════════════════════════════════════════════════════
WASLA_PROMPT = PromptTemplate(
    template="""You are Wasla AI, a knowledgeable and friendly assistant for Wasla Solutions.

**CONVERSATION CONTEXT:**
Message #{msg_count}. Previous topics: {previous_topics}

**RETRIEVED CONTEXT (vector + graph-expanded):**
{context}

**USER QUESTION:**
{question}

**GUIDELINES:**
- Vary your openings; never repeat the same phrase twice.
- Use bullet points for lists; be specific and cite document details.
- If information is missing, say so politely and suggest related topics.
- Professional, warm tone. End with a natural follow-up question.

**YOUR RESPONSE:**""",
    input_variables=["context", "question", "msg_count", "previous_topics"],
)

SYSTEM_PROMPT = (
    "You are Wasla AI, a knowledgeable and friendly assistant for Wasla Solutions. "
    "Be professional, warm, and vary your responses naturally. "
    "Only share information from the provided document context; never invent facts."
)


# ══════════════════════════════════════════════════════════════════════════════
# LLM
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_resource(ttl=3600)
def load_llm():
    try:
        from groq import Groq
    except ImportError:
        st.sidebar.error("❌ Install groq: pip install groq")
        return None

    key = None
    if hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
        key = st.secrets["GROQ_API_KEY"]
    elif os.getenv("GROQ_API_KEY"):
        key = os.getenv("GROQ_API_KEY")
    if not key:
        st.sidebar.error("❌ GROQ_API_KEY not found")
        return None

    client = Groq(api_key=key)

    class GroqLLM:
        def __init__(self, c, model):
            self.client = c; self.model = model
        def invoke(self, prompt):
            try:
                r = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role":"system","content":SYSTEM_PROMPT},
                               {"role":"user","content":prompt}],
                    temperature=0.8, max_tokens=600, top_p=0.9,
                )
                return r.choices[0].message.content
            except Exception as e:
                return f"Sorry, I ran into an issue: {e}"

    ph = st.sidebar.empty()
    for model in ["llama-3.3-70b-versatile","deepseek-r1-distill-llama-70b",
                  "meta-llama/llama-4-scout-17b-16e-instruct","gemma2-9b-it"]:
        try:
            ph.info(f"🔄 Testing {model.split('/')[-1]}…")
            llm  = GroqLLM(client, model)
            test = llm.invoke("Reply with: ready")
            if test and "Error" not in test:
                ph.success(f"✅ AI ready · {model.split('/')[-1]}")
                return llm
        except Exception:
            continue
    ph.error("❌ Could not start AI")
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Vector store & graph
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_resource(ttl=3600)
def init_vectorstore():
    try:
        emb = HuggingFaceEmbeddings(model_name=EMBED_MODEL, model_kwargs={"device":"cpu"})
        if os.path.exists(os.path.join(DB_DIR,"chroma.sqlite3")):
            db = Chroma(embedding_function=emb, persist_directory=DB_DIR)
            try:
                count = db._collection.count()
                st.sidebar.success(f"✅ Vector DB — {count} chunks")
            except Exception:
                st.sidebar.success("✅ Vector DB loaded")
            return db
        st.sidebar.warning("📁 No vector DB — run ingestion")
    except Exception as e:
        st.sidebar.error(f"❌ Vector store: {e}")
    return None


@st.cache_resource(ttl=3600)
def init_graph():
    builder = KnowledgeGraphBuilder()
    if builder.load():
        s = builder.stats()
        st.sidebar.success(f"🕸️ Graph — {s['nodes']} nodes · {s['edges']} edges")
        return builder.G
    st.sidebar.warning("🕸️ No graph — run ingestion")
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Ingestion
# ══════════════════════════════════════════════════════════════════════════════
def run_ingestion():
    bar = st.progress(0); status = st.empty()
    try:
        status.text("📁 Scanning PDFs…")
        docs_path = Path("docs"); docs_path.mkdir(exist_ok=True)
        pdfs = list(docs_path.glob("**/*.pdf"))
        if not pdfs:
            status.warning("No PDFs in docs/ folder."); bar.progress(100); time.sleep(2); return False

        all_docs = []
        for i, pdf in enumerate(pdfs):
            status.text(f"📄 {pdf.name} ({i+1}/{len(pdfs)})…")
            all_docs.extend(PyPDFLoader(str(pdf)).load())
            bar.progress(int(20*(i+1)/len(pdfs)))

        status.text("✂️ Splitting…")
        chunks = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
        ).split_documents(all_docs)
        bar.progress(30)

        status.text("🔤 Building vector store…")
        emb = HuggingFaceEmbeddings(model_name=EMBED_MODEL, model_kwargs={"device":"cpu"})
        Path(DB_DIR).mkdir(exist_ok=True)
        db = Chroma.from_documents(chunks, embedding=emb, persist_directory=DB_DIR)
        db.persist(); bar.progress(65)

        status.text("🕸️ Building knowledge graph…")
        builder = KnowledgeGraphBuilder()
        builder.build_from_documents(chunks, progress_callback=lambda d,t: bar.progress(65+int(30*d/t)))
        s = builder.stats(); bar.progress(100)
        status.success(f"✅ {len(chunks)} chunks · {s['nodes']} nodes · {s['edges']} edges")
        time.sleep(2); status.empty(); bar.empty()
        return True
    except Exception as e:
        status.error(f"❌ {e}"); bar.progress(100); time.sleep(3); status.empty(); bar.empty()
        return False


# ══════════════════════════════════════════════════════════════════════════════
# Question processing
# ══════════════════════════════════════════════════════════════════════════════
def process_question(prompt, vectorstore, graph, llm):
    conv = st.session_state.conversation_tracker
    if is_greeting(prompt) and conv.get_context()["msg_count"] <= 2:
        conv.increment_count()
        return get_greeting(), []

    retriever = GraphRetriever(vectorstore=vectorstore, graph=graph, k=5, graph_k=5, hop_depth=2)
    docs      = retriever.get_relevant_documents(prompt)
    conv.increment_count()

    ctx       = conv.get_context()
    context   = "\n\n".join(f"[Doc {i+1}]: {d.page_content}" for i,d in enumerate(docs))
    formatted = WASLA_PROMPT.format(
        context=context, question=prompt,
        msg_count=ctx["msg_count"], previous_topics=ctx["previous_topics"],
    )
    response = llm.invoke(formatted)
    save_csv(prompt, response)
    return response, docs


# ══════════════════════════════════════════════════════════════════════════════
# Welcome & starters
# ══════════════════════════════════════════════════════════════════════════════
WELCOME = (
    "👋 **Welcome to Wasla AI!** I'm your intelligent assistant powered by Graph RAG.\n\n"
    "**What I can help with:**\n"
    "• 📋 Document analysis and insights\n"
    "• 🕸️ Connected information across the knowledge base\n"
    "• 💡 Detailed answers with source references\n"
    "• 🔗 Relationship discovery between topics\n\n"
    "💬 Ask me anything about Wasla Solutions!"
)

STARTERS = [
    "What services does Wasla offer?",
    "How does Graph RAG work?",
    "Tell me about Wasla's API",
    "What industries does Wasla serve?",
]


# ══════════════════════════════════════════════════════════════════════════════
# Render helpers
# ══════════════════════════════════════════════════════════════════════════════
def render_messages():
    msgs = st.session_state.messages
    for i, m in enumerate(msgs):
        role    = m["role"]
        content = m["content"]
        t       = m.get("ts", "")
        sources = m.get("sources", [])

        if role == "user":
            st.markdown(
                f'<div class="msg u">'
                f'<div class="av u">YOU</div>'
                f'<div class="bub usr"><div class="bi">{content}</div>'
                f'<div class="bm">{t}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
        else:
            src_html = ""
            if sources:
                pills = "".join(f'<span class="spill">doc {j+1}</span>'
                                for j in range(min(len(sources), 4)))
                src_html = f'<div class="srcs">{pills}</div>'

            st.markdown(
                f'<div class="msg bot">'
                f'<div class="av b">W</div>'
                f'<div class="bub bot"><div class="bi">{content}</div>'
                f'{src_html}'
                f'<div class="bm">Wasla AI <span class="bmd"></span> {t}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

            # Feedback on last bot message
            if i == len(msgs) - 1:
                st.markdown('<div class="fb-row">', unsafe_allow_html=True)
                fb1, fb2, _ = st.columns([1, 1, 10])
                with fb1:
                    if st.button("👍", key=f"up_{i}"):
                        save_feedback(msgs[i-1]["content"] if i>0 else "", content, "positive")
                        st.toast("Thanks!", icon="✅")
                with fb2:
                    if st.button("👎", key=f"dn_{i}"):
                        save_feedback(msgs[i-1]["content"] if i>0 else "", content, "negative")
                        st.toast("Got it!", icon="📝")
                st.markdown('</div>', unsafe_allow_html=True)


def render_sidebar():
    with st.sidebar:
        # Logo
        st.markdown(
            '<div style="padding:20px 16px 16px;border-bottom:1px solid rgba(255,255,255,.06)">'
            '<div style="display:flex;align-items:center;gap:12px">'
            '<div style="width:38px;height:38px;border-radius:11px;'
            'background:linear-gradient(135deg,#007acc,#00d9ff);'
            'display:flex;align-items:center;justify-content:center;font-size:18px;'
            'box-shadow:0 4px 14px rgba(0,217,255,.25)">🕸️</div>'
            '<div><div style="font-size:15px;font-weight:800;color:#e8eeff;letter-spacing:-.3px">Wasla AI</div>'
            '<div style="font-size:10px;color:#00d9ff;background:rgba(0,217,255,.08);'
            'padding:2px 8px;border-radius:20px;border:1px solid rgba(0,217,255,.2);'
            'display:inline-block;font-weight:600;margin-top:2px">Graph RAG</div>'
            '</div></div></div>',
            unsafe_allow_html=True,
        )

        st.markdown("<div style='padding:14px 14px 0'>", unsafe_allow_html=True)

        # AI
        st.markdown('<div class="sb-lbl">AI Engine</div>', unsafe_allow_html=True)
        key_ok = (hasattr(st,"secrets") and "GROQ_API_KEY" in st.secrets) or bool(os.getenv("GROQ_API_KEY"))
        if key_ok:
            st.success("✅ Groq API key found")
            if st.button("▶ Start AI", key="btn_start_ai", use_container_width=True):
                with st.spinner("Loading AI…"):
                    st.session_state.llm = load_llm(); st.rerun()
        else:
            st.error("❌ GROQ_API_KEY missing")

        st.markdown('<div class="sb-div"></div>', unsafe_allow_html=True)

        # Knowledge base
        st.markdown('<div class="sb-lbl">Knowledge Base</div>', unsafe_allow_html=True)
        db_ok    = os.path.exists(os.path.join(DB_DIR,"chroma.sqlite3"))
        graph_ok = os.path.exists(GRAPH_PATH)

        if db_ok and graph_ok:
            st.success("✅ Index ready")
            if st.session_state.vectorstore is None:
                with st.spinner("Loading vector DB…"): st.session_state.vectorstore = init_vectorstore()
            if st.session_state.graph is None:
                with st.spinner("Loading graph…"): st.session_state.graph = init_graph()
        else:
            docs_path = Path("docs")
            pdfs = list(docs_path.glob("**/*.pdf")) if docs_path.exists() else []
            st.warning(f"{'📄 '+str(len(pdfs))+' PDF(s) found — index not built' if pdfs else '📁 No PDFs in docs/ folder'}")
            if st.button("🔨 Build Index", key="btn_build", use_container_width=True):
                if run_ingestion():
                    st.cache_resource.clear(); st.rerun()

        st.markdown('<div class="sb-div"></div>', unsafe_allow_html=True)

        # Status
        with st.expander("⚙️ System Status", expanded=True):
            vs = st.session_state.vectorstore; g = st.session_state.graph
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Groq",   "🟢" if key_ok else "🔴")
                st.metric("AI",     "🟢" if st.session_state.llm else "🔴")
            with c2:
                st.metric("Vector", "🟢" if vs else "🔴")
                st.metric("Graph",  "🟢" if g  else "🔴")
            if g: st.caption(f"Nodes: {g.number_of_nodes()} · Edges: {g.number_of_edges()}")
            st.caption(f"Messages: {len(st.session_state.messages)}")

        st.markdown('<div class="sb-div"></div>', unsafe_allow_html=True)

        # Controls
        st.markdown('<div class="sb-lbl">Controls</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔄 Reset", key="btn_reset", use_container_width=True):
                st.cache_resource.clear(); st.session_state.llm = None; st.rerun()
        with c2:
            if st.button("🗑 Clear", key="btn_clear", use_container_width=True):
                st.session_state.messages = [{"role":"assistant","content":WELCOME,"ts":ts(),"sources":[]}]
                st.session_state.conversation_tracker = ConversationTracker(); st.rerun()

        st.markdown('<div class="sb-div"></div>', unsafe_allow_html=True)

        # Export
        st.markdown('<div class="sb-lbl">Export</div>', unsafe_allow_html=True)
        if os.path.exists("chat_history.csv"):
            with open("chat_history.csv") as f:
                st.download_button("💬 Chat History", f, "chat_history.csv",
                                   use_container_width=True, key="dl_chat")
        if os.path.exists("feedback.csv"):
            with open("feedback.csv") as f:
                st.download_button("👍 Feedback", f, "feedback.csv",
                                   use_container_width=True, key="dl_fb")

        st.markdown('<div class="sb-div"></div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="sb-stat">'
            '<div class="sb-dot" style="background:#34d399"></div>'
            'Graph RAG · LLaMA 3.3-70b'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Submit handler
# ══════════════════════════════════════════════════════════════════════════════
def _submit(user_msg: str):
    msgs = st.session_state.messages
    msgs.append({"role":"user","content":user_msg,"ts":ts(),"sources":[]})

    llm   = st.session_state.llm
    vs    = st.session_state.vectorstore
    graph = st.session_state.graph

    if not llm:
        msgs.append({"role":"assistant","ts":ts(),"sources":[],
                     "content":"⚠️ AI not started. Click **▶ Start AI** in the sidebar."})
        st.rerun(); return

    if not vs or not graph:
        msgs.append({"role":"assistant","ts":ts(),"sources":[],
                     "content":"⚠️ Knowledge base not ready. Click **Build Index** in the sidebar first."})
        st.rerun(); return

    with st.spinner("Wasla AI is thinking…"):
        response, sources = process_question(user_msg, vs, graph, llm)

    msgs.append({"role":"assistant","content":response,"ts":ts(),"sources":sources})
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════
def main():
    inject_css()

    # Session state
    for k, v in {
        "messages":             [],
        "llm":                  None,
        "vectorstore":          None,
        "graph":                None,
        "conversation_tracker": ConversationTracker(),
        "auto_ingest_done":     False,
        "_pending":             None,
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # Auto-ingest
    if not st.session_state.auto_ingest_done:
        docs_path = Path("docs"); docs_path.mkdir(exist_ok=True)
        pdfs     = list(docs_path.glob("**/*.pdf"))
        db_ok    = os.path.exists(os.path.join(DB_DIR,"chroma.sqlite3"))
        graph_ok = os.path.exists(GRAPH_PATH)
        if pdfs and (not db_ok or not graph_ok):
            with st.spinner("🚀 Setting up knowledge base (runs once)…"):
                try:
                    run_ingestion(); st.cache_resource.clear()
                except Exception as e:
                    st.warning(f"Auto-ingest issue: {e}")
        st.session_state.auto_ingest_done = True

    # Welcome message
    if not st.session_state.messages:
        st.session_state.messages.append(
            {"role":"assistant","content":WELCOME,"ts":ts(),"sources":[]}
        )

    # Sidebar
    render_sidebar()

    # Header
    vs_ok = st.session_state.vectorstore is not None
    g_ok  = st.session_state.graph is not None
    st.markdown(
        '<div class="wasla-hdr">'
        '<div class="hdr-left">'
        '<div class="hdr-gem">🕸️</div>'
        '<div><div class="hdr-title">Wasla AI Assistant</div>'
        '<div class="hdr-sub">Powered by Graph RAG · Ask anything about Wasla Solutions</div>'
        '</div></div>'
        '<div class="hdr-right">'
        + ('<div class="hdr-badge live">● RAG Active</div>' if vs_ok and g_ok
           else '<div class="hdr-badge">○ RAG Offline</div>')
        + '<div class="hdr-badge">Groq · LLaMA 3.3</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    # Starter chips (first visit only)
    if len(st.session_state.messages) == 1:
        cols = st.columns(len(STARTERS))
        for i, (col, q) in enumerate(zip(cols, STARTERS)):
            with col:
                if st.button(q, key=f"s_{i}", use_container_width=True):
                    st.session_state._pending = q; st.rerun()

    # Messages
    render_messages()

    # Handle chip pending
    if st.session_state._pending:
        p = st.session_state._pending
        st.session_state._pending = None
        _submit(p); return

    # ── Chat input — Enter sends! ──────────────────────────────────────────
    st.markdown(
        '<div class="input-meta">'
        '<span class="im-tag">WASLA AI</span>'
        '<span class="im-hint">Enter to send · Shift+Enter for new line</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    user_input = st.chat_input("Ask Wasla AI anything…", key="chat_main")
    if user_input and user_input.strip():
        _submit(user_input.strip())


if __name__ == "__main__":
    main()