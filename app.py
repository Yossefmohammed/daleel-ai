"""
PathIQ — Career Intelligence Platform
UI: Claude / ChatGPT style. No prompt suggestions. Human-like responses.
"""

import os, csv, json, re, random, datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
import streamlit as st

st.set_page_config(
    page_title="PathIQ",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Optional imports ──────────────────────────────────────────────────────────
try:
    from cv_analyzer import CVAnalyzer
    CV_OK = True
except ImportError:
    CV_OK = False

try:
    from github_analyzer import GitHubAnalyzer
    GH_OK = True
except ImportError:
    GH_OK = False

try:
    from job_matcher import JobMatcher
    JM_OK = True
except ImportError:
    JM_OK = False

try:
    from graph_builder import KnowledgeGraphBuilder, GRAPH_PATH
    from graph_retriever import GraphRetriever
    from langchain_community.vectorstores import Chroma
    from langchain_community.embeddings import HuggingFaceEmbeddings
    RAG_OK = True
except ImportError:
    RAG_OK = False

DB_DIR      = "db"
EMBED_MODEL = "sentence-transformers/all-mpnet-base-v2"

SERVICES = {
    "cv":     {"label": "CV Analyzer",     "icon": "📄"},
    "github": {"label": "Code Profile",    "icon": "💻"},
    "jobs":   {"label": "Job Matcher",     "icon": "🎯"},
    "assess": {"label": "Full Assessment", "icon": "📊"},
    "rag":    {"label": "Knowledge Chat",  "icon": "🧠"},
}

SERVICE_META = {
    "cv": {
        "welcome": "Hey! I'm your CV Analyzer. Paste your CV text, upload a PDF, or just describe your background — I'll give you honest, specific feedback on what's working and exactly what to fix.",
        "placeholder": "Ask me anything about your CV or career profile…",
        "system": """You are PathIQ's CV coach — a direct, warm career expert who has reviewed thousands of CVs.

Rules:
- Never open with "Certainly!", "Great question!", "Of course!" — just answer directly
- Talk like a smart, knowledgeable friend — not a corporate bot
- Give SPECIFIC feedback: name the exact section, say exactly what to rewrite and why
- If something is weak, say so. If it's strong, say that too. Be honest.
- Use short paragraphs. Write like a human.
- Use **bold** for key terms, bullet points only when listing 3+ things
- End with ONE natural follow-up question to keep the conversation going
- No filler, no corporate speak, no generic tips""",
    },
    "github": {
        "welcome": "Hi! Share your GitHub username and I'll analyze your profile the way a senior engineering recruiter would — repos, commit patterns, language depth, documentation quality. Tell me what you'd like to know.",
        "placeholder": "Share your GitHub username or ask about your developer profile…",
        "system": """You are PathIQ's GitHub profile analyst — you think like a senior engineering recruiter.

Rules:
- No filler openers — get straight to the point
- Be honest about weaknesses. Sugarcoating wastes everyone's time.
- Explain WHY something matters, not just what to change
- Give concrete examples: "instead of X, do Y"
- Write like a smart colleague giving real feedback — not a report
- End with one natural follow-up question""",
    },
    "jobs": {
        "welcome": "Hey! Tell me about your skills and experience and I'll match you to the right roles, explain your fit, and show you exactly what gaps to close. What's your background?",
        "placeholder": "Describe your skills, experience, or the role you're targeting…",
        "system": """You are PathIQ's job matching specialist — a career strategist who knows the real tech job market inside out.

Rules:
- Be specific: name real companies, actual salary ranges, real role titles
- Tell people what they might not want to hear if it's true — it's more useful
- Give 3-5 focused role matches, not an overwhelming list
- Write naturally, like a recruiter friend over coffee
- End with one specific next-step question""",
    },
    "assess": {
        "welcome": "I'm your Full Assessment engine. Give me everything — your background, GitHub, target roles — and I'll put together a complete picture of where you stand and your clearest path forward.",
        "placeholder": "Tell me about your overall career situation…",
        "system": """You are PathIQ's career intelligence engine — you synthesize the full picture and give people a clear map forward.

Rules:
- Be direct about the biggest lever to pull — don't bury it
- Give timelines and specific steps, not vague direction
- Write like a trusted advisor, not a management consultant
- Structured but human — not a formal report
- End with one clear next action""",
    },
    "rag": {
        "welcome": "Hi! I'm connected to the Wasla knowledge base using Graph RAG — vector search combined with knowledge graph traversal for deeper, multi-hop answers. What would you like to know?",
        "placeholder": "Ask anything about Wasla Solutions or the knowledge base…",
        "system": """You are PathIQ's Knowledge Chat — connected to Wasla Solutions' document base via Graph RAG.

Rules:
- Only share information from the retrieved context — never invent facts
- If you don't have the information, say so clearly and honestly
- Explain technical concepts in plain language
- Be specific — reference document details when relevant
- Write naturally, not like a search result""",
    },
}

# ── CSS ───────────────────────────────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stApp"] {
    background: #212121 !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    color: #ececec !important;
}

/* Hide Streamlit chrome */
#MainMenu, header, footer,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
[data-testid="collapsedControl"],
.stDeployButton { display: none !important; }

.block-container { padding: 0 !important; max-width: 100% !important; }
section.main > div { padding: 0 !important; }
[data-testid="stVerticalBlock"] { gap: 0 !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #171717 !important;
    border-right: 1px solid rgba(255,255,255,0.07) !important;
}
[data-testid="stSidebar"] > div { padding: 0 !important; }
[data-testid="stSidebarContent"] { padding: 0 !important; }

[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    border: none !important;
    color: #b4b4c8 !important;
    font-size: 13.5px !important;
    font-weight: 400 !important;
    padding: 9px 14px !important;
    border-radius: 8px !important;
    text-align: left !important;
    width: 100% !important;
    justify-content: flex-start !important;
    transition: background 0.12s !important;
    box-shadow: none !important;
    transform: none !important;
    letter-spacing: 0 !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.07) !important;
    color: #fff !important;
    box-shadow: none !important;
    transform: none !important;
}
[data-testid="stSidebar"] .stButton > button:active { transform: none !important; }
[data-testid="stSidebar"] .stButton > button:focus { box-shadow: none !important; outline: none !important; }
[data-testid="stSidebar"] .stButton > button:disabled {
    color: #3a3a50 !important;
    opacity: 1 !important;
}

/* Sidebar layout */
.sb-brand {
    display: flex; align-items: center; gap: 10px;
    padding: 20px 16px 16px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
}
.sb-gem {
    width: 28px; height: 28px; border-radius: 8px;
    background: #9b8afb;
    display: flex; align-items: center; justify-content: center;
    font-size: 13px; color: #fff; font-weight: 700; flex-shrink: 0;
}
.sb-name { font-size: 15px; font-weight: 600; color: #ececec; }
.sb-tag  { font-size: 10px; color: #9b8afb; margin-top: 1px; }

.sb-group {
    font-size: 10.5px; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.07em;
    color: #3a3a52; padding: 16px 16px 5px;
}
.sb-div {
    height: 1px; background: rgba(255,255,255,0.05);
    margin: 6px 12px;
}
.sb-status {
    display: flex; align-items: center; gap: 7px;
    font-size: 11px; color: #3a3a52;
    padding: 12px 16px;
}
.sb-pulse {
    width: 6px; height: 6px; border-radius: 50%;
    background: #4ade80;
    animation: sbpulse 2.5s ease-in-out infinite;
}
@keyframes sbpulse { 0%,100%{opacity:1} 50%{opacity:.25} }

/* ── Welcome ── */
.welcome {
    max-width: 680px; margin: 80px auto 0;
    padding: 0 24px; text-align: center;
}
.welcome-icon {
    width: 50px; height: 50px; border-radius: 50%;
    background: #9b8afb;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 20px; margin-bottom: 20px;
}
.welcome-title { font-size: 22px; font-weight: 500; color: #ececec; margin-bottom: 10px; }
.welcome-body  { font-size: 15px; color: #737387; line-height: 1.7; max-width: 500px; margin: 0 auto; }

/* ── Messages ── */
.msgs { max-width: 680px; margin: 0 auto; padding: 28px 24px 16px; }

.msg-block { margin-bottom: 22px; animation: msgpop .2s ease; }
@keyframes msgpop { from{opacity:0;transform:translateY(5px)} to{opacity:1;transform:translateY(0)} }

/* User */
.user-row { display: flex; justify-content: flex-end; }
.user-bub {
    background: #2f2f2f;
    color: #ececec;
    border-radius: 18px 18px 4px 18px;
    padding: 12px 18px;
    font-size: 14.5px; line-height: 1.65;
    max-width: 82%; word-wrap: break-word;
    white-space: pre-wrap;
}

/* Bot — no bubble, like Claude */
.bot-row { display: flex; gap: 13px; align-items: flex-start; }
.bot-av {
    width: 28px; height: 28px; border-radius: 50%;
    background: #9b8afb;
    display: flex; align-items: center; justify-content: center;
    font-size: 12px; font-weight: 700; color: #fff;
    flex-shrink: 0; margin-top: 2px;
}
.bot-body {
    flex: 1; font-size: 14.5px; line-height: 1.78;
    color: #e0e0f0; min-width: 0;
}
.bot-body p            { margin-bottom: 12px; }
.bot-body p:last-child { margin-bottom: 0; }
.bot-body strong  { color: #fff; font-weight: 500; }
.bot-body em      { color: #aeaec8; }
.bot-body ul,
.bot-body ol      { margin: 8px 0 14px 20px; color: #c8c8e0; }
.bot-body li      { margin-bottom: 6px; line-height: 1.6; }
.bot-body h3      { font-size: 15px; font-weight: 500; color: #fff; margin: 14px 0 8px; }
.bot-body code    {
    background: #252535; color: #c4b5fd;
    padding: 2px 7px; border-radius: 5px;
    font-size: 13px; font-family: 'Fira Code', monospace;
}
.bot-body pre {
    background: #1a1a2a;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 10px; padding: 14px 16px;
    overflow-x: auto; margin: 12px 0;
    font-size: 13px; color: #d0d0e8;
}

/* Typing */
.typing-block { display: flex; gap: 13px; align-items: flex-start; margin-bottom: 22px; }
.t-dots { display: flex; gap: 5px; align-items: center; padding-top: 7px; }
.t-dot  {
    width: 7px; height: 7px; border-radius: 50%;
    background: #4a4a5a;
    animation: tdot 1.3s ease-in-out infinite;
}
.t-dot:nth-child(2) { animation-delay: .2s; }
.t-dot:nth-child(3) { animation-delay: .4s; }
@keyframes tdot { 0%,60%,100%{opacity:.3;transform:scale(.85)} 30%{opacity:1;transform:scale(1.1)} }

/* ── Input ── */
.inp-wrap { background: #212121; padding: 10px 0 18px; }
.inp-inner { max-width: 680px; margin: 0 auto; padding: 0 24px; }
.inp-shell {
    background: #2f2f2f;
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 14px;
    padding: 6px 8px 6px 16px;
    display: flex; align-items: flex-end; gap: 8px;
    transition: border-color .2s;
}
.inp-shell:focus-within { border-color: rgba(155,138,251,.4); }

.stTextArea textarea {
    background: transparent !important; border: none !important;
    outline: none !important; box-shadow: none !important;
    color: #ececec !important; font-size: 14.5px !important;
    font-family: 'Inter', sans-serif !important;
    resize: none !important; line-height: 1.6 !important;
    padding: 10px 0 !important; min-height: 22px !important;
    caret-color: #9b8afb !important;
}
.stTextArea textarea::placeholder { color: #4a4a60 !important; }
.stTextArea textarea:focus { box-shadow: none !important; border: none !important; }
.stTextArea [data-baseweb="textarea"] { background: transparent !important; border: none !important; }
.stTextArea { margin: 0 !important; }
[data-testid="stTextArea"] { margin: 0 !important; }

/* Send button */
.stButton > button {
    background: #9b8afb !important; border: none !important;
    border-radius: 9px !important;
    width: 34px !important; height: 34px !important;
    padding: 0 !important; font-size: 15px !important;
    color: #fff !important; flex-shrink: 0 !important;
    min-width: unset !important; margin-bottom: 5px !important;
    transition: background .15s !important;
    box-shadow: none !important; transform: none !important;
}
.stButton > button:hover { background: #8572f0 !important; box-shadow: none !important; transform: none !important; }
.stButton > button:active { transform: scale(.97) !important; }

.inp-note { text-align: center; font-size: 11.5px; color: #333348; margin-top: 8px; }
</style>
"""

# ── Helpers ───────────────────────────────────────────────────────────────────
def now_ts():
    return datetime.datetime.now().strftime("%H:%M")

def save_csv(service, q, a):
    path = "chat_history.csv"
    exists = os.path.isfile(path)
    try:
        with open(path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if not exists:
                w.writerow(["Service","Question","Answer","Time","Date"])
            w.writerow([service, q, a,
                        datetime.datetime.now().strftime("%H:%M:%S"),
                        datetime.datetime.now().strftime("%Y-%m-%d")])
    except Exception:
        pass

def is_greeting(q):
    q = q.lower().strip()
    if len(q.split()) > 5:
        return False
    return any(re.search(p, q) for p in [
        r'\b(hi|hello|hey|howdy|yo|sup)\b',
        r'how are you', r"what'?s up",
        r'good (morning|afternoon|evening)',
    ])

def greeting_reply():
    return random.choice([
        "Hey! Good to have you here. What are you working on?",
        "Hi! I'm PathIQ — ask me anything about your CV, GitHub, job search, or career path.",
        "Hey there! What can I help you with today?",
    ])

def md_to_html(text):
    # Code blocks first
    text = re.sub(r'```\w*\n?(.*?)```',
                  lambda m: f'<pre><code>{m.group(1).strip()}</code></pre>',
                  text, flags=re.DOTALL)
    # Inline code
    text = re.sub(r'`([^`\n]+)`', r'<code>\1</code>', text)
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Italic
    text = re.sub(r'\*([^*\n]+)\*', r'<em>\1</em>', text)
    # H3
    text = re.sub(r'^### (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    # Bullet lists
    lines = text.split('\n')
    out, in_ul = [], False
    for line in lines:
        if re.match(r'^[-•]\s(.+)', line):
            if not in_ul:
                out.append('<ul>'); in_ul = True
            out.append(f'<li>{re.sub(r"^[-•]\\s", "", line)}</li>')
        else:
            if in_ul:
                out.append('</ul>'); in_ul = False
            out.append(line)
    if in_ul:
        out.append('</ul>')
    # Numbered lists
    lines = '\n'.join(out).split('\n')
    out, in_ol = [], False
    for line in lines:
        if re.match(r'^\d+\.\s(.+)', line):
            if not in_ol:
                out.append('<ol>'); in_ol = True
            out.append(f'<li>{re.sub(r"^\\d+\\.\\s", "", line)}</li>')
        else:
            if in_ol:
                out.append('</ol>'); in_ol = False
            out.append(line)
    if in_ol:
        out.append('</ol>')
    text = '\n'.join(out)
    # Paragraphs
    parts = re.split(r'\n{2,}', text)
    html  = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if p.startswith('<'):
            html.append(p)
        else:
            html.append(f'<p>{p.replace(chr(10), " ")}</p>')
    return '\n'.join(html)


# ── Session state ─────────────────────────────────────────────────────────────
def init_state():
    for k, v in {
        "active_service": "cv",
        "conversations":  {k: [] for k in SERVICES},
        "llm":            None,
        "vectorstore":    None,
        "graph":          None,
        "cv_result":      None,
        "gh_result":      None,
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ── LLM ───────────────────────────────────────────────────────────────────────
@st.cache_resource(ttl=3600)
def load_llm():
    try:
        from groq import Groq
    except ImportError:
        return None
    key = None
    try:    key = st.secrets.get("GROQ_API_KEY")
    except: pass
    if not key: key = os.getenv("GROQ_API_KEY")
    if not key: return None

    client = Groq(api_key=key)

    class G:
        def __init__(self, c, m): self.c, self.m = c, m
        def invoke(self, prompt, system=None):
            try:
                r = self.c.chat.completions.create(
                    model=self.m,
                    messages=[
                        {"role":"system","content": system or "You are PathIQ, a helpful career assistant."},
                        {"role":"user",  "content": prompt},
                    ],
                    temperature=0.78, max_tokens=800, top_p=0.92,
                )
                return r.choices[0].message.content
            except Exception as e:
                return f"Something went wrong on my end: {e}. Give it another try."

    for m in ["llama-3.3-70b-versatile","deepseek-r1-distill-llama-70b","gemma2-9b-it"]:
        try:
            llm = G(client, m)
            if "Error" not in llm.invoke("say: ready"):
                return llm
        except: continue
    return None


@st.cache_resource(ttl=3600)
def load_vectorstore():
    if not RAG_OK: return None
    try:
        emb = HuggingFaceEmbeddings(model_name=EMBED_MODEL, model_kwargs={"device":"cpu"})
        if os.path.exists(os.path.join(DB_DIR,"chroma.sqlite3")):
            return Chroma(embedding_function=emb, persist_directory=DB_DIR)
    except: pass
    return None


@st.cache_resource(ttl=3600)
def load_graph():
    if not RAG_OK: return None
    try:
        b = KnowledgeGraphBuilder()
        return b.G if b.load() else None
    except: return None


# ── Render ────────────────────────────────────────────────────────────────────
def render_user(text):
    safe = text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace("\n","<br>")
    st.markdown(
        f'<div class="msg-block"><div class="user-row">'
        f'<div class="user-bub">{safe}</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

def render_bot(text):
    html = md_to_html(text)
    st.markdown(
        f'<div class="msg-block"><div class="bot-row">'
        f'<div class="bot-av">P</div>'
        f'<div class="bot-body">{html}</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

def render_typing():
    st.markdown(
        '<div class="typing-block">'
        '<div class="bot-av">P</div>'
        '<div class="t-dots">'
        '<div class="t-dot"></div><div class="t-dot"></div><div class="t-dot"></div>'
        '</div></div>',
        unsafe_allow_html=True,
    )

def render_welcome(sid):
    meta = SERVICE_META[sid]
    svc  = SERVICES[sid]
    st.markdown(
        f'<div class="welcome">'
        f'<div class="welcome-icon">✦</div>'
        f'<div class="welcome-title">PathIQ — {svc["label"]}</div>'
        f'<div class="welcome-body">{meta["welcome"]}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Chat logic ────────────────────────────────────────────────────────────────
def handle_send(user_msg, sid):
    if not user_msg.strip():
        return
    conv = st.session_state.conversations[sid]
    conv.append({"role":"user","content":user_msg,"ts":now_ts()})

    if is_greeting(user_msg) and len(conv) <= 2:
        reply = greeting_reply()
        conv.append({"role":"assistant","content":reply,"ts":now_ts()})
        save_csv(sid, user_msg, reply)
        st.rerun()
        return

    llm = st.session_state.llm or load_llm()
    if not llm:
        reply = "I need a GROQ_API_KEY to respond — add it to your .env file or Streamlit secrets."
        conv.append({"role":"assistant","content":reply,"ts":now_ts()})
        st.rerun()
        return
    st.session_state.llm = llm

    sys_prompt = SERVICE_META[sid]["system"]

    if sid == "rag" and RAG_OK:
        vs = st.session_state.vectorstore or load_vectorstore()
        g  = st.session_state.graph or load_graph()
        if vs and g:
            try:
                docs    = GraphRetriever(vectorstore=vs, graph=g, k=5, graph_k=5, hop_depth=2).get_relevant_documents(user_msg)
                context = "\n\n".join(f"[Doc {i+1}]: {d.page_content}" for i,d in enumerate(docs))
                prompt  = f"Retrieved context:\n{context}\n\nUser: {user_msg}"
            except:
                prompt = user_msg
        else:
            prompt = user_msg
    else:
        history = "\n".join(
            f"{'User' if m['role']=='user' else 'PathIQ'}: {m['content']}"
            for m in conv[-8:]
        )
        prompt = f"Conversation:\n{history}\n\nReply to the user's last message naturally and specifically."

    with st.spinner(""):
        reply = llm.invoke(prompt, system=sys_prompt)

    conv.append({"role":"assistant","content":reply,"ts":now_ts()})
    save_csv(sid, user_msg, reply)
    st.rerun()


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    init_state()
    st.markdown(CSS, unsafe_allow_html=True)
    sid  = st.session_state.active_service
    conv = st.session_state.conversations[sid]

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(
            '<div class="sb-brand">'
            '<div class="sb-gem">✦</div>'
            '<div><div class="sb-name">PathIQ</div>'
            '<div class="sb-tag">Career Intelligence</div></div>'
            '</div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="sb-group">Services</div>', unsafe_allow_html=True)
        for s_id, meta in SERVICES.items():
            if st.button(f"{meta['icon']}  {meta['label']}", key=f"sb_{s_id}", use_container_width=True):
                st.session_state.active_service = s_id
                st.rerun()

        st.markdown('<div class="sb-div"></div>', unsafe_allow_html=True)
        st.markdown('<div class="sb-group">Phase 2</div>', unsafe_allow_html=True)
        for icon, label in [("🎤","Mock Interview"),("🔗","LinkedIn Optimizer"),("🗺️","Skill Roadmap")]:
            st.button(f"{icon}  {label}", key=f"ph2_{label}", disabled=True, use_container_width=True)

        st.markdown('<div class="sb-div"></div>', unsafe_allow_html=True)

        if st.button("🗑   Clear chat", key="clear", use_container_width=True):
            st.session_state.conversations[sid] = []
            st.rerun()

        if os.path.exists("chat_history.csv"):
            with open("chat_history.csv", encoding="utf-8") as f:
                st.download_button("⬇   Export history", f,
                                   file_name="pathiq_history.csv",
                                   use_container_width=True)

        # CV upload
        if sid == "cv":
            st.markdown('<div class="sb-div"></div>', unsafe_allow_html=True)
            st.markdown('<div class="sb-group">Upload CV (PDF)</div>', unsafe_allow_html=True)
            uploaded = st.file_uploader("PDF", type=["pdf"], label_visibility="collapsed")
            if uploaded and st.button("Analyze PDF", key="analyze_cv", use_container_width=True):
                if CV_OK:
                    with st.spinner("Reading…"):
                        try:
                            tmp = f"tmp_{uploaded.name}"
                            with open(tmp,"wb") as f: f.write(uploaded.getbuffer())
                            result = CVAnalyzer().analyze_cv(tmp)
                            os.remove(tmp)
                            if result.get("success"):
                                handle_send(
                                    f"I uploaded my CV. Extracted data:\n{json.dumps(result.get('analysis',{}), indent=2)}\nGive me a full honest analysis.",
                                    "cv",
                                )
                            else:
                                st.error(result.get("error","Unknown error"))
                        except Exception as e:
                            st.error(str(e))
                else:
                    st.warning("cv_analyzer.py not found.")

        # GitHub fetch
        if sid == "github":
            st.markdown('<div class="sb-div"></div>', unsafe_allow_html=True)
            st.markdown('<div class="sb-group">Analyze GitHub</div>', unsafe_allow_html=True)
            gh_user = st.text_input("Username", placeholder="e.g. torvalds", label_visibility="collapsed")
            if gh_user and st.button("Fetch profile", key="fetch_gh", use_container_width=True):
                if GH_OK:
                    with st.spinner(f"Fetching @{gh_user}…"):
                        try:
                            result = GitHubAnalyzer().analyze_github_profile(gh_user)
                            if result.get("success"):
                                handle_send(
                                    f"GitHub @{gh_user}:\n{json.dumps(result, indent=2)}\nGive me a full profile analysis.",
                                    "github",
                                )
                            else:
                                st.error(result.get("error","Unknown error"))
                        except Exception as e:
                            st.error(str(e))
                else:
                    st.warning("github_analyzer.py not found.")

        st.markdown(
            '<div class="sb-status"><div class="sb-pulse"></div>Graph RAG · LLaMA 3.3-70b</div>',
            unsafe_allow_html=True,
        )

    # ── Chat area ─────────────────────────────────────────────────────────────
    if not conv:
        render_welcome(sid)
    else:
        st.markdown('<div class="msgs">', unsafe_allow_html=True)
        for msg in conv:
            if msg["role"] == "user":
                render_user(msg["content"])
            else:
                render_bot(msg["content"])
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Input bar ─────────────────────────────────────────────────────────────
    st.markdown(
        '<div class="inp-wrap"><div class="inp-inner"><div class="inp-shell">',
        unsafe_allow_html=True,
    )
    col_txt, col_btn = st.columns([12, 1])
    with col_txt:
        user_input = st.text_area(
            "msg", key=f"inp_{sid}",
            placeholder=SERVICE_META[sid]["placeholder"],
            height=52, label_visibility="collapsed",
        )
    with col_btn:
        st.markdown("<div style='padding-top:10px'>", unsafe_allow_html=True)
        send = st.button("↑", key=f"send_{sid}")
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown(
        '</div>'
        '<div class="inp-note">PathIQ can make mistakes. Verify important career decisions.</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    if send and user_input.strip():
        handle_send(user_input, sid)


if __name__ == "__main__":
    main()