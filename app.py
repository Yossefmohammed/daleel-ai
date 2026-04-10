"""
Career AI Assistant - app.py
CV Analyzer + GitHub Profiler + Job Matcher + Live Job Scraper
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
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

st.title("🎯 Career AI Assistant")
st.markdown(
    "<p style='text-align:center;color:#aaa;'>AI-powered CV analysis · GitHub profiling · Job matching</p>",
    unsafe_allow_html=True,
)
st.divider()

for key in ["cv_analysis", "github_analysis", "job_matches"]:
    if key not in st.session_state:
        st.session_state[key] = None

groq_key = os.getenv("GROQ_API_KEY", "")
if not groq_key:
    st.error("❌ GROQ_API_KEY not set. Add it to your `.env` file.")
    st.stop()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📄 CV Analyzer",
    "🐙 GitHub Profile",
    "💼 Job Matcher",
    "🌐 Scrape Jobs",
    "📊 Full Assessment",
])

# ═══════════════════════════════════════════════════════════════
# TAB 1 – CV Analyzer
# ═══════════════════════════════════════════════════════════════
with tab1:
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
                    st.success("✅ Done!")
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
# TAB 2 – GitHub
# ═══════════════════════════════════════════════════════════════
with tab2:
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
                        st.success("✅ Done!")
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
            st.markdown(f"**Strength:** `{analysis.get('profile_strength','?')}/10` | **Readiness:** `{analysis.get('career_readiness','?')}`")
            for r in analysis.get("recommendations", []):
                st.markdown(f"- {r}")
        else:
            st.code(str(analysis))

# ═══════════════════════════════════════════════════════════════
# TAB 3 – Job Matcher
# ═══════════════════════════════════════════════════════════════
with tab3:
    st.header("💼 Job Matcher")
    db_exists = os.path.exists("data/jobs_combined.csv") or os.path.exists("data/jobs.csv")
    if not db_exists:
        st.warning("⚠️ No job database found. Use the **🌐 Scrape Jobs** tab first.")

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
                with st.expander(f"**{job.get('job_title','?')}** @ {job.get('company','?')} — {job.get('match_score','?')}%"):
                    st.markdown(f"**Why:** {job.get('reason','')}")
                    st.markdown(f"**Required:** {', '.join(job.get('required_skills', []))}")
                    st.markdown(f"**Nice to have:** {', '.join(job.get('nice_to_have', []))}")
            st.info(matches.get("summary", ""))
        else:
            st.code(str(matches))

# ═══════════════════════════════════════════════════════════════
# TAB 4 – Scrape Jobs
# ═══════════════════════════════════════════════════════════════
with tab4:
    st.header("🌐 Scrape Live Jobs")

    # ── DB stats ─────────────────────────────────────────────────
    db_path = ("data/jobs_combined.csv" if os.path.exists("data/jobs_combined.csv") else
               "data/jobs.csv"          if os.path.exists("data/jobs.csv") else None)
    if db_path:
        try:
            import pandas as pd
            df_current = pd.read_csv(db_path)
            c1, c2, c3 = st.columns(3)
            c1.metric("Jobs in DB", f"{len(df_current):,}")
            c2.metric("Sources", df_current["source"].nunique() if "source" in df_current.columns else "—")
            c3.metric("File", db_path)
        except Exception:
            pass

    st.divider()

    # ── Source selection ──────────────────────────────────────────
    st.subheader("📡 Sources")

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### ✅ Available sources")
        use_remoteok  = st.checkbox("🌍 RemoteOK — global remote tech jobs",  value=True)
        use_arbeitnow = st.checkbox("🇩🇪 Arbeitnow — European & global jobs", value=True)
        use_muse      = st.checkbox("🇺🇸 The Muse — professional tech roles", value=True)
        use_wuzzuf    = st.checkbox("🇪🇬 Wuzzuf — Egypt job board",            value=True)

    with col_b:
        st.markdown("#### ❌ LinkedIn — why it's not supported")
        st.error(
            "**LinkedIn scraping is not possible** for these reasons:\n\n"
            "1. **ToS violation** — Section 8.2 explicitly forbids it\n"
            "2. **JS-rendered pages** — `requests` gets a login wall, not job data\n"
            "3. **Bot detection** — Cloudflare + proprietary layer blocks scripts\n"
            "4. **Legal risk** — They actively pursue scrapers (hiQ case, 2022)\n\n"
            "✅ **Legitimate alternative:** Apply for the "
            "[LinkedIn Jobs API](https://developer.linkedin.com/product-catalog/jobs) "
            "as a registered partner app."
        )

    st.divider()

    # ── Per-source settings ───────────────────────────────────────
    st.subheader("⚙️ Settings")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        remoteok_limit = st.slider("RemoteOK jobs", 20, 200, 100, 20, disabled=not use_remoteok)
    with c2:
        arb_pages = st.slider("Arbeitnow pages", 1, 10, 3, disabled=not use_arbeitnow)
    with c3:
        muse_pages = st.slider("The Muse pages", 1, 5, 2, disabled=not use_muse)
    with c4:
        wuzzuf_pages = st.slider("Wuzzuf pages/keyword", 1, 5, 2, disabled=not use_wuzzuf)

    if use_wuzzuf:
        default_kw = (
            "software engineer, python developer, data scientist, "
            "frontend developer, backend developer, full stack developer, devops"
        )
        wuzzuf_kw_raw = st.text_area(
            "Wuzzuf keywords (comma-separated)",
            value=default_kw,
            height=80,
            help="Each keyword = one search on Wuzzuf. More keywords = more jobs but slower.",
        )
        wuzzuf_keywords = [k.strip() for k in wuzzuf_kw_raw.split(",") if k.strip()]
    else:
        wuzzuf_keywords = []

    st.divider()

    if st.button("🚀 Scrape Now", use_container_width=True, type="primary"):
        if not any([use_remoteok, use_arbeitnow, use_muse, use_wuzzuf]):
            st.warning("⚠️ Select at least one source.")
        else:
            progress = st.progress(0, text="Starting...")
            log_box = st.empty()
            logs: list = []

            def log(msg: str):
                logs.append(msg)
                log_box.markdown("\n\n".join(f"`{l}`" for l in logs[-10:]))

            try:
                from data_scraper import (
                    RemoteOKScraper, ArbeitnowScraper,
                    TheMuseScraper, WuzzufScraper,
                )
                import pandas as pd

                os.makedirs("data", exist_ok=True)
                all_jobs: list = []
                step = 0
                total_steps = sum([use_remoteok, use_arbeitnow, use_muse, use_wuzzuf])

                if use_remoteok:
                    log("📡 Scraping RemoteOK...")
                    progress.progress(int(100 * step / total_steps), text="RemoteOK...")
                    j = RemoteOKScraper().scrape(limit=remoteok_limit)
                    all_jobs += j; step += 1
                    log(f"   ✅ {len(j)} jobs from RemoteOK")

                if use_arbeitnow:
                    log("📡 Scraping Arbeitnow...")
                    progress.progress(int(100 * step / total_steps), text="Arbeitnow...")
                    j = ArbeitnowScraper().scrape(pages=arb_pages)
                    all_jobs += j; step += 1
                    log(f"   ✅ {len(j)} jobs from Arbeitnow")

                if use_muse:
                    log("📡 Scraping The Muse...")
                    progress.progress(int(100 * step / total_steps), text="The Muse...")
                    j = TheMuseScraper().scrape(pages=muse_pages)
                    all_jobs += j; step += 1
                    log(f"   ✅ {len(j)} jobs from The Muse")

                if use_wuzzuf:
                    log(f"📡 Scraping Wuzzuf ({len(wuzzuf_keywords)} keywords × {wuzzuf_pages} pages)...")
                    progress.progress(int(100 * step / total_steps), text="Wuzzuf...")
                    j = WuzzufScraper().scrape(
                        keywords=wuzzuf_keywords, pages_per_keyword=wuzzuf_pages
                    )
                    all_jobs += j; step += 1
                    log(f"   ✅ {len(j)} jobs from Wuzzuf")

                # Merge with existing
                existing_df = pd.DataFrame()
                for path in ["data/jobs.csv", "docs/ai_jobs_market_2025_2026.csv"]:
                    if os.path.exists(path):
                        try:
                            existing_df = pd.read_csv(path)
                            log(f"   📂 Loaded {len(existing_df)} existing jobs from {path}")
                            break
                        except Exception:
                            pass

                combined = pd.concat([existing_df, pd.DataFrame(all_jobs)], ignore_index=True)
                before = len(combined)
                combined.drop_duplicates(subset=["job_title", "company"], keep="first", inplace=True)
                log(f"   🗑️  Removed {before - len(combined)} duplicates")

                combined.to_csv("data/jobs_combined.csv", index=False)
                progress.progress(100, text="Done!")
                log(f"💾 Saved {len(combined):,} jobs → data/jobs_combined.csv")

                st.success(f"✅ **{len(combined):,} jobs** saved to `data/jobs_combined.csv`")

                # Source breakdown
                if "source" in combined.columns:
                    st.markdown("### 📊 Jobs by source")
                    st.bar_chart(combined["source"].value_counts())

                # Preview
                display_cols = [c for c in ["job_title","company","location","remote_work","source"]
                                if c in combined.columns]
                st.markdown("### 👀 Preview")
                st.dataframe(combined[display_cols].head(25), use_container_width=True)

                st.download_button(
                    "⬇️ Download jobs_combined.csv",
                    combined.to_csv(index=False).encode(),
                    "jobs_combined.csv", "text/csv",
                    use_container_width=True,
                )

            except Exception as e:
                st.error(f"❌ Scraping failed: {e}")
                progress.progress(100)

# ═══════════════════════════════════════════════════════════════
# TAB 5 – Full Assessment
# ═══════════════════════════════════════════════════════════════
with tab5:
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
                p = {k: v for k, v in st.session_state.github_analysis.get("profile", {}).items()
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
    st.success("✅ Groq API") if groq_key else st.error("❌ No API key")
    st.success("✅ CV analyzed")     if st.session_state.cv_analysis     else st.info("⬜ CV")
    st.success("✅ GitHub analyzed") if st.session_state.github_analysis else st.info("⬜ GitHub")
    st.success("✅ Jobs matched")    if st.session_state.job_matches      else st.info("⬜ Jobs")

    st.markdown("---")
    db_f = ("data/jobs_combined.csv" if os.path.exists("data/jobs_combined.csv")
            else "data/jobs.csv"     if os.path.exists("data/jobs.csv") else None)
    if db_f:
        try:
            import pandas as pd
            n = len(pd.read_csv(db_f))
            st.success(f"✅ {n:,} jobs in DB")
        except Exception:
            st.warning("⚠️ DB unreadable")
    else:
        st.warning("⚠️ No DB — Scrape Jobs first")

    st.markdown("---")
    if st.button("🗑️ Clear Results", use_container_width=True):
        for k in ["cv_analysis", "github_analysis", "job_matches"]:
            st.session_state[k] = None
        st.rerun()
    st.caption("Phase 1 ✅ | Powered by Groq")