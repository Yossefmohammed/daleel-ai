"""
Career AI Assistant
Auto-builds Graph RAG index on startup.
Chatbot streams word-by-word, feels human.
"""

import os, time
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="🎯 Career AI Assistant",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

from cv_analyzer   import CVAnalyzer
from github_analyzer import GitHubAnalyzer
from job_matcher   import JobMatcher

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #0a0a1a 0%, #0f0c29 40%, #1a1035 100%);
    color: #E8E8F0;
}
h1 {
    text-align: center; font-size: 2.6rem; font-weight: 800;
    background: linear-gradient(135deg, #00D9FF, #0091FF);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
h2, h3 { color: #00D9FF; }
.stTabs [data-baseweb="tab-list"] button { font-size: 1rem; font-weight: 600; }
.stChatMessage {
    background: rgba(20, 20, 50, 0.8) !important;
    border: 1px solid rgba(0, 217, 255, 0.12) !important;
    border-radius: 16px !important;
    margin: 10px 0 !important;
    padding: 4px 8px !important;
}
[data-testid="stChatMessageContent"] {
    color: #E8E8F0 !important;
    font-size: 15px !important;
    line-height: 1.8 !important;
}
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

st.title("🎯 Career AI Assistant")
st.markdown(
    "<p style='text-align:center;color:#aaa;font-size:1rem;'>"
    "Graph RAG · CV Analysis · GitHub · Job Matching · Live Scraping"
    "</p>",
    unsafe_allow_html=True,
)
st.divider()

# ── Session state ─────────────────────────────────────────────────────────────
_defaults = {
    "cv_analysis": None, "github_analysis": None, "job_matches": None,
    "chat_messages": None,
    "rag_embeddings": None, "rag_chunks": None,
    "rag_meta": None, "rag_graph": None, "rag_model": None,
    "rag_stats": None, "rag_load_attempted": False,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

groq_key = os.getenv("GROQ_API_KEY", "")
if not groq_key:
    st.error("❌ GROQ_API_KEY not set in `.env`")
    st.stop()


# ── Auto-load or auto-build RAG index ────────────────────────────────────────
def _auto_setup_rag():
    """
    Called once per session.
    1. If index exists and is fresh  → load it silently.
    2. If data exists but index is stale/missing → build automatically.
    3. If no data at all → skip (chatbot works without RAG).
    """
    if st.session_state.rag_load_attempted:
        return
    st.session_state.rag_load_attempted = True

    from rag_ingest import index_exists, data_is_newer_than_index, build_index, load_index, JOB_CSV_PATHS

    data_available = any(os.path.exists(p) for p in JOB_CSV_PATHS)

    # ── Case 1: index fresh, just load ───────────────────────────────────────
    if index_exists() and not data_is_newer_than_index():
        try:
            from sentence_transformers import SentenceTransformer
            emb, chunks, meta, graph = load_index()
            model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            st.session_state.rag_embeddings = emb
            st.session_state.rag_chunks     = chunks
            st.session_state.rag_meta       = meta
            st.session_state.rag_graph      = graph
            st.session_state.rag_model      = model
            return
        except Exception as e:
            st.sidebar.warning(f"⚠️ RAG load: {e}")

    # ── Case 2: data exists, build automatically ──────────────────────────────
    if data_available:
        bar  = st.sidebar.progress(0, text="🔨 Building RAG index automatically...")
        info = st.sidebar.empty()

        def _cb(pct, msg):
            bar.progress(pct, text=msg)
            info.caption(msg)

        try:
            stats = build_index(progress_callback=_cb)
            st.session_state.rag_stats = stats

            from sentence_transformers import SentenceTransformer
            emb, chunks, meta, graph = load_index()
            model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            st.session_state.rag_embeddings = emb
            st.session_state.rag_chunks     = chunks
            st.session_state.rag_meta       = meta
            st.session_state.rag_graph      = graph
            st.session_state.rag_model      = model

            bar.progress(100, text="✅ RAG index ready!")
            time.sleep(1)
            bar.empty()
            info.empty()
        except Exception as e:
            bar.empty()
            info.empty()
            st.sidebar.warning(f"⚠️ Auto-build failed: {e}")

    # Case 3: no data → silently skip


_auto_setup_rag()

rag_ready = (
    st.session_state.rag_embeddings is not None and
    st.session_state.rag_model      is not None
)

# ── Welcome message ───────────────────────────────────────────────────────────
if st.session_state.chat_messages is None:
    if rag_ready:
        count = len(st.session_state.rag_chunks or [])
        welcome = (
            f"👋 Hey! I'm your **Career AI Assistant**, and I'm fully loaded — "
            f"I've got **{count:,} real job listings** in my knowledge base right now.\n\n"
            "Ask me anything, like:\n"
            "- *\"What Python jobs are available in Cairo?\"*\n"
            "- *\"Write me a cover letter for a senior backend role\"*\n"
            "- *\"Which companies are hiring data scientists remotely?\"*\n"
            "- *\"Help me reply to this recruiter...\"*"
        )
    else:
        welcome = (
            "👋 Hey! I'm your **Career AI Assistant**.\n\n"
            "I don't have job data loaded yet — scrape some jobs first using "
            "the **🌐 Scrape Jobs** tab, then I'll automatically index them.\n\n"
            "In the meantime I can still help with:\n"
            "- 📝 Writing cover letters and emails\n"
            "- 💬 Interview prep and Q&A practice\n"
            "- 🎯 Career advice and salary negotiation"
        )
    st.session_state.chat_messages = [{"role": "assistant", "content": welcome}]


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "💬 Career Chat",
    "📄 CV Analyzer",
    "🐙 GitHub Profile",
    "💼 Job Matcher",
    "🌐 Scrape Jobs",
    "📊 Full Assessment",
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Career Chat (Graph RAG · streaming · human-like)
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.header("💬 Career AI Chat")

    # Status strip
    if rag_ready:
        n = len(st.session_state.rag_chunks or [])
        g = st.session_state.rag_graph
        st.success(
            f"🕸️ **Graph RAG active** — {n:,} job listings · "
            f"{g.number_of_nodes():,} knowledge nodes · "
            f"{g.number_of_edges():,} connections"
        )
    else:
        st.info("💡 No job data indexed yet. Scrape jobs and the index builds automatically.")

    # Build user context from other tabs
    ctx_parts = []
    if st.session_state.cv_analysis and st.session_state.cv_analysis.get("success"):
        a = st.session_state.cv_analysis.get("analysis", {})
        if isinstance(a, dict):
            ctx_parts.append(
                f"User CV: skills={', '.join(a.get('skills',[]))}; "
                f"tech={', '.join(a.get('technologies',[]))}; "
                f"level={a.get('seniority_level','?')}; "
                f"summary: {a.get('summary','')}"
            )
    if st.session_state.github_analysis and st.session_state.github_analysis.get("success"):
        p  = st.session_state.github_analysis.get("profile", {})
        ga = st.session_state.github_analysis.get("analysis", {})
        ctx_parts.append(
            f"User GitHub: repos={p.get('public_repos','?')}, "
            f"top langs={list(p.get('languages',{}).keys())[:4]}, "
            f"readiness={ga.get('career_readiness','?') if isinstance(ga,dict) else '?'}"
        )

    # Controls
    cc1, cc2 = st.columns([1, 5])
    with cc1:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.chat_messages = [
                {"role": "assistant", "content": "Chat cleared! What can I help you with?"}
            ]
            st.rerun()
    with cc2:
        tone = st.radio(
            "Tone", ["Professional", "Friendly", "Formal", "Concise"],
            horizontal=True, label_visibility="collapsed"
        )

    st.divider()

    # Render history
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("Ask me anything about jobs, your career, or say 'write me a cover letter'..."):

        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # ── Graph RAG retrieval ────────────────────────────────────────────────
        rag_context = ""
        if rag_ready:
            try:
                from rag_retriever import GraphRAGRetriever
                retriever = GraphRAGRetriever(
                    embeddings = st.session_state.rag_embeddings,
                    chunks     = st.session_state.rag_chunks,
                    meta       = st.session_state.rag_meta,
                    graph      = st.session_state.rag_graph,
                    model      = st.session_state.rag_model,
                    k=7, graph_k=6, hop_depth=2,
                )
                rag_context = retriever.get_context_string(prompt, max_chars=4500)
            except Exception as e:
                st.sidebar.warning(f"Retrieval note: {e}")

        # ── System prompt (human-like personality) ────────────────────────────
        tone_guide = {
            "Professional": "Write in a confident, professional tone. Avoid filler phrases.",
            "Friendly":     "Be warm, conversational, and encouraging — like a helpful friend.",
            "Formal":       "Use formal business English. No contractions. Polished.",
            "Concise":      "Be extremely concise. Short sentences. No padding. Get to the point.",
        }.get(tone, "")

        user_ctx = f"\n\nUser profile:\n{chr(10).join(ctx_parts)}" if ctx_parts else ""

        rag_block = (
            f"\n\nREAL JOB DATA (retrieved via Graph RAG — cite this in your answer):\n{rag_context}\n\n"
            "Use the job data above to give specific, grounded answers. "
            "If a job listing is relevant, mention the title and company. "
            "If the data doesn't cover the question, say so and answer from general knowledge."
        ) if rag_context else (
            "\n\nNo job database is available right now. Answer from general career knowledge."
        )

        system = f"""You are a Career AI Assistant — knowledgeable, direct, and genuinely helpful.

Personality:
- You talk like a real expert, not a chatbot. No "Certainly!" or "Of course!" — just answer.
- You give specific advice, not generic platitudes.
- When writing emails or cover letters, you produce the full text, ready to send.
- You remember context from earlier in the conversation.
- You occasionally ask a short follow-up question to help better.
{user_ctx}{rag_block}

{tone_guide}"""

        history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.chat_messages[-14:]
            if m["role"] in ("user", "assistant")
        ]

        # ── Streaming response ─────────────────────────────────────────────────
        with st.chat_message("assistant"):
            placeholder   = st.empty()
            full_response = ""

            try:
                from groq import Groq
                client = Groq(api_key=groq_key)

                stream = client.chat.completions.create(
                    model       = "llama-3.3-70b-versatile",
                    messages    = [{"role": "system", "content": system}] + history,
                    temperature = 0.72,
                    max_tokens  = 1400,
                    stream      = True,
                )

                for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        full_response += delta
                        placeholder.markdown(full_response + "▌")

                placeholder.markdown(full_response)

            except Exception as e:
                full_response = f"❌ Error: {e}"
                placeholder.error(full_response)

        st.session_state.chat_messages.append(
            {"role": "assistant", "content": full_response}
        )

    # Quick prompts
    st.markdown("---")
    st.markdown("**💡 Try asking:**")
    suggestions = [
        "What Python jobs are available right now?",
        "Find remote data science jobs",
        "What tech companies are hiring in Cairo?",
        "Write a cover letter for a senior backend developer role",
        "How do I answer 'Why should we hire you?'",
        "Draft a follow-up email after an interview",
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
    c1, c2 = st.columns([3, 1])
    with c1:
        up = st.file_uploader("Upload your CV (PDF)", type=["pdf"])
    with c2:
        st.write(""); st.write("")
        go_cv = st.button("🔍 Analyze", use_container_width=True)

    if go_cv:
        if not up:
            st.warning("⚠️ Upload a PDF first.")
        else:
            temp = f"temp_{up.name}"
            try:
                with open(temp, "wb") as f: f.write(up.getbuffer())
                with st.spinner("Analyzing your CV..."):
                    result = CVAnalyzer().analyze_cv(temp)
                if result.get("success"):
                    st.session_state.cv_analysis = result
                    st.success("✅ Done! The chatbot now knows your CV profile.")
                else:
                    st.error(result.get("error"))
            except Exception as e:
                st.error(str(e))
            finally:
                if os.path.exists(temp): os.remove(temp)

    if st.session_state.cv_analysis:
        a = st.session_state.cv_analysis.get("analysis", {})
        if isinstance(a, dict):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**🛠️ Skills**")
                for s in a.get("skills",      []): st.markdown(f"- {s}")
                st.markdown("**💻 Technologies**")
                for t in a.get("technologies", []): st.markdown(f"- {t}")
            with c2:
                st.markdown("**🎓 Education**")
                for e in a.get("education",   []):
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
    c1, c2 = st.columns([3, 1])
    with c1:
        uname = st.text_input("GitHub Username", placeholder="e.g. torvalds")
    with c2:
        st.write(""); st.write("")
        go_gh = st.button("🔍 Analyze", use_container_width=True, key="gh_btn")

    if go_gh:
        if not uname.strip():
            st.warning("⚠️ Enter a username.")
        else:
            with st.spinner("Fetching profile..."):
                try:
                    r = GitHubAnalyzer().analyze_github_profile(uname.strip())
                    if r.get("success"):
                        st.session_state.github_analysis = r
                        st.success("✅ Done! Chatbot knows your GitHub profile.")
                    else:
                        st.error(r.get("error"))
                except Exception as e:
                    st.error(str(e))

    if st.session_state.github_analysis:
        p  = st.session_state.github_analysis.get("profile", {})
        ga = st.session_state.github_analysis.get("analysis", {})
        c1, c2, c3 = st.columns(3)
        c1.metric("Followers",    p.get("followers",    0))
        c2.metric("Public Repos", p.get("public_repos", 0))
        c3.metric("Following",    p.get("following",    0))
        if p.get("languages"):
            st.bar_chart(p["languages"])
        if isinstance(ga, dict):
            st.markdown(
                f"**Strength:** `{ga.get('profile_strength','?')}/10`  |  "
                f"**Readiness:** `{ga.get('career_readiness','?')}`"
            )
            for r in ga.get("recommendations", []): st.markdown(f"- {r}")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Job Matcher
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.header("💼 Job Matcher")
    if not (os.path.exists("data/jobs_combined.csv") or os.path.exists("data/jobs.csv")):
        st.warning("⚠️ No job database. Use 🌐 Scrape Jobs first.")

    c1, c2 = st.columns(2)
    with c1:
        skills_in = st.text_area("Skills (one per line)",
                                  placeholder="Python\nReact\nDocker", height=110)
        exp = st.number_input("Years of Experience", 0, 50, 2)
    with c2:
        sen   = st.selectbox("Seniority", ["Junior", "Mid-Level", "Senior"])
        roles = st.multiselect("Interested Roles", [
            "Full Stack Developer","Backend Engineer","Frontend Developer",
            "Data Scientist","ML Engineer","DevOps Engineer","Product Manager",
        ])

    if st.button("🔍 Find Jobs", use_container_width=True):
        skills = [s.strip() for s in skills_in.splitlines() if s.strip()]
        if not skills:
            st.warning("⚠️ Enter at least one skill.")
        else:
            with st.spinner("Matching..."):
                try:
                    r = JobMatcher().match_jobs({
                        "skills": skills, "experience_years": exp,
                        "seniority_level": sen.lower(), "interested_roles": roles,
                    })
                    if r.get("success"):
                        st.session_state.job_matches = r
                        st.success("✅ Done!")
                    else:
                        st.warning(r.get("error"))
                except Exception as e:
                    st.error(str(e))

    if st.session_state.job_matches:
        m = st.session_state.job_matches.get("matches", {})
        if isinstance(m, dict):
            for job in m.get("jobs", []):
                with st.expander(
                    f"**{job.get('job_title','?')}** @ {job.get('company','?')} "
                    f"— {job.get('match_score','?')}%"
                ):
                    st.markdown(f"**Why:** {job.get('reason','')}")
                    st.markdown(f"**Required:** {', '.join(job.get('required_skills',[]))}")
                    st.markdown(f"**Nice to have:** {', '.join(job.get('nice_to_have',[]))}")
            st.info(m.get("summary", ""))
        else:
            st.code(str(m))


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
            st.success("✅ After scraping, the RAG index rebuilds automatically on next startup.")
        except Exception:
            pass

    st.divider()
    ca, cb = st.columns(2)
    with ca:
        st.markdown("#### ✅ Sources")
        use_ro  = st.checkbox("🌍 RemoteOK",  value=True)
        use_arb = st.checkbox("🇩🇪 Arbeitnow", value=True)
        use_mu  = st.checkbox("🇺🇸 The Muse",  value=True)
        use_wu  = st.checkbox("🇪🇬 Wuzzuf",    value=True)
    with cb:
        st.markdown("#### ❌ LinkedIn")
        st.error(
            "Not supported — ToS, JS rendering, bot detection & legal risk.\n\n"
            "✅ [LinkedIn Jobs API](https://developer.linkedin.com/product-catalog/jobs) for official access."
        )

    st.divider()
    cc1, cc2, cc3, cc4 = st.columns(4)
    ro_lim  = cc1.slider("RemoteOK",     20, 200, 100, 20, disabled=not use_ro)
    arb_pg  = cc2.slider("Arbeitnow pg",  1,  10,   3,    disabled=not use_arb)
    mu_pg   = cc3.slider("Muse pages",    1,   5,   2,    disabled=not use_mu)
    wu_pg   = cc4.slider("Wuzzuf pg/kw",  1,   5,   2,    disabled=not use_wu)

    if use_wu:
        wu_kw_raw = st.text_area(
            "Wuzzuf keywords (comma-separated)",
            value="software engineer, python developer, data scientist, frontend developer, backend developer, full stack developer, devops",
            height=65,
        )
        wu_kw = [k.strip() for k in wu_kw_raw.split(",") if k.strip()]
    else:
        wu_kw = []

    if st.button("🚀 Scrape Now", use_container_width=True, type="primary"):
        if not any([use_ro, use_arb, use_mu, use_wu]):
            st.warning("Select at least one source.")
        else:
            prog = st.progress(0, text="Starting...")
            lb   = st.empty()
            logs: list = []

            def log(msg):
                logs.append(msg)
                lb.markdown("\n\n".join(f"`{l}`" for l in logs[-10:]))

            try:
                from data_scraper import RemoteOKScraper, ArbeitnowScraper, TheMuseScraper, WuzzufScraper
                import pandas as pd
                os.makedirs("data", exist_ok=True)
                all_j: list = []
                tot = sum([use_ro, use_arb, use_mu, use_wu])
                step = 0

                if use_ro:
                    log("📡 RemoteOK..."); prog.progress(int(100*step/tot))
                    j = RemoteOKScraper().scrape(limit=ro_lim)
                    all_j += j; step += 1; log(f"   ✅ {len(j)} jobs")
                if use_arb:
                    log("📡 Arbeitnow..."); prog.progress(int(100*step/tot))
                    j = ArbeitnowScraper().scrape(pages=arb_pg)
                    all_j += j; step += 1; log(f"   ✅ {len(j)} jobs")
                if use_mu:
                    log("📡 The Muse..."); prog.progress(int(100*step/tot))
                    j = TheMuseScraper().scrape(pages=mu_pg)
                    all_j += j; step += 1; log(f"   ✅ {len(j)} jobs")
                if use_wu:
                    log(f"📡 Wuzzuf ({len(wu_kw)} keywords)..."); prog.progress(int(100*step/tot))
                    j = WuzzufScraper().scrape(keywords=wu_kw, pages_per_keyword=wu_pg)
                    all_j += j; step += 1; log(f"   ✅ {len(j)} jobs")

                existing = pd.DataFrame()
                for p2 in ["data/jobs.csv", "docs/ai_jobs_market_2025_2026.csv"]:
                    if os.path.exists(p2):
                        try: existing = pd.read_csv(p2); log(f"   📂 {len(existing)} existing"); break
                        except Exception: pass

                combined = pd.concat([existing, pd.DataFrame(all_j)], ignore_index=True)
                before   = len(combined)
                combined.drop_duplicates(subset=["job_title","company"], keep="first", inplace=True)
                log(f"   🗑️ {before-len(combined)} duplicates removed")
                combined.to_csv("data/jobs_combined.csv", index=False)
                prog.progress(100, text="Done!")
                log(f"💾 {len(combined):,} jobs saved — RAG index will rebuild on next app load")

                st.success(
                    f"✅ **{len(combined):,} jobs** saved. "
                    "**Restart the app** (or press R) and the RAG index will rebuild automatically."
                )
                if "source" in combined.columns:
                    st.bar_chart(combined["source"].value_counts())
                display_cols = [c for c in ["job_title","company","location","remote_work","source"] if c in combined.columns]
                st.dataframe(combined[display_cols].head(25), use_container_width=True)
                st.download_button("⬇️ Download CSV", combined.to_csv(index=False).encode(),
                                   "jobs_combined.csv", "text/csv", use_container_width=True)
            except Exception as e:
                st.error(f"❌ {e}"); prog.progress(100)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 6 — Full Assessment
# ═══════════════════════════════════════════════════════════════════════════════
with tab6:
    st.header("📊 Full Career Assessment")
    has = any([st.session_state.cv_analysis, st.session_state.github_analysis, st.session_state.job_matches])
    if not has:
        st.info("Complete at least one analysis in the other tabs first.")
    else:
        if st.button("📋 Generate Report", use_container_width=True):
            if st.session_state.cv_analysis:
                st.markdown("### 📄 CV")
                a = st.session_state.cv_analysis.get("analysis", {})
                st.json(a) if isinstance(a, dict) else st.code(str(a))
            if st.session_state.github_analysis:
                st.markdown("### 🐙 GitHub")
                p = {k: v for k, v in st.session_state.github_analysis.get("profile",{}).items() if k != "success"}
                st.json(p)
            if st.session_state.job_matches:
                st.markdown("### 💼 Matches")
                m = st.session_state.job_matches.get("matches", {})
                st.json(m) if isinstance(m, dict) else st.code(str(m))
            st.success("✅ Done!")


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🎯 Career AI")
    st.markdown("---")

    # RAG status
    st.subheader("🕸️ Graph RAG")
    if rag_ready:
        n = len(st.session_state.rag_chunks or [])
        g = st.session_state.rag_graph
        st.success(f"✅ Active — {n:,} chunks")
        st.caption(f"🕸️ {g.number_of_nodes():,} nodes · {g.number_of_edges():,} edges")
    else:
        st.warning("⚠️ Not loaded")
        st.caption("Scrape jobs → restart app → auto-builds")

    # Manual rebuild button (for after scraping without restart)
    if st.button("🔄 Rebuild Index Now", use_container_width=True):
        from rag_ingest import build_index, load_index
        bar  = st.progress(0)
        info = st.empty()
        def _cb(pct, msg): bar.progress(pct, text=msg); info.caption(msg)
        try:
            stats = build_index(progress_callback=_cb)
            from sentence_transformers import SentenceTransformer
            emb, chunks, meta, graph = load_index()
            model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            st.session_state.rag_embeddings = emb
            st.session_state.rag_chunks     = chunks
            st.session_state.rag_meta       = meta
            st.session_state.rag_graph      = graph
            st.session_state.rag_model      = model
            st.session_state.rag_stats      = stats
            bar.empty(); info.empty()
            st.success(f"✅ {stats['chunks']:,} chunks · {stats['graph_nodes']:,} nodes")
            st.rerun()
        except Exception as e:
            st.error(f"❌ {e}")

    st.markdown("---")
    st.subheader("📊 Status")
    st.success("✅ Groq API")        if groq_key                              else st.error("❌ No key")
    st.success("✅ CV analyzed")     if st.session_state.cv_analysis          else st.info("⬜ CV")
    st.success("✅ GitHub analyzed") if st.session_state.github_analysis      else st.info("⬜ GitHub")
    st.success("✅ Jobs matched")    if st.session_state.job_matches           else st.info("⬜ Jobs")

    db_f = ("data/jobs_combined.csv" if os.path.exists("data/jobs_combined.csv")
            else "data/jobs.csv"     if os.path.exists("data/jobs.csv") else None)
    if db_f:
        try:
            import pandas as pd
            st.success(f"✅ {len(pd.read_csv(db_f)):,} jobs in DB")
        except Exception:
            st.warning("⚠️ DB unreadable")
    else:
        st.warning("⚠️ No job DB yet")

    st.markdown("---")
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.chat_messages = None
        st.rerun()
    if st.button("🗑️ Clear All", use_container_width=True):
        for k in _defaults: st.session_state[k] = None
        st.rerun()
    st.caption("Graph RAG ✅ | Powered by Groq")