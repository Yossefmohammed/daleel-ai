"""
PathIQ — Career Intelligence Platform
======================================
Rebuilt UI: professional dark design, service-based chat tabs,
human-like streaming responses, Graph RAG backend.
"""

import os
import streamlit as st
from dotenv import load_dotenv
import json
import csv
import datetime
import random
import re
import time
from pathlib import Path

load_dotenv()

# ── Page config (must be first Streamlit call) ─────────────────────────────
st.set_page_config(
    page_title="PathIQ — Career Intelligence",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Lazy imports (graceful degradation if deps missing) ─────────────────────
try:
    from cv_analyzer import CVAnalyzer
    CV_AVAILABLE = True
except ImportError:
    CV_AVAILABLE = False

try:
    from github_analyzer import GitHubAnalyzer
    GH_AVAILABLE = True
except ImportError:
    GH_AVAILABLE = False

try:
    from job_matcher import JobMatcher
    JM_AVAILABLE = True
except ImportError:
    JM_AVAILABLE = False

try:
    from graph_builder import KnowledgeGraphBuilder, GRAPH_PATH
    from graph_retriever import GraphRetriever
    from langchain_community.vectorstores import Chroma
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_core.prompts import PromptTemplate
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False

# ── Constants ───────────────────────────────────────────────────────────────
DB_DIR        = "db"
EMBED_MODEL   = "sentence-transformers/all-mpnet-base-v2"
CHUNK_SIZE    = 500
CHUNK_OVERLAP = 100

SERVICES = {
    "cv":     {"label": "CV Analyzer",      "icon": "📄", "color": "#7c6af5"},
    "github": {"label": "Code Profile",     "icon": "💻", "color": "#2dd4c4"},
    "jobs":   {"label": "Job Matcher",      "icon": "🎯", "color": "#f5a623"},
    "assess": {"label": "Full Assessment",  "icon": "📊", "color": "#f56c6c"},
    "rag":    {"label": "Knowledge Chat",   "icon": "🧠", "color": "#56d19e"},
}

# ── Inject full custom UI CSS ────────────────────────────────────────────────
def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

/* ── Reset & base ── */
*, *::before, *::after { box-sizing: border-box; }
html, body, [data-testid="stAppViewContainer"],
[data-testid="stApp"], .main { background: #0a0a0f !important; }

/* Hide Streamlit chrome */
#MainMenu, header, footer,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"]        { display: none !important; }
[data-testid="collapsedControl"]      { display: none !important; }
.block-container                      { padding: 0 !important; max-width: 100% !important; }
section.main > div                    { padding: 0 !important; }

/* ── Design tokens ── */
:root {
  --ink:  #0a0a0f; --ink2: #12121c; --ink3: #1a1a28;
  --ink4: #222234; --ink5: #2e2e48;
  --line:  rgba(255,255,255,0.06);
  --line2: rgba(255,255,255,0.10);
  --line3: rgba(255,255,255,0.16);
  --t1: #f0f0fa; --t2: #9898b8; --t3: #55556a;
  --violet: #7c6af5; --violet2: #6458e8;
  --violet-dim: rgba(124,106,245,0.10);
  --violet-border: rgba(124,106,245,0.25);
  --teal: #2dd4c4; --sage: #56d19e;
  --amber: #f5a623; --rose: #f56c6c;
  --r: 10px; --rs: 6px; --rl: 14px;
  --ff: 'Inter', system-ui, -apple-system, sans-serif;
}

/* ── Shell layout ── */
.pathiq-shell {
  display: flex; height: 100vh; overflow: hidden;
  font-family: var(--ff); background: var(--ink);
}

/* ── Sidebar ── */
.pathiq-sidebar {
  width: 220px; min-width: 220px;
  background: var(--ink2); border-right: 1px solid var(--line);
  display: flex; flex-direction: column; overflow: hidden;
}
.sb-brand {
  padding: 18px 16px 14px; border-bottom: 1px solid var(--line);
  display: flex; align-items: center; gap: 10px;
}
.brand-gem {
  width: 30px; height: 30px; border-radius: 9px;
  background: var(--violet); display: flex; align-items: center;
  justify-content: center; flex-shrink: 0;
  font-size: 14px; font-weight: 700; color: #fff;
}
.brand-name { font-size: 13px; font-weight: 600; color: var(--t1); }
.brand-sub  { font-size: 10px; color: var(--violet); margin-top: 1px;
              background: var(--violet-dim); padding: 1px 6px;
              border-radius: 20px; border: 1px solid var(--violet-border);
              display: inline-block; font-weight: 500; }

.sb-nav { flex: 1; overflow-y: auto; padding: 10px 8px; scrollbar-width: none; }
.sb-nav::-webkit-scrollbar { display: none; }
.sb-section { margin-bottom: 18px; }
.sb-section-label {
  font-size: 10px; font-weight: 600; text-transform: uppercase;
  letter-spacing: .07em; color: var(--t3); padding: 0 8px 7px;
}
.sb-btn {
  display: flex; align-items: center; gap: 9px;
  width: 100%; padding: 8px 10px; border-radius: var(--rs);
  border: none; background: transparent; cursor: pointer;
  color: var(--t2); font-size: 12.5px; font-family: var(--ff);
  font-weight: 500; text-align: left; transition: all .15s;
}
.sb-btn:hover { background: var(--ink4); color: var(--t1); }
.sb-btn.active {
  background: var(--violet-dim); color: var(--violet);
  border: 1px solid var(--violet-border);
}
.sb-btn.disabled { opacity: .35; cursor: not-allowed; pointer-events: none; }
.sb-icon {
  width: 28px; height: 28px; border-radius: var(--rs);
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; flex-shrink: 0;
  background: var(--ink4);
}
.sb-btn.active .sb-icon { background: rgba(124,106,245,.18); }
.sb-pill {
  font-size: 9px; padding: 2px 6px; border-radius: 20px;
  font-weight: 600; margin-left: auto;
}
.pill-live { background: rgba(45,212,196,.1); color: var(--teal);
             border: 1px solid rgba(45,212,196,.2); }
.pill-soon { background: var(--ink4); color: var(--t3);
             border: 1px solid var(--line2); }

.sb-foot {
  padding: 12px; border-top: 1px solid var(--line);
}
.status-row {
  display: flex; align-items: center; gap: 7px;
  font-size: 11px; color: var(--t3); margin-bottom: 8px;
}
.pulse {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--sage); flex-shrink: 0;
  animation: blink 2.4s ease-in-out infinite;
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.3} }

/* ── Main panel ── */
.pathiq-main {
  flex: 1; display: flex; flex-direction: column; overflow: hidden;
  background: var(--ink);
}

/* ── Top tab bar ── */
.pathiq-tabs {
  height: 46px; background: var(--ink2);
  border-bottom: 1px solid var(--line);
  display: flex; align-items: center;
  padding: 0 16px; gap: 0; overflow-x: auto;
  scrollbar-width: none; flex-shrink: 0;
}
.pathiq-tabs::-webkit-scrollbar { display: none; }
.tab-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 0 14px; height: 46px; cursor: pointer;
  border: none; background: transparent;
  color: var(--t3); font-size: 12px; font-weight: 500;
  font-family: var(--ff); white-space: nowrap;
  border-bottom: 2px solid transparent;
  transition: all .15s; flex-shrink: 0;
}
.tab-btn:hover  { color: var(--t2); }
.tab-btn.active { color: var(--violet); border-bottom-color: var(--violet); }
.tab-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--t3); flex-shrink: 0;
}
.tab-btn.active .tab-dot { background: var(--violet); }

/* ── Chat feed ── */
.pathiq-feed {
  flex: 1; overflow-y: auto; padding: 20px 18px;
  scrollbar-width: thin; scrollbar-color: var(--line2) transparent;
}
.pathiq-feed::-webkit-scrollbar { width: 3px; }
.pathiq-feed::-webkit-scrollbar-thumb { background: var(--line2); border-radius: 3px; }

/* Service banner */
.svc-banner {
  background: var(--ink3); border: 1px solid var(--line);
  border-radius: var(--rl); padding: 16px 18px; margin-bottom: 22px;
  display: flex; gap: 12px; align-items: flex-start;
}
.svc-banner-icon {
  width: 40px; height: 40px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; flex-shrink: 0;
}
.svc-banner-title { font-size: 14px; font-weight: 600; color: var(--t1); margin-bottom: 3px; }
.svc-banner-desc  { font-size: 12px; color: var(--t3); line-height: 1.55; }
.chip-row { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 10px; }
.qchip {
  font-size: 11px; padding: 5px 11px; border-radius: 20px;
  border: 1px solid var(--line2); color: var(--t2);
  background: var(--ink4); cursor: pointer; transition: all .15s;
  font-family: var(--ff);
}
.qchip:hover {
  border-color: var(--violet-border); color: var(--violet);
  background: var(--violet-dim);
}

/* Messages */
.msg-row { display: flex; gap: 10px; margin-bottom: 16px; animation: popIn .22s ease; }
@keyframes popIn { from{opacity:0;transform:translateY(5px)} to{opacity:1;transform:translateY(0)} }
.msg-row.user { flex-direction: row-reverse; }
.av {
  width: 28px; height: 28px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 10px; font-weight: 700; flex-shrink: 0; margin-top: 3px;
}
.av.bot { background: var(--violet); color: #fff; }
.av.usr { background: var(--ink4); border: 1px solid var(--line2); color: var(--t2); }
.bubble { max-width: 75%; }
.bubble-inner {
  padding: 11px 14px; border-radius: 14px;
  font-size: 13px; line-height: 1.65; color: var(--t1);
}
.msg-row.bot .bubble-inner {
  background: var(--ink3); border: 1px solid var(--line);
  border-top-left-radius: 3px;
}
.msg-row.user .bubble-inner {
  background: var(--violet2); border-top-right-radius: 3px; color: #fff;
}
.bubble-meta {
  font-size: 10px; color: var(--t3); margin-top: 5px;
  display: flex; align-items: center; gap: 5px;
}
.msg-row.user .bubble-meta { justify-content: flex-end; }
.meta-sep { width: 3px; height: 3px; border-radius: 50%; background: var(--t3); }

/* Typing dots */
.typing-row { display: flex; gap: 10px; margin-bottom: 16px; }
.typing-dots {
  background: var(--ink3); border: 1px solid var(--line);
  padding: 12px 16px; border-radius: 14px; border-top-left-radius: 3px;
  display: flex; gap: 4px; align-items: center;
}
.td {
  width: 5px; height: 5px; border-radius: 50%;
  background: var(--t3); animation: tdot 1.1s ease-in-out infinite;
}
.td:nth-child(2){animation-delay:.18s}
.td:nth-child(3){animation-delay:.36s}
@keyframes tdot{0%,60%,100%{transform:translateY(0);opacity:.4}30%{transform:translateY(-4px);opacity:1}}

/* Suggestion row */
.sugg-row { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 6px; margin-bottom: 4px; }
.sugg {
  font-size: 11px; padding: 6px 12px; border-radius: 20px;
  border: 1px solid var(--line2); color: var(--t2);
  background: var(--ink3); cursor: pointer; transition: all .15s;
  font-family: var(--ff);
}
.sugg:hover { border-color: var(--violet-border); color: var(--violet); background: var(--violet-dim); }

/* ── Input area ── */
.pathiq-input {
  flex-shrink: 0; padding: 12px 18px;
  background: var(--ink2); border-top: 1px solid var(--line);
}
.ctx-row {
  display: flex; align-items: center; gap: 8px; margin-bottom: 9px;
}
.ctx-label {
  font-size: 10px; font-weight: 600; letter-spacing: .04em;
  padding: 3px 9px; border-radius: 20px;
  background: var(--violet-dim); color: var(--violet);
  border: 1px solid var(--violet-border);
}
.ctx-model { font-size: 10px; color: var(--t3); }

/* Override Streamlit form elements in input */
.stTextArea textarea {
  background: var(--ink3) !important;
  border: 1px solid var(--line2) !important;
  border-radius: var(--rl) !important;
  color: var(--t1) !important;
  font-size: 13px !important;
  font-family: var(--ff) !important;
  resize: none !important;
  transition: border-color .15s !important;
}
.stTextArea textarea:focus {
  border-color: var(--violet-border) !important;
  box-shadow: none !important;
}
.stButton > button {
  background: var(--violet) !important;
  border: none !important; border-radius: 8px !important;
  color: #fff !important; font-weight: 600 !important;
  font-size: 13px !important; padding: 10px 20px !important;
  transition: background .15s !important;
}
.stButton > button:hover { background: var(--violet2) !important; }

/* Streamlit metrics / info boxes */
.stMetric { background: var(--ink3) !important; border-radius: var(--r) !important;
            border: 1px solid var(--line) !important; padding: 12px !important; }
[data-testid="metric-container"] label { color: var(--t3) !important; font-size: 11px !important; }
[data-testid="metric-container"] [data-testid="stMetricValue"] { color: var(--t1) !important; }

div[data-testid="stTabs"] { display: none !important; }
</style>
""", unsafe_allow_html=True)


# ── Session state bootstrap ──────────────────────────────────────────────────
def init_state():
    defaults = {
        "active_service": "cv",
        "conversations": {k: [] for k in SERVICES},
        "cv_result": None,
        "gh_result": None,
        "job_result": None,
        "llm": None,
        "vectorstore": None,
        "graph": None,
        "auto_ingest_done": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ── Helpers ──────────────────────────────────────────────────────────────────
def ts():
    return datetime.datetime.now().strftime("%H:%M")


def save_csv(q, a):
    path = "chat_history.csv"
    exists = os.path.isfile(path)
    try:
        with open(path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if not exists:
                w.writerow(["Service", "Question", "Answer", "Time", "Date"])
            w.writerow([
                st.session_state.active_service, q, a,
                datetime.datetime.now().strftime("%H:%M:%S"),
                datetime.datetime.now().strftime("%Y-%m-%d"),
            ])
    except Exception:
        pass


def is_greeting(q: str) -> bool:
    patterns = [r'\b(hi|hello|hey|greetings|howdy|yo|sup)\b',
                r'how are you', r"what'?s up", r'good (morning|afternoon|evening)']
    q = q.lower().strip()
    if len(q.split()) <= 4:
        for p in patterns:
            if re.search(p, q):
                return True
    return False


def greeting_reply() -> str:
    return random.choice([
        "Hey! Great to have you here. I'm PathIQ — your career intelligence assistant. What would you like to work on today?",
        "Hello! I'm ready to help you level up your career. Which service would you like to start with — CV analysis, GitHub profile, or job matching?",
        "Hi there! PathIQ at your service. Ask me anything about your career, CV, or job search.",
    ])


# ── LLM (Groq) ───────────────────────────────────────────────────────────────
@st.cache_resource(ttl=3600)
def load_llm():
    try:
        from groq import Groq
    except ImportError:
        return None

    key = None
    if hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
        key = st.secrets["GROQ_API_KEY"]
    elif os.getenv("GROQ_API_KEY"):
        key = os.getenv("GROQ_API_KEY")
    if not key:
        return None

    client = Groq(api_key=key)
    models = [
        "llama-3.3-70b-versatile",
        "deepseek-r1-distill-llama-70b",
        "gemma2-9b-it",
    ]

    class GroqLLM:
        def __init__(self, client, model):
            self.client = client
            self.model = model

        def invoke(self, prompt, system=None):
            sys_msg = system or (
                "You are PathIQ, a world-class AI career intelligence assistant. "
                "Be specific, warm, and structured. Use bullet points and bold "
                "for key terms. Always end with a clear next-step question."
            )
            try:
                r = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": sys_msg},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.75,
                    max_tokens=700,
                    top_p=0.9,
                )
                return r.choices[0].message.content
            except Exception as e:
                return f"I ran into a small issue: {e}. Please try again!"

    for model in models:
        try:
            llm = GroqLLM(client, model)
            test = llm.invoke("Reply with: ready")
            if test and "Error" not in test:
                return llm
        except Exception:
            continue
    return None


# ── Vector store ─────────────────────────────────────────────────────────────
@st.cache_resource(ttl=3600)
def load_vectorstore():
    if not RAG_AVAILABLE:
        return None
    try:
        emb = HuggingFaceEmbeddings(model_name=EMBED_MODEL, model_kwargs={"device": "cpu"})
        if os.path.exists(os.path.join(DB_DIR, "chroma.sqlite3")):
            return Chroma(embedding_function=emb, persist_directory=DB_DIR)
    except Exception:
        pass
    return None


@st.cache_resource(ttl=3600)
def load_graph():
    if not RAG_AVAILABLE:
        return None
    try:
        builder = KnowledgeGraphBuilder()
        if builder.load():
            return builder.G
    except Exception:
        pass
    return None


# ── Human-like streaming response ────────────────────────────────────────────
def stream_response(placeholder, text: str):
    """Stream text word-by-word into a Streamlit placeholder."""
    words = text.split(" ")
    displayed = ""
    for i, word in enumerate(words):
        displayed += ("" if i == 0 else " ") + word
        placeholder.markdown(
            f'<div class="bubble-inner" style="background:var(--ink3);border:1px solid var(--line);'
            f'border-radius:14px;border-top-left-radius:3px;font-size:13px;line-height:1.65;'
            f'color:var(--t1);padding:11px 14px">{displayed}▌</div>',
            unsafe_allow_html=True,
        )
        # Variable delay: faster for common words, slight pause at punctuation
        delay = 0.025
        if word.endswith((".", "!", "?")):
            delay = 0.12
        elif word.endswith(","):
            delay = 0.06
        time.sleep(delay)
    # Final render without cursor
    placeholder.markdown(
        f'<div class="bubble-inner" style="background:var(--ink3);border:1px solid var(--line);'
        f'border-radius:14px;border-top-left-radius:3px;font-size:13px;line-height:1.65;'
        f'color:var(--t1);padding:11px 14px">{displayed}</div>',
        unsafe_allow_html=True,
    )
    return displayed


# ── Render conversation ───────────────────────────────────────────────────────
def render_messages(service_id: str):
    msgs = st.session_state.conversations[service_id]
    for m in msgs:
        if m["role"] == "user":
            st.markdown(
                f'<div class="msg-row user">'
                f'<div class="av usr">ME</div>'
                f'<div class="bubble">'
                f'<div class="bubble-inner" style="background:#6458e8;border-top-right-radius:3px;color:#fff">'
                f'{m["content"]}</div>'
                f'<div class="bubble-meta" style="justify-content:flex-end">{m["ts"]}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="msg-row bot">'
                f'<div class="av bot">P</div>'
                f'<div class="bubble">'
                f'<div class="bubble-inner">{m["content"]}</div>'
                f'<div class="bubble-meta">PathIQ <span class="meta-sep"></span> {m["ts"]}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )


# ── Service banners ───────────────────────────────────────────────────────────
SERVICE_META = {
    "cv": {
        "title": "CV Analyzer",
        "color": "#7c6af5",
        "icon": "📄",
        "desc": "Upload your CV and I'll extract your skill fingerprint, experience level, achievement gaps, and tell you exactly what to rewrite.",
        "chips": ["Analyze my CV", "What skills am I missing?", "How senior am I?", "Rewrite my summary"],
    },
    "github": {
        "title": "Code Profile",
        "color": "#2dd4c4",
        "icon": "💻",
        "desc": "Share your GitHub username and I'll score your repositories, language diversity, and contribution quality — then show you how to level up.",
        "chips": ["Analyze my GitHub", "Score my profile", "Best repos to pin", "Improve documentation"],
    },
    "jobs": {
        "title": "Job Matcher",
        "color": "#f5a623",
        "icon": "🎯",
        "desc": "Tell me your skills and experience. I'll match you against thousands of live postings and explain your fit score for each role.",
        "chips": ["Find matching jobs", "I have 4 years Python", "Senior backend remote", "Highest-paying roles for me"],
    },
    "assess": {
        "title": "Full Assessment",
        "color": "#f56c6c",
        "icon": "📊",
        "desc": "I synthesize your CV, GitHub, and job market data into a structured PathIQ Career Intelligence Report with a clear 30-day action plan.",
        "chips": ["Generate my full report", "Career gap analysis", "30-day action plan", "What should I do next?"],
    },
    "rag": {
        "title": "Knowledge Chat",
        "color": "#56d19e",
        "icon": "🧠",
        "desc": "Graph RAG hybrid retrieval — vector similarity + knowledge graph traversal — answers questions across your entire document base.",
        "chips": ["What services does Wasla offer?", "How does Graph RAG work?", "API documentation", "Deployment guide"],
    },
}


def render_banner(sid: str):
    meta = SERVICE_META[sid]
    chips_html = "".join(
        f'<button class="qchip" onclick="window.parent.document.getElementById(\'pathiq_chip_{i}\').click()">'
        f'{c}</button>'
        for i, c in enumerate(meta["chips"])
    )
    st.markdown(
        f'<div class="svc-banner">'
        f'<div class="svc-banner-icon" style="background:{meta["color"]}22">{meta["icon"]}</div>'
        f'<div>'
        f'<div class="svc-banner-title">{meta["title"]}</div>'
        f'<div class="svc-banner-desc">{meta["desc"]}</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )
    # Render chips as Streamlit buttons in a horizontal row
    cols = st.columns(len(meta["chips"]))
    for i, (col, chip) in enumerate(zip(cols, meta["chips"])):
        with col:
            if st.button(chip, key=f"chip_{sid}_{i}_{chip[:8]}", use_container_width=True):
                handle_input(chip, sid)


# ── Core response logic per service ──────────────────────────────────────────
def handle_input(user_msg: str, sid: str):
    if not user_msg.strip():
        return

    conv = st.session_state.conversations[sid]
    conv.append({"role": "user", "content": user_msg, "ts": ts()})

    # Greeting shortcut
    if is_greeting(user_msg) and len(conv) <= 2:
        reply = greeting_reply()
        conv.append({"role": "assistant", "content": reply, "ts": ts()})
        save_csv(user_msg, reply)
        st.rerun()
        return

    llm = st.session_state.get("llm") or load_llm()
    if not llm:
        st.session_state.llm = None
        conv.append({
            "role": "assistant",
            "content": "I need a Groq API key to respond. Please add GROQ_API_KEY to your .env or Streamlit secrets.",
            "ts": ts(),
        })
        st.rerun()
        return

    st.session_state.llm = llm

    # Build service-specific system prompt
    system_prompts = {
        "cv": (
            "You are PathIQ's CV Analyzer — a world-class career consultant. "
            "Analyze CVs with precision. Be specific: name real skills, flag real gaps, "
            "suggest concrete rewrites. Use bold for key points, bullet points for lists. "
            "End every response with one sharp follow-up question."
        ),
        "github": (
            "You are PathIQ's Code Profile analyzer. You assess GitHub profiles like a "
            "senior engineering recruiter. Score profiles across: consistency, depth, "
            "visibility, documentation quality. Give concrete improvement steps. "
            "End with a specific actionable question."
        ),
        "jobs": (
            "You are PathIQ's Job Matcher. Match users to roles based on their skills. "
            "Give match percentages, explain why they fit, identify skill gaps. "
            "Be specific about company types, salary ranges, and growth trajectories. "
            "End with a targeted next-step question."
        ),
        "assess": (
            "You are PathIQ's Full Assessment engine. Synthesize CV, GitHub, and market data "
            "into a structured career intelligence report. Use sections: Profile Score, "
            "CV Score, GitHub Score, Market Fit, 30-Day Action Plan. Be thorough and precise."
        ),
        "rag": (
            "You are PathIQ's Knowledge Chat powered by Graph RAG. Answer questions from "
            "the company knowledge base. Be precise, cite document context when available, "
            "and clearly state when something isn't in the knowledge base."
        ),
    }

    # For RAG service, use graph retrieval if available
    if sid == "rag" and RAG_AVAILABLE:
        vs = st.session_state.get("vectorstore") or load_vectorstore()
        g  = st.session_state.get("graph")      or load_graph()
        if vs and g:
            try:
                retriever = GraphRetriever(vectorstore=vs, graph=g, k=5, graph_k=5, hop_depth=2)
                docs = retriever.get_relevant_documents(user_msg)
                context = "\n\n".join(f"[Doc {i+1}]: {d.page_content}" for i, d in enumerate(docs))
                prompt = f"Context from knowledge base:\n{context}\n\nUser question: {user_msg}"
            except Exception:
                prompt = user_msg
        else:
            prompt = user_msg
    else:
        # Build conversation context
        history = "\n".join(
            f"{'User' if m['role']=='user' else 'PathIQ'}: {m['content']}"
            for m in conv[-6:]
        )
        prompt = f"Conversation so far:\n{history}\n\nRespond to the latest user message."

    with st.spinner(""):
        reply = llm.invoke(prompt, system=system_prompts.get(sid))

    conv.append({"role": "assistant", "content": reply, "ts": ts()})
    save_csv(user_msg, reply)
    st.rerun()


# ── Main app ─────────────────────────────────────────────────────────────────
def main():
    init_state()
    inject_css()

    # ── Sidebar ──
    with st.sidebar:
        st.markdown(
            '<div class="sb-brand">'
            '<div class="brand-gem">✦</div>'
            '<div><div class="brand-name">PathIQ</div>'
            '<div class="brand-sub">Career Intelligence</div></div>'
            '</div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="sb-section"><div class="sb-section-label">Core Services</div>', unsafe_allow_html=True)
        for sid, meta in SERVICES.items():
            active = "active" if st.session_state.active_service == sid else ""
            if st.button(
                f"{meta['icon']}  {meta['label']}",
                key=f"sb_{sid}",
                use_container_width=True,
            ):
                st.session_state.active_service = sid
                st.rerun()

        st.markdown("---")
        st.markdown('<div class="sb-section-label" style="padding-left:8px">Coming — Phase 2</div>', unsafe_allow_html=True)
        for label in ["🎤  Mock Interview", "🔗  LinkedIn Optimizer", "🗺️  Skill Roadmap"]:
            st.button(label, key=f"ph2_{label}", disabled=True, use_container_width=True)

        st.markdown("---")
        st.markdown(
            '<div class="status-row"><div class="pulse"></div> Graph RAG · LLaMA 3.3-70b</div>',
            unsafe_allow_html=True,
        )

        if st.button("🗑  Clear conversation", key="clear_conv", use_container_width=True):
            st.session_state.conversations[st.session_state.active_service] = []
            st.rerun()

        if os.path.exists("chat_history.csv"):
            with open("chat_history.csv") as f:
                st.download_button("⬇ Export chat history", f, "pathiq_history.csv",
                                   use_container_width=True)

    # ── Tab bar (rendered as HTML + Streamlit buttons) ──
    sid = st.session_state.active_service
    cols = st.columns(len(SERVICES))
    for i, (s_id, meta) in enumerate(SERVICES.items()):
        with cols[i]:
            active_style = "border-bottom:2px solid #7c6af5;color:#7c6af5;" if s_id == sid else ""
            if st.button(
                f"{meta['icon']} {meta['label']}",
                key=f"tab_{s_id}",
                use_container_width=True,
            ):
                st.session_state.active_service = s_id
                st.rerun()

    st.markdown("<hr style='margin:0;border-color:rgba(255,255,255,0.06)'>", unsafe_allow_html=True)

    # ── Service banner ──
    render_banner(sid)

    # ── Messages ──
    render_messages(sid)

    # ── CV file upload (only for CV service) ──
    if sid == "cv":
        with st.expander("📎 Upload CV (PDF)", expanded=False):
            uploaded = st.file_uploader("Choose PDF", type=["pdf"], label_visibility="collapsed")
            if uploaded and st.button("Analyze uploaded CV", key="analyze_cv"):
                if CV_AVAILABLE:
                    with st.spinner("Extracting CV data..."):
                        try:
                            tmp = f"tmp_{uploaded.name}"
                            with open(tmp, "wb") as f:
                                f.write(uploaded.getbuffer())
                            analyzer = CVAnalyzer()
                            result = analyzer.analyze_cv(tmp)
                            os.remove(tmp)
                            if result.get("success"):
                                st.session_state.cv_result = result
                                handle_input(
                                    f"I've uploaded my CV. Here is the extracted data: {json.dumps(result.get('analysis', {}), indent=2)}. Please analyze it in depth.",
                                    "cv",
                                )
                            else:
                                st.error(f"Error: {result.get('error')}")
                        except Exception as e:
                            st.error(f"Upload error: {e}")
                else:
                    st.warning("CVAnalyzer module not available.")

    # ── GitHub username input ──
    if sid == "github":
        with st.expander("🔍 Analyze a GitHub profile", expanded=False):
            gh_user = st.text_input("GitHub username", placeholder="e.g. torvalds", label_visibility="collapsed")
            if gh_user and st.button("Fetch & analyze", key="analyze_gh"):
                if GH_AVAILABLE:
                    with st.spinner(f"Fetching @{gh_user}..."):
                        try:
                            analyzer = GitHubAnalyzer()
                            result = analyzer.analyze_github_profile(gh_user)
                            if result.get("success"):
                                st.session_state.gh_result = result
                                handle_input(
                                    f"Here is the GitHub profile data for @{gh_user}: {json.dumps(result, indent=2)}. Please give a full analysis.",
                                    "github",
                                )
                            else:
                                st.error(f"Error: {result.get('error')}")
                        except Exception as e:
                            st.error(f"GitHub error: {e}")
                else:
                    st.warning("GitHubAnalyzer module not available.")

    # ── Input box ──
    st.markdown(
        f'<div class="ctx-row">'
        f'<span class="ctx-label">{SERVICE_META[sid]["title"].upper()}</span>'
        f'<span class="ctx-model">PathIQ · Groq Graph RAG</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    col_input, col_btn = st.columns([8, 1])
    with col_input:
        user_input = st.text_area(
            "message",
            placeholder=f"Ask PathIQ about {SERVICE_META[sid]['title'].lower()}…",
            key=f"input_{sid}",
            height=70,
            label_visibility="collapsed",
        )
    with col_btn:
        st.markdown("<div style='padding-top:20px'>", unsafe_allow_html=True)
        if st.button("Send →", key=f"send_{sid}", use_container_width=True):
            if user_input.strip():
                handle_input(user_input, sid)
        st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()