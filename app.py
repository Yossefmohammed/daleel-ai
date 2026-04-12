"""
Career AI Assistant - Phase 1
Fixed: Floating chat panel + auto-fill skills from CV
"""

import os
import json
import streamlit as st
from dotenv import load_dotenv
from cv_analyzer import CVAnalyzer
from github_analyzer import GitHubAnalyzer
from job_matcher import JobMatcher

load_dotenv()

st.set_page_config(
    page_title="🚀 Career AI Assistant",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS + Floating Chat Panel ──────────────────────────────────────────
GROQ_KEY = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY", ""))

st.markdown(f"""
<style>
/* ── Base ── */
.main {{ padding: 2rem; }}
.stTabs [data-baseweb="tab-list"] button {{ font-size: 1.1rem; }}

/* ── Floating chat button ── */
#wasla-chat-btn {{
    position: fixed;
    bottom: 32px;
    right: 32px;
    width: 60px;
    height: 60px;
    border-radius: 50%;
    background: linear-gradient(135deg,#00D9FF,#0091FF);
    color: #000;
    font-size: 26px;
    border: none;
    cursor: pointer;
    box-shadow: 0 4px 20px rgba(0,145,255,.45);
    z-index: 9999;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: transform .2s,box-shadow .2s;
}}
#wasla-chat-btn:hover {{
    transform: scale(1.1);
    box-shadow: 0 6px 28px rgba(0,145,255,.6);
}}

/* ── Sliding panel ── */
#wasla-chat-panel {{
    position: fixed;
    top: 0; right: -420px;
    width: 400px; height: 100vh;
    background: linear-gradient(160deg,#0F0F1E 0%,#1A1A2E 100%);
    border-left: 1px solid rgba(0,217,255,.25);
    box-shadow: -6px 0 40px rgba(0,0,0,.6);
    z-index: 9998;
    display: flex;
    flex-direction: column;
    transition: right .35s cubic-bezier(.4,0,.2,1);
    font-family: 'Segoe UI',sans-serif;
}}
#wasla-chat-panel.open {{ right: 0; }}

/* header */
#chat-header {{
    padding: 18px 20px;
    border-bottom: 1px solid rgba(0,217,255,.2);
    display: flex; align-items: center; justify-content: space-between;
}}
#chat-header h3 {{
    margin:0; font-size:17px; font-weight:700;
    background:linear-gradient(135deg,#00D9FF,#0091FF);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
}}
#chat-close {{
    background:none; border:none; color:#aaa;
    font-size:22px; cursor:pointer; line-height:1;
    padding:0 4px;
}}
#chat-close:hover {{ color:#fff; }}

/* messages */
#chat-messages {{
    flex:1; overflow-y:auto; padding:16px;
    display:flex; flex-direction:column; gap:10px;
}}
.msg {{
    max-width:85%; padding:10px 14px;
    border-radius:14px; font-size:14px; line-height:1.55;
    animation: fadeUp .2s ease;
}}
@keyframes fadeUp {{
    from {{ opacity:0; transform:translateY(6px); }}
    to   {{ opacity:1; transform:translateY(0); }}
}}
.msg.user {{
    align-self:flex-end;
    background:linear-gradient(135deg,#00D9FF22,#0091FF33);
    border:1px solid rgba(0,145,255,.4);
    color:#E8E8F0;
}}
.msg.bot {{
    align-self:flex-start;
    background:rgba(255,255,255,.06);
    border:1px solid rgba(255,255,255,.1);
    color:#E8E8F0;
}}
.msg.bot.typing {{ opacity:.6; font-style:italic; }}

/* input row */
#chat-input-row {{
    padding:14px 16px;
    border-top:1px solid rgba(0,217,255,.15);
    display:flex; gap:8px;
}}
#chat-input {{
    flex:1; background:rgba(255,255,255,.07);
    border:1px solid rgba(0,217,255,.3);
    border-radius:10px; padding:9px 13px;
    color:#E8E8F0; font-size:14px; outline:none;
    resize:none;
}}
#chat-input:focus {{ border-color:#00D9FF; }}
#chat-send {{
    width:40px; height:40px; border-radius:10px; flex-shrink:0;
    background:linear-gradient(135deg,#00D9FF,#0091FF);
    border:none; cursor:pointer; font-size:18px;
    display:flex; align-items:center; justify-content:center;
    transition:opacity .2s;
}}
#chat-send:hover {{ opacity:.85; }}
</style>

<!-- Floating button -->
<button id="wasla-chat-btn" title="Chat with Wasla AI">💬</button>

<!-- Sliding panel -->
<div id="wasla-chat-panel">
  <div id="chat-header">
    <h3>🤖 Wasla AI Chat</h3>
    <button id="chat-close">✕</button>
  </div>
  <div id="chat-messages">
    <div class="msg bot">
      👋 Hi! I'm <b>Wasla AI</b>. Ask me anything about your career, CV, or job search!
    </div>
  </div>
  <div id="chat-input-row">
    <textarea id="chat-input" rows="1" placeholder="Ask something…"></textarea>
    <button id="chat-send">➤</button>
  </div>
</div>

<script>
(function() {{
  const btn   = document.getElementById('wasla-chat-btn');
  const panel = document.getElementById('wasla-chat-panel');
  const close = document.getElementById('chat-close');
  const msgs  = document.getElementById('chat-messages');
  const input = document.getElementById('chat-input');
  const send  = document.getElementById('chat-send');

  btn.onclick   = () => panel.classList.add('open');
  close.onclick = () => panel.classList.remove('open');

  // auto-resize textarea
  input.addEventListener('input', () => {{
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';
  }});
  input.addEventListener('keydown', e => {{
    if (e.key === 'Enter' && !e.shiftKey) {{ e.preventDefault(); sendMsg(); }}
  }});
  send.onclick = sendMsg;

  const GROQ_KEY = "{GROQ_KEY}";
  const history  = [];           // {{role, content}}[]

  function addMsg(role, text) {{
    const div = document.createElement('div');
    div.className = 'msg ' + role;
    div.innerHTML = text.replace(/\\n/g, '<br>');
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
    return div;
  }}

  async function sendMsg() {{
    const text = input.value.trim();
    if (!text) return;
    input.value = ''; input.style.height = 'auto';

    addMsg('user', text);
    history.push({{role:'user', content:text}});

    const typing = addMsg('bot typing', '● ● ●');

    try {{
      const res = await fetch('https://api.groq.com/openai/v1/chat/completions', {{
        method: 'POST',
        headers: {{
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + GROQ_KEY
        }},
        body: JSON.stringify({{
          model: 'llama-3.3-70b-versatile',
          messages: [
            {{role:'system', content:'You are Wasla AI, a helpful career assistant. Be concise, warm and practical. Help with CVs, job search, career advice, skills development and job matching.'}},
            ...history
          ],
          max_tokens: 500,
          temperature: 0.75
        }})
      }});

      const data = await res.json();
      const reply = data?.choices?.[0]?.message?.content
                 || data?.error?.message
                 || '⚠️ No response received.';

      history.push({{role:'assistant', content:reply}});
      typing.classList.remove('typing');
      typing.innerHTML = reply.replace(/\\n/g,'<br>');
      msgs.scrollTop = msgs.scrollHeight;

    }} catch(err) {{
      typing.classList.remove('typing');
      typing.innerHTML = '❌ Error: ' + err.message;
    }}
  }}
}})();
</script>
""", unsafe_allow_html=True)


# ── Title ─────────────────────────────────────────────────────────────────────
st.title("🎯 Career AI Assistant")
st.markdown("""
### Phase 1: MVP Features
- 📄 **CV Analyzer** - Extract skills, experience, education
- 🐙 **GitHub Profile Analysis** - Assess your coding skills
- 💼 **Job Matcher** - Find positions that match your profile
""")
st.divider()

# ── Session state ──────────────────────────────────────────────────────────────
for key, default in [
    ("cv_analysis", None),
    ("github_analysis", None),
    ("job_matches", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ── Helper: extract skills from CV analysis ────────────────────────────────────
def extract_skills_from_cv() -> str:
    """Return newline-separated skills extracted from the CV analysis."""
    cv = st.session_state.cv_analysis
    if not cv:
        return ""
    analysis = cv.get("analysis", {})
    # analysis may be a dict or a JSON string
    if isinstance(analysis, str):
        try:
            analysis = json.loads(analysis)
        except Exception:
            return ""
    if not isinstance(analysis, dict):
        return ""
    skills = analysis.get("skills", [])
    if isinstance(skills, list):
        return "\n".join(str(s) for s in skills if s)
    if isinstance(skills, str):
        return skills
    return ""


# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📄 CV Analyzer",
    "🐙 GitHub Profile",
    "💼 Job Matcher",
    "📊 Full Assessment"
])

# ════════════════════════════════════════════════════════════════════════
# TAB 1 – CV ANALYZER
# ════════════════════════════════════════════════════════════════════════
with tab1:
    st.header("📄 CV Analyzer")
    st.markdown("Upload your CV (PDF) to extract skills, experience, and education")

    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_file = st.file_uploader(
            "Choose your CV file", type=["pdf"],
            help="Upload a PDF version of your CV"
        )
    with col2:
        analyze_cv = st.button("🔍 Analyze CV", use_container_width=True)

    if analyze_cv and uploaded_file:
        with st.spinner("Analyzing CV…"):
            try:
                temp_path = f"temp_{uploaded_file.name}"
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                analyzer = CVAnalyzer()
                result = analyzer.analyze_cv(temp_path)
                os.remove(temp_path)

                if result.get("success"):
                    st.session_state.cv_analysis = result
                    st.success("✅ CV analyzed successfully! Skills auto-filled in Job Matcher.")
                    st.markdown("### Analysis Results")
                    st.json(result.get("analysis", {}))
                else:
                    st.error(f"❌ Error: {result.get('error', 'Unknown error')}")
            except Exception as e:
                st.error(f"❌ Error processing file: {e}")
    elif analyze_cv:
        st.warning("⚠️ Please upload a PDF file first.")

    if st.session_state.cv_analysis:
        with st.expander("📋 Cached CV Analysis (this session)", expanded=False):
            st.json(st.session_state.cv_analysis.get("analysis", {}))

# ════════════════════════════════════════════════════════════════════════
# TAB 2 – GITHUB ANALYZER
# ════════════════════════════════════════════════════════════════════════
with tab2:
    st.header("🐙 GitHub Profile Analysis")
    st.markdown("Enter your GitHub username to analyze your coding profile")

    col1, col2 = st.columns([2, 1])
    with col1:
        github_username = st.text_input(
            "GitHub Username",
            placeholder="e.g., your-username",
            help="Enter your GitHub username (without @)"
        )
    with col2:
        analyze_github = st.button("🔍 Analyze GitHub", use_container_width=True)

    if analyze_github and github_username:
        with st.spinner("Fetching GitHub profile…"):
            try:
                analyzer = GitHubAnalyzer()
                result = analyzer.analyze_github_profile(github_username)

                if result.get("success"):
                    st.session_state.github_analysis = result
                    st.success("✅ GitHub profile analyzed!")

                    profile = result.get("profile", {})
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Followers", profile.get("followers", 0))
                    c2.metric("Public Repos", profile.get("public_repos", 0))
                    c3.metric("Following", profile.get("following", 0))

                    languages = profile.get("languages", {})
                    if languages:
                        st.markdown("### Top Languages")
                        st.bar_chart(languages)

                    st.markdown("### AI Analysis")
                    st.json(result.get("analysis", {}))
                else:
                    st.error(f"❌ Error: {result.get('error', 'Unknown error')}")
                    st.info("💡 Make sure the username is correct and the profile is public")
            except Exception as e:
                st.error(f"❌ Error: {e}")

    if st.session_state.github_analysis:
        with st.expander("📋 Cached GitHub Analysis", expanded=False):
            st.json(st.session_state.github_analysis.get("profile", {}))

# ════════════════════════════════════════════════════════════════════════
# TAB 3 – JOB MATCHER  (skills auto-filled from CV)
# ════════════════════════════════════════════════════════════════════════
with tab3:
    st.header("💼 Job Matcher")
    st.markdown("Find jobs that match your skills and experience")
    st.warning("⚠️ **Note:** Job database needs to be populated from Kaggle datasets. See README for setup instructions.")

    # ── Auto-fill banner ──────────────────────────────────────────────
    auto_skills = extract_skills_from_cv()
    if auto_skills:
        st.success("✅ Skills auto-filled from your uploaded CV! You can edit them below.")
    else:
        st.info("💡 Upload and analyze your CV in the **📄 CV Analyzer** tab to auto-fill your skills here.")

    # ── Form ─────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        skills_input = st.text_area(
            "Your Skills",
            value=auto_skills,                          # ← AUTO-FILLED from CV
            placeholder="Python, JavaScript, React, Node.js\n(one per line or comma-separated)",
            height=120,
            help="Edit or add skills. Auto-filled from your CV when available."
        )
        experience_years = st.number_input(
            "Years of Experience", min_value=0, max_value=50, value=2
        )

    with col2:
        seniority = st.selectbox("Seniority Level", ["Junior", "Mid-Level", "Senior"])
        interested_roles = st.multiselect(
            "Interested Roles",
            ["Full Stack Developer", "Backend Engineer", "Frontend Developer",
             "Data Scientist", "DevOps Engineer", "Product Manager"]
        )

    if st.button("🔍 Find Matching Jobs", use_container_width=True):
        # parse skills – support both newline and comma separators
        raw_skills = skills_input.replace(",", "\n")
        parsed_skills = [s.strip() for s in raw_skills.split("\n") if s.strip()]

        if not parsed_skills:
            st.warning("⚠️ Please add at least one skill, or upload your CV to auto-fill.")
        else:
            with st.spinner("Matching jobs…"):
                try:
                    user_profile = {
                        "skills": parsed_skills,
                        "experience_years": experience_years,
                        "seniority_level": seniority.lower(),
                        "interested_roles": interested_roles,
                    }
                    matcher = JobMatcher()
                    result = matcher.match_jobs(user_profile)

                    if result.get("success"):
                        st.session_state.job_matches = result
                        st.success("✅ Job matching complete!")
                        st.json(result.get("matches", {}))
                    else:
                        st.warning(f"⚠️ {result.get('error', 'No jobs found')}")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

# ════════════════════════════════════════════════════════════════════════
# TAB 4 – FULL ASSESSMENT
# ════════════════════════════════════════════════════════════════════════
with tab4:
    st.header("📊 Complete Career Assessment")
    st.markdown("Compile all analyses into a comprehensive career report")

    if st.button("📋 Generate Full Report", use_container_width=True):
        report_data = {
            "cv_analysis":    st.session_state.cv_analysis,
            "github_analysis": st.session_state.github_analysis,
            "job_matches":    st.session_state.job_matches,
        }
        if not any(report_data.values()):
            st.warning("⚠️ Please complete at least one analysis first")
        else:
            st.success("✅ Report compiled!")
            if st.session_state.cv_analysis:
                st.markdown("### CV Analysis")
                st.json(st.session_state.cv_analysis)
            if st.session_state.github_analysis:
                st.markdown("### GitHub Analysis")
                st.json(st.session_state.github_analysis)
            if st.session_state.job_matches:
                st.markdown("### Job Matches")
                st.json(st.session_state.job_matches)

# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.markdown("## 📚 Resources")
st.sidebar.markdown("""
### Kaggle Datasets to Download:
1. **[Data Science Job Salaries](https://www.kaggle.com/datasets/ruchi798/data-science-job-salaries)**
2. **[Tech Jobs](https://www.kaggle.com/datasets/andrewmvd/tech-jobs)**
3. **[LinkedIn Jobs](https://www.kaggle.com/datasets/arjunprasadsarkhel/linkedin-job-postings)**

### Setup Instructions:
1. Download CSV files from Kaggle
2. Create `data/` folder
3. Place CSV as `data/jobs.csv`

### Environment Variables:
```
GROQ_API_KEY=your_key
GITHUB_TOKEN=your_token (optional)
```
""")
st.sidebar.divider()
st.sidebar.markdown("**Phase 1 Status:** ✅ MVP Complete")
st.sidebar.markdown("""
**Coming in Phase 2:**
- Mock Interview Practice
- LinkedIn Optimization
- Enhancement Recommendations
""")