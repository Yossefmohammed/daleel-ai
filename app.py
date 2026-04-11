"""
Career AI Assistant - app.py
CV Analyzer + GitHub Profiler + Job Matcher + Live Job Scraper + AI Chatbot
"""

import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="🎯 Career AI Assistant",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

from cv_analyzer import CVAnalyzer
from github_analyzer import GitHubAnalyzer
from job_matcher import JobMatcher

st.markdown("""
<style>
.stApp { background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); color: #E8E8F0; }
h1 { text-align: center; font-size: 2.8rem; font-weight: 800;
     background: linear-gradient(135deg, #00D9FF, #0091FF);
     -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
h2, h3 { color: #00D9FF; }
.stTabs [data-baseweb="tab-list"] button { font-size: 1rem; font-weight: 600; }

/* Chat messages */
.stChatMessage {
    background: rgba(30, 30, 60, 0.7) !important;
    border: 1px solid rgba(0, 217, 255, 0.15) !important;
    border-radius: 14px !important;
    padding: 14px !important;
    margin: 8px 0 !important;
}
[data-testid="stChatMessageContent"] { color: #E8E8F0 !important; font-size: 15px !important; line-height: 1.7 !important; }

/* Chat input */
[data-testid="stChatInput"] textarea {
    background: rgba(20, 20, 50, 0.9) !important;
    color: #E8E8F0 !important;
    border: 1px solid rgba(0, 217, 255, 0.3) !important;
    border-radius: 12px !important;
}

footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

st.title("🎯 Career AI Assistant")
st.markdown(
    "<p style='text-align:center;color:#aaa;'>CV analysis · GitHub profiling · Job matching · AI Career Chat</p>",
    unsafe_allow_html=True,
)
st.divider()

# ── Session state ─────────────────────────────────────────────
for key in ["cv_analysis", "github_analysis", "job_matches", "chat_messages"]:
    if key not in st.session_state:
        st.session_state[key] = None

if st.session_state.chat_messages is None:
    st.session_state.chat_messages = [
        {
            "role": "assistant",
            "content": (
                "👋 Hi! I'm your **Career AI Assistant**.\n\n"
                "I can help you with:\n"
                "- 📝 Writing a professional cover letter\n"
                "- 💬 Preparing for interviews\n"
                "- 🎯 Career advice & skill gap analysis\n"
                "- 📧 Emailing recruiters or clients\n"
                "- 📄 Improving your CV summary\n\n"
                "What would you like help with today?"
            ),
        }
    ]

groq_key = os.getenv("GROQ_API_KEY", "")
if not groq_key:
    st.error("❌ GROQ_API_KEY not set. Add it to your `.env` file.")
    st.stop()

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "💬 Career Chat",
    "📄 CV Analyzer",
    "🐙 GitHub Profile",
    "💼 Job Matcher",
    "🌐 Scrape Jobs",
    "📊 Full Assessment",
])

# ═══════════════════════════════════════════════════════════════
# TAB 1 – Career Chatbot (streaming, word-by-word)
# ═══════════════════════════════════════════════════════════════
with tab1:
    st.header("💬 Career AI Chat")
    st.markdown("Chat with your AI career assistant. Responses appear word by word.")

    # ── Build context from other tabs if available ─────────────
    context_parts = []
    if st.session_state.cv_analysis and st.session_state.cv_analysis.get("success"):
        analysis = st.session_state.cv_analysis.get("analysis", {})
        if isinstance(analysis, dict):
            context_parts.append(
                f"The user's CV has been analyzed. Here's their profile:\n"
                f"- Skills: {', '.join(analysis.get('skills', []))}\n"
                f"- Technologies: {', '.join(analysis.get('technologies', []))}\n"
                f"- Seniority: {analysis.get('seniority_level', 'unknown')}\n"
                f"- Summary: {analysis.get('summary', '')}"
            )

    if st.session_state.github_analysis and st.session_state.github_analysis.get("success"):
        profile  = st.session_state.github_analysis.get("profile", {})
        gh_analysis = st.session_state.github_analysis.get("analysis", {})
        context_parts.append(
            f"The user's GitHub profile: username={profile.get('username','?')}, "
            f"repos={profile.get('public_repos','?')}, "
            f"top languages={list(profile.get('languages', {}).keys())[:5]}, "
            f"career readiness={gh_analysis.get('career_readiness','?') if isinstance(gh_analysis, dict) else '?'}"
        )

    if st.session_state.job_matches and st.session_state.job_matches.get("success"):
        context_parts.append(
            "The user has already run job matching. They are actively job hunting."
        )

    system_prompt = """You are a friendly, expert Career AI Assistant helping job seekers advance their careers.

You can help with:
- Writing cover letters, emails to recruiters, LinkedIn messages
- Interview preparation and common Q&A
- Career advice, skill gap analysis, salary negotiation
- Improving CV summaries and professional profiles
- Explaining job market trends

Guidelines:
- Be warm, encouraging, and professional
- Give concrete, actionable advice
- When writing emails or messages, format them cleanly and ready to send
- Keep responses focused and not too long unless asked for detail
- Use bullet points for lists
- If the user wants to write to a client or recruiter, write the full message for them
"""

    if context_parts:
        system_prompt += "\n\nContext about this user:\n" + "\n".join(context_parts)

    # ── Chat controls ──────────────────────────────────────────
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.chat_messages = [
                {"role": "assistant", "content": "Chat cleared. How can I help you?"}
            ]
            st.rerun()
    with col2:
        tone = st.selectbox("Tone", ["Professional", "Friendly", "Formal", "Concise"],
                            label_visibility="collapsed")

    st.divider()

    # ── Render chat history ────────────────────────────────────
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ── Chat input + streaming ─────────────────────────────────
    if prompt := st.chat_input("Ask anything... e.g. 'Write a cover letter for a Python developer role'"):

        # Add user message
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Build message history for API (last 10 turns to stay within context)
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.chat_messages[-10:]
            if m["role"] in ("user", "assistant")
        ]

        # Inject tone instruction
        tone_instruction = {
            "Professional": "Use a professional tone.",
            "Friendly":     "Use a warm, friendly and encouraging tone.",
            "Formal":       "Use a formal, polished tone suitable for business correspondence.",
            "Concise":      "Be as concise as possible — short sentences, minimal fluff.",
        }.get(tone, "")

        full_system = system_prompt + f"\n\nTone instruction: {tone_instruction}"

        # Stream response word-by-word
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""

            try:
                from groq import Groq
                client = Groq(api_key=groq_key)

                stream = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "system", "content": full_system}] + history,
                    temperature=0.75,
                    max_tokens=1200,
                    stream=True,                   # ← streaming enabled
                )

                for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        full_response += delta
                        # Render markdown as it grows — creates the word-by-word effect
                        response_placeholder.markdown(full_response + "▌")

                # Final render without cursor
                response_placeholder.markdown(full_response)

            except Exception as e:
                full_response = f"❌ Error: {e}"
                response_placeholder.error(full_response)

        # Save assistant reply
        st.session_state.chat_messages.append(
            {"role": "assistant", "content": full_response}
        )

    # ── Quick prompt suggestions ───────────────────────────────
    st.markdown("---")
    st.markdown("**💡 Quick prompts:**")
    suggestions = [
        "Write a cover letter for a senior Python developer role",
        "How do I answer 'Tell me about yourself' in an interview?",
        "Write a LinkedIn message to a recruiter",
        "What skills should I learn to become a data scientist?",
        "Help me negotiate my salary offer",
        "Write a follow-up email after an interview",
    ]
    cols = st.columns(3)
    for i, suggestion in enumerate(suggestions):
        if cols[i % 3].button(suggestion, key=f"suggest_{i}", use_container_width=True):
            st.session_state.chat_messages.append({"role": "user", "content": suggestion})
            st.rerun()


# ═══════════════════════════════════════════════════════════════
# TAB 2 – CV Analyzer
# ═══════════════════════════════════════════════════════════════
with tab2:
    st.header("📄 CV Analyzer")
    col1, col2 = st.columns([3, 1])
    with col1:
        uploaded_file = st.file_uploader("Upload your CV (PDF)", type=["pdf"])
    with col2:
        st.write(""); st.write("")
        go = st.button("🔍 Analyze CV", use_container_width=True)

    if go:
        if not uploaded_file:
            st.warning("⚠️ Upload a PDF first.")
        else:
            temp = f"temp_{uploaded_file.name}"
            try:
                with open(temp, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                with st.spinner("Analyzing..."):
                    result = CVAnalyzer().analyze_cv(temp)
                if result.get("success"):
                    st.session_state.cv_analysis = result
                    st.success("✅ Done! The chatbot now knows your CV — go to 💬 Career Chat.")
                else:
                    st.error(result.get("error"))
            except Exception as e:
                st.error(str(e))
            finally:
                if os.path.exists(temp):
                    os.remove(temp)

    if st.session_state.cv_analysis:
        analysis = st.session_state.cv_analysis.get("analysis", {})
        if isinstance(analysis, dict):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**🛠️ Skills**")
                for s in analysis.get("skills", []):
                    st.markdown(f"- {s}")
                st.markdown("**💻 Technologies**")
                for t in analysis.get("technologies", []):
                    st.markdown(f"- {t}")
            with c2:
                st.markdown("**🎓 Education**")
                for e in analysis.get("education", []):
                    st.markdown(f"- {e.get('degree','?')} @ {e.get('school','?')}")
                st.markdown("**💼 Experience**")
                for ex in analysis.get("experience", []):
                    st.markdown(f"- {ex.get('title','?')} at {ex.get('company','?')}")
            st.markdown(f"**Seniority:** `{analysis.get('seniority_level','?')}`")
            st.info(analysis.get("summary", ""))
        else:
            st.code(str(analysis))

# ═══════════════════════════════════════════════════════════════
# TAB 3 – GitHub
# ═══════════════════════════════════════════════════════════════
with tab3:
    st.header("🐙 GitHub Profile Analysis")
    col1, col2 = st.columns([3, 1])
    with col1:
        username = st.text_input("GitHub Username", placeholder="e.g. torvalds")
    with col2:
        st.write(""); st.write("")
        go_gh = st.button("🔍 Analyze", use_container_width=True)

    if go_gh:
        if not username.strip():
            st.warning("⚠️ Enter a username.")
        else:
            with st.spinner("Fetching profile..."):
                try:
                    result = GitHubAnalyzer().analyze_github_profile(username.strip())
                    if result.get("success"):
                        st.session_state.github_analysis = result
                        st.success("✅ Done! The chatbot now knows your GitHub profile.")
                    else:
                        st.error(result.get("error"))
                except Exception as e:
                    st.error(str(e))

    if st.session_state.github_analysis:
        profile  = st.session_state.github_analysis.get("profile", {})
        analysis = st.session_state.github_analysis.get("analysis", {})
        c1, c2, c3 = st.columns(3)
        c1.metric("Followers",    profile.get("followers", 0))
        c2.metric("Public Repos", profile.get("public_repos", 0))
        c3.metric("Following",    profile.get("following", 0))
        if profile.get("languages"):
            st.bar_chart(profile["languages"])
        if isinstance(analysis, dict):
            st.markdown(
                f"**Strength:** `{analysis.get('profile_strength','?')}/10` | "
                f"**Readiness:** `{analysis.get('career_readiness','?')}`"
            )
            for r in analysis.get("recommendations", []):
                st.markdown(f"- {r}")
        else:
            st.code(str(analysis))

# ═══════════════════════════════════════════════════════════════
# TAB 4 – Job Matcher
# ═══════════════════════════════════════════════════════════════
with tab4:
    st.header("💼 Job Matcher")
    db_exists = os.path.exists("data/jobs_combined.csv") or os.path.exists("data/jobs.csv")
    if not db_exists:
        st.warning("⚠️ No job database. Use 🌐 Scrape Jobs first.")

    col1, col2 = st.columns(2)
    with col1:
        skills_input = st.text_area("Your Skills (one per line)",
                                    placeholder="Python\nJavaScript\nReact", height=120)
        exp_years = st.number_input("Years of Experience", 0, 50, 2)
    with col2:
        seniority = st.selectbox("Seniority", ["Junior", "Mid-Level", "Senior"])
        roles = st.multiselect("Interested Roles", [
            "Full Stack Developer", "Backend Engineer", "Frontend Developer",
            "Data Scientist", "ML Engineer", "DevOps Engineer", "Product Manager",
        ])

    if st.button("🔍 Find Matching Jobs", use_container_width=True):
        skills = [s.strip() for s in skills_input.splitlines() if s.strip()]
        if not skills:
            st.warning("⚠️ Enter at least one skill.")
        else:
            with st.spinner("Matching..."):
                try:
                    result = JobMatcher().match_jobs({
                        "skills": skills, "experience_years": exp_years,
                        "seniority_level": seniority.lower(), "interested_roles": roles,
                    })
                    if result.get("success"):
                        st.session_state.job_matches = result
                        st.success("✅ Done!")
                    else:
                        st.warning(result.get("error"))
                except Exception as e:
                    st.error(str(e))

    if st.session_state.job_matches:
        matches = st.session_state.job_matches.get("matches", {})
        if isinstance(matches, dict):
            for job in matches.get("jobs", []):
                with st.expander(
                    f"**{job.get('job_title','?')}** @ {job.get('company','?')} "
                    f"— {job.get('match_score','?')}%"
                ):
                    st.markdown(f"**Why:** {job.get('reason','')}")
                    st.markdown(f"**Required:** {', '.join(job.get('required_skills', []))}")
                    st.markdown(f"**Nice to have:** {', '.join(job.get('nice_to_have', []))}")
            st.info(matches.get("summary", ""))
        else:
            st.code(str(matches))

# ═══════════════════════════════════════════════════════════════
# TAB 5 – Scrape Jobs
# ═══════════════════════════════════════════════════════════════
with tab5:
    st.header("🌐 Scrape Live Jobs")

    db_path = ("data/jobs_combined.csv" if os.path.exists("data/jobs_combined.csv") else
               "data/jobs.csv"          if os.path.exists("data/jobs.csv") else None)
    if db_path:
        try:
            import pandas as pd
            df_c = pd.read_csv(db_path)
            c1, c2, c3 = st.columns(3)
            c1.metric("Jobs in DB", f"{len(df_c):,}")
            c2.metric("Sources", df_c["source"].nunique() if "source" in df_c.columns else "—")
            c3.metric("File", db_path)
        except Exception:
            pass

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### ✅ Available sources")
        use_remoteok  = st.checkbox("🌍 RemoteOK",  value=True)
        use_arbeitnow = st.checkbox("🇩🇪 Arbeitnow", value=True)
        use_muse      = st.checkbox("🇺🇸 The Muse",  value=True)
        use_wuzzuf    = st.checkbox("🇪🇬 Wuzzuf",    value=True)
    with col_b:
        st.markdown("#### ❌ LinkedIn")
        st.error(
            "Not supported — ToS violation, JS rendering, bot detection, "
            "and legal risk (hiQ v LinkedIn, 2022).\n\n"
            "✅ Use the official [LinkedIn Jobs API](https://developer.linkedin.com/product-catalog/jobs) instead."
        )

    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    remoteok_limit = c1.slider("RemoteOK jobs",     20, 200, 100, 20, disabled=not use_remoteok)
    arb_pages      = c2.slider("Arbeitnow pages",    1,  10,   3,    disabled=not use_arbeitnow)
    muse_pages     = c3.slider("The Muse pages",     1,   5,   2,    disabled=not use_muse)
    wuzzuf_pages   = c4.slider("Wuzzuf pages/kw",    1,   5,   2,    disabled=not use_wuzzuf)

    if use_wuzzuf:
        wuzzuf_kw_raw = st.text_area(
            "Wuzzuf keywords (comma-separated)",
            value="software engineer, python developer, data scientist, frontend developer, backend developer, full stack developer, devops",
            height=70,
        )
        wuzzuf_keywords = [k.strip() for k in wuzzuf_kw_raw.split(",") if k.strip()]
    else:
        wuzzuf_keywords = []

    if st.button("🚀 Scrape Now", use_container_width=True, type="primary"):
        if not any([use_remoteok, use_arbeitnow, use_muse, use_wuzzuf]):
            st.warning("⚠️ Select at least one source.")
        else:
            progress = st.progress(0, text="Starting...")
            log_box  = st.empty()
            logs: list = []

            def log(msg: str):
                logs.append(msg)
                log_box.markdown("\n\n".join(f"`{l}`" for l in logs[-10:]))

            try:
                from data_scraper import RemoteOKScraper, ArbeitnowScraper, TheMuseScraper, WuzzufScraper
                import pandas as pd

                os.makedirs("data", exist_ok=True)
                all_jobs: list = []
                total = sum([use_remoteok, use_arbeitnow, use_muse, use_wuzzuf])
                step = 0

                if use_remoteok:
                    log("📡 RemoteOK...")
                    progress.progress(int(100 * step / total), text="RemoteOK...")
                    j = RemoteOKScraper().scrape(limit=remoteok_limit)
                    all_jobs += j; step += 1
                    log(f"   ✅ {len(j)} jobs")

                if use_arbeitnow:
                    log("📡 Arbeitnow...")
                    progress.progress(int(100 * step / total), text="Arbeitnow...")
                    j = ArbeitnowScraper().scrape(pages=arb_pages)
                    all_jobs += j; step += 1
                    log(f"   ✅ {len(j)} jobs")

                if use_muse:
                    log("📡 The Muse...")
                    progress.progress(int(100 * step / total), text="The Muse...")
                    j = TheMuseScraper().scrape(pages=muse_pages)
                    all_jobs += j; step += 1
                    log(f"   ✅ {len(j)} jobs")

                if use_wuzzuf:
                    log(f"📡 Wuzzuf ({len(wuzzuf_keywords)} keywords)...")
                    progress.progress(int(100 * step / total), text="Wuzzuf...")
                    j = WuzzufScraper().scrape(keywords=wuzzuf_keywords, pages_per_keyword=wuzzuf_pages)
                    all_jobs += j; step += 1
                    log(f"   ✅ {len(j)} jobs")

                existing_df = pd.DataFrame()
                for path in ["data/jobs.csv", "docs/ai_jobs_market_2025_2026.csv"]:
                    if os.path.exists(path):
                        try:
                            existing_df = pd.read_csv(path)
                            log(f"   📂 {len(existing_df)} existing jobs loaded")
                            break
                        except Exception:
                            pass

                combined = pd.concat([existing_df, pd.DataFrame(all_jobs)], ignore_index=True)
                before = len(combined)
                combined.drop_duplicates(subset=["job_title", "company"], keep="first", inplace=True)
                log(f"   🗑️  {before - len(combined)} duplicates removed")

                combined.to_csv("data/jobs_combined.csv", index=False)
                progress.progress(100, text="Done!")
                log(f"💾 {len(combined):,} jobs → data/jobs_combined.csv")

                st.success(f"✅ **{len(combined):,} jobs** saved!")

                if "source" in combined.columns:
                    st.bar_chart(combined["source"].value_counts())

                display_cols = [c for c in ["job_title","company","location","remote_work","source"]
                                if c in combined.columns]
                st.dataframe(combined[display_cols].head(25), use_container_width=True)
                st.download_button(
                    "⬇️ Download jobs_combined.csv",
                    combined.to_csv(index=False).encode(),
                    "jobs_combined.csv", "text/csv", use_container_width=True,
                )
            except Exception as e:
                st.error(f"❌ {e}")
                progress.progress(100)

# ═══════════════════════════════════════════════════════════════
# TAB 6 – Full Assessment
# ═══════════════════════════════════════════════════════════════
with tab6:
    st.header("📊 Full Career Assessment")
    has_data = any([st.session_state.cv_analysis,
                    st.session_state.github_analysis,
                    st.session_state.job_matches])
    if not has_data:
        st.info("Complete at least one analysis in the other tabs first.")
    else:
        if st.button("📋 Generate Report", use_container_width=True):
            if st.session_state.cv_analysis:
                st.markdown("### 📄 CV")
                a = st.session_state.cv_analysis.get("analysis", {})
                st.json(a) if isinstance(a, dict) else st.code(str(a))
            if st.session_state.github_analysis:
                st.markdown("### 🐙 GitHub")
                p = {k: v for k, v in
                     st.session_state.github_analysis.get("profile", {}).items()
                     if k != "success"}
                st.json(p)
            if st.session_state.job_matches:
                st.markdown("### 💼 Job Matches")
                m = st.session_state.job_matches.get("matches", {})
                st.json(m) if isinstance(m, dict) else st.code(str(m))
            st.success("✅ Report ready!")

# ── Sidebar ────────────────────────────────────────────────────
with st.sidebar:
    st.title("🎯 Career AI")
    st.markdown("---")
    st.success("✅ Groq API")        if groq_key                              else st.error("❌ No API key")
    st.success("✅ CV analyzed")     if st.session_state.cv_analysis          else st.info("⬜ CV")
    st.success("✅ GitHub analyzed") if st.session_state.github_analysis      else st.info("⬜ GitHub")
    st.success("✅ Jobs matched")    if st.session_state.job_matches           else st.info("⬜ Jobs")

    chat_count = len([m for m in (st.session_state.chat_messages or []) if m["role"] == "user"])
    if chat_count:
        st.success(f"✅ {chat_count} chat messages")
    else:
        st.info("⬜ No chats yet")

    st.markdown("---")
    db_f = ("data/jobs_combined.csv" if os.path.exists("data/jobs_combined.csv")
            else "data/jobs.csv"     if os.path.exists("data/jobs.csv") else None)
    if db_f:
        try:
            import pandas as pd
            st.success(f"✅ {len(pd.read_csv(db_f)):,} jobs in DB")
        except Exception:
            st.warning("⚠️ DB unreadable")
    else:
        st.warning("⚠️ No DB — Scrape Jobs first")

    st.markdown("---")
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.chat_messages = None
        st.rerun()
    if st.button("🗑️ Clear All Results", use_container_width=True):
        for k in ["cv_analysis", "github_analysis", "job_matches", "chat_messages"]:
            st.session_state[k] = None
        st.rerun()
    st.caption("Phase 1 ✅ | Powered by Groq")