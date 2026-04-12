"""
Career AI Assistant  –  Phase 1
================================
Human-readable, chat-style responses throughout.
No raw JSON dumps visible to the user.

Tabs
────
  1. 📄  CV Analyzer        → skills pills, timeline, AI summary paragraph
  2. 🐙  GitHub Profile     → profile card, language bars, AI narrative
  3. 💼  Job Matcher        → job cards with match %, skills, explanation
  4. 💬  Career Chat        → conversational Q&A about your career/results
  5. 📊  Full Assessment    → narrative report

Fixes applied vs original:
  • Both cv_analyzer.py and job_matcher.py used langchain_community.llms.Groq
    which does NOT exist → replaced with groq package directly (in the helper files)
  • LLM responses were raw strings, never parsed → now parsed as JSON dicts
  • st.set_page_config() was duplicated → single call here
"""

import os
import json
import re
import datetime

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ══════════════════════════════════════════════════════════════════════════════
# Page config  ← must be FIRST
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Career AI",
    page_icon="🎯",
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
  --navy:   #080c18; --navy2:  #0d1326; --navy3:  #111829;
  --navy4:  #172035; --navy5:  #1e2d47;
  --line:   rgba(255,255,255,.06); --line2: rgba(255,255,255,.10);
  --t1: #e8eeff; --t2: #7a8ab0; --t3: #3d4a6a;
  --cyan: #00d9ff; --cyan2: #00b3d4;
  --cyan-d: rgba(0,217,255,.08); --cyan-b: rgba(0,217,255,.20);
  --sage:  #34d399; --amber: #fbbf24; --rose: #f87171;
  --ff: 'Plus Jakarta Sans', system-ui, sans-serif;
  --fm: 'JetBrains Mono', monospace;
  --r: 14px; --rs: 9px;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body,
[data-testid="stApp"],
[data-testid="stAppViewContainer"],
.main { background: var(--navy) !important; font-family: var(--ff) !important; color: var(--t1) !important; }
#MainMenu, header, footer,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"] { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
section.main > div { padding: 0 !important; }

/* Sidebar */
[data-testid="stSidebar"] { background: var(--navy2) !important; border-right: 1px solid var(--line) !important; min-width: 270px !important; max-width: 270px !important; }
[data-testid="stSidebar"] > div:first-child { padding: 0 !important; }
[data-testid="stSidebar"] label, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span { color: var(--t2) !important; font-size: 12.5px !important; }
[data-testid="stSidebar"] .stButton > button { background: transparent !important; border: 1px solid var(--line2) !important; border-radius: var(--rs) !important; color: var(--t2) !important; font-family: var(--ff) !important; font-size: 12.5px !important; font-weight: 500 !important; padding: 9px 14px !important; width: 100% !important; transition: all 0.18s !important; }
[data-testid="stSidebar"] .stButton > button:hover { background: var(--navy4) !important; border-color: var(--cyan-b) !important; color: var(--t1) !important; }
[data-testid="stSidebar"] [data-testid="stMetricValue"] { color: var(--t1) !important; font-size: 16px !important; }

/* Tabs */
[data-testid="stTabs"] [data-baseweb="tab-list"] { background: var(--navy2) !important; border-bottom: 1px solid var(--line) !important; padding: 0 28px !important; gap: 2px !important; }
[data-testid="stTabs"] [data-baseweb="tab"] { background: transparent !important; border: none !important; color: var(--t2) !important; font-family: var(--ff) !important; font-size: 13px !important; font-weight: 600 !important; padding: 14px 16px !important; border-bottom: 2px solid transparent !important; transition: all .18s !important; }
[data-testid="stTabs"] [data-baseweb="tab"]:hover { color: var(--t1) !important; }
[data-testid="stTabs"] [aria-selected="true"] { color: var(--cyan) !important; border-bottom-color: var(--cyan) !important; }
[data-testid="stTabPanel"] { background: transparent !important; padding: 28px !important; }

/* Inputs */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stNumberInput"] input { background: var(--navy3) !important; border: 1px solid var(--line2) !important; border-radius: var(--r) !important; color: var(--t1) !important; font-family: var(--ff) !important; font-size: 13.5px !important; caret-color: var(--cyan) !important; }
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus { border-color: var(--cyan) !important; box-shadow: 0 0 0 2px var(--cyan-d) !important; outline: none !important; }
[data-testid="stTextInput"] label,
[data-testid="stTextArea"] label,
[data-testid="stNumberInput"] label,
[data-testid="stSelectbox"] label,
[data-testid="stMultiSelect"] label { color: var(--t2) !important; font-size: 12.5px !important; font-weight: 600 !important; }
[data-testid="stFileUploader"] { background: var(--navy3) !important; border: 1px dashed var(--cyan-b) !important; border-radius: var(--r) !important; padding: 16px !important; }
[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stMultiSelect"] [data-baseweb="select"] > div { background: var(--navy3) !important; border: 1px solid var(--line2) !important; border-radius: var(--r) !important; color: var(--t1) !important; }

/* Buttons (main) */
.stButton > button { background: linear-gradient(135deg,#007acc,#00d9ff) !important; border: none !important; border-radius: var(--r) !important; color: var(--navy) !important; font-family: var(--ff) !important; font-size: 13.5px !important; font-weight: 700 !important; padding: 11px 22px !important; transition: all .2s !important; box-shadow: 0 4px 14px rgba(0,217,255,.25) !important; }
.stButton > button:hover { transform: translateY(-2px) !important; box-shadow: 0 6px 20px rgba(0,217,255,.4) !important; }
.stButton > button:active { transform: translateY(0) !important; }
.stButton > button:disabled { opacity: 0.4 !important; transform: none !important; }

/* Metrics */
[data-testid="stMetric"] { background: var(--navy3) !important; border: 1px solid var(--line) !important; border-radius: var(--r) !important; padding: 14px 18px !important; }
[data-testid="stMetricLabel"] { color: var(--t3) !important; font-size: 11px !important; }
[data-testid="stMetricValue"] { color: var(--t1) !important; font-size: 22px !important; }

/* Expanders */
[data-testid="stExpander"] { background: var(--navy3) !important; border: 1px solid var(--line) !important; border-radius: var(--r) !important; }
[data-testid="stExpander"] summary { color: var(--t2) !important; font-size: 12.5px !important; }

/* Chat input */
[data-testid="stChatInput"] { background: var(--navy3) !important; border: 1px solid var(--line2) !important; border-radius: var(--r) !important; margin: 0 0 12px !important; }
[data-testid="stChatInput"]:focus-within { border-color: var(--cyan) !important; box-shadow: 0 0 0 2px var(--cyan-d) !important; }
[data-testid="stChatInput"] textarea { background: transparent !important; border: none !important; color: var(--t1) !important; font-family: var(--ff) !important; font-size: 13.5px !important; caret-color: var(--cyan) !important; }
[data-testid="stChatInput"] textarea::placeholder { color: var(--t3) !important; }
[data-testid="stChatInput"] button { background: linear-gradient(135deg,#007acc,#00d9ff) !important; border: none !important; border-radius: 9px !important; color: var(--navy) !important; }

/* Chat messages */
[data-testid="stChatMessageContent"] { color: var(--t1) !important; font-size: 13.5px !important; line-height: 1.7 !important; font-family: var(--ff) !important; }
[data-testid="stChatMessage"] { background: var(--navy3) !important; border: 1px solid var(--line) !important; border-radius: 16px !important; padding: 4px 8px !important; margin: 6px 0 !important; }

/* Progress */
.stProgress > div > div { background: var(--cyan) !important; }

/* Download button */
[data-testid="stDownloadButton"] > button { background: transparent !important; border: 1px solid var(--line2) !important; box-shadow: none !important; color: var(--t2) !important; }
[data-testid="stDownloadButton"] > button:hover { border-color: var(--cyan-b) !important; color: var(--cyan) !important; transform: none !important; box-shadow: none !important; }

hr { border-color: var(--line) !important; }

/* Custom components */
.page-hdr { background: var(--navy2); border-bottom: 1px solid var(--line); padding: 0 28px; height: 64px; display: flex; align-items: center; justify-content: space-between; }
.hdr-gem { width: 42px; height: 42px; border-radius: 12px; background: linear-gradient(135deg,#007acc,#00d9ff); display: flex; align-items: center; justify-content: center; font-size: 20px; box-shadow: 0 4px 14px rgba(0,217,255,.25); }
.hdr-title { font-size: 17px; font-weight: 800; color: var(--t1); letter-spacing: -.3px; }
.hdr-sub { font-size: 11px; color: var(--t3); margin-top: 2px; }
.hdr-badge { font-size: 10px; font-weight: 600; padding: 4px 10px; border-radius: 20px; border: 1px solid var(--line2); color: var(--t3); background: var(--navy3); }
.hdr-badge.live { background: rgba(52,211,153,.10); border-color: rgba(52,211,153,.25); color: #34d399; }

.skill-pill { display: inline-block; background: var(--cyan-d); border: 1px solid var(--cyan-b); color: var(--cyan); font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 20px; margin: 3px 2px; font-family: var(--fm); }
.tech-pill  { display: inline-block; background: rgba(251,191,36,.08); border: 1px solid rgba(251,191,36,.25); color: #fbbf24; font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 20px; margin: 3px 2px; font-family: var(--fm); }

.ai-bubble { background: var(--navy3); border: 1px solid var(--line); border-left: 3px solid var(--cyan); border-radius: 0 var(--r) var(--r) var(--r); padding: 16px 20px; font-size: 13.5px; line-height: 1.75; color: var(--t1); margin: 12px 0; }
.ai-label  { font-size: 10px; font-weight: 700; letter-spacing: .09em; text-transform: uppercase; color: var(--cyan); margin-bottom: 8px; }

.job-card  { background: var(--navy3); border: 1px solid var(--line); border-radius: var(--r); padding: 20px 22px; margin-bottom: 14px; transition: border-color .18s; }
.job-card:hover { border-color: var(--cyan-b); }
.job-title { font-size: 15px; font-weight: 700; color: var(--t1); margin-bottom: 2px; }
.job-company { font-size: 12px; color: var(--t2); margin-bottom: 10px; }
.match-bar-wrap { background: var(--navy5); border-radius: 4px; height: 6px; width: 100%; margin: 6px 0 10px; }
.match-bar { height: 6px; border-radius: 4px; background: linear-gradient(90deg,#007acc,#00d9ff); }
.job-why { font-size: 13px; color: var(--t2); line-height: 1.6; margin-top: 8px; }

.exp-row  { display: flex; gap: 14px; align-items: flex-start; margin-bottom: 12px; }
.exp-dot  { width: 10px; height: 10px; border-radius: 50%; background: var(--cyan); margin-top: 4px; flex-shrink: 0; }
.exp-line { width: 1px; background: var(--line2); position: absolute; }
.exp-title { font-size: 13.5px; font-weight: 600; color: var(--t1); }
.exp-sub   { font-size: 12px; color: var(--t2); margin-top: 2px; }

.sec-hdr { font-size: 12px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--t3); margin: 22px 0 10px; padding-bottom: 6px; border-bottom: 1px solid var(--line); }

.sb-div { height: 1px; background: var(--line); margin: 12px 0; }
.sb-lbl { font-size: 10px; font-weight: 700; letter-spacing: .09em; text-transform: uppercase; color: var(--t3); padding-bottom: 6px; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════
def _groq_key():
    try:
        if hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
            return st.secrets["GROQ_API_KEY"]
    except Exception:
        pass
    return os.getenv("GROQ_API_KEY")


def _github_token():
    try:
        if hasattr(st, "secrets") and "GITHUB_TOKEN" in st.secrets:
            return st.secrets["GITHUB_TOKEN"]
    except Exception:
        pass
    return os.getenv("GITHUB_TOKEN")


def _make_groq_client():
    from groq import Groq
    key = _groq_key()
    if not key:
        st.error("❌ GROQ_API_KEY not found. Add it to your `.env` or `secrets.toml`.")
        st.stop()
    return Groq(api_key=key)


def _llm_chat(client, system: str, user: str, max_tokens: int = 900) -> str:
    for model in ["llama-3.3-70b-versatile", "gemma2-9b-it"]:
        try:
            r = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system",  "content": system},
                    {"role": "user",    "content": user},
                ],
                temperature=0.75,
                max_tokens=max_tokens,
            )
            return r.choices[0].message.content
        except Exception:
            continue
    return "Sorry, I couldn't reach the AI right now. Please try again."


def _pill(text, kind="skill"):
    cls = "skill-pill" if kind == "skill" else "tech-pill"
    return f'<span class="{cls}">{text}</span>'


def _pills_html(items, kind="skill"):
    if not items:
        return '<span style="color:var(--t3);font-size:12px">None found</span>'
    return "".join(_pill(i, kind) for i in items)


def _score_colour(score: int) -> str:
    if score >= 80: return "#34d399"
    if score >= 60: return "#00d9ff"
    if score >= 40: return "#fbbf24"
    return "#f87171"


def init_state():
    defaults = {
        "cv_analysis":     None,
        "github_analysis": None,
        "job_matches":     None,
        "chat_messages":   [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ══════════════════════════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        st.markdown(
            '<div style="padding:20px 16px 14px;border-bottom:1px solid rgba(255,255,255,.06)">'
            '<div style="display:flex;align-items:center;gap:12px">'
            '<div style="width:40px;height:40px;border-radius:12px;background:linear-gradient(135deg,#007acc,#00d9ff);'
            'display:flex;align-items:center;justify-content:center;font-size:20px;box-shadow:0 4px 14px rgba(0,217,255,.25)">🎯</div>'
            '<div>'
            '<div style="font-size:15px;font-weight:800;color:#e8eeff;letter-spacing:-.3px">Career AI</div>'
            '<div style="font-size:10px;color:#00d9ff;background:rgba(0,217,255,.08);padding:2px 8px;'
            'border-radius:20px;border:1px solid rgba(0,217,255,.2);display:inline-block;font-weight:600;margin-top:2px">Phase 1 · MVP</div>'
            '</div></div></div>',
            unsafe_allow_html=True,
        )

        st.markdown("<div style='padding:14px 14px 0'>", unsafe_allow_html=True)

        # API status
        st.markdown('<div class="sb-lbl">Status</div>', unsafe_allow_html=True)
        key_ok = bool(_groq_key())
        gh_ok  = bool(_github_token())
        jobs_ok = os.path.isfile(os.path.join("data", "jobs.csv"))

        c1, c2 = st.columns(2)
        with c1: st.metric("Groq AI",  "🟢 Ready" if key_ok  else "🔴 Missing")
        with c2: st.metric("GitHub",   "🟢" if gh_ok else "⚪ Optional")
        st.metric("Job DB", "🟢 Found" if jobs_ok else "🔴 Not found")

        if not key_ok:
            st.error("GROQ_API_KEY missing.\nAdd to `.env` or `secrets.toml`.")
        if not jobs_ok:
            st.warning("No `data/jobs.csv`.\nSee setup guide below.")

        st.markdown('<div class="sb-div"></div>', unsafe_allow_html=True)

        # Session progress
        st.markdown('<div class="sb-lbl">Your Progress</div>', unsafe_allow_html=True)
        steps = [
            ("📄 CV analyzed",     st.session_state.cv_analysis     is not None),
            ("🐙 GitHub analyzed", st.session_state.github_analysis is not None),
            ("💼 Jobs matched",    st.session_state.job_matches     is not None),
        ]
        for label, done in steps:
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;padding:4px 0;font-size:12.5px;'
                f'color:{"#34d399" if done else "var(--t3)"}">'
                f'{"✅" if done else "⬜"} {label}</div>',
                unsafe_allow_html=True,
            )

        if st.button("🗑 Clear Session", key="sb_clear", use_container_width=True):
            st.session_state.cv_analysis     = None
            st.session_state.github_analysis = None
            st.session_state.job_matches     = None
            st.session_state.chat_messages   = []
            st.rerun()

        st.markdown('<div class="sb-div"></div>', unsafe_allow_html=True)

        # Export
        cv_done  = st.session_state.cv_analysis     is not None
        gh_done  = st.session_state.github_analysis is not None
        job_done = st.session_state.job_matches     is not None
        if cv_done or gh_done or job_done:
            report = {
                "generated_at":    datetime.datetime.now().isoformat(),
                "cv_analysis":     st.session_state.cv_analysis,
                "github_analysis": st.session_state.github_analysis,
                "job_matches":     st.session_state.job_matches,
            }
            st.download_button(
                "📥 Download Report",
                data=json.dumps(report, indent=2, default=str),
                file_name=f"career_report_{datetime.date.today()}.json",
                mime="application/json",
                use_container_width=True,
                key="sb_dl",
            )

        st.markdown('<div class="sb-div"></div>', unsafe_allow_html=True)

        with st.expander("⚙️ Setup Guide"):
            st.markdown("""
**Environment variables**
```
GROQ_API_KEY=gsk_...
GITHUB_TOKEN=ghp_...  # optional
```

**Job database** — download one and save as `data/jobs.csv`
- [Tech Jobs ⭐](https://www.kaggle.com/datasets/andrewmvd/tech-jobs)
- [DS Job Salaries](https://www.kaggle.com/datasets/ruchi798/data-science-job-salaries)
- [LinkedIn Jobs](https://www.kaggle.com/datasets/arjunprasadsarkhel/linkedin-job-postings)

**Run**
```
streamlit run app.py
```
""")
        st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Header
# ══════════════════════════════════════════════════════════════════════════════
def render_header():
    ready = any([
        st.session_state.cv_analysis,
        st.session_state.github_analysis,
        st.session_state.job_matches,
    ])
    st.markdown(
        '<div class="page-hdr">'
        '<div style="display:flex;align-items:center;gap:14px">'
        '<div class="hdr-gem">🎯</div>'
        '<div>'
        '<div class="hdr-title">Career AI Assistant</div>'
        '<div class="hdr-sub">CV · GitHub · Job Matching · Career Chat</div>'
        '</div></div>'
        '<div style="display:flex;gap:8px">'
        + ('<div class="hdr-badge live">● Session Active</div>' if ready
           else '<div class="hdr-badge">○ No Data Yet</div>')
        + '<div class="hdr-badge">Groq · LLaMA 3.3</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Tab 1 – CV Analyzer
# ══════════════════════════════════════════════════════════════════════════════
def tab_cv():
    st.markdown('<div class="sec-hdr">📄 CV Analyzer</div>', unsafe_allow_html=True)
    st.markdown(
        '<p style="color:var(--t2);font-size:13px;margin-bottom:18px">'
        'Upload your PDF CV — the AI will read it and give you a clear, human breakdown '
        'of your skills, experience, and where you stand.</p>',
        unsafe_allow_html=True,
    )

    col_up, col_btn = st.columns([3, 1])
    with col_up:
        uploaded = st.file_uploader("Choose your CV (PDF)", type=["pdf"], key="cv_file")
    with col_btn:
        st.write(""); st.write("")
        go = st.button("🔍 Analyze CV", key="btn_cv", use_container_width=True,
                       disabled=uploaded is None)

    if go and uploaded:
        if not _groq_key():
            return
        with st.spinner("Reading your CV…"):
            try:
                from cv_analyzer import CVAnalyzer
                temp = f"temp_{uploaded.name}"
                with open(temp, "wb") as f:
                    f.write(uploaded.getbuffer())
                result = CVAnalyzer().analyze_cv(temp)
                os.remove(temp)

                if result.get("success"):
                    st.session_state.cv_analysis = result
                else:
                    st.error(f"❌ {result.get('error', 'Unknown error')}")
                    return
            except ImportError:
                st.error("❌ cv_analyzer.py not found.")
                return
            except Exception as e:
                st.error(f"❌ {e}")
                return

    # ── Display ───────────────────────────────────────────────────────────────
    if not st.session_state.cv_analysis:
        st.info("Upload your CV and click **Analyze CV** to get started.")
        return

    a = st.session_state.cv_analysis.get("analysis", {})

    # Handle case where analysis came back as a raw string (shouldn't happen now)
    if isinstance(a, str):
        try:
            a = json.loads(re.sub(r"```(?:json)?", "", a).strip().rstrip("`"))
        except Exception:
            st.markdown(f'<div class="ai-bubble"><div class="ai-label">AI Analysis</div>{a}</div>',
                        unsafe_allow_html=True)
            return

    # Top metrics
    cols = st.columns(3)
    with cols[0]: st.metric("Seniority",  a.get("seniority_level", "—"))
    with cols[1]: st.metric("Experience", f"{a.get('experience_years', '—')} yrs")
    with cols[2]: st.metric("Skills found", len(a.get("skills", [])))

    # AI summary bubble
    if a.get("summary"):
        st.markdown(
            f'<div class="ai-bubble"><div class="ai-label">🤖 AI Summary</div>{a["summary"]}</div>',
            unsafe_allow_html=True,
        )

    # Skills
    skills = a.get("skills", [])
    techs  = a.get("technologies", [])
    if skills or techs:
        st.markdown('<div class="sec-hdr">Skills & Technologies</div>', unsafe_allow_html=True)
        st.markdown(_pills_html(skills, "skill") + _pills_html(techs, "tech"),
                    unsafe_allow_html=True)

    # Experience
    exp = a.get("experience", [])
    if exp:
        st.markdown('<div class="sec-hdr">Experience</div>', unsafe_allow_html=True)
        for e in exp:
            st.markdown(
                f'<div class="exp-row">'
                f'<div class="exp-dot"></div>'
                f'<div>'
                f'<div class="exp-title">{e.get("title","—")}</div>'
                f'<div class="exp-sub">{e.get("company","—")}  ·  {e.get("duration","")}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

    # Education
    edu = a.get("education", [])
    if edu:
        st.markdown('<div class="sec-hdr">Education</div>', unsafe_allow_html=True)
        for e in edu:
            st.markdown(
                f'<div class="exp-row">'
                f'<div class="exp-dot" style="background:#34d399"></div>'
                f'<div>'
                f'<div class="exp-title">{e.get("degree","")} {e.get("field","")}</div>'
                f'<div class="exp-sub">{e.get("school","—")}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

    # Strengths / improvement areas
    c1, c2 = st.columns(2)
    with c1:
        strengths = a.get("strengths", [])
        if strengths:
            st.markdown('<div class="sec-hdr">💪 Strengths</div>', unsafe_allow_html=True)
            for s in strengths:
                st.markdown(f'<div style="color:var(--t2);font-size:13px;padding:3px 0">✅ {s}</div>',
                            unsafe_allow_html=True)
    with c2:
        gaps = a.get("improvement_areas", [])
        if gaps:
            st.markdown('<div class="sec-hdr">🎯 Areas to Improve</div>', unsafe_allow_html=True)
            for g in gaps:
                st.markdown(f'<div style="color:var(--t2);font-size:13px;padding:3px 0">→ {g}</div>',
                            unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Tab 2 – GitHub Analyzer
# ══════════════════════════════════════════════════════════════════════════════
def tab_github():
    st.markdown('<div class="sec-hdr">🐙 GitHub Profile Analysis</div>', unsafe_allow_html=True)
    st.markdown(
        '<p style="color:var(--t2);font-size:13px;margin-bottom:18px">'
        'Enter any public GitHub username and get a plain-English read of their '
        'coding activity, language strengths, and profile score.</p>',
        unsafe_allow_html=True,
    )

    col_in, col_btn = st.columns([3, 1])
    with col_in:
        username = st.text_input("GitHub Username", placeholder="e.g. torvalds", key="gh_username")
    with col_btn:
        st.write(""); st.write("")
        go = st.button("🔍 Analyze", key="btn_gh", use_container_width=True,
                       disabled=not (username or "").strip())

    if go and (username or "").strip():
        if not _groq_key():
            return
        with st.spinner(f"Fetching @{username.strip()}…"):
            try:
                from github_analyzer import GitHubAnalyzer
                result = GitHubAnalyzer().analyze_github_profile(username.strip())
                if result.get("success"):
                    st.session_state.github_analysis = result
                else:
                    st.error(f"❌ {result.get('error', 'Profile not found or is private.')}")
                    st.info("Make sure the username is spelled correctly and the profile is public.")
                    return
            except ImportError:
                st.error("❌ github_analyzer.py not found.")
                return
            except Exception as e:
                st.error(f"❌ {e}")
                return

    # ── Display ───────────────────────────────────────────────────────────────
    if not st.session_state.github_analysis:
        st.info("Enter a username and click **Analyze** to get started.")
        return

    data     = st.session_state.github_analysis
    profile  = data.get("profile", {})
    analysis = data.get("analysis", {})

    # Handle raw string analysis
    if isinstance(analysis, str):
        try:
            analysis = json.loads(re.sub(r"```(?:json)?", "", analysis).strip().rstrip("`"))
        except Exception:
            pass

    # Metrics row
    cols = st.columns(4)
    with cols[0]: st.metric("Followers",    profile.get("followers", 0))
    with cols[1]: st.metric("Public Repos", profile.get("public_repos", 0))
    with cols[2]: st.metric("Following",    profile.get("following", 0))
    score = (analysis.get("profile_score") or analysis.get("score") or "—") if isinstance(analysis, dict) else "—"
    with cols[3]: st.metric("Profile Score", f"{score}/100" if str(score).isdigit() else score)

    # AI narrative
    summary = None
    if isinstance(analysis, dict):
        summary = (analysis.get("summary") or analysis.get("overall_assessment")
                   or analysis.get("analysis") or analysis.get("narrative"))
    elif isinstance(analysis, str):
        summary = analysis

    if summary:
        st.markdown(
            f'<div class="ai-bubble"><div class="ai-label">🤖 AI Assessment</div>{summary}</div>',
            unsafe_allow_html=True,
        )

    # Languages bar chart
    langs = profile.get("languages", {})
    if langs:
        st.markdown('<div class="sec-hdr">Top Languages</div>', unsafe_allow_html=True)
        st.bar_chart(langs)

    # Recommendations
    recs = None
    if isinstance(analysis, dict):
        recs = analysis.get("recommendations") or analysis.get("suggestions")
    if recs and isinstance(recs, list):
        st.markdown('<div class="sec-hdr">💡 Recommendations</div>', unsafe_allow_html=True)
        for r in recs:
            st.markdown(f'<div style="color:var(--t2);font-size:13px;padding:4px 0">→ {r}</div>',
                        unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Tab 3 – Job Matcher
# ══════════════════════════════════════════════════════════════════════════════
def tab_jobs():
    st.markdown('<div class="sec-hdr">💼 Job Matcher</div>', unsafe_allow_html=True)
    st.markdown(
        '<p style="color:var(--t2);font-size:13px;margin-bottom:18px">'
        'Fill in your profile and we\'ll search the job database, score every match, '
        'and explain in plain English why each role fits you.</p>',
        unsafe_allow_html=True,
    )

    jobs_ok = os.path.isfile(os.path.join("data", "jobs.csv"))
    if not jobs_ok:
        st.warning(
            "**Job database not found.**  \n"
            "Download a CSV from Kaggle (e.g. [Tech Jobs](https://www.kaggle.com/datasets/andrewmvd/tech-jobs)) "
            "and save it as `data/jobs.csv`. See the Setup Guide in the sidebar."
        )

    col1, col2 = st.columns(2)
    with col1:
        skills_raw = st.text_area("Your Skills (one per line)",
                                  placeholder="Python\nReact\nPostgreSQL", height=120, key="js_skills")
        exp = st.number_input("Years of Experience", 0, 50, 2, key="js_exp")
    with col2:
        seniority = st.selectbox("Seniority Level",
                                 ["Junior", "Mid-Level", "Senior", "Lead", "Principal"], key="js_sen")
        roles = st.multiselect("Interested Roles",
                               ["Full Stack Developer", "Backend Engineer", "Frontend Developer",
                                "Data Scientist", "ML Engineer", "DevOps Engineer",
                                "Product Manager", "Mobile Developer", "Cloud Architect"],
                               key="js_roles")

    go = st.button("🔍 Find My Best Jobs", key="btn_jobs", disabled=not jobs_ok)

    if go:
        if not _groq_key():
            return
        skills = [s.strip() for s in skills_raw.split("\n") if s.strip()]
        if not skills:
            st.warning("Please enter at least one skill.")
            return

        with st.spinner("Scanning job database and matching with AI…"):
            try:
                from job_matcher import JobMatcher
                profile = {
                    "skills": skills,
                    "experience_years": int(exp),
                    "seniority_level": seniority.lower().replace("-", "_"),
                    "interested_roles": roles,
                }
                result = JobMatcher().match_jobs(profile)

                if result.get("success"):
                    st.session_state.job_matches = result
                else:
                    st.error(f"❌ {result.get('error', 'Matching failed.')}")
                    return
            except ImportError:
                st.error("❌ job_matcher.py not found.")
                return
            except Exception as e:
                st.error(f"❌ {e}")
                return

    # ── Display ───────────────────────────────────────────────────────────────
    if not st.session_state.job_matches:
        if jobs_ok:
            st.info("Fill in your profile and click **Find My Best Jobs**.")
        return

    result  = st.session_state.job_matches
    matches = result.get("matches", [])
    total   = result.get("total_in_db", "?")

    if not matches:
        st.warning("No matches found. Try broadening your skills or interests.")
        return

    st.markdown(
        f'<div class="ai-bubble"><div class="ai-label">Results</div>'
        f'Found <strong>{len(matches)}</strong> great matches from <strong>{total}</strong> jobs in the database. '
        f'Here they are, ranked by how well they fit your profile.</div>',
        unsafe_allow_html=True,
    )

    for i, job in enumerate(matches):
        if not isinstance(job, dict):
            continue

        score   = int(job.get("match_score", 0))
        colour  = _score_colour(score)
        matched = job.get("matched_skills", [])
        missing = job.get("missing_skills", [])
        why     = job.get("why_good_fit", "")
        salary  = job.get("salary", "")

        matched_html = "".join(_pill(s, "skill") for s in matched) if matched else ""
        missing_html = "".join(
            f'<span style="display:inline-block;background:rgba(248,113,113,.08);border:1px solid rgba(248,113,113,.25);'
            f'color:#f87171;font-size:11px;font-weight:600;padding:3px 10px;border-radius:20px;margin:3px 2px;'
            f'font-family:var(--fm)">{s}</span>'
            for s in missing
        ) if missing else ""

        st.markdown(f"""
<div class="job-card">
  <div style="display:flex;justify-content:space-between;align-items:flex-start">
    <div>
      <div class="job-title">{job.get('title','—')}</div>
      <div class="job-company">🏢 {job.get('company','—')}
        {"  ·  📍 " + job.get('location','') if job.get('location') else ""}
        {"  ·  💰 " + salary if salary and salary != "N/A" else ""}
      </div>
    </div>
    <div style="text-align:right;flex-shrink:0;margin-left:16px">
      <div style="font-size:22px;font-weight:800;color:{colour}">{score}%</div>
      <div style="font-size:10px;color:var(--t3)">match</div>
    </div>
  </div>
  <div class="match-bar-wrap"><div class="match-bar" style="width:{score}%;background:linear-gradient(90deg,#007acc,{colour})"></div></div>
  {"<div style='margin-bottom:6px'><span style='font-size:10px;font-weight:700;text-transform:uppercase;color:var(--t3);letter-spacing:.07em'>Matched skills  </span>" + matched_html + "</div>" if matched_html else ""}
  {"<div style='margin-bottom:8px'><span style='font-size:10px;font-weight:700;text-transform:uppercase;color:var(--t3);letter-spacing:.07em'>Skills to learn  </span>" + missing_html + "</div>" if missing_html else ""}
  {"<div class='job-why'>💬 " + why + "</div>" if why else ""}
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Tab 4 – Career Chat
# ══════════════════════════════════════════════════════════════════════════════
def tab_chat():
    st.markdown('<div class="sec-hdr">💬 Career Chat</div>', unsafe_allow_html=True)
    st.markdown(
        '<p style="color:var(--t2);font-size:13px;margin-bottom:18px">'
        'Ask me anything about your career — interview tips, salary negotiation, '
        'which skills to learn next, how to improve your CV, you name it. '
        'If you\'ve run analyses above, I\'ll use that context automatically.</p>',
        unsafe_allow_html=True,
    )

    # Starter chips
    if not st.session_state.chat_messages:
        starters = [
            "How can I improve my CV?",
            "What skills should I learn next?",
            "How do I negotiate my salary?",
            "Am I ready for a senior role?",
        ]
        cols = st.columns(len(starters))
        for col, q in zip(cols, starters):
            with col:
                if st.button(q, key=f"chip_{q[:15]}", use_container_width=True):
                    st.session_state.chat_messages.append({"role": "user", "content": q})
                    st.rerun()

    # Render conversation
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "🎯"):
            st.markdown(msg["content"])

    # Input
    user_input = st.chat_input("Ask me anything about your career…")
    if user_input and user_input.strip():
        st.session_state.chat_messages.append({"role": "user", "content": user_input.strip()})

        # Build context from session data
        context_parts = []
        if st.session_state.cv_analysis:
            a = st.session_state.cv_analysis.get("analysis", {})
            if isinstance(a, dict):
                context_parts.append(
                    f"CV Summary: {a.get('summary', '')} | "
                    f"Skills: {', '.join(a.get('skills', [])[:10])} | "
                    f"Seniority: {a.get('seniority_level', '')} | "
                    f"Experience: {a.get('experience_years', '')} years"
                )
        if st.session_state.github_analysis:
            p = st.session_state.github_analysis.get("profile", {})
            context_parts.append(
                f"GitHub: {p.get('public_repos', 0)} repos, "
                f"{p.get('followers', 0)} followers, "
                f"top languages: {', '.join(list(p.get('languages', {}).keys())[:5])}"
            )
        if st.session_state.job_matches:
            m = st.session_state.job_matches.get("matches", [])
            if m and isinstance(m[0], dict):
                top = m[0]
                context_parts.append(
                    f"Top job match: {top.get('title', '')} at {top.get('company', '')} "
                    f"({top.get('match_score', '')}% match)"
                )

        context_block = "\n".join(context_parts)
        system = (
            "You are a friendly, expert career advisor. You give honest, specific, "
            "actionable advice in a warm, conversational tone — like a smart mentor, not a robot. "
            "Keep answers focused and practical. Use bullet points when listing more than 3 things. "
            "Never say 'As an AI' or 'I cannot'. "
            + (f"\n\nUser context from their analyses:\n{context_block}" if context_block else "")
        )

        # Build history (last 10 messages)
        history = st.session_state.chat_messages[-10:]
        messages_for_api = [{"role": "system", "content": system}]
        for m in history:
            messages_for_api.append({"role": m["role"], "content": m["content"]})

        with st.chat_message("assistant", avatar="🎯"):
            with st.spinner("Thinking…"):
                try:
                    client = _make_groq_client()
                    r = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=messages_for_api,
                        temperature=0.75,
                        max_tokens=700,
                    )
                    reply = r.choices[0].message.content
                except Exception as e:
                    reply = f"Sorry, something went wrong: {e}"
                st.markdown(reply)
                st.session_state.chat_messages.append({"role": "assistant", "content": reply})


# ══════════════════════════════════════════════════════════════════════════════
# Tab 5 – Full Assessment
# ══════════════════════════════════════════════════════════════════════════════
def tab_assessment():
    st.markdown('<div class="sec-hdr">📊 Full Career Assessment</div>', unsafe_allow_html=True)

    cv_done  = st.session_state.cv_analysis     is not None
    gh_done  = st.session_state.github_analysis is not None
    job_done = st.session_state.job_matches     is not None

    if not any([cv_done, gh_done, job_done]):
        st.info("Complete at least one analysis in the other tabs first, then come back here for your full report.")
        return

    # Progress indicators
    cols = st.columns(3)
    with cols[0]: st.metric("CV Analysis",     "✅ Done" if cv_done  else "⬜ Pending")
    with cols[1]: st.metric("GitHub Analysis", "✅ Done" if gh_done  else "⬜ Pending")
    with cols[2]: st.metric("Job Matches",     "✅ Done" if job_done else "⬜ Pending")

    if st.button("✨ Generate AI Narrative Report", key="btn_report"):
        client = _make_groq_client()

        # Gather data
        parts = []
        if cv_done:
            a = st.session_state.cv_analysis.get("analysis", {})
            if isinstance(a, dict):
                parts.append(
                    f"CV: seniority={a.get('seniority_level')}, "
                    f"experience={a.get('experience_years')} years, "
                    f"skills={a.get('skills', [])}, "
                    f"summary={a.get('summary')}"
                )
        if gh_done:
            p = st.session_state.github_analysis.get("profile", {})
            parts.append(
                f"GitHub: {p.get('public_repos')} repos, "
                f"languages={list(p.get('languages', {}).keys())}"
            )
        if job_done:
            m = st.session_state.job_matches.get("matches", [])
            if m and isinstance(m[0], dict):
                top3 = [f"{j.get('title')} at {j.get('company')} ({j.get('match_score')}%)"
                        for j in m[:3] if isinstance(j, dict)]
                parts.append(f"Top job matches: {', '.join(top3)}")

        prompt = (
            "Write a warm, conversational career assessment report for this person. "
            "Cover: where they are now, what their data says about their strengths, "
            "what opportunities suit them best, and 3-4 concrete next steps. "
            "Write like a mentor talking to a friend — specific, honest, encouraging. "
            "Use markdown formatting with headers.\n\n"
            "Data:\n" + "\n".join(parts)
        )

        with st.spinner("Writing your personalised report…"):
            report_text = _llm_chat(client, "You are a career advisor writing a personal report.", prompt, 1000)

        st.markdown(
            f'<div class="ai-bubble"><div class="ai-label">🤖 Your Career Report</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown(report_text)

        # Download
        st.download_button(
            "📥 Download Full Report (JSON)",
            data=json.dumps({
                "generated_at":    datetime.datetime.now().isoformat(),
                "narrative":       report_text,
                "cv_analysis":     st.session_state.cv_analysis,
                "github_analysis": st.session_state.github_analysis,
                "job_matches":     st.session_state.job_matches,
            }, indent=2, default=str),
            file_name=f"career_report_{datetime.date.today()}.json",
            mime="application/json",
            key="dl_full",
        )
    else:
        # Show existing data nicely even before generating report
        if cv_done:
            a = st.session_state.cv_analysis.get("analysis", {})
            if isinstance(a, dict) and a.get("summary"):
                st.markdown('<div class="sec-hdr">📄 CV Summary</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="ai-bubble">{a["summary"]}</div>', unsafe_allow_html=True)

        if job_done:
            matches = st.session_state.job_matches.get("matches", [])
            if matches and isinstance(matches[0], dict):
                st.markdown('<div class="sec-hdr">💼 Your Top 3 Job Matches</div>', unsafe_allow_html=True)
                for j in matches[:3]:
                    st.markdown(
                        f'<div style="display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid var(--line)">'
                        f'<div style="font-size:22px;font-weight:800;color:{_score_colour(int(j.get("match_score",0)))}">'
                        f'{j.get("match_score","?")}%</div>'
                        f'<div><div style="font-size:13.5px;font-weight:600;color:var(--t1)">{j.get("title","—")}</div>'
                        f'<div style="font-size:12px;color:var(--t2)">{j.get("company","—")}</div></div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════
def main():
    inject_css()
    init_state()
    render_sidebar()
    render_header()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📄  CV Analyzer",
        "🐙  GitHub Profile",
        "💼  Job Matcher",
        "💬  Career Chat",
        "📊  Full Assessment",
    ])

    with tab1: tab_cv()
    with tab2: tab_github()
    with tab3: tab_jobs()
    with tab4: tab_chat()
    with tab5: tab_assessment()


if __name__ == "__main__":
    main()