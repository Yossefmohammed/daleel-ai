"""
Career AI Assistant — app.py
Tabs: Career Chat (Graph RAG) · CV Analyzer · GitHub · Job Matcher · Scrape Jobs · Assessment
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
h1 { text-align:center; font-size:2.8rem; font-weight:800;
     background:linear-gradient(135deg,#00D9FF,#0091FF);
     -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
h2, h3 { color: #00D9FF; }
.stTabs [data-baseweb="tab-list"] button { font-size:1rem; font-weight:600; }
.stChatMessage {
    background: rgba(25,25,55,0.75) !important;
    border: 1px solid rgba(0,217,255,0.15) !important;
    border-radius: 14px !important;
    margin: 8px 0 !important;
}
[data-testid="stChatMessageContent"] {
    color: #E8E8F0 !important; font-size:15px !important; line-height:1.75 !important;
}
footer { visibility:hidden; }
</style>
""", unsafe_allow_html=True)

st.title("🎯 Career AI Assistant")
st.markdown(
    "<p style='text-align:center;color:#aaa;'>Graph RAG · CV Analysis · GitHub Profiling · Job Matching</p>",
    unsafe_allow_html=True,
)
st.divider()

# ── Session state ──────────────────────────────────────────────────────────────
_defaults = {
    "cv_analysis":     None,
    "github_analysis": None,
    "job_matches":     None,
    "chat_messages":   None,
    "rag_collection":  None,
    "rag_graph":       None,
    "rag_stats":       None,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

if st.session_state.chat_messages is None:
    st.session_state.chat_messages = [{
        "role": "assistant",
        "content": (
            "👋 Hi! I'm your **Career AI Assistant** powered by **Graph RAG**.\n\n"
            "I can search through real job listings and documents to give you grounded answers.\n\n"
            "**Build the RAG index first** (sidebar → 🔨 Build Index), then ask me:\n"
            "- 🔍 *What Python jobs are available in Cairo?*\n"
            "- 📝 *Write a cover letter for a senior data scientist role*\n"
            "- 💬 *How do I prepare for a React developer interview?*\n"
            "- 📧 *Draft an email to a recruiter at a fintech company*"
        ),
    }]

groq_key = os.getenv("GROQ_API_KEY", "")
if not groq_key:
    st.error("❌ GROQ_API_KEY not set. Add it to your `.env` file.")
    st.stop()


# ── RAG loader (cached per session) ───────────────────────────────────────────
@st.cache_resource(ttl=3600)
def _load_rag():
    """Load ChromaDB collection + knowledge graph into memory."""
    try:
        from rag_ingest import get_collection, load_graph, index_exists
        if not index_exists():
            return None, None
        col   = get_collection()
        graph = load_graph()
        return col, graph
    except Exception as e:
        st.sidebar.warning(f"RAG load error: {e}")
        return None, None


# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "💬 Career Chat",
    "📄 CV Analyzer",
    "🐙 GitHub Profile",
    "💼 Job Matcher",
    "🌐 Scrape Jobs",
    "📊 Full Assessment",
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Career Chat (Graph RAG + streaming)
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.header("💬 Career AI Chat")

    # ── Load RAG index if available ────────────────────────────────────────────
    if st.session_state.rag_collection is None:
        col, graph = _load_rag()
        if col and graph:
            st.session_state.rag_collection = col
            st.session_state.rag_graph      = graph

    rag_ready = (
        st.session_state.rag_collection is not None and
        st.session_state.rag_graph      is not None
    )

    # ── Status banner ──────────────────────────────────────────────────────────
    if rag_ready:
        col_count = st.session_state.rag_collection.count()
        node_count = st.session_state.rag_graph.number_of_nodes()
        edge_count = st.session_state.rag_graph.number_of_edges()
        st.success(
            f"🕸️ **Graph RAG active** — "
            f"{col_count:,} chunks in vector store · "
            f"{node_count:,} graph nodes · "
            f"{edge_count:,} graph edges"
        )
    else:
        st.warning(
            "⚠️ **Graph RAG index not built yet.** "
            "Click **🔨 Build Index** in the sidebar to enable document-grounded answers. "
            "Until then the chatbot uses general knowledge only."
        )

    # ── CV context injection ───────────────────────────────────────────────────
    context_parts = []
    if st.session_state.cv_analysis and st.session_state.cv_analysis.get("success"):
        a = st.session_state.cv_analysis.get("analysis", {})
        if isinstance(a, dict):
            context_parts.append(
                f"User CV profile — skills: {', '.join(a.get('skills',[]))}; "
                f"technologies: {', '.join(a.get('technologies',[]))}; "
                f"seniority: {a.get('seniority_level','?')}; "
                f"summary: {a.get('summary','')}"
            )
    if st.session_state.github_analysis and st.session_state.github_analysis.get("success"):
        p  = st.session_state.github_analysis.get("profile", {})
        ga = st.session_state.github_analysis.get("analysis", {})
        context_parts.append(
            f"User GitHub — repos: {p.get('public_repos','?')}, "
            f"top languages: {list(p.get('languages',{}).keys())[:4]}, "
            f"readiness: {ga.get('career_readiness','?') if isinstance(ga,dict) else '?'}"
        )

    # ── Controls row ───────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns([1, 1, 4])
    with c1:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.chat_messages = [{
                "role": "assistant",
                "content": "Chat cleared! How can I help you?",
            }]
            st.rerun()
    with c2:
        tone = st.selectbox(
            "Tone", ["Professional", "Friendly", "Formal", "Concise"],
            label_visibility="collapsed",
        )

    st.divider()

    # ── Render history ─────────────────────────────────────────────────────────
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ── Chat input ─────────────────────────────────────────────────────────────
    if prompt := st.chat_input("Ask anything about jobs, career advice, or ask me to write something..."):

        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # ── Graph RAG retrieval ────────────────────────────────────────────────
        rag_context = ""
        rag_source_note = ""

        if rag_ready:
            try:
                from rag_retriever import GraphRAGRetriever
                retriever = GraphRAGRetriever(
                    collection = st.session_state.rag_collection,
                    graph      = st.session_state.rag_graph,
                    k          = 6,
                    graph_k    = 6,
                    hop_depth  = 2,
                )
                rag_context = retriever.get_context_string(prompt, max_chars=4000)
                if rag_context:
                    rag_source_note = "\n\n*(Answer grounded in your job database via Graph RAG)*"
            except Exception as e:
                st.sidebar.warning(f"RAG retrieval warning: {e}")

        # ── Build system prompt ────────────────────────────────────────────────
        tone_map = {
            "Professional": "Use a professional tone.",
            "Friendly":     "Use a warm, friendly, encouraging tone.",
            "Formal":       "Use a formal, polished business tone.",
            "Concise":      "Be concise — short sentences, no filler.",
        }

        system = f"""You are a Career AI Assistant. You help job seekers with:
- Writing cover letters, recruiter emails, LinkedIn messages
- Interview preparation and Q&A practice
- Career advice and skill gap analysis
- Salary negotiation guidance
- Searching and explaining job opportunities

{f"User profile context: {chr(10).join(context_parts)}" if context_parts else ""}

{f'''RETRIEVED JOB DATA (from Graph RAG search — use this to ground your answer):
{rag_context}

Important: Base your answer on the retrieved data above when relevant. If the data doesn't cover the question, use your general knowledge and say so.''' if rag_context else "No job database context available. Answer from general knowledge."}

Tone: {tone_map.get(tone, "")}
Format emails and messages cleanly, ready to send. Use bullet points for lists."""

        # ── Stream response ────────────────────────────────────────────────────
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.chat_messages[-12:]
            if m["role"] in ("user", "assistant")
        ]

        with st.chat_message("assistant"):
            placeholder   = st.empty()
            full_response = ""
            try:
                from groq import Groq
                client = Groq(api_key=groq_key)

                stream = client.chat.completions.create(
                    model       = "llama-3.3-70b-versatile",
                    messages    = [{"role": "system", "content": system}] + history,
                    temperature = 0.7,
                    max_tokens  = 1400,
                    stream      = True,          # ← word-by-word streaming
                )

                for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        full_response += delta
                        placeholder.markdown(full_response + "▌")   # blinking cursor

                placeholder.markdown(full_response + rag_source_note)
                full_response += rag_source_note

            except Exception as e:
                full_response = f"❌ Error: {e}"
                placeholder.error(full_response)

        st.session_state.chat_messages.append(
            {"role": "assistant", "content": full_response}
        )

    # ── Quick prompts ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("**💡 Quick prompts:**")
    suggestions = [
        "What Python jobs are available?",
        "Find remote data science jobs",
        "What jobs are hiring in Cairo?",
        "Write a cover letter for a backend developer role",
        "How do I answer 'Tell me about yourself'?",
        "Draft an email to a recruiter at a fintech company",
    ]
    cols = st.columns(3)
    for i, s in enumerate(suggestions):
        if cols[i % 3].button(s, key=f"q_{i}", use_container_width=True):
            st.session_state.chat_messages.append({"role": "user", "content": s})
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — CV Analyzer
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.header("📄 CV Analyzer")
    col1, col2 = st.columns([3, 1])
    with col1:
        uploaded_file = st.file_uploader("Upload your CV (PDF)", type=["pdf"])
    with col2:
        st.write(""); st.write("")
        go_cv = st.button("🔍 Analyze CV", use_container_width=True)

    if go_cv:
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
                    st.success("✅ CV analyzed! The chatbot now knows your profile.")
                else:
                    st.error(result.get("error"))
            except Exception as e:
                st.error(str(e))
            finally:
                if os.path.exists(temp):
                    os.remove(temp)

    if st.session_state.cv_analysis:
        a = st.session_state.cv_analysis.get("analysis", {})
        if isinstance(a, dict):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**🛠️ Skills**")
                for s in a.get("skills", []):      st.markdown(f"- {s}")
                st.markdown("**💻 Technologies**")
                for t in a.get("technologies", []): st.markdown(f"- {t}")
            with c2:
                st.markdown("**🎓 Education**")
                for e in a.get("education", []):
                    st.markdown(f"- {e.get('degree','?')} @ {e.get('school','?')}")
                st.markdown("**💼 Experience**")
                for ex in a.get("experience", []):
                    st.markdown(f"- {ex.get('title','?')} at {ex.get('company','?')}")
            st.markdown(f"**Seniority:** `{a.get('seniority_level','?')}`")
            st.info(a.get("summary", ""))
        else:
            st.code(str(a))


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — GitHub
# ═══════════════════════════════════════════════════════════════════════════════
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
            with st.spinner("Fetching..."):
                try:
                    result = GitHubAnalyzer().analyze_github_profile(username.strip())
                    if result.get("success"):
                        st.session_state.github_analysis = result
                        st.success("✅ Done! Chatbot knows your GitHub profile.")
                    else:
                        st.error(result.get("error"))
                except Exception as e:
                    st.error(str(e))

    if st.session_state.github_analysis:
        p  = st.session_state.github_analysis.get("profile", {})
        ga = st.session_state.github_analysis.get("analysis", {})
        c1, c2, c3 = st.columns(3)
        c1.metric("Followers",    p.get("followers", 0))
        c2.metric("Public Repos", p.get("public_repos", 0))
        c3.metric("Following",    p.get("following", 0))
        if p.get("languages"):
            st.bar_chart(p["languages"])
        if isinstance(ga, dict):
            st.markdown(
                f"**Strength:** `{ga.get('profile_strength','?')}/10`  |  "
                f"**Readiness:** `{ga.get('career_readiness','?')}`"
            )
            for r in ga.get("recommendations", []): st.markdown(f"- {r}")
        else:
            st.code(str(ga))


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Job Matcher
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.header("💼 Job Matcher")
    if not (os.path.exists("data/jobs_combined.csv") or os.path.exists("data/jobs.csv")):
        st.warning("⚠️ No job database. Use 🌐 Scrape Jobs first.")

    col1, col2 = st.columns(2)
    with col1:
        skills_input = st.text_area("Your Skills (one per line)",
                                    placeholder="Python\nReact\nDocker", height=120)
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
                    st.markdown(f"**Required:** {', '.join(job.get('required_skills',[]))}")
                    st.markdown(f"**Nice to have:** {', '.join(job.get('nice_to_have',[]))}")
            st.info(matches.get("summary", ""))
        else:
            st.code(str(matches))


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5 — Scrape Jobs
# ═══════════════════════════════════════════════════════════════════════════════
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
            "Not supported — ToS, JS rendering, bot detection, legal risk.\n\n"
            "✅ Use the official [LinkedIn Jobs API](https://developer.linkedin.com/product-catalog/jobs)."
        )

    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    remoteok_limit = c1.slider("RemoteOK",      20, 200, 100, 20, disabled=not use_remoteok)
    arb_pages      = c2.slider("Arbeitnow pgs",  1,  10,   3,    disabled=not use_arbeitnow)
    muse_pages     = c3.slider("Muse pgs",        1,   5,   2,    disabled=not use_muse)
    wuzzuf_pages   = c4.slider("Wuzzuf pgs/kw",   1,   5,   2,    disabled=not use_wuzzuf)

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
                from data_scraper import (RemoteOKScraper, ArbeitnowScraper,
                                          TheMuseScraper, WuzzufScraper)
                import pandas as pd
                os.makedirs("data", exist_ok=True)
                all_jobs: list = []
                total = sum([use_remoteok, use_arbeitnow, use_muse, use_wuzzuf])
                step  = 0

                if use_remoteok:
                    log("📡 RemoteOK...")
                    progress.progress(int(100 * step / total))
                    j = RemoteOKScraper().scrape(limit=remoteok_limit)
                    all_jobs += j; step += 1; log(f"   ✅ {len(j)} jobs")

                if use_arbeitnow:
                    log("📡 Arbeitnow...")
                    progress.progress(int(100 * step / total))
                    j = ArbeitnowScraper().scrape(pages=arb_pages)
                    all_jobs += j; step += 1; log(f"   ✅ {len(j)} jobs")

                if use_muse:
                    log("📡 The Muse...")
                    progress.progress(int(100 * step / total))
                    j = TheMuseScraper().scrape(pages=muse_pages)
                    all_jobs += j; step += 1; log(f"   ✅ {len(j)} jobs")

                if use_wuzzuf:
                    log(f"📡 Wuzzuf ({len(wuzzuf_keywords)} keywords)...")
                    progress.progress(int(100 * step / total))
                    j = WuzzufScraper().scrape(keywords=wuzzuf_keywords, pages_per_keyword=wuzzuf_pages)
                    all_jobs += j; step += 1; log(f"   ✅ {len(j)} jobs")

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
                before   = len(combined)
                combined.drop_duplicates(subset=["job_title","company"], keep="first", inplace=True)
                log(f"   🗑️  {before - len(combined)} duplicates removed")
                combined.to_csv("data/jobs_combined.csv", index=False)
                progress.progress(100, text="Done!")
                log(f"💾 {len(combined):,} jobs → data/jobs_combined.csv")
                st.success(f"✅ **{len(combined):,} jobs** saved! Now build the RAG index in the sidebar ↗")

                if "source" in combined.columns:
                    st.bar_chart(combined["source"].value_counts())

                display_cols = [c for c in ["job_title","company","location","remote_work","source"]
                                if c in combined.columns]
                st.dataframe(combined[display_cols].head(25), use_container_width=True)
                st.download_button("⬇️ Download", combined.to_csv(index=False).encode(),
                                   "jobs_combined.csv", "text/csv", use_container_width=True)
            except Exception as e:
                st.error(f"❌ {e}")
                progress.progress(100)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 6 — Full Assessment
# ═══════════════════════════════════════════════════════════════════════════════
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
                p = {k: v for k, v in st.session_state.github_analysis.get("profile",{}).items()
                     if k != "success"}
                st.json(p)
            if st.session_state.job_matches:
                st.markdown("### 💼 Job Matches")
                m = st.session_state.job_matches.get("matches", {})
                st.json(m) if isinstance(m, dict) else st.code(str(m))
            st.success("✅ Report ready!")


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.title("🎯 Career AI")
    st.markdown("---")

    # ── Graph RAG panel ────────────────────────────────────────────────────────
    st.subheader("🕸️ Graph RAG Index")

    from rag_ingest import index_exists
    idx_ready = index_exists()

    if idx_ready:
        st.success("✅ Index ready")
        if st.session_state.rag_stats:
            s = st.session_state.rag_stats
            st.caption(
                f"📦 {s.get('chunks',0):,} chunks\n"
                f"🕸️ {s.get('graph_nodes',0):,} nodes · {s.get('graph_edges',0):,} edges"
            )
    else:
        st.warning("⚠️ Not built yet")

    if st.button("🔨 Build / Rebuild Index", use_container_width=True, type="primary"):
        prog  = st.progress(0, text="Starting...")
        sbar  = st.empty()

        def _cb(pct, msg):
            prog.progress(pct, text=msg)
            sbar.caption(msg)

        try:
            from rag_ingest import build_index
            stats = build_index(progress_callback=_cb)
            st.session_state.rag_stats = stats

            # Reload into session
            st.cache_resource.clear()
            from rag_ingest import get_collection, load_graph
            st.session_state.rag_collection = get_collection()
            st.session_state.rag_graph      = load_graph()

            st.success(
                f"✅ Built! {stats['chunks']:,} chunks · "
                f"{stats['graph_nodes']:,} nodes · "
                f"{stats['graph_edges']:,} edges"
            )
            sbar.empty()
        except Exception as e:
            st.error(f"❌ {e}")
            prog.progress(100)

    st.markdown("---")

    # ── Other status ───────────────────────────────────────────────────────────
    st.subheader("📊 Status")
    st.success("✅ Groq API")        if groq_key else st.error("❌ No API key")
    st.success("✅ CV analyzed")     if st.session_state.cv_analysis     else st.info("⬜ CV")
    st.success("✅ GitHub analyzed") if st.session_state.github_analysis else st.info("⬜ GitHub")
    st.success("✅ Jobs matched")    if st.session_state.job_matches      else st.info("⬜ Jobs")

    db_f = ("data/jobs_combined.csv" if os.path.exists("data/jobs_combined.csv")
            else "data/jobs.csv"     if os.path.exists("data/jobs.csv") else None)
    if db_f:
        try:
            import pandas as pd
            st.success(f"✅ {len(pd.read_csv(db_f)):,} jobs in DB")
        except Exception:
            st.warning("⚠️ DB unreadable")
    else:
        st.warning("⚠️ No DB — Scrape first")

    st.markdown("---")
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.chat_messages = None
        st.rerun()
    if st.button("🗑️ Clear All", use_container_width=True):
        for k in _defaults:
            st.session_state[k] = None
        st.cache_resource.clear()
        st.rerun()
    st.caption("Graph RAG ✅ | Powered by Groq")