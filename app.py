"""
Career AI Assistant — Production App
Every tab is a conversational service with word-by-word streaming.
Graph RAG auto-builds on startup from scraped job data.
"""

import os, time, json
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── Must be first Streamlit call ───────────────────────────────────────────────
st.set_page_config(
    page_title="Career AI",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Professional dark UI ───────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Reset & base ─────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

.stApp {
    background: #0d0d1a;
    color: #e2e8f0;
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
}

/* ── Hide Streamlit chrome ────────────────────────────────── */
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="collapsedControl"] { display: none !important; }

/* ── Sidebar ──────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #0a0a14 !important;
    border-right: 1px solid #1e2a4a !important;
    padding-top: 0 !important;
}
[data-testid="stSidebar"] * { color: #94a3b8 !important; }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #38bdf8 !important; }

/* ── Tab bar ──────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    background: #111827 !important;
    border-bottom: 1px solid #1e2a4a !important;
    gap: 0 !important;
    padding: 0 8px !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #64748b !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    padding: 12px 18px !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    transition: all .2s !important;
}
.stTabs [aria-selected="true"] {
    color: #38bdf8 !important;
    border-bottom-color: #38bdf8 !important;
    background: transparent !important;
}
.stTabs [data-baseweb="tab"]:hover { color: #94a3b8 !important; }

/* ── Chat messages ─────────────────────────────────────────── */
.stChatMessage {
    background: transparent !important;
    border: none !important;
    padding: 8px 0 !important;
}
[data-testid="stChatMessageContent"] {
    color: #e2e8f0 !important;
    font-size: 0.93rem !important;
    line-height: 1.75 !important;
}
/* User bubble */
[data-testid="stChatMessage"][data-testid*="user"] [data-testid="stChatMessageContent"] {
    background: #1e3a5f !important;
    border-radius: 18px 18px 4px 18px !important;
    padding: 10px 16px !important;
}
/* Assistant bubble */
[data-testid="stChatMessage"]:not([data-testid*="user"]) [data-testid="stChatMessageContent"] {
    background: #161b2e !important;
    border: 1px solid #1e2a4a !important;
    border-radius: 18px 18px 18px 4px !important;
    padding: 12px 16px !important;
}

/* ── Chat input ────────────────────────────────────────────── */
[data-testid="stChatInput"] {
    background: #111827 !important;
    border: 1px solid #1e2a4a !important;
    border-radius: 14px !important;
    padding: 4px 8px !important;
}
[data-testid="stChatInput"] textarea {
    background: transparent !important;
    color: #e2e8f0 !important;
    font-size: 0.92rem !important;
    border: none !important;
}
[data-testid="stChatInput"] textarea::placeholder { color: #475569 !important; }

/* ── Buttons ────────────────────────────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg, #1d4ed8, #0ea5e9) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    padding: 8px 16px !important;
    transition: all .2s !important;
}
.stButton > button:hover {
    opacity: .88 !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="secondary"] {
    background: #1e2a4a !important;
    color: #94a3b8 !important;
}

/* ── Inputs / selects ───────────────────────────────────────── */
.stTextInput > div > input,
.stTextArea > div > textarea,
.stSelectbox > div > div,
.stNumberInput > div > div > input {
    background: #111827 !important;
    color: #e2e8f0 !important;
    border: 1px solid #1e2a4a !important;
    border-radius: 10px !important;
    font-size: 0.9rem !important;
}
.stMultiSelect > div { background: #111827 !important; border: 1px solid #1e2a4a !important; border-radius: 10px !important; }

/* ── Metrics ────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: #111827 !important;
    border: 1px solid #1e2a4a !important;
    border-radius: 12px !important;
    padding: 14px !important;
}
[data-testid="stMetricLabel"] { color: #64748b !important; font-size: 0.8rem !important; }
[data-testid="stMetricValue"] { color: #38bdf8 !important; font-size: 1.4rem !important; font-weight: 700 !important; }

/* ── Alerts ─────────────────────────────────────────────────── */
.stSuccess { background: #052e16 !important; border: 1px solid #16a34a !important; border-radius: 10px !important; color: #86efac !important; }
.stWarning { background: #1c1008 !important; border: 1px solid #d97706 !important; border-radius: 10px !important; color: #fcd34d !important; }
.stError   { background: #1c0a0a !important; border: 1px solid #dc2626 !important; border-radius: 10px !important; color: #fca5a5 !important; }
.stInfo    { background: #0c1a2e !important; border: 1px solid #1d4ed8 !important; border-radius: 10px !important; color: #93c5fd !important; }

/* ── Progress ────────────────────────────────────────────────── */
.stProgress > div > div { background: #38bdf8 !important; }
.stProgress { background: #1e2a4a !important; border-radius: 8px !important; }

/* ── File uploader ────────────────────────────────────────────── */
[data-testid="stFileUploader"] {
    background: #111827 !important;
    border: 2px dashed #1e2a4a !important;
    border-radius: 12px !important;
    padding: 20px !important;
}

/* ── Expander ─────────────────────────────────────────────────── */
.streamlit-expanderHeader {
    background: #111827 !important;
    border: 1px solid #1e2a4a !important;
    border-radius: 10px !important;
    color: #94a3b8 !important;
}
.streamlit-expanderContent { background: #0d1117 !important; border: 1px solid #1e2a4a !important; border-top: none !important; border-radius: 0 0 10px 10px !important; }

/* ── Divider ──────────────────────────────────────────────────── */
hr { border-color: #1e2a4a !important; }

/* ── Scrollbar ────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0d0d1a; }
::-webkit-scrollbar-thumb { background: #1e2a4a; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# ── Imports (after set_page_config) ───────────────────────────────────────────
from cv_analyzer     import CVAnalyzer
from github_analyzer import GitHubAnalyzer
from job_matcher     import JobMatcher
from constant        import GROQ_MODEL, GROQ_MODEL_FALLBACK, HISTORY_TURNS

GROQ_KEY = os.getenv("GROQ_API_KEY", "")
if not GROQ_KEY:
    st.error("❌  `GROQ_API_KEY` not set. Add it to your `.env` file.")
    st.stop()

# ── Session state ──────────────────────────────────────────────────────────────
SERVICES = ["chat", "cv", "github", "jobs", "scraper"]

_defaults = {
    **{f"msgs_{s}": None for s in SERVICES},
    "cv_data":    None,   # analyzed CV dict
    "gh_data":    None,   # analyzed GitHub dict
    "rag_emb":    None,
    "rag_chunks": None,
    "rag_meta":   None,
    "rag_graph":  None,
    "rag_model":  None,
    "rag_ready":  False,
    "rag_attempted": False,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── RAG auto-setup ─────────────────────────────────────────────────────────────
def _setup_rag():
    if st.session_state.rag_attempted:
        return
    st.session_state.rag_attempted = True

    from rag_ingest import index_exists, data_is_newer_than_index, build_index, load_index, JOB_CSV_PATHS
    from sentence_transformers import SentenceTransformer

    data_ok = any(os.path.exists(p) for p in JOB_CSV_PATHS)

    def _load():
        emb, chunks, meta, graph = load_index()
        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        st.session_state.rag_emb    = emb
        st.session_state.rag_chunks = chunks
        st.session_state.rag_meta   = meta
        st.session_state.rag_graph  = graph
        st.session_state.rag_model  = model
        st.session_state.rag_ready  = True

    # Fresh index — just load
    if index_exists() and not data_is_newer_than_index():
        try: _load(); return
        except Exception: pass

    # Stale or missing — build automatically
    if data_ok:
        bar  = st.sidebar.progress(0, text="⚙️ Building RAG index…")
        info = st.sidebar.empty()
        def _cb(pct, msg):
            bar.progress(pct, text=msg); info.caption(msg)
        try:
            build_index(progress_callback=_cb)
            _load()
            bar.empty(); info.empty()
        except Exception as e:
            bar.empty(); info.empty()
            st.sidebar.warning(f"RAG build: {e}")

_setup_rag()

rag_ready  = st.session_state.rag_ready
job_count  = len(st.session_state.rag_chunks or [])


# ── LLM streaming helper ───────────────────────────────────────────────────────
def _stream(system: str, history: list, placeholder) -> str:
    from groq import Groq
    client = Groq(api_key=GROQ_KEY)
    full   = ""
    for model in [GROQ_MODEL, GROQ_MODEL_FALLBACK]:
        try:
            stream = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system}] + history,
                temperature=0.72, max_tokens=1400, stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    full += delta
                    placeholder.markdown(full + "▌")
            placeholder.markdown(full)
            return full
        except Exception:
            continue
    full = "❌ Could not reach AI. Check your API key."
    placeholder.error(full)
    return full


# ── RAG context helper ─────────────────────────────────────────────────────────
def _rag_context(query: str) -> str:
    if not rag_ready:
        return ""
    try:
        from rag_retriever import GraphRAGRetriever
        r = GraphRAGRetriever(
            st.session_state.rag_emb, st.session_state.rag_chunks,
            st.session_state.rag_meta, st.session_state.rag_graph,
            st.session_state.rag_model,
        )
        return r.get_context_string(query)
    except Exception:
        return ""


# ── Chat renderer (shared) ─────────────────────────────────────────────────────
def render_chat(service: str, system_fn, placeholder_text: str,
                suggestions: list | None = None):
    """
    Renders a full chat interface for a given service.
    system_fn(query) → system prompt string
    """
    key = f"msgs_{service}"
    if st.session_state[key] is None:
        st.session_state[key] = []

    # Render history
    for msg in st.session_state[key]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Quick suggestion buttons
    if suggestions and not st.session_state[key]:
        st.markdown(
            "<p style='color:#475569;font-size:0.82rem;margin:16px 0 8px;'>Try asking:</p>",
            unsafe_allow_html=True,
        )
        cols = st.columns(min(len(suggestions), 3))
        for i, s in enumerate(suggestions):
            if cols[i % 3].button(s, key=f"sug_{service}_{i}", use_container_width=True):
                st.session_state[key].append({"role": "user", "content": s})
                st.rerun()

    # Chat input
    if prompt := st.chat_input(placeholder_text):
        st.session_state[key].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state[key][-HISTORY_TURNS:]
            if m["role"] in ("user", "assistant")
        ]

        with st.chat_message("assistant"):
            ph  = st.empty()
            sys = system_fn(prompt)
            reply = _stream(sys, history, ph)

        st.session_state[key].append({"role": "assistant", "content": reply})
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
col_logo, col_title, col_status = st.columns([1, 6, 3])
with col_logo:
    st.markdown(
        "<div style='font-size:2.2rem;padding-top:8px;'>🚀</div>",
        unsafe_allow_html=True,
    )
with col_title:
    st.markdown(
        "<h1 style='font-size:1.6rem;font-weight:800;"
        "background:linear-gradient(135deg,#38bdf8,#818cf8);"
        "-webkit-background-clip:text;-webkit-text-fill-color:transparent;"
        "margin:8px 0 2px;'>Career AI Assistant</h1>"
        "<p style='color:#475569;font-size:0.82rem;margin:0;'>"
        "Graph RAG · CV Analysis · GitHub · Job Matching · Live Scraping</p>",
        unsafe_allow_html=True,
    )
with col_status:
    if rag_ready:
        st.markdown(
            f"<div style='text-align:right;padding-top:10px;'>"
            f"<span style='background:#052e16;color:#86efac;border:1px solid #16a34a;"
            f"border-radius:20px;padding:4px 12px;font-size:0.78rem;font-weight:600;'>"
            f"🕸️ RAG Live · {job_count:,} jobs</span></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div style='text-align:right;padding-top:10px;'>"
            "<span style='background:#1c1008;color:#fcd34d;border:1px solid #d97706;"
            "border-radius:20px;padding:4px 12px;font-size:0.78rem;font-weight:600;'>"
            "⚠️ RAG offline</span></div>",
            unsafe_allow_html=True,
        )

st.markdown("<hr style='margin:8px 0 0;'>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
t_chat, t_cv, t_gh, t_jobs, t_scrape = st.tabs([
    "💬  Career Chat",
    "📄  CV Analyzer",
    "🐙  GitHub Profiler",
    "💼  Job Matcher",
    "🌐  Job Scraper",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Career Chat  (Graph RAG grounded)
# ══════════════════════════════════════════════════════════════════════════════
with t_chat:
    # Build user context string from other services
    ctx = []
    if st.session_state.cv_data:
        a = st.session_state.cv_data.get("analysis", {})
        if isinstance(a, dict):
            ctx.append(
                f"User CV: {a.get('name','')} | "
                f"level={a.get('seniority_level','?')} | "
                f"years={a.get('years_experience','?')} | "
                f"score={a.get('overall_score','?')}/100 | "
                f"skills={', '.join(a.get('skills',{}).get('languages',[]))}"
            )
    if st.session_state.gh_data:
        p  = st.session_state.gh_data.get("profile",  {})
        ga = st.session_state.gh_data.get("analysis", {})
        ctx.append(
            f"GitHub: {p.get('username','?')} | "
            f"repos={p.get('public_repos','?')} | "
            f"score={ga.get('overall_score','?') if isinstance(ga,dict) else '?'}/100 | "
            f"readiness={ga.get('career_readiness','?') if isinstance(ga,dict) else '?'}"
        )

    def _chat_system(query):
        rag = _rag_context(query)
        user_ctx = f"\n\nUser context: {' | '.join(ctx)}" if ctx else ""
        rag_block = (
            f"\n\nREAL JOB DATA (Graph RAG):\n{rag}\n\n"
            "Ground your answer in this data. Mention specific job titles and companies when relevant."
        ) if rag else "\n\nNo job database loaded yet."

        return (
            "You are a senior career advisor — direct, specific, and human.\n"
            "Rules: Never start with 'Certainly' or 'Of course'. No filler openers.\n"
            "Give concrete advice. When writing cover letters or emails, write the full text.\n"
            "Use bullet points only when listing 3+ items. Keep paragraphs short.\n"
            f"{user_ctx}{rag_block}"
        )

    render_chat(
        service          = "chat",
        system_fn        = _chat_system,
        placeholder_text = "Ask about jobs, career advice, or say 'write me a cover letter'…",
        suggestions      = [
            "What Python jobs are available right now?",
            "Which companies are hiring remotely in Egypt?",
            "Write a cover letter for a senior backend role",
            "How do I negotiate a higher salary?",
            "What skills should a data scientist learn in 2025?",
            "Draft a LinkedIn message to a recruiter",
        ],
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — CV Analyzer  (chat-driven)
# ══════════════════════════════════════════════════════════════════════════════
with t_cv:
    col_up, col_info = st.columns([1, 1])
    with col_up:
        uploaded = st.file_uploader("Upload your CV (PDF)", type=["pdf"], label_visibility="collapsed")
        if uploaded:
            if st.button("🔍 Analyze CV", use_container_width=True):
                temp = f"temp_{uploaded.name}"
                try:
                    with open(temp, "wb") as f: f.write(uploaded.getbuffer())
                    with st.spinner("Reading your CV…"):
                        result = CVAnalyzer().analyze_cv(temp)
                    if result.get("success"):
                        st.session_state.cv_data = result
                        a = result["analysis"]
                        # Push summary into chat history
                        intro = (
                            f"I've analyzed your CV. Here's what I found:\n\n"
                            f"**Overall Score:** {a.get('overall_score','?')}/100\n"
                            f"**Level:** {a.get('seniority_level','?').title()}\n"
                            f"**Experience:** {a.get('years_experience','?')} years\n\n"
                            f"**Top Skills:** {', '.join(a.get('skills',{}).get('languages',[]))}\n\n"
                            f"**Summary:** {a.get('summary','')}\n\n"
                            "What would you like to dig into? I can rewrite your summary, "
                            "identify skill gaps, find matching jobs, or draft a cover letter."
                        )
                        st.session_state.msgs_cv = [{"role": "assistant", "content": intro}]
                        st.rerun()
                    else:
                        st.error(result.get("error"))
                except Exception as e:
                    st.error(str(e))
                finally:
                    if os.path.exists(temp): os.remove(temp)

    with col_info:
        if st.session_state.cv_data:
            a = st.session_state.cv_data.get("analysis", {})
            c1, c2, c3 = st.columns(3)
            c1.metric("Score",   f"{a.get('overall_score','?')}/100")
            c2.metric("Level",   a.get("seniority_level","?").title())
            c3.metric("Years",   a.get("years_experience","?"))
            # Impact scores
            exp = a.get("experience", [])
            if exp:
                st.markdown(
                    "<p style='color:#475569;font-size:0.8rem;margin:12px 0 4px;'>Role impact scores:</p>",
                    unsafe_allow_html=True,
                )
                for role in exp:
                    score = role.get("impact_score", 5)
                    bar_w = int(score * 10)
                    st.markdown(
                        f"<div style='display:flex;align-items:center;gap:10px;margin:3px 0;'>"
                        f"<span style='color:#94a3b8;font-size:0.78rem;width:160px;white-space:nowrap;"
                        f"overflow:hidden;text-overflow:ellipsis;'>{role.get('title','?')[:25]}</span>"
                        f"<div style='flex:1;background:#1e2a4a;border-radius:4px;height:8px;'>"
                        f"<div style='width:{bar_w}%;background:#38bdf8;border-radius:4px;height:8px;'></div></div>"
                        f"<span style='color:#38bdf8;font-size:0.78rem;'>{score}/10</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
        else:
            st.markdown(
                "<div style='padding:40px;text-align:center;color:#475569;'>"
                "<div style='font-size:2.5rem;'>📄</div>"
                "<p style='margin-top:8px;'>Upload your CV to get a full analysis,<br>"
                "then chat about it below.</p></div>",
                unsafe_allow_html=True,
            )

    st.markdown("<hr style='margin:12px 0;'>", unsafe_allow_html=True)

    # CV chat
    def _cv_system(query):
        cv_ctx = ""
        if st.session_state.cv_data:
            a = st.session_state.cv_data.get("analysis", {})
            cv_ctx = (
                f"\n\nCV DATA:\n{json.dumps(a, indent=2)[:2000]}\n\n"
                "Use this CV data to give specific, personalized answers."
            )
        return (
            "You are a career coach specializing in CV improvement. Be direct and specific.\n"
            "Never say 'Certainly' or 'Great question'. Just answer.\n"
            "When rewriting CV sections, show the full rewritten text in a code block.\n"
            f"{cv_ctx}"
        )

    render_chat(
        service          = "cv",
        system_fn        = _cv_system,
        placeholder_text = "Ask about your CV, request rewrites, or explore career paths…",
        suggestions      = [
            "Rewrite my professional summary",
            "What are my biggest skill gaps?",
            "What roles am I best suited for?",
            "How can I improve my overall score?",
        ],
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — GitHub Profiler  (chat-driven)
# ══════════════════════════════════════════════════════════════════════════════
with t_gh:
    col_in, col_stats = st.columns([1, 1])
    with col_in:
        uname = st.text_input("GitHub username", placeholder="e.g. torvalds", label_visibility="collapsed")
        if st.button("🔍 Analyze Profile", use_container_width=True):
            if not uname.strip():
                st.warning("Enter a username.")
            else:
                with st.spinner("Fetching GitHub data…"):
                    try:
                        result = GitHubAnalyzer().analyze_github_profile(uname.strip())
                        if result.get("success"):
                            st.session_state.gh_data = result
                            p  = result["profile"]
                            ga = result["analysis"]
                            intro = (
                                f"Here's the analysis for **@{p.get('username','?')}**:\n\n"
                                f"**Overall Score:** {ga.get('overall_score','?')}/100\n"
                                f"**Career Readiness:** {ga.get('career_readiness','?').title()}\n"
                                f"**Salary Band:** {ga.get('salary_band_usd','?')}\n\n"
                                f"**Recruiter Verdict:** {ga.get('recruiter_verdict','')}\n\n"
                                "What would you like to know more about? I can suggest "
                                "improvements, compare to job requirements, or help write a GitHub bio."
                            )
                            st.session_state.msgs_github = [{"role": "assistant", "content": intro}]
                            st.rerun()
                        else:
                            st.error(result.get("error"))
                    except Exception as e:
                        st.error(str(e))

    with col_stats:
        if st.session_state.gh_data:
            p  = st.session_state.gh_data.get("profile",  {})
            ga = st.session_state.gh_data.get("analysis", {})
            c1, c2, c3 = st.columns(3)
            c1.metric("Followers",  p.get("followers",   0))
            c2.metric("Repos",      p.get("public_repos",0))
            c3.metric("Score",      f"{ga.get('overall_score','?')}/100")
            # 5-dimension radar (progress bars)
            if isinstance(ga, dict) and "scores" in ga:
                dims = ga["scores"]
                st.markdown(
                    "<p style='color:#475569;font-size:0.8rem;margin:12px 0 4px;'>Dimension scores:</p>",
                    unsafe_allow_html=True,
                )
                for dim, val in dims.items():
                    bar_w = int(int(val) * 10) if str(val).isdigit() else 50
                    st.markdown(
                        f"<div style='display:flex;align-items:center;gap:10px;margin:3px 0;'>"
                        f"<span style='color:#94a3b8;font-size:0.78rem;width:110px;'>{dim.title()}</span>"
                        f"<div style='flex:1;background:#1e2a4a;border-radius:4px;height:8px;'>"
                        f"<div style='width:{bar_w}%;background:#818cf8;border-radius:4px;height:8px;'></div></div>"
                        f"<span style='color:#818cf8;font-size:0.78rem;'>{val}/10</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
            # Language chart
            langs = p.get("languages", {})
            if langs:
                st.markdown(
                    "<p style='color:#475569;font-size:0.8rem;margin:12px 0 4px;'>Top languages:</p>",
                    unsafe_allow_html=True,
                )
                top = sorted(langs.items(), key=lambda x: x[1], reverse=True)[:6]
                total_repos = sum(v for _, v in top) or 1
                for lang, cnt in top:
                    pct = int(cnt / total_repos * 100)
                    st.markdown(
                        f"<div style='display:flex;align-items:center;gap:10px;margin:3px 0;'>"
                        f"<span style='color:#94a3b8;font-size:0.78rem;width:90px;'>{lang}</span>"
                        f"<div style='flex:1;background:#1e2a4a;border-radius:4px;height:8px;'>"
                        f"<div style='width:{pct}%;background:#0ea5e9;border-radius:4px;height:8px;'></div></div>"
                        f"<span style='color:#0ea5e9;font-size:0.78rem;'>{cnt} repos</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
        else:
            st.markdown(
                "<div style='padding:40px;text-align:center;color:#475569;'>"
                "<div style='font-size:2.5rem;'>🐙</div>"
                "<p style='margin-top:8px;'>Enter a GitHub username to analyze<br>the profile, then chat about it.</p>"
                "</div>",
                unsafe_allow_html=True,
            )

    st.markdown("<hr style='margin:12px 0;'>", unsafe_allow_html=True)

    def _gh_system(query):
        gh_ctx = ""
        if st.session_state.gh_data:
            p  = st.session_state.gh_data.get("profile",  {})
            ga = st.session_state.gh_data.get("analysis", {})
            gh_ctx = (
                f"\n\nGITHUB DATA:\n{json.dumps({'profile':p,'analysis':ga}, indent=2)[:2000]}\n\n"
                "Use this to give specific, data-driven advice."
            )
        return (
            "You are a senior engineering mentor reviewing a GitHub profile.\n"
            "Be direct, specific, and actionable. No filler. Reference actual repo data.\n"
            f"{gh_ctx}"
        )

    render_chat(
        service          = "github",
        system_fn        = _gh_system,
        placeholder_text = "Ask about the GitHub profile, get improvement tips…",
        suggestions      = [
            "How can I improve my profile score?",
            "Write a better GitHub bio for me",
            "What projects would make me more hireable?",
            "Compare this profile to what recruiters look for",
        ],
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Job Matcher  (chat-driven)
# ══════════════════════════════════════════════════════════════════════════════
with t_jobs:
    # Quick profile form
    with st.expander("⚙️ Set your profile (used for matching)", expanded=not bool(st.session_state.msgs_jobs)):
        c1, c2, c3 = st.columns(3)
        with c1:
            skills_raw = st.text_area("Skills (one per line)", height=90,
                                      placeholder="Python\nReact\nDocker")
        with c2:
            exp_yr  = st.number_input("Years experience", 0, 40, 2)
            seniority = st.selectbox("Seniority", ["Junior","Mid-Level","Senior","Lead"])
        with c3:
            roles = st.multiselect("Target roles", [
                "Full Stack Developer","Backend Engineer","Frontend Developer",
                "Data Scientist","ML Engineer","DevOps Engineer","Product Manager",
                "Mobile Developer","QA Engineer",
            ])
        if st.button("🔍 Match Jobs", use_container_width=True):
            skills = [s.strip() for s in skills_raw.splitlines() if s.strip()]
            if not skills:
                st.warning("Add at least one skill.")
            else:
                profile = {"skills": skills, "experience_years": exp_yr,
                           "seniority_level": seniority.lower(), "interested_roles": roles}
                with st.spinner("Searching job database…"):
                    try:
                        result = JobMatcher().match_jobs(profile)
                        if result.get("success"):
                            m = result["matches"]
                            jobs_list = m.get("jobs", []) if isinstance(m, dict) else []
                            intro_parts = [
                                f"Found **{len(jobs_list)} matches** for your profile.\n"
                            ]
                            for j in jobs_list[:3]:
                                intro_parts.append(
                                    f"**{j.get('job_title','?')}** at {j.get('company','?')} "
                                    f"— Fit: {j.get('fit_score','?')}% | Priority: {j.get('apply_priority','?').upper()}\n"
                                    f"_{j.get('why_fit','')}_\n"
                                )
                            if isinstance(m, dict):
                                intro_parts.append(f"\n{m.get('summary','')}")
                            intro_parts.append("\nAsk me to write an application email, explain a gap, or find more specific roles.")
                            intro = "\n".join(intro_parts)
                            st.session_state.msgs_jobs = [{"role": "assistant", "content": intro}]
                            st.rerun()
                        else:
                            st.warning(result.get("error"))
                    except Exception as e:
                        st.error(str(e))

    def _jobs_system(query):
        rag = _rag_context(query)
        rag_block = (f"\n\nJOB DATABASE (Graph RAG):\n{rag}"
                     if rag else "\n\nNo job database loaded.")
        cv_ctx = ""
        if st.session_state.cv_data:
            a = st.session_state.cv_data.get("analysis", {})
            cv_ctx = (f"\n\nUser CV: seniority={a.get('seniority_level','?')}, "
                      f"skills={', '.join(a.get('skills',{}).get('languages',[]))}")
        return (
            "You are a job search strategist. Give specific, actionable job hunting advice.\n"
            "When the user asks about jobs, reference real listings from the database.\n"
            "No filler openers. Be direct.\n"
            f"{cv_ctx}{rag_block}"
        )

    render_chat(
        service          = "jobs",
        system_fn        = _jobs_system,
        placeholder_text = "Ask about specific jobs, companies, or say 'write me an application email'…",
        suggestions      = [
            "What remote jobs pay over $80k?",
            "Find Python jobs in Cairo",
            "Write an email applying to a fintech startup",
            "What companies are hiring senior developers?",
        ],
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — Job Scraper  (chat-driven + manual controls)
# ══════════════════════════════════════════════════════════════════════════════
with t_scrape:
    # DB status strip
    db_path = next((p for p in ["data/jobs_combined.csv","data/jobs.csv"] if os.path.exists(p)), None)
    if db_path:
        try:
            import pandas as pd
            df_c = pd.read_csv(db_path)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Jobs in DB", f"{len(df_c):,}")
            c2.metric("Sources",    df_c["source"].nunique() if "source" in df_c.columns else "—")
            c3.metric("File",       db_path.split("/")[-1])
            c4.metric("RAG",        "✅ Active" if rag_ready else "⚠️ Offline")
        except Exception:
            pass
        st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)

    # Source controls (collapsed by default)
    with st.expander("⚙️ Scraper settings", expanded=False):
        ca, cb = st.columns(2)
        with ca:
            use_ro  = st.checkbox("🌍 RemoteOK",  value=True)
            use_arb = st.checkbox("🇩🇪 Arbeitnow", value=True)
            use_mu  = st.checkbox("🇺🇸 The Muse",  value=True)
            use_wu  = st.checkbox("🇪🇬 Wuzzuf",    value=True)
        with cb:
            ro_lim = st.slider("RemoteOK jobs", 20, 200, 100, 20, disabled=not use_ro)
            arb_pg = st.slider("Arbeitnow pages", 1, 10, 3, disabled=not use_arb)
            mu_pg  = st.slider("Muse pages", 1, 5, 2, disabled=not use_mu)
            wu_pg  = st.slider("Wuzzuf pages/keyword", 1, 5, 2, disabled=not use_wu)

        wu_kw_raw = st.text_area(
            "Wuzzuf keywords", height=55, disabled=not use_wu,
            value="software engineer, python developer, data scientist, frontend developer, backend developer, devops",
        )
        wu_kw = [k.strip() for k in wu_kw_raw.split(",") if k.strip()]

        if st.button("🚀 Start Scraping", use_container_width=True, type="primary"):
            if not any([use_ro, use_arb, use_mu, use_wu]):
                st.warning("Select at least one source.")
            else:
                prog = st.progress(0, text="Starting…")
                lb   = st.empty(); logs: list = []
                def log(msg):
                    logs.append(msg)
                    lb.markdown("\n".join(f"`{l}`" for l in logs[-8:]))
                try:
                    from data_scraper import (RemoteOKScraper, ArbeitnowScraper,
                                              TheMuseScraper, WuzzufScraper)
                    import pandas as pd
                    os.makedirs("data", exist_ok=True)
                    all_j: list = []
                    tot = sum([use_ro,use_arb,use_mu,use_wu]); step = 0
                    if use_ro:
                        log("📡 RemoteOK…"); prog.progress(int(100*step/tot))
                        j = RemoteOKScraper().scrape(limit=ro_lim); all_j+=j; step+=1
                        log(f"   ✅ {len(j)} jobs")
                    if use_arb:
                        log("📡 Arbeitnow…"); prog.progress(int(100*step/tot))
                        j = ArbeitnowScraper().scrape(pages=arb_pg); all_j+=j; step+=1
                        log(f"   ✅ {len(j)} jobs")
                    if use_mu:
                        log("📡 The Muse…"); prog.progress(int(100*step/tot))
                        j = TheMuseScraper().scrape(pages=mu_pg); all_j+=j; step+=1
                        log(f"   ✅ {len(j)} jobs")
                    if use_wu:
                        log(f"📡 Wuzzuf ({len(wu_kw)} kw)…"); prog.progress(int(100*step/tot))
                        j = WuzzufScraper().scrape(keywords=wu_kw, pages_per_keyword=wu_pg)
                        all_j+=j; step+=1; log(f"   ✅ {len(j)} jobs")
                    existing = pd.DataFrame()
                    for p2 in ["data/jobs.csv","docs/ai_jobs_market_2025_2026.csv"]:
                        if os.path.exists(p2):
                            try: existing=pd.read_csv(p2); log(f"   📂 {len(existing)} existing"); break
                            except Exception: pass
                    combined = pd.concat([existing,pd.DataFrame(all_j)],ignore_index=True)
                    before   = len(combined)
                    combined.drop_duplicates(subset=["job_title","company"],keep="first",inplace=True)
                    log(f"   🗑️ {before-len(combined)} dupes removed")
                    combined.to_csv("data/jobs_combined.csv",index=False)
                    prog.progress(100,text="Done!")
                    log(f"💾 {len(combined):,} jobs → data/jobs_combined.csv")
                    msg = (
                        f"✅ Scraped **{len(all_j):,} new jobs** from "
                        f"{sum([use_ro,use_arb,use_mu,use_wu])} sources. "
                        f"**{len(combined):,} total** in database.\n\n"
                        "The RAG index will rebuild automatically on the next app restart, "
                        "or click **🔄 Rebuild RAG** in the sidebar right now."
                    )
                    st.session_state.msgs_scraper = [{"role":"assistant","content":msg}]
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ {e}"); prog.progress(100)

    def _scraper_system(query):
        ctx_str = ""
        if db_path:
            try:
                import pandas as pd
                df2 = pd.read_csv(db_path)
                srcs = df2["source"].value_counts().to_dict() if "source" in df2.columns else {}
                ctx_str = (
                    f"\n\nDatabase stats: {len(df2):,} jobs | "
                    f"sources: {srcs} | "
                    f"RAG: {'active' if rag_ready else 'offline'}"
                )
            except Exception:
                pass
        return (
            "You are a data engineering assistant helping manage a job scraping pipeline.\n"
            "Answer questions about the job database, scraping sources, or how to get more relevant data.\n"
            "Be concise and technical.\n"
            f"{ctx_str}"
        )

    render_chat(
        service          = "scraper",
        system_fn        = _scraper_system,
        placeholder_text = "Ask about the job database or scraping…",
        suggestions      = [
            "How many jobs do we have per source?",
            "Why might Wuzzuf return fewer results than expected?",
            "How often should I re-scrape?",
        ],
    )


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(
        "<h2 style='font-size:1rem;margin:16px 0 8px;'>⚙️ Controls</h2>",
        unsafe_allow_html=True,
    )

    # RAG panel
    st.markdown(
        "<p style='font-size:0.8rem;color:#64748b;margin:8px 0 4px;'>🕸️ Graph RAG Index</p>",
        unsafe_allow_html=True,
    )
    if rag_ready:
        g = st.session_state.rag_graph
        st.markdown(
            f"<div style='font-size:0.78rem;color:#86efac;'>"
            f"✅ {job_count:,} chunks · {g.number_of_nodes():,} nodes · {g.number_of_edges():,} edges"
            f"</div>", unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div style='font-size:0.78rem;color:#fcd34d;'>⚠️ Not loaded</div>",
            unsafe_allow_html=True,
        )

    if st.button("🔄 Rebuild RAG Now", use_container_width=True):
        from rag_ingest import build_index, load_index
        from sentence_transformers import SentenceTransformer
        bar  = st.progress(0)
        info = st.empty()
        def _cb(pct, msg): bar.progress(pct, text=msg); info.caption(msg)
        try:
            build_index(progress_callback=_cb)
            emb, chunks, meta, graph = load_index()
            model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            st.session_state.rag_emb    = emb
            st.session_state.rag_chunks = chunks
            st.session_state.rag_meta   = meta
            st.session_state.rag_graph  = graph
            st.session_state.rag_model  = model
            st.session_state.rag_ready  = True
            bar.empty(); info.empty()
            st.rerun()
        except Exception as e:
            st.error(f"❌ {e}")

    st.markdown("<hr style='margin:12px 0;border-color:#1e2a4a;'>", unsafe_allow_html=True)

    # Status
    st.markdown(
        "<p style='font-size:0.8rem;color:#64748b;margin:8px 0 4px;'>📊 Session</p>",
        unsafe_allow_html=True,
    )
    def _dot(ok, label):
        color = "#86efac" if ok else "#475569"
        st.markdown(
            f"<div style='font-size:0.78rem;color:{color};margin:2px 0;'>"
            f"{'●' if ok else '○'} {label}</div>",
            unsafe_allow_html=True,
        )
    _dot(bool(GROQ_KEY),                        "Groq API")
    _dot(rag_ready,                              "RAG Index")
    _dot(bool(st.session_state.cv_data),         "CV Analyzed")
    _dot(bool(st.session_state.gh_data),         "GitHub Profiled")
    _dot(bool(db_path),                          "Job DB")

    st.markdown("<hr style='margin:12px 0;border-color:#1e2a4a;'>", unsafe_allow_html=True)

    # Clear buttons
    if st.button("🗑️ Clear All Chats", use_container_width=True):
        for s in SERVICES:
            st.session_state[f"msgs_{s}"] = None
        st.rerun()
    if st.button("🗑️ Clear Everything", use_container_width=True):
        for k in _defaults:
            st.session_state[k] = None
        st.rerun()

    st.markdown(
        "<p style='font-size:0.72rem;color:#334155;margin-top:20px;text-align:center;'>"
        "Career AI · Graph RAG · Groq</p>",
        unsafe_allow_html=True,
    )