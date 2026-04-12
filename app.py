"""
PathIQ — Career Intelligence Platform  (Single Unified Chat UI)
================================================================
All 4 services live inside ONE chat canvas.
Service is selected from the sidebar; the chat header + input bar
reflect the active mode. No top tab bar.
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

load_dotenv()

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PathIQ — Career Intelligence",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Lazy imports ────────────────────────────────────────────────────────────
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
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# ── Constants ───────────────────────────────────────────────────────────────
DB_DIR      = "db"
EMBED_MODEL = "sentence-transformers/all-mpnet-base-v2"

SERVICES = {
    "cv":     {"label": "CV Analyzer",     "icon": "📄", "accent": "#7c6af5"},
    "github": {"label": "Code Profile",    "icon": "💻", "accent": "#2dd4c4"},
    "jobs":   {"label": "Job Matcher",     "icon": "🎯", "accent": "#f5a623"},
    "assess": {"label": "Full Assessment", "icon": "📊", "accent": "#f56c6c"},
}

SERVICE_HINTS = {
    "cv":     "Try: \"Analyze my CV\" · \"What skills am I missing?\" · \"Rewrite my summary\"",
    "github": "Try: \"Score my GitHub\" · \"Best repos to pin\" · \"Improve my README\"",
    "jobs":   "Try: \"Find jobs for a Python dev\" · \"Senior remote roles\" · \"Best-paying AI jobs\"",
    "assess": "Try: \"Show my dashboard\" · \"Generate full report\" · \"Compare with market\"",
}

QUICK_ACTIONS = {
    "cv":     ["Analyze my CV", "What skills am I missing?", "How senior am I?", "Rewrite my summary"],
    "github": ["Score my GitHub profile", "Best repos to pin", "Improve documentation", "Contribution tips"],
    "jobs":   ["Find matching jobs", "Senior backend remote roles", "Highest-paying AI roles", "Salary benchmarks"],
    "assess": ["Show my full dashboard", "Generate AI report", "Compare with market", "30-day action plan"],
}

SYSTEM_PROMPTS = {
    "cv": (
        "You are PathIQ's CV Analyzer — a world-class career consultant. "
        "Analyze CVs with precision. Name real skills, flag real gaps, suggest concrete rewrites. "
        "Use **bold** for key points and bullet points for lists. End with a sharp follow-up question."
    ),
    "github": (
        "You are PathIQ's Code Profile analyzer. Assess GitHub profiles like a senior engineering recruiter. "
        "Score across: consistency, depth, visibility, documentation quality. "
        "Give concrete improvement steps and end with a specific actionable question."
    ),
    "jobs": (
        "You are PathIQ's Job Matcher. Match users to roles based on their skills. "
        "Give match percentages, explain fit, identify skill gaps. "
        "Be specific about company types, salary ranges, and growth trajectories. End with a targeted question."
    ),
    "assess": (
        "You are PathIQ's career dashboard assistant. "
        "Answer questions about the user's career assessment data. "
        "Be analytical, structured, and encouraging. Use bullet points and clear headings."
    ),
    "rag": (
        "You are PathIQ's Knowledge Chat powered by Graph RAG. "
        "Answer questions from the knowledge base precisely. Cite document context when available."
    ),
}


# ── CSS injection ──────────────────────────────────────────────────────────
def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=DM+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

/* ─── Tokens ─── */
:root {
  --bg:      #08080f;
  --bg2:     #0f0f1a;
  --bg3:     #15151f;
  --bg4:     #1c1c2a;
  --bg5:     #252535;
  --line:    rgba(255,255,255,0.055);
  --line2:   rgba(255,255,255,0.09);
  --line3:   rgba(255,255,255,0.14);
  --t1:      #eeeef8;
  --t2:      #8888aa;
  --t3:      #44445a;
  --violet:  #7c6af5;
  --violet2: #6458e0;
  --vdim:    rgba(124,106,245,0.10);
  --vbdr:    rgba(124,106,245,0.22);
  --teal:    #2dd4c4;
  --sage:    #5ad19e;
  --amber:   #f5a63a;
  --rose:    #f56c6c;
  --ff:      'DM Sans', system-ui, sans-serif;
  --fm:      'DM Mono', monospace;
  --r:       14px;
  --rs:      9px;
}

/* ─── Streamlit chrome reset ─── */
html, body,
[data-testid="stApp"],
[data-testid="stAppViewContainer"],
.main { background: var(--bg) !important; }

#MainMenu, header, footer,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"] { display: none !important; }

[data-testid="collapsedControl"] { display: none !important; }

.block-container {
  padding: 0 !important;
  max-width: 100% !important;
}
section.main > div { padding: 0 !important; }

/* ─── Sidebar ─── */
[data-testid="stSidebar"] {
  background: var(--bg2) !important;
  border-right: 1px solid var(--line) !important;
}
[data-testid="stSidebar"] > div:first-child {
  padding: 0 !important;
}

.sb-wrap { padding: 0 12px 20px; }

.sb-logo {
  display: flex; align-items: center; gap: 12px;
  padding: 20px 6px 18px;
  border-bottom: 1px solid var(--line);
  margin-bottom: 18px;
}
.gem {
  width: 36px; height: 36px; border-radius: 11px;
  background: linear-gradient(135deg, var(--violet), #b09cff);
  display: flex; align-items: center; justify-content: center;
  font-size: 17px; font-weight: 800; color: #fff;
  box-shadow: 0 4px 14px rgba(124,106,245,.35);
  flex-shrink: 0;
}
.logo-title { font-size: 15px; font-weight: 700; color: var(--t1); letter-spacing: -.3px; }
.logo-badge {
  font-size: 9px; font-weight: 600;
  background: var(--vdim); color: var(--violet);
  border: 1px solid var(--vbdr);
  padding: 2px 8px; border-radius: 20px;
  margin-top: 3px; display: inline-block;
}

.sb-section-title {
  font-size: 10px; font-weight: 700; letter-spacing: .09em;
  text-transform: uppercase; color: var(--t3);
  padding: 0 6px 10px; margin-top: 4px;
}

/* Active service pill in sidebar header */
.sb-active-pill {
  display: flex; align-items: center; gap: 8px;
  background: var(--bg3); border: 1px solid var(--line2);
  border-radius: var(--rs); padding: 10px 12px;
  margin-bottom: 18px;
}
.sap-dot {
  width: 8px; height: 8px; border-radius: 50%;
  flex-shrink: 0; animation: pulse 2.5s ease-in-out infinite;
}
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.35} }
.sap-label { font-size: 12px; font-weight: 600; color: var(--t1); }
.sap-sub { font-size: 10px; color: var(--t3); margin-top: 1px; }

/* Sidebar nav buttons */
[data-testid="stSidebar"] .stButton > button {
  background: transparent !important;
  border: 1px solid transparent !important;
  color: var(--t2) !important;
  font-family: var(--ff) !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  text-align: left !important;
  padding: 9px 12px !important;
  border-radius: var(--rs) !important;
  transition: all 0.18s !important;
  justify-content: flex-start !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
  background: var(--bg4) !important;
  color: var(--t1) !important;
  border-color: var(--line2) !important;
  transform: none !important;
}

.sb-divider {
  height: 1px; background: var(--line);
  margin: 14px 0;
}
.sb-status {
  display: flex; align-items: center; gap: 8px;
  font-size: 11px; color: var(--t3);
  padding: 0 6px;
}
.status-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--sage); flex-shrink: 0;
  animation: pulse 2.4s ease-in-out infinite;
}

/* ─── Main area ─── */
.chat-root {
  display: flex; flex-direction: column;
  height: 100vh; overflow: hidden;
  background: var(--bg);
}

/* ─── Chat header bar ─── */
.chat-header {
  flex-shrink: 0;
  background: var(--bg2);
  border-bottom: 1px solid var(--line);
  padding: 0 28px;
  height: 58px;
  display: flex; align-items: center; justify-content: space-between;
}
.ch-left { display: flex; align-items: center; gap: 14px; }
.ch-icon {
  width: 38px; height: 38px; border-radius: 11px;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px;
}
.ch-name { font-size: 15px; font-weight: 700; color: var(--t1); letter-spacing: -.2px; }
.ch-sub  { font-size: 11px; color: var(--t3); margin-top: 2px; }
.ch-right { display: flex; align-items: center; gap: 10px; }
.ch-badge {
  font-size: 10px; font-weight: 600; padding: 4px 10px;
  border-radius: 20px; border: 1px solid var(--line2);
  color: var(--t3); background: var(--bg3);
}

/* ─── Feed ─── */
.chat-feed {
  flex: 1; overflow-y: auto;
  padding: 28px 32px 10px;
  scrollbar-width: thin;
  scrollbar-color: var(--line2) transparent;
}
.chat-feed::-webkit-scrollbar { width: 3px; }
.chat-feed::-webkit-scrollbar-thumb { background: var(--line2); border-radius: 3px; }

/* Welcome card */
.welcome-card {
  background: var(--bg3);
  border: 1px solid var(--line);
  border-radius: var(--r);
  padding: 26px 30px;
  margin-bottom: 28px;
  max-width: 680px;
}
.wc-title { font-size: 18px; font-weight: 700; color: var(--t1); margin-bottom: 6px; }
.wc-desc  { font-size: 13px; color: var(--t2); line-height: 1.65; }
.wc-chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }
/* chips rendered as st.buttons via columns — styled below */

/* ─── Messages ─── */
.msg-wrap { margin-bottom: 20px; animation: fadeUp .22s ease; }
@keyframes fadeUp { from{opacity:0;transform:translateY(5px)} to{opacity:1;transform:translateY(0)} }

.msg-row  { display: flex; gap: 12px; align-items: flex-start; }
.msg-row.user { flex-direction: row-reverse; }

.av {
  width: 34px; height: 34px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700; flex-shrink: 0;
  font-family: var(--fm);
}
.av.bot { background: linear-gradient(135deg, var(--violet), #a898ff); color: #fff; }
.av.usr { background: var(--bg4); border: 1px solid var(--line2); color: var(--t2); }

.bubble       { max-width: 72%; }
.bubble-inner {
  padding: 13px 17px;
  font-size: 13.5px; line-height: 1.7;
  color: var(--t1); font-family: var(--ff);
}
.bot .bubble-inner {
  background: var(--bg3); border: 1px solid var(--line);
  border-radius: 18px; border-top-left-radius: 4px;
}
.user .bubble-inner {
  background: var(--violet2); color: #fff;
  border-radius: 18px; border-top-right-radius: 4px;
}

.bubble-meta {
  font-size: 10px; color: var(--t3);
  margin-top: 5px; padding: 0 4px;
  display: flex; align-items: center; gap: 6px;
}
.msg-row.user .bubble-meta { justify-content: flex-end; }

/* Service tag inline in bot message */
.svc-tag {
  font-size: 9px; font-weight: 700; letter-spacing: .06em;
  padding: 2px 7px; border-radius: 20px;
  text-transform: uppercase;
}

/* Typing indicator */
.typing-wrap { margin-bottom: 16px; }
.typing-row  { display: flex; gap: 12px; align-items: center; }
.typing-dots {
  background: var(--bg3); border: 1px solid var(--line);
  padding: 14px 18px; border-radius: 18px; border-top-left-radius: 4px;
  display: flex; gap: 5px; align-items: center;
}
.td {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--t3); animation: tdot 1s ease-in-out infinite;
}
.td:nth-child(2){animation-delay:.16s}
.td:nth-child(3){animation-delay:.32s}
@keyframes tdot{0%,60%,100%{transform:translateY(0);opacity:.35}30%{transform:translateY(-5px);opacity:1}}

/* ─── Quick action chips (rendered via st.columns) ─── */
/* The main content area buttons get special quick-action styling */
.quick-actions .stButton > button {
  background: var(--bg3) !important;
  border: 1px solid var(--line2) !important;
  border-radius: 30px !important;
  color: var(--t2) !important;
  font-size: 12px !important;
  font-weight: 500 !important;
  padding: 6px 14px !important;
  transition: all 0.18s !important;
  white-space: nowrap !important;
}
.quick-actions .stButton > button:hover {
  border-color: var(--vbdr) !important;
  color: var(--violet) !important;
  background: var(--vdim) !important;
  transform: translateY(-1px) !important;
}

/* ─── Input bar ─── */
.input-bar {
  flex-shrink: 0;
  background: var(--bg2);
  border-top: 1px solid var(--line);
  padding: 14px 28px 16px;
}
.input-context {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 10px;
}
.ic-mode {
  font-size: 10px; font-weight: 700; letter-spacing: .06em;
  text-transform: uppercase; padding: 3px 10px;
  border-radius: 20px;
}
.ic-engine { font-size: 11px; color: var(--t3); }

/* Streamlit textarea override */
.stTextArea textarea {
  background: var(--bg3) !important;
  border: 1px solid var(--line2) !important;
  border-radius: var(--r) !important;
  color: var(--t1) !important;
  font-size: 13px !important;
  font-family: var(--ff) !important;
  resize: none !important;
  transition: border-color .18s, box-shadow .18s !important;
  caret-color: var(--violet) !important;
}
.stTextArea textarea:focus {
  border-color: var(--violet) !important;
  box-shadow: 0 0 0 2px var(--vdim) !important;
  outline: none !important;
}
.stTextArea textarea::placeholder { color: var(--t3) !important; }

/* Send button */
.send-col .stButton > button {
  background: var(--violet) !important;
  border: none !important;
  border-radius: var(--rs) !important;
  color: #fff !important;
  font-weight: 700 !important;
  font-size: 13px !important;
  padding: 12px 20px !important;
  height: 70px !important;
  width: 100% !important;
  transition: all .18s !important;
  letter-spacing: -.1px !important;
}
.send-col .stButton > button:hover {
  background: var(--violet2) !important;
  transform: scale(0.97) !important;
}

/* Tool toggle buttons in input area */
.tool-row .stButton > button {
  background: var(--bg3) !important;
  border: 1px solid var(--line) !important;
  border-radius: var(--rs) !important;
  color: var(--t3) !important;
  font-size: 11px !important;
  padding: 6px 12px !important;
  transition: all .15s !important;
}
.tool-row .stButton > button:hover {
  border-color: var(--line3) !important;
  color: var(--t2) !important;
  background: var(--bg4) !important;
  transform: none !important;
}

/* File uploader */
[data-testid="stFileUploader"] {
  background: var(--bg3) !important;
  border: 1px dashed var(--line2) !important;
  border-radius: var(--r) !important;
  padding: 12px !important;
}
[data-testid="stFileUploader"] label { color: var(--t2) !important; font-size: 12px !important; }

/* Text input */
.stTextInput input {
  background: var(--bg3) !important;
  border: 1px solid var(--line2) !important;
  border-radius: var(--rs) !important;
  color: var(--t1) !important;
  font-family: var(--ff) !important;
  font-size: 13px !important;
}
.stTextInput input:focus {
  border-color: var(--violet) !important;
  box-shadow: 0 0 0 2px var(--vdim) !important;
}

/* Expanders */
[data-testid="stExpander"] {
  background: var(--bg3) !important;
  border: 1px solid var(--line) !important;
  border-radius: var(--r) !important;
}
[data-testid="stExpander"] summary {
  color: var(--t2) !important; font-size: 12px !important;
}

/* Dashboard cards */
.dash-kpi {
  background: var(--bg3); border: 1px solid var(--line);
  border-radius: var(--r); padding: 20px 22px;
  transition: box-shadow .2s;
}
.dash-kpi:hover { box-shadow: 0 8px 24px rgba(0,0,0,.35); }
.kpi-val   { font-size: 34px; font-weight: 800; line-height: 1.1; font-family: var(--fm); }
.kpi-label { font-size: 10px; font-weight: 600; text-transform: uppercase;
             letter-spacing: .07em; color: var(--t3); margin-top: 6px; }
.kpi-sub   { font-size: 11px; color: var(--t3); }

.dash-section {
  background: var(--bg3); border: 1px solid var(--line);
  border-radius: var(--r); padding: 20px 22px;
  margin-top: 16px;
}
.dash-section-title {
  font-size: 11px; font-weight: 700; letter-spacing: .07em;
  text-transform: uppercase; color: var(--t3); margin-bottom: 14px;
}

/* Streamlit info/warning/success */
[data-testid="stAlert"] {
  background: var(--bg3) !important;
  border-radius: var(--r) !important;
  border: 1px solid var(--line2) !important;
  color: var(--t2) !important;
}
</style>
""", unsafe_allow_html=True)


# ── Session init ────────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "active_service": "cv",
        "conversations":  [],          # single unified conversation list
        "cv_result":      None,
        "gh_result":      None,
        "llm":            None,
        "vectorstore":    None,
        "graph":          None,
        "assessment_data": None,
        "show_upload":    False,
        "show_gh_input":  False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ── Helpers ─────────────────────────────────────────────────────────────────
def ts():
    return datetime.datetime.now().strftime("%H:%M")


def save_csv(sid, q, a):
    path = "chat_history.csv"
    exists = os.path.isfile(path)
    try:
        with open(path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if not exists:
                w.writerow(["Service", "Question", "Answer", "Time", "Date"])
            w.writerow([sid, q, a,
                        datetime.datetime.now().strftime("%H:%M:%S"),
                        datetime.datetime.now().strftime("%Y-%m-%d")])
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
        "Hey! Great to have you here. I'm **PathIQ** — your career intelligence assistant. Pick a service from the sidebar and let's get started!",
        "Hello! I'm ready to help you level up your career. Switch services from the sidebar — CV analysis, GitHub profile, job matching, or full assessment.",
        "Hi there! PathIQ at your service. Choose a mode on the left and ask me anything about your career, CV, or job search.",
    ])


# ── LLM ─────────────────────────────────────────────────────────────────────
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

    class GroqLLM:
        def __init__(self, c, model):
            self.client = c
            self.model  = model

        def invoke(self, prompt, system=None):
            sys_msg = system or (
                "You are PathIQ, a world-class AI career intelligence assistant. "
                "Be specific, warm, and structured. Use bold and bullets. "
                "Always end with a clear next-step question."
            )
            try:
                r = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": sys_msg},
                        {"role": "user",   "content": prompt},
                    ],
                    temperature=0.75, max_tokens=700, top_p=0.9,
                )
                return r.choices[0].message.content
            except Exception as e:
                return f"I ran into a small issue: {e}. Please try again!"

    for model in ["llama-3.3-70b-versatile", "deepseek-r1-distill-llama-70b", "gemma2-9b-it"]:
        try:
            llm  = GroqLLM(client, model)
            test = llm.invoke("Reply with: ready")
            if test and "Error" not in test:
                return llm
        except Exception:
            continue
    return None


# ── Vector / Graph store ─────────────────────────────────────────────────────
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


# ── Assessment data ──────────────────────────────────────────────────────────
def compute_assessment_data():
    cv = st.session_state.cv_result
    gh = st.session_state.gh_result
    data = {
        "overall_score": 0, "cv_score": 0, "github_score": 0, "market_fit": 0,
        "skills": [], "missing_skills": [], "experience_years": 0,
        "top_languages": [], "repo_count": 0, "total_commits": 0,
        "recommendations": [],
    }
    if cv and cv.get("success"):
        a = cv.get("analysis", {})
        data["cv_score"]        = a.get("score", 65)
        data["experience_years"]= a.get("experience_years", 3)
        data["skills"]          = a.get("skills", ["Python", "SQL", "ML"])
        data["missing_skills"]  = a.get("missing_skills", ["Docker", "Cloud"])
    else:
        data["cv_score"]       = 50
        data["skills"]         = ["Python", "Data Analysis"]
        data["missing_skills"] = ["Version Control", "Testing"]

    if gh and gh.get("success"):
        data["github_score"]  = gh.get("score", 70)
        data["top_languages"] = gh.get("languages", [("Python", 60), ("JS", 30)])
        data["repo_count"]    = gh.get("total_repos", 5)
        data["total_commits"] = gh.get("total_commits", 200)
    else:
        data["github_score"] = 45

    data["overall_score"] = min(100, max(0,
        int(0.5 * data["cv_score"] + 0.3 * data["github_score"] + 20)))
    data["market_fit"]    = min(100,
        int(data["overall_score"] * 0.9 + random.randint(-5, 5)))
    data["recommendations"] = [
        "Complete missing skills: " + ", ".join(data["missing_skills"][:2]),
        f"Add READMEs to {max(0, 5 - data['repo_count'])} more GitHub repos",
        "Add quantifiable achievements to your CV",
        "Network with 3 professionals in your target industry per week",
    ]
    return data


def render_dashboard():
    """Power BI-style dashboard rendered inline in the chat feed."""
    if not st.session_state.cv_result and not st.session_state.gh_result:
        st.warning("No profile data yet. Upload your CV or enter a GitHub username using the toolbar below.")
        return

    if st.session_state.assessment_data is None:
        st.session_state.assessment_data = compute_assessment_data()
    d = st.session_state.assessment_data

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    for col, label, val, unit, color in [
        (c1, "Career Score",  d["overall_score"], "/100", "#7c6af5"),
        (c2, "CV Score",      d["cv_score"],      "/100", "#7c6af5"),
        (c3, "GitHub Score",  d["github_score"],  "/100", "#2dd4c4"),
        (c4, "Market Fit",    d["market_fit"],    "%",    "#5ad19e"),
    ]:
        with col:
            st.markdown(
                f'<div class="dash-kpi">'
                f'<div class="kpi-label">{label}</div>'
                f'<div class="kpi-val" style="color:{color}">{val}'
                f'<span style="font-size:16px;color:var(--t3)">{unit}</span></div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # Charts
    if PLOTLY_AVAILABLE:
        import plotly.graph_objects as go
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown('<div class="dash-section"><div class="dash-section-title">Skill Gap</div>', unsafe_allow_html=True)
            skills   = d["skills"][:5]
            missing  = d["missing_skills"][:5]
            fig = go.Figure(data=[
                go.Bar(name="Present", x=skills,  y=[85]*len(skills),  marker_color="#7c6af5"),
                go.Bar(name="Missing", x=missing, y=[30]*len(missing), marker_color="#f56c6c"),
            ])
            fig.update_layout(
                barmode="group", height=240,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#8888aa", family="DM Sans", size=11),
                margin=dict(l=10, r=10, t=10, b=20),
                legend=dict(bgcolor="rgba(0,0,0,0)", font_color="#8888aa"),
                xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
                yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col_b:
            st.markdown('<div class="dash-section"><div class="dash-section-title">Language Distribution</div>', unsafe_allow_html=True)
            if d["top_languages"]:
                langs = [l[0] for l in d["top_languages"]]
                vals  = [l[1] for l in d["top_languages"]]
                fig2 = go.Figure(data=[go.Pie(
                    labels=langs, values=vals, hole=0.45,
                    marker=dict(colors=["#7c6af5","#2dd4c4","#f5a63a","#f56c6c","#5ad19e"]),
                )])
                fig2.update_layout(
                    height=240, paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#8888aa", family="DM Sans", size=11),
                    margin=dict(l=10, r=10, t=10, b=10),
                    legend=dict(bgcolor="rgba(0,0,0,0)", font_color="#8888aa"),
                )
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No language data available.")
            st.markdown("</div>", unsafe_allow_html=True)

    # 30-day plan
    st.markdown('<div class="dash-section"><div class="dash-section-title">🚀 30-Day Action Plan</div>', unsafe_allow_html=True)
    for rec in d["recommendations"]:
        st.markdown(f"- ✅ {rec}")
    st.markdown("</div>", unsafe_allow_html=True)

    # AI report
    if st.button("📄 Generate AI Report", key="dash_gen_report"):
        llm = st.session_state.get("llm") or load_llm()
        if llm:
            with st.spinner("Generating your report…"):
                prompt = (
                    f"Career assessment — Overall: {d['overall_score']}/100, "
                    f"CV: {d['cv_score']}, GitHub: {d['github_score']}, "
                    f"Market fit: {d['market_fit']}%. "
                    f"Skills: {', '.join(d['skills'])}. "
                    f"Missing: {', '.join(d['missing_skills'])}. "
                    f"Experience: {d['experience_years']} yrs."
                )
                report = llm.invoke(
                    prompt,
                    system="You are a career intelligence analyst. Write a structured, encouraging, actionable report.",
                )
                st.markdown("---")
                st.markdown(report)
        else:
            st.error("LLM not available. Add GROQ_API_KEY.")


# ── Message rendering ────────────────────────────────────────────────────────
def render_messages():
    conv = st.session_state.conversations
    if not conv:
        return

    for m in conv:
        sid    = m.get("service", "cv")
        accent = SERVICES[sid]["accent"]
        sicon  = SERVICES[sid]["icon"]

        if m["role"] == "user":
            st.markdown(
                f'<div class="msg-wrap">'
                f'<div class="msg-row user">'
                f'<div class="av usr">YOU</div>'
                f'<div class="bubble">'
                f'<div class="bubble-inner user">{m["content"]}</div>'
                f'<div class="bubble-meta">{m["ts"]}</div>'
                f'</div></div></div>',
                unsafe_allow_html=True,
            )
        elif m["role"] == "assistant":
            st.markdown(
                f'<div class="msg-wrap">'
                f'<div class="msg-row bot">'
                f'<div class="av bot">P</div>'
                f'<div class="bubble">'
                f'<div class="bubble-inner bot">{m["content"]}</div>'
                f'<div class="bubble-meta">'
                f'<span class="svc-tag" style="background:{accent}22;color:{accent};border:1px solid {accent}44">'
                f'{sicon} {SERVICES[sid]["label"]}</span>'
                f'PathIQ · {m["ts"]}'
                f'</div></div></div></div>',
                unsafe_allow_html=True,
            )
        elif m["role"] == "dashboard":
            # Special dashboard card
            st.markdown(
                f'<div class="msg-wrap">'
                f'<div class="msg-row bot">'
                f'<div class="av bot">P</div>'
                f'<div style="flex:1;min-width:0">',
                unsafe_allow_html=True,
            )
            render_dashboard()
            st.markdown('</div></div></div>', unsafe_allow_html=True)


# ── Core response handler ────────────────────────────────────────────────────
def handle_input(user_msg: str):
    user_msg = user_msg.strip()
    if not user_msg:
        return

    sid  = st.session_state.active_service
    conv = st.session_state.conversations

    conv.append({"role": "user", "content": user_msg, "ts": ts(), "service": sid})

    # Greeting shortcut
    if is_greeting(user_msg) and len(conv) <= 3:
        reply = greeting_reply()
        conv.append({"role": "assistant", "content": reply, "ts": ts(), "service": sid})
        save_csv(sid, user_msg, reply)
        st.rerun()
        return

    # Assessment: dashboard request
    if sid == "assess" and any(k in user_msg.lower() for k in
                               ["dashboard", "show", "assessment", "full report", "30-day"]):
        if not st.session_state.cv_result and not st.session_state.gh_result:
            reply = ("I'd love to show your dashboard! First, please **upload your CV** or "
                     "**connect your GitHub** using the 📎 / 🐙 buttons in the input bar below.")
            conv.append({"role": "assistant", "content": reply, "ts": ts(), "service": sid})
        else:
            if st.session_state.assessment_data is None:
                st.session_state.assessment_data = compute_assessment_data()
            conv.append({"role": "dashboard", "content": "", "ts": ts(), "service": sid})
        save_csv(sid, user_msg, "[dashboard rendered]")
        st.rerun()
        return

    # LLM path
    llm = st.session_state.get("llm") or load_llm()
    if not llm:
        conv.append({
            "role": "assistant",
            "content": "⚠️ I need a **Groq API key** to respond. Add `GROQ_API_KEY` to your `.env` or Streamlit secrets.",
            "ts": ts(), "service": sid,
        })
        st.rerun()
        return

    st.session_state.llm = llm

    # Build prompt
    history = "\n".join(
        f"{'User' if m['role']=='user' else 'PathIQ'}: {m['content']}"
        for m in conv[-8:] if m["role"] in ("user", "assistant")
    )

    if sid == "rag" and RAG_AVAILABLE:
        vs = st.session_state.get("vectorstore") or load_vectorstore()
        g  = st.session_state.get("graph")       or load_graph()
        if vs and g:
            try:
                retriever = GraphRetriever(vectorstore=vs, graph=g, k=5, graph_k=5, hop_depth=2)
                docs      = retriever.get_relevant_documents(user_msg)
                context   = "\n\n".join(f"[Doc {i+1}]: {d.page_content}" for i, d in enumerate(docs))
                prompt    = f"Context:\n{context}\n\nConversation:\n{history}\n\nAnswer the latest question."
            except Exception:
                prompt = f"Conversation:\n{history}\n\nAnswer the latest question."
        else:
            prompt = f"Conversation:\n{history}\n\nAnswer the latest question."
    else:
        prompt = f"Conversation:\n{history}\n\nAnswer the latest user question helpfully and specifically."

    with st.spinner(""):
        reply = llm.invoke(prompt, system=SYSTEM_PROMPTS.get(sid, SYSTEM_PROMPTS["cv"]))

    conv.append({"role": "assistant", "content": reply, "ts": ts(), "service": sid})
    save_csv(sid, user_msg, reply)
    st.rerun()


# ── Sidebar ─────────────────────────────────────────────────────────────────
def render_sidebar():
    sid    = st.session_state.active_service
    smeta  = SERVICES[sid]

    with st.sidebar:
        st.markdown(
            '<div class="sb-wrap">'
            '<div class="sb-logo">'
            '<div class="gem">✦</div>'
            '<div><div class="logo-title">PathIQ</div>'
            '<div class="logo-badge">Career Intelligence</div>'
            '</div></div>',
            unsafe_allow_html=True,
        )

        # Active service indicator
        st.markdown(
            f'<div class="sb-active-pill">'
            f'<div class="sap-dot" style="background:{smeta["accent"]}"></div>'
            f'<div><div class="sap-label">{smeta["icon"]} {smeta["label"]}</div>'
            f'<div class="sap-sub">Active mode</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="sb-section-title">Services</div>', unsafe_allow_html=True)
        for s_id, meta in SERVICES.items():
            is_active = s_id == sid
            label     = f"{meta['icon']}  {meta['label']}"
            if is_active:
                st.markdown(
                    f'<div style="background:rgba(124,106,245,.10);border:1px solid rgba(124,106,245,.22);'
                    f'border-radius:9px;padding:9px 12px;color:{meta["accent"]};'
                    f'font-size:13px;font-weight:600;font-family:DM Sans,sans-serif;'
                    f'margin-bottom:4px">{label}</div>',
                    unsafe_allow_html=True,
                )
            else:
                if st.button(label, key=f"sb_{s_id}", use_container_width=True):
                    st.session_state.active_service = s_id
                    st.rerun()

        st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)
        st.markdown('<div class="sb-section-title">Coming — Phase 2</div>', unsafe_allow_html=True)
        for label in ["🎤  Mock Interview", "🔗  LinkedIn Optimizer", "🗺️  Skill Roadmap"]:
            st.button(label, key=f"ph2_{label}", disabled=True, use_container_width=True)

        st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)

        st.markdown(
            '<div class="sb-status">'
            '<div class="status-dot"></div>'
            'Graph RAG · LLaMA 3.3-70b'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        if st.button("🗑  Clear conversation", key="clear_conv", use_container_width=True):
            st.session_state.conversations = []
            st.session_state.assessment_data = None
            st.rerun()

        if os.path.exists("chat_history.csv"):
            with open("chat_history.csv") as f:
                st.download_button("⬇  Export history", f, "pathiq_history.csv",
                                   use_container_width=True)

        st.markdown('</div>', unsafe_allow_html=True)


# ── Chat header ──────────────────────────────────────────────────────────────
def render_header():
    sid   = st.session_state.active_service
    meta  = SERVICES[sid]
    msgs  = len([m for m in st.session_state.conversations if m["role"] == "user"])
    st.markdown(
        f'<div class="chat-header">'
        f'<div class="ch-left">'
        f'<div class="ch-icon" style="background:{meta["accent"]}18">{meta["icon"]}</div>'
        f'<div>'
        f'<div class="ch-name">{meta["label"]}</div>'
        f'<div class="ch-sub">{SERVICE_HINTS[sid]}</div>'
        f'</div></div>'
        f'<div class="ch-right">'
        f'<div class="ch-badge">{msgs} messages</div>'
        f'<div class="ch-badge">PathIQ · Groq</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


# ── Welcome card + quick chips ───────────────────────────────────────────────
def render_welcome():
    sid  = st.session_state.active_service
    meta = SERVICES[sid]
    if st.session_state.conversations:
        return  # only show when chat is empty

    descriptions = {
        "cv":     "Upload your CV and I'll extract your skill fingerprint, experience level, achievement gaps, and tell you exactly what to rewrite.",
        "github": "Share your GitHub username and I'll score your repositories, language diversity, and contribution quality — then show you how to level up.",
        "jobs":   "Tell me your skills and experience. I'll match you against thousands of live postings and explain your fit score for each role.",
        "assess": "Interactive Power BI–style dashboard: overall career score, skill gaps, GitHub metrics, and a personalized 30-day action plan.",
    }
    st.markdown(
        f'<div class="welcome-card">'
        f'<div class="wc-title">{meta["icon"]} {meta["label"]}</div>'
        f'<div class="wc-desc">{descriptions[sid]}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    # Quick action chips
    actions = QUICK_ACTIONS[sid]
    st.markdown('<div class="quick-actions">', unsafe_allow_html=True)
    cols = st.columns(len(actions))
    for i, (col, action) in enumerate(zip(cols, actions)):
        with col:
            if st.button(action, key=f"qa_{sid}_{i}", use_container_width=True):
                handle_input(action)
    st.markdown('</div>', unsafe_allow_html=True)


# ── Input bar ────────────────────────────────────────────────────────────────
def render_input_bar():
    sid  = st.session_state.active_service
    meta = SERVICES[sid]

    # Context pill
    st.markdown(
        f'<div class="input-context">'
        f'<span class="ic-mode" style="background:{meta["accent"]}18;'
        f'color:{meta["accent"]};border:1px solid {meta["accent"]}33">'
        f'{meta["icon"]} {meta["label"].upper()}</span>'
        f'<span class="ic-engine">PathIQ · Groq Graph RAG</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Tool toggles (CV upload / GitHub input) shown inline
    if sid == "cv":
        st.markdown('<div class="tool-row">', unsafe_allow_html=True)
        with st.expander("📎 Upload CV (PDF)", expanded=st.session_state.show_upload):
            uploaded = st.file_uploader(
                "CV PDF", type=["pdf"], label_visibility="collapsed", key="cv_upload_main"
            )
            if uploaded and st.button("Analyze CV", key="analyze_cv_main"):
                if CV_AVAILABLE:
                    with st.spinner("Reading your CV…"):
                        try:
                            tmp = f"tmp_{uploaded.name}"
                            with open(tmp, "wb") as f:
                                f.write(uploaded.getbuffer())
                            analyzer = CVAnalyzer()
                            result   = analyzer.analyze_cv(tmp)
                            os.remove(tmp)
                            if result.get("success"):
                                st.session_state.cv_result = result
                                handle_input(
                                    f"I've uploaded my CV. Data: {json.dumps(result.get('analysis', {}), indent=2)}. Please analyze in depth."
                                )
                            else:
                                st.error(f"Error: {result.get('error')}")
                        except Exception as e:
                            st.error(f"Upload error: {e}")
                else:
                    st.warning("CVAnalyzer module not available.")
        st.markdown("</div>", unsafe_allow_html=True)

    if sid == "github":
        with st.expander("🐙 Analyze a GitHub profile", expanded=False):
            gh_col1, gh_col2 = st.columns([3, 1])
            with gh_col1:
                gh_user = st.text_input(
                    "GitHub username", placeholder="e.g. torvalds",
                    label_visibility="collapsed", key="gh_user_main"
                )
            with gh_col2:
                if st.button("Fetch →", key="fetch_gh_main"):
                    if gh_user:
                        if GH_AVAILABLE:
                            with st.spinner(f"Fetching @{gh_user}…"):
                                try:
                                    analyzer = GitHubAnalyzer()
                                    result   = analyzer.analyze_github_profile(gh_user)
                                    if result.get("success"):
                                        st.session_state.gh_result = result
                                        handle_input(
                                            f"GitHub @{gh_user} data: {json.dumps(result, indent=2)}. Full analysis please."
                                        )
                                    else:
                                        st.error(f"Error: {result.get('error')}")
                                except Exception as e:
                                    st.error(f"GitHub error: {e}")
                        else:
                            st.warning("GitHubAnalyzer module not available.")

    if sid == "assess":
        with st.expander("🔧 Load Profile Data", expanded=False):
            a1, a2 = st.columns(2)
            with a1:
                up2 = st.file_uploader("CV PDF", type=["pdf"], label_visibility="collapsed", key="assess_cv")
                if up2 and st.button("Load CV", key="assess_load_cv"):
                    if CV_AVAILABLE:
                        with st.spinner("Reading CV…"):
                            try:
                                tmp = f"tmp_{up2.name}"
                                with open(tmp, "wb") as f:
                                    f.write(up2.getbuffer())
                                analyzer = CVAnalyzer()
                                result   = analyzer.analyze_cv(tmp)
                                os.remove(tmp)
                                if result.get("success"):
                                    st.session_state.cv_result = result
                                    st.session_state.assessment_data = None
                                    st.success("CV loaded! Ask me to show the dashboard.")
                                else:
                                    st.error(result.get("error"))
                            except Exception as e:
                                st.error(str(e))
                    else:
                        st.warning("CVAnalyzer not available.")
            with a2:
                gh2 = st.text_input("GitHub username", label_visibility="collapsed",
                                    placeholder="e.g. torvalds", key="assess_gh")
                if st.button("Load GitHub", key="assess_load_gh"):
                    if gh2 and GH_AVAILABLE:
                        with st.spinner(f"Fetching @{gh2}…"):
                            try:
                                analyzer = GitHubAnalyzer()
                                result   = analyzer.analyze_github_profile(gh2)
                                if result.get("success"):
                                    st.session_state.gh_result = result
                                    st.session_state.assessment_data = None
                                    st.success("GitHub loaded! Ask me to show the dashboard.")
                                else:
                                    st.error(result.get("error"))
                            except Exception as e:
                                st.error(str(e))
                    else:
                        st.warning("GitHubAnalyzer not available.")

    # Main text input + send
    st.markdown('<div style="display:flex;gap:10px">', unsafe_allow_html=True)
    col_txt, col_btn = st.columns([9, 1])
    with col_txt:
        user_input = st.text_area(
            "message",
            placeholder=f"Message PathIQ about {meta['label'].lower()}…",
            key=f"main_input_{sid}",
            height=70,
            label_visibility="collapsed",
        )
    with col_btn:
        st.markdown('<div class="send-col" style="padding-top:0">', unsafe_allow_html=True)
        if st.button("Send\n→", key=f"send_{sid}", use_container_width=True):
            if user_input.strip():
                handle_input(user_input)
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    init_state()
    inject_css()
    render_sidebar()
    render_header()

    # Chat feed area
    with st.container():
        render_welcome()
        render_messages()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # Input bar (always at bottom)
    render_input_bar()


if __name__ == "__main__":
    main()