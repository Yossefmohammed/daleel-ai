"""
Career AI Assistant
Auto-builds Graph RAG index on startup.
Chatbot streams word-by-word, feels human.
"""

import os, time
import streamlit as st
from dotenv import load_dotenv
from datetime import datetime

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

/* Chat message bubbles */
.chat-message {
    display: flex;
    margin-bottom: 1rem;
    align-items: flex-start;
}
.chat-message-user {
    justify-content: flex-end;
}
.chat-message-assistant {
    justify-content: flex-start;
}
.chat-avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: #1e1e3a;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.2rem;
    margin: 0 8px;
    flex-shrink: 0;
}
.chat-bubble {
    max-width: 80%;
    padding: 10px 14px;
    border-radius: 18px;
    background: rgba(30, 30, 60, 0.9);
    border: 1px solid rgba(0, 217, 255, 0.15);
    font-size: 15px;
    line-height: 1.5;
    box-shadow: 0 2px 6px rgba(0,0,0,0.2);
}
.chat-bubble-user {
    background: linear-gradient(135deg, #0055cc, #003399);
    border: none;
    color: white;
}
.chat-bubble-assistant {
    background: rgba(20, 20, 50, 0.9);
}
.chat-time {
    font-size: 0.7rem;
    color: #aaa;
    margin-top: 4px;
    text-align: right;
}
.typing-indicator {
    background: rgba(20, 20, 50, 0.9);
    border-radius: 18px;
    padding: 10px 14px;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: #00D9FF;
}
.typing-dot {
    width: 8px;
    height: 8px;
    background: #00D9FF;
    border-radius: 50%;
    animation: pulse 1.2s infinite;
}
.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes pulse {
    0%, 60%, 100% { opacity: 0.3; transform: scale(0.8); }
    30% { opacity: 1; transform: scale(1.2); }
}
.chat-container {
    max-height: 65vh;
    overflow-y: auto;
    padding-right: 10px;
    margin-bottom: 1rem;
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

# ── CHANGED: No pinned welcome message ───────────────────────────────────────
# Start with empty chat history (or a minimal greeting - uncomment if desired)
if st.session_state.chat_messages is None:
    st.session_state.chat_messages = []   # completely empty
    # Optional minimal opener:
    # st.session_state.chat_messages = [{
    #     "role": "assistant",
    #     "content": "Hey there 👋 I'm your career assistant. Ask me anything — jobs, resume tips, interview prep, or just career advice.",
    #     "time": datetime.now().isoformat()
    # }]

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
# TAB 1 — Career Chat (Human‑like UI)
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
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.chat_messages = []
            st.rerun()
    with cc2:
        tone = st.radio(
            "Tone", ["Professional", "Friendly", "Formal", "Concise"],
            horizontal=True, label_visibility="collapsed"
        )

    st.divider()

    # Chat container with scroll
    chat_container = st.container()
    with chat_container:
        st.markdown('<div class="chat-container" id="chat-scroll">', unsafe_allow_html=True)
        # Render existing messages
        for msg in st.session_state.chat_messages:
            role = msg["role"]
            content = msg["content"]
            timestamp = msg.get("time")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    time_str = dt.strftime("%I:%M %p")
                except:
                    time_str = ""
            else:
                time_str = ""

            if role == "user":
                st.markdown(f'''
                <div class="chat-message chat-message-user">
                    <div style="flex-grow:1"></div>
                    <div class="chat-bubble chat-bubble-user">
                        {content}
                        <div class="chat-time">{time_str}</div>
                    </div>
                    <div class="chat-avatar">👤</div>
                </div>
                ''', unsafe_allow_html=True)
            else:
                st.markdown(f'''
                <div class="chat-message chat-message-assistant">
                    <div class="chat-avatar">🤖</div>
                    <div class="chat-bubble chat-bubble-assistant">
                        {content}
                        <div class="chat-time">{time_str}</div>
                    </div>
                </div>
                ''', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Auto-scroll JavaScript
    st.markdown("""
    <script>
    var chatDiv = document.getElementById('chat-scroll');
    if(chatDiv) chatDiv.scrollTop = chatDiv.scrollHeight;
    </script>
    """, unsafe_allow_html=True)

    # Chat input
    if prompt := st.chat_input("Ask me anything about jobs, your career, or say 'write me a cover letter'..."):

        # Add user message
        user_time = datetime.now().isoformat()
        st.session_state.chat_messages.append({"role": "user", "content": prompt, "time": user_time})
        # Re-render
        with chat_container:
            st.markdown(f'''
            <div class="chat-message chat-message-user">
                <div style="flex-grow:1"></div>
                <div class="chat-bubble chat-bubble-user">
                    {prompt}
                    <div class="chat-time">{datetime.now().strftime("%I:%M %p")}</div>
                </div>
                <div class="chat-avatar">👤</div>
            </div>
            ''', unsafe_allow_html=True)

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

        # ── System prompt (human-like, no automatic job stats) ─────────────────
        tone_guide = {
            "Professional": "Write in a confident, professional tone. Avoid filler phrases.",
            "Friendly":     "Be warm, conversational, and encouraging — like a helpful friend.",
            "Formal":       "Use formal business English. No contractions. Polished.",
            "Concise":      "Be extremely concise. Short sentences. No padding. Get to the point.",
        }.get(tone, "")

        user_ctx = f"\n\nUser profile:\n{chr(10).join(ctx_parts)}" if ctx_parts else ""

        rag_block = (
            f"\n\nREAL JOB DATA (retrieved via Graph RAG — use this if relevant to the user's question):\n{rag_context}\n\n"
            "If the user asks for specific jobs, mention titles and companies from this data. "
            "If the data doesn't cover the question, say so and answer from general knowledge. "
            "Do NOT list job data unless the user explicitly asks for it."
        ) if rag_context else (
            "\n\nNo job database is available right now. Answer from general career knowledge."
        )

        system = f"""You are a Career AI Assistant — a friendly, knowledgeable career coach.

Personality:
- You talk like a real human expert, not a chatbot. No "Certainly!" or "Of course!" — just answer naturally.
- You give specific, actionable advice, not generic platitudes.
- When writing emails or cover letters, produce the full text, ready to send.
- You remember context from earlier in the conversation.
- You occasionally ask a short follow-up question to help better.
- Do NOT start every conversation by listing job stats or salaries. Only mention job data if it directly answers the user's question.
{user_ctx}

{tone_guide}

{rag_block}"""

        history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.chat_messages[-14:]
            if m["role"] in ("user", "assistant")
        ]

        # ── Streaming response with typing indicator ─────────────────────────────
        with chat_container:
            # Show typing indicator
            typing_placeholder = st.empty()
            typing_placeholder.markdown('''
            <div class="chat-message chat-message-assistant">
                <div class="chat-avatar">🤖</div>
                <div class="typing-indicator">
                    <span>Assistant is typing</span>
                    <div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>
                </div>
            </div>
            ''', unsafe_allow_html=True)

            # Placeholder for actual response
            response_placeholder = st.empty()
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

                # Remove typing indicator
                typing_placeholder.empty()

                # Stream word by word
                for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        full_response += delta
                        response_placeholder.markdown(f'''
                        <div class="chat-message chat-message-assistant">
                            <div class="chat-avatar">🤖</div>
                            <div class="chat-bubble chat-bubble-assistant">
                                {full_response}▌
                                <div class="chat-time">{datetime.now().strftime("%I:%M %p")}</div>
                            </div>
                        </div>
                        ''', unsafe_allow_html=True)

                # Final response without cursor
                response_placeholder.markdown(f'''
                <div class="chat-message chat-message-assistant">
                    <div class="chat-avatar">🤖</div>
                    <div class="chat-bubble chat-bubble-assistant">
                        {full_response}
                        <div class="chat-time">{datetime.now().strftime("%I:%M %p")}</div>
                    </div>
                </div>
                ''', unsafe_allow_html=True)

            except Exception as e:
                response_placeholder.error(f"❌ Error: {e}")
                full_response = f"Error: {e}"

        # Save assistant message
        st.session_state.chat_messages.append({"role": "assistant", "content": full_response, "time": datetime.now().isoformat()})

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
            st.session_state.chat_messages.append({"role": "user", "content": s, "time": datetime.now().isoformat()})
            st.rerun()


# ... (the rest of the tabs (CV, GitHub, Job Matcher, Scrape, Assessment) and sidebar remain exactly the same as in the previous version) ...