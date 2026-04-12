"""
Career AI Assistant  –  Phase 1
================================
Single, clean entry-point.  Replaces the broken double-app file.

Tabs:
  1. 📄  CV Analyzer        – PDF upload → LLM skill extraction
  2. 🐙  GitHub Profile     – GitHub API + LLM analysis
  3. 💼  Job Matcher        – Kaggle CSV job search
  4. 📊  Full Assessment    – Combined report

All logic delegates to:
  cv_analyzer.py  ·  github_analyzer.py  ·  job_matcher.py

Requires:
  GROQ_API_KEY  in st.secrets  OR  .env file
  GITHUB_TOKEN  (optional, for higher API rate-limits)
"""

import os
import json
import datetime
import csv

import streamlit as st
from dotenv import load_dotenv

# ── Load .env (local dev) ──────────────────────────────────────────────────
load_dotenv()

# ══════════════════════════════════════════════════════════════════════════════
# Page config  ← must be the FIRST Streamlit call
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Career AI Assistant",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# CSS  –  deep navy / cyan accent design
# ══════════════════════════════════════════════════════════════════════════════
def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --navy:   #080c18;
  --navy2:  #0d1326;
  --navy3:  #111829;
  --navy4:  #172035;
  --navy5:  #1e2d47;
  --line:   rgba(255,255,255,0.06);
  --line2:  rgba(255,255,255,0.10);
  --t1:     #e8eeff;
  --t2:     #7a8ab0;
  --t3:     #3d4a6a;
  --cyan:   #00d9ff;
  --cyan2:  #00b3d4;
  --cyan-d: rgba(0,217,255,0.08);
  --cyan-b: rgba(0,217,255,0.20);
  --sage:   #34d399;
  --amber:  #fbbf24;
  --rose:   #f87171;
  --ff: 'Plus Jakarta Sans', system-ui, sans-serif;
  --fm: 'JetBrains Mono', monospace;
  --r: 14px; --rs: 9px;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body,
[data-testid="stApp"],
[data-testid="stAppViewContainer"],
.main {
  background: var(--navy) !important;
  font-family: var(--ff) !important;
  color: var(--t1) !important;
}

/* hide streamlit chrome */
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
  min-width: 270px !important; max-width: 270px !important;
}
[data-testid="stSidebar"] > div:first-child { padding: 0 !important; }
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span { color: var(--t2) !important; font-size: 12.5px !important; }
[data-testid="stSidebar"] .stButton > button {
  background: transparent !important;
  border: 1px solid var(--line2) !important;
  border-radius: var(--rs) !important;
  color: var(--t2) !important;
  font-family: var(--ff) !important;
  font-size: 12.5px !important; font-weight: 500 !important;
  padding: 9px 14px !important; width: 100% !important;
  transition: all 0.18s !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
  background: var(--navy4) !important;
  border-color: var(--cyan-b) !important;
  color: var(--t1) !important;
}
[data-testid="stSidebar"] [data-testid="stMetricLabel"] { color: var(--t3) !important; font-size: 11px !important; }
[data-testid="stSidebar"] [data-testid="stMetricValue"] { color: var(--t1) !important; font-size: 16px !important; }

/* ── Tabs ── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
  background: var(--navy2) !important;
  border-bottom: 1px solid var(--line) !important;
  padding: 0 28px !important; gap: 4px !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
  background: transparent !important;
  border: none !important;
  color: var(--t2) !important;
  font-family: var(--ff) !important;
  font-size: 13px !important; font-weight: 600 !important;
  padding: 14px 18px !important;
  border-bottom: 2px solid transparent !important;
  transition: all 0.18s !important;
}
[data-testid="stTabs"] [data-baseweb="tab"]:hover { color: var(--t1) !important; }
[data-testid="stTabs"] [aria-selected="true"] {
  color: var(--cyan) !important;
  border-bottom-color: var(--cyan) !important;
}
[data-testid="stTabPanel"] {
  background: transparent !important;
  padding: 28px !important;
}

/* ── Generic inputs ── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stNumberInput"] input {
  background: var(--navy3) !important;
  border: 1px solid var(--line2) !important;
  border-radius: var(--r) !important;
  color: var(--t1) !important;
  font-family: var(--ff) !important;
  font-size: 13.5px !important;
  caret-color: var(--cyan) !important;
  transition: border-color 0.18s, box-shadow 0.18s !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
  border-color: var(--cyan) !important;
  box-shadow: 0 0 0 2px var(--cyan-d) !important;
  outline: none !important;
}
[data-testid="stTextInput"] label,
[data-testid="stTextArea"] label,
[data-testid="stNumberInput"] label,
[data-testid="stSelectbox"] label,
[data-testid="stMultiSelect"] label {
  color: var(--t2) !important;
  font-size: 12.5px !important; font-weight: 600 !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
  background: var(--navy3) !important;
  border: 1px dashed var(--cyan-b) !important;
  border-radius: var(--r) !important;
  padding: 20px !important;
}
[data-testid="stFileUploader"] label { color: var(--t2) !important; }

/* ── Selectbox / multiselect ── */
[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stMultiSelect"] [data-baseweb="select"] > div {
  background: var(--navy3) !important;
  border: 1px solid var(--line2) !important;
  border-radius: var(--r) !important;
  color: var(--t1) !important;
}

/* ── Buttons (main area) ── */
.stButton > button {
  background: linear-gradient(135deg, #007acc, #00d9ff) !important;
  border: none !important;
  border-radius: var(--r) !important;
  color: var(--navy) !important;
  font-family: var(--ff) !important;
  font-size: 13.5px !important; font-weight: 700 !important;
  padding: 11px 22px !important;
  transition: all 0.2s !important;
  box-shadow: 0 4px 14px rgba(0,217,255,0.25) !important;
}
.stButton > button:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 6px 20px rgba(0,217,255,0.4) !important;
}
.stButton > button:active { transform: translateY(0) !important; }

/* ── Status alerts ── */
[data-testid="stAlert"][data-baseweb="notification"] {
  background: var(--navy3) !important;
  border-radius: var(--r) !important;
  border: 1px solid var(--line2) !important;
  font-size: 12.5px !important;
}

/* ── Metrics ── */
[data-testid="stMetric"] {
  background: var(--navy3) !important;
  border: 1px solid var(--line) !important;
  border-radius: var(--r) !important;
  padding: 14px 18px !important;
}
[data-testid="stMetricLabel"] { color: var(--t3) !important; font-size: 11px !important; }
[data-testid="stMetricValue"] { color: var(--t1) !important; font-size: 22px !important; }

/* ── JSON display ── */
[data-testid="stJson"] {
  background: var(--navy3) !important;
  border: 1px solid var(--line) !important;
  border-radius: var(--r) !important;
}

/* ── Expanders ── */
[data-testid="stExpander"] {
  background: var(--navy3) !important;
  border: 1px solid var(--line) !important;
  border-radius: var(--r) !important;
}
[data-testid="stExpander"] summary { color: var(--t2) !important; font-size: 12.5px !important; }

/* ── Progress bar ── */
.stProgress > div > div { background: var(--cyan) !important; }

/* ── Download button ── */
[data-testid="stDownloadButton"] > button {
  background: transparent !important;
  border: 1px solid var(--line2) !important;
  box-shadow: none !important;
  color: var(--t2) !important;
}
[data-testid="stDownloadButton"] > button:hover {
  border-color: var(--cyan-b) !important;
  color: var(--cyan) !important;
  transform: none !important;
  box-shadow: none !important;
}

/* ── Bar chart axis ── */
.stVegaLiteChart svg text { fill: var(--t2) !important; }

/* ── Divider ── */
hr { border-color: var(--line) !important; }

/* ── Markdown headings ── */
[data-testid="stMarkdownContainer"] h3 {
  color: var(--cyan) !important;
  font-size: 14px !important; font-weight: 700 !important;
  margin: 18px 0 8px !important;
}
[data-testid="stMarkdownContainer"] p { color: var(--t2) !important; font-size: 13px !important; }

/* ── sb helpers ── */
.sb-div  { height: 1px; background: var(--line); margin: 12px 0; }
.sb-lbl  {
  font-size: 10px; font-weight: 700; letter-spacing: .09em;
  text-transform: uppercase; color: var(--t3); padding-bottom: 6px;
}
.sb-dot  { width:7px;height:7px;border-radius:50%; }
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}

/* ── Spinner ── */
[data-testid="stSpinner"] p { color: var(--t2) !important; }

/* ── page header ── */
.page-hdr {
  background: var(--navy2);
  border-bottom: 1px solid var(--line);
  padding: 0 28px; height: 64px;
  display: flex; align-items: center; justify-content: space-between;
}
.hdr-left { display: flex; align-items: center; gap: 14px; }
.hdr-gem  {
  width: 42px; height: 42px; border-radius: 12px;
  background: linear-gradient(135deg,#007acc,#00d9ff);
  display: flex; align-items: center; justify-content: center;
  font-size: 20px; box-shadow: 0 4px 14px rgba(0,217,255,.25);
}
.hdr-title { font-size: 17px; font-weight: 800; color: var(--t1); letter-spacing: -.3px; }
.hdr-sub   { font-size: 11px; color: var(--t3); margin-top: 2px; }
.hdr-badge {
  font-size: 10px; font-weight: 600; padding: 4px 10px;
  border-radius: 20px; border: 1px solid var(--line2);
  color: var(--t3); background: var(--navy3);
}
.hdr-badge.live {
  background: rgba(52,211,153,.10); border-color: rgba(52,211,153,.25); color: var(--sage);
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Groq key helper
# ══════════════════════════════════════════════════════════════════════════════
def _groq_key() -> str | None:
    """Return the Groq API key from secrets or env, or None."""
    try:
        if hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
            return st.secrets["GROQ_API_KEY"]
    except Exception:
        pass
    return os.getenv("GROQ_API_KEY")


def _github_token() -> str | None:
    try:
        if hasattr(st, "secrets") and "GITHUB_TOKEN" in st.secrets:
            return st.secrets["GITHUB_TOKEN"]
    except Exception:
        pass
    return os.getenv("GITHUB_TOKEN")


# ══════════════════════════════════════════════════════════════════════════════
# Session state bootstrap
# ══════════════════════════════════════════════════════════════════════════════
def init_state():
    defaults = {
        "cv_analysis":     None,
        "github_analysis": None,
        "job_matches":     None,
        "chat_history":    [],   # for potential future chatbot extension
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ══════════════════════════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        # Logo block
        st.markdown(
            '<div style="padding:20px 16px 14px;border-bottom:1px solid rgba(255,255,255,.06)">'
            '<div style="display:flex;align-items:center;gap:12px">'
            '<div style="width:40px;height:40px;border-radius:12px;'
            'background:linear-gradient(135deg,#007acc,#00d9ff);'
            'display:flex;align-items:center;justify-content:center;font-size:20px;'
            'box-shadow:0 4px 14px rgba(0,217,255,.25)">🎯</div>'
            '<div>'
            '<div style="font-size:15px;font-weight:800;color:#e8eeff;letter-spacing:-.3px">Career AI</div>'
            '<div style="font-size:10px;color:#00d9ff;background:rgba(0,217,255,.08);'
            'padding:2px 8px;border-radius:20px;border:1px solid rgba(0,217,255,.2);'
            'display:inline-block;font-weight:600;margin-top:2px">Phase 1 · MVP</div>'
            '</div></div></div>',
            unsafe_allow_html=True,
        )

        st.markdown("<div style='padding:14px 14px 0'>", unsafe_allow_html=True)

        # API status
        st.markdown('<div class="sb-lbl">API Status</div>', unsafe_allow_html=True)
        key_ok   = bool(_groq_key())
        gh_ok    = bool(_github_token())
        c1, c2   = st.columns(2)
        with c1:
            st.metric("Groq",   "🟢" if key_ok else "🔴")
        with c2:
            st.metric("GitHub", "🟢" if gh_ok  else "⚪")

        if not key_ok:
            st.error("❌ GROQ_API_KEY missing\nAdd to .env or secrets.toml")

        st.markdown('<div class="sb-div"></div>', unsafe_allow_html=True)

        # Session data
        st.markdown('<div class="sb-lbl">Session Data</div>', unsafe_allow_html=True)
        cv_done  = st.session_state.cv_analysis     is not None
        gh_done  = st.session_state.github_analysis is not None
        job_done = st.session_state.job_matches     is not None
        c1, c2   = st.columns(2)
        with c1:
            st.metric("CV",     "✅" if cv_done  else "—")
            st.metric("GitHub", "✅" if gh_done  else "—")
        with c2:
            st.metric("Jobs",   "✅" if job_done else "—")

        if st.button("🗑 Clear Session", key="sb_clear", use_container_width=True):
            st.session_state.cv_analysis     = None
            st.session_state.github_analysis = None
            st.session_state.job_matches     = None
            st.rerun()

        st.markdown('<div class="sb-div"></div>', unsafe_allow_html=True)

        # Export
        st.markdown('<div class="sb-lbl">Export</div>', unsafe_allow_html=True)
        if cv_done or gh_done or job_done:
            report = {
                "generated_at": datetime.datetime.now().isoformat(),
                "cv_analysis":     st.session_state.cv_analysis,
                "github_analysis": st.session_state.github_analysis,
                "job_matches":     st.session_state.job_matches,
            }
            st.download_button(
                "📥 Download Report (JSON)",
                data=json.dumps(report, indent=2, default=str),
                file_name="career_report.json",
                mime="application/json",
                use_container_width=True,
                key="sb_dl",
            )
        else:
            st.caption("Complete an analysis to export.")

        st.markdown('<div class="sb-div"></div>', unsafe_allow_html=True)

        # Setup help
        with st.expander("⚙️ Setup Guide", expanded=False):
            st.markdown("""
**1. Environment variables**
```
GROQ_API_KEY=gsk_...
GITHUB_TOKEN=ghp_...  # optional
```

**2. Job database**
Download from Kaggle → save as `data/jobs.csv`
- [Tech Jobs ⭐](https://www.kaggle.com/datasets/andrewmvd/tech-jobs)
- [Data Science Salaries](https://www.kaggle.com/datasets/ruchi798/data-science-job-salaries)
- [LinkedIn Jobs](https://www.kaggle.com/datasets/arjunprasadsarkhel/linkedin-job-postings)

**3. Run**
```
streamlit run app.py
```
""")

        st.markdown(
            '<div class="sb-div"></div>'
            '<div style="font-size:10px;color:#3d4a6a;padding-bottom:12px">'
            'Phase 1 MVP · Groq · LLaMA 3.3-70b'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Page header
# ══════════════════════════════════════════════════════════════════════════════
def render_header():
    cv_done  = st.session_state.cv_analysis     is not None
    gh_done  = st.session_state.github_analysis is not None
    job_done = st.session_state.job_matches     is not None
    ready    = cv_done or gh_done or job_done

    st.markdown(
        '<div class="page-hdr">'
        '<div class="hdr-left">'
        '<div class="hdr-gem">🎯</div>'
        '<div>'
        '<div class="hdr-title">Career AI Assistant</div>'
        '<div class="hdr-sub">CV · GitHub · Job Matching · Full Assessment</div>'
        '</div></div>'
        '<div style="display:flex;gap:8px">'
        + ('<div class="hdr-badge live">● Session Active</div>' if ready
           else '<div class="hdr-badge">○ No Data Yet</div>')
        + '<div class="hdr-badge">Phase 1 · MVP</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Tab 1 – CV Analyzer
# ══════════════════════════════════════════════════════════════════════════════
def tab_cv():
    st.markdown("### 📄 CV Analyzer")
    st.markdown(
        '<p>Upload your CV as a PDF and the AI will extract your skills, '
        'experience level, education, and career highlights.</p>',
        unsafe_allow_html=True,
    )

    col_up, col_btn = st.columns([3, 1])
    with col_up:
        uploaded = st.file_uploader(
            "Choose your CV (PDF)",
            type=["pdf"],
            key="cv_file",
            help="Max 10 MB · PDF only",
        )
    with col_btn:
        st.write("")  # vertical spacing
        st.write("")
        analyze = st.button("🔍 Analyze CV", key="btn_cv", use_container_width=True,
                            disabled=uploaded is None)

    if analyze and uploaded:
        if not _groq_key():
            st.error("❌ GROQ_API_KEY not found. Add it to your .env or secrets.toml.")
            return

        with st.spinner("Analyzing your CV with AI…"):
            try:
                from cv_analyzer import CVAnalyzer

                temp_path = f"temp_{uploaded.name}"
                with open(temp_path, "wb") as f:
                    f.write(uploaded.getbuffer())

                analyzer = CVAnalyzer()
                result   = analyzer.analyze_cv(temp_path)

                os.remove(temp_path)

                if result.get("success"):
                    st.session_state.cv_analysis = result
                    st.success("✅ CV analyzed successfully!")
                else:
                    st.error(f"❌ {result.get('error', 'Unknown error')}")
                    return
            except ImportError:
                st.error("❌ cv_analyzer.py not found in project directory.")
                return
            except Exception as e:
                st.error(f"❌ Error processing file: {e}")
                return

    # Display result
    if st.session_state.cv_analysis:
        analysis = st.session_state.cv_analysis.get("analysis", {})
        st.markdown("### Analysis Results")

        # Try to show nicely if it's a dict, else raw JSON
        if isinstance(analysis, dict):
            cols = st.columns(3)
            skill_count = len(analysis.get("skills", []))
            exp_years   = analysis.get("experience_years", analysis.get("years_of_experience", "—"))
            seniority   = analysis.get("seniority_level", analysis.get("level", "—"))
            with cols[0]: st.metric("Skills Found",      skill_count)
            with cols[1]: st.metric("Experience (yrs)",  exp_years)
            with cols[2]: st.metric("Seniority Level",   seniority)

        with st.expander("📋 Full JSON Analysis", expanded=True):
            st.json(analysis)
    else:
        st.info("Upload a PDF and click **Analyze CV** to get started.")


# ══════════════════════════════════════════════════════════════════════════════
# Tab 2 – GitHub Analyzer
# ══════════════════════════════════════════════════════════════════════════════
def tab_github():
    st.markdown("### 🐙 GitHub Profile Analysis")
    st.markdown(
        '<p>Enter a public GitHub username to get an AI-powered assessment of '
        'coding activity, languages, and profile strength.</p>',
        unsafe_allow_html=True,
    )

    col_in, col_btn = st.columns([3, 1])
    with col_in:
        username = st.text_input(
            "GitHub Username",
            placeholder="e.g. torvalds",
            key="gh_username",
        )
    with col_btn:
        st.write("")
        st.write("")
        analyze = st.button("🔍 Analyze Profile", key="btn_gh", use_container_width=True,
                            disabled=not username.strip() if username else True)

    if analyze and username and username.strip():
        if not _groq_key():
            st.error("❌ GROQ_API_KEY not found.")
            return

        with st.spinner(f"Fetching @{username.strip()}…"):
            try:
                from github_analyzer import GitHubAnalyzer

                analyzer = GitHubAnalyzer()
                result   = analyzer.analyze_github_profile(username.strip())

                if result.get("success"):
                    st.session_state.github_analysis = result
                    st.success("✅ GitHub profile analyzed!")
                else:
                    st.error(f"❌ {result.get('error', 'Profile not found or is private.')}")
                    st.info("💡 Make sure the username is correct and the profile is public.")
                    return
            except ImportError:
                st.error("❌ github_analyzer.py not found in project directory.")
                return
            except Exception as e:
                st.error(f"❌ Error: {e}")
                return

    # Display result
    if st.session_state.github_analysis:
        profile  = st.session_state.github_analysis.get("profile", {})
        analysis = st.session_state.github_analysis.get("analysis", {})

        st.markdown("### Profile Overview")
        cols = st.columns(4)
        metrics = [
            ("Followers",     profile.get("followers", 0)),
            ("Public Repos",  profile.get("public_repos", 0)),
            ("Following",     profile.get("following", 0)),
            ("Profile Score", analysis.get("profile_score", analysis.get("score", "—"))),
        ]
        for col, (label, val) in zip(cols, metrics):
            with col:
                st.metric(label, val)

        langs = profile.get("languages", {})
        if langs:
            st.markdown("### Top Languages")
            st.bar_chart(langs)

        with st.expander("🤖 AI Analysis", expanded=True):
            st.json(analysis)
    else:
        st.info("Enter a GitHub username and click **Analyze Profile** to get started.")


# ══════════════════════════════════════════════════════════════════════════════
# Tab 3 – Job Matcher
# ══════════════════════════════════════════════════════════════════════════════
def tab_jobs():
    st.markdown("### 💼 Job Matcher")
    st.markdown(
        '<p>Describe your skills and preferences to find matching jobs from '
        'the loaded Kaggle job dataset.</p>',
        unsafe_allow_html=True,
    )

    # Check if job database exists
    jobs_ok = os.path.isfile(os.path.join("data", "jobs.csv"))
    if not jobs_ok:
        st.warning(
            "⚠️ **Job database not found.** "
            "Download a Kaggle dataset and save it as `data/jobs.csv`. "
            "See the Setup Guide in the sidebar for links."
        )

    col1, col2 = st.columns(2)
    with col1:
        skills_raw = st.text_area(
            "Your Skills (one per line)",
            placeholder="Python\nReact\nPostgreSQL\nDocker",
            height=120,
            key="job_skills",
        )
        experience = st.number_input(
            "Years of Experience", min_value=0, max_value=50, value=2, key="job_exp"
        )

    with col2:
        seniority = st.selectbox(
            "Seniority Level",
            ["Junior", "Mid-Level", "Senior", "Lead", "Principal"],
            key="job_seniority",
        )
        roles = st.multiselect(
            "Interested Roles",
            [
                "Full Stack Developer", "Backend Engineer", "Frontend Developer",
                "Data Scientist", "ML Engineer", "DevOps Engineer",
                "Product Manager", "Mobile Developer", "Cloud Architect",
            ],
            key="job_roles",
        )

    if st.button("🔍 Find Matching Jobs", key="btn_jobs", use_container_width=False,
                 disabled=not jobs_ok):
        if not _groq_key():
            st.error("❌ GROQ_API_KEY not found.")
            return

        skills = [s.strip() for s in skills_raw.split("\n") if s.strip()]
        if not skills:
            st.warning("Please enter at least one skill.")
            return

        with st.spinner("Searching job database…"):
            try:
                from job_matcher import JobMatcher

                user_profile = {
                    "skills":           skills,
                    "experience_years": int(experience),
                    "seniority_level":  seniority.lower().replace("-", "_"),
                    "interested_roles": roles,
                }

                matcher = JobMatcher()
                result  = matcher.match_jobs(user_profile)

                if result.get("success"):
                    st.session_state.job_matches = result
                    st.success("✅ Job matching complete!")
                else:
                    st.warning(f"⚠️ {result.get('error', 'No matching jobs found.')}")
                    return
            except ImportError:
                st.error("❌ job_matcher.py not found in project directory.")
                return
            except Exception as e:
                st.error(f"❌ Error: {e}")
                return

    # Display results
    if st.session_state.job_matches:
        matches = st.session_state.job_matches.get("matches", {})
        st.markdown("### 🎯 Matched Jobs")
        with st.expander("View Results", expanded=True):
            st.json(matches)
    elif jobs_ok:
        st.info("Fill in your profile and click **Find Matching Jobs**.")


# ══════════════════════════════════════════════════════════════════════════════
# Tab 4 – Full Assessment
# ══════════════════════════════════════════════════════════════════════════════
def tab_assessment():
    st.markdown("### 📊 Full Career Assessment")
    st.markdown(
        '<p>Combines all analyses into one consolidated career report. '
        'Complete at least one analysis in the other tabs first.</p>',
        unsafe_allow_html=True,
    )

    cv_done  = st.session_state.cv_analysis     is not None
    gh_done  = st.session_state.github_analysis is not None
    job_done = st.session_state.job_matches     is not None
    any_done = cv_done or gh_done or job_done

    # Status summary
    cols = st.columns(3)
    with cols[0]: st.metric("CV Analysis",     "✅ Done" if cv_done  else "⬜ Pending")
    with cols[1]: st.metric("GitHub Analysis", "✅ Done" if gh_done  else "⬜ Pending")
    with cols[2]: st.metric("Job Matches",     "✅ Done" if job_done else "⬜ Pending")

    st.write("")

    if not any_done:
        st.info("👆 Go to the other tabs and run at least one analysis to generate your report.")
        return

    if st.button("📋 Generate Full Report", key="btn_report", use_container_width=False):
        st.success("✅ Report compiled from session data!")

    if cv_done:
        with st.expander("📄 CV Analysis", expanded=True):
            st.json(st.session_state.cv_analysis)

    if gh_done:
        with st.expander("🐙 GitHub Analysis", expanded=True):
            st.json(st.session_state.github_analysis)

    if job_done:
        with st.expander("💼 Job Matches", expanded=True):
            st.json(st.session_state.job_matches)

    # Download button
    report = {
        "generated_at":    datetime.datetime.now().isoformat(),
        "cv_analysis":     st.session_state.cv_analysis,
        "github_analysis": st.session_state.github_analysis,
        "job_matches":     st.session_state.job_matches,
    }
    st.download_button(
        "📥 Download Report (JSON)",
        data=json.dumps(report, indent=2, default=str),
        file_name=f"career_report_{datetime.date.today()}.json",
        mime="application/json",
        key="dl_report",
    )


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════
def main():
    inject_css()
    init_state()
    render_sidebar()
    render_header()

    tab1, tab2, tab3, tab4 = st.tabs([
        "📄  CV Analyzer",
        "🐙  GitHub Profile",
        "💼  Job Matcher",
        "📊  Full Assessment",
    ])

    with tab1: tab_cv()
    with tab2: tab_github()
    with tab3: tab_jobs()
    with tab4: tab_assessment()


if __name__ == "__main__":
    main()