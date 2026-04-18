"""
Daleel – دليل – Career Intelligence Platform v1.1
=======================================================
Redesigned from Career AI Assistant v7.1

PHASE 1 SECURITY & STABILITY FIXES:
✅ API key validation on startup
✅ Rate limiting (6 requests/minute per session)
✅ User-friendly error messages (no stack traces exposed)
✅ Persistent storage for chat/feedback (SQLite fallback)
✅ Better exception handling with logging
✅ Session state management improvements
"""

import os, re, json, datetime, time, hashlib
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('daleel.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

# ══════════════════════════════════════════════════════════════════════════════
# CRITICAL: Validate API Keys on Startup
# ══════════════════════════════════════════════════════════════════════════════

def _validate_environment():
    """Validate required environment variables exist before app starts."""
    missing = []
    
    # Check for API key in environment or Streamlit secrets
    groq_key = None
    try:
        if hasattr(st, 'secrets') and "GROQ_API_KEY" in st.secrets:
            groq_key = st.secrets["GROQ_API_KEY"]
    except Exception:
        pass
    
    if not groq_key:
        groq_key = os.getenv("GROQ_API_KEY", "")
    
    if not groq_key:
        missing.append("GROQ_API_KEY")
    
    if missing:
        st.error(f"""
        ❌ **Missing Required Configuration**
        
        The following environment variables are not set:
        {', '.join(missing)}
        
        **To fix this:**
        1. Copy `.env.example` to `.env`
        2. Add your API keys to `.env`
        3. Restart the application
        
        Or if using Streamlit Cloud:
        1. Go to App Settings → Secrets
        2. Add your GROQ_API_KEY
        """)
        st.stop()
    
    return True

# Validate before doing anything else
_validate_environment()

st.set_page_config(
    page_title="Daleel · دليل",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# Rate Limiting
# ══════════════════════════════════════════════════════════════════════════════

class RateLimiter:
    """Simple in-memory rate limiter per session."""
    
    def __init__(self, max_requests=6, window_seconds=60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        
        if 'rate_limit_timestamps' not in st.session_state:
            st.session_state.rate_limit_timestamps = []
    
    def check_rate_limit(self) -> bool:
        """Returns True if request is allowed, False if rate limited."""
        now = time.time()
        
        # Remove timestamps outside the window
        st.session_state.rate_limit_timestamps = [
            ts for ts in st.session_state.rate_limit_timestamps
            if now - ts < self.window_seconds
        ]
        
        if len(st.session_state.rate_limit_timestamps) >= self.max_requests:
            return False
        
        # Add current timestamp
        st.session_state.rate_limit_timestamps.append(now)
        return True
    
    def time_until_reset(self) -> int:
        """Returns seconds until rate limit resets."""
        if not st.session_state.rate_limit_timestamps:
            return 0
        
        oldest = min(st.session_state.rate_limit_timestamps)
        wait_time = self.window_seconds - (time.time() - oldest)
        return max(0, int(wait_time))

rate_limiter = RateLimiter(
    max_requests=int(os.getenv("MAX_REQUESTS_PER_MINUTE", 6)),
    window_seconds=60
)

# ══════════════════════════════════════════════════════════════════════════════
# Persistent Storage (SQLite fallback for chat/feedback)
# ══════════════════════════════════════════════════════════════════════════════

import sqlite3
from contextlib import contextmanager

DB_PATH = Path("db") / "daleel_data.db"

@contextmanager
def get_db():
    """Context manager for database connections."""
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    try:
        yield conn
    finally:
        conn.close()

def init_database():
    """Initialize SQLite database for chat history and feedback."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Chat history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                timestamp TEXT,
                user_message TEXT,
                bot_response TEXT,
                response_time REAL
            )
        ''')
        
        # Feedback table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                timestamp TEXT,
                message_id INTEGER,
                feedback_type TEXT,
                comment TEXT
            )
        ''')
        
        conn.commit()

def save_chat_message(user_msg: str, bot_response: str, response_time: float):
    """Save chat interaction to database."""
    try:
        session_id = st.session_state.get('session_id', 'unknown')
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO chat_history (session_id, timestamp, user_message, bot_response, response_time)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                session_id,
                datetime.datetime.now().isoformat(),
                user_msg,
                bot_response,
                response_time
            ))
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to save chat message: {e}")

def save_feedback(message_id: int, feedback_type: str, comment: str = ""):
    """Save user feedback to database."""
    try:
        session_id = st.session_state.get('session_id', 'unknown')
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO feedback (session_id, timestamp, message_id, feedback_type, comment)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                session_id,
                datetime.datetime.now().isoformat(),
                message_id,
                feedback_type,
                comment
            ))
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to save feedback: {e}")

def export_chat_history():
    """Export chat history as CSV for download."""
    try:
        import pandas as pd
        with get_db() as conn:
            df = pd.read_sql_query("SELECT * FROM chat_history ORDER BY timestamp DESC LIMIT 1000", conn)
            return df.to_csv(index=False).encode('utf-8')
    except Exception as e:
        logger.error(f"Failed to export chat history: {e}")
        return None

def export_feedback():
    """Export feedback as CSV for download."""
    try:
        import pandas as pd
        with get_db() as conn:
            df = pd.read_sql_query("SELECT * FROM feedback ORDER BY timestamp DESC", conn)
            return df.to_csv(index=False).encode('utf-8')
    except Exception as e:
        logger.error(f"Failed to export feedback: {e}")
        return None

# Initialize database
init_database()

# Initialize session ID
if 'session_id' not in st.session_state:
    st.session_state.session_id = hashlib.md5(
        f"{time.time()}".encode()
    ).hexdigest()[:16]

# ══════════════════════════════════════════════════════════════════════════════
# Import optional modules with graceful fallbacks
# ══════════════════════════════════════════════════════════════════════════════

try:
    import data_scraper as _ds
    HAS_SCRAPER = True
except ImportError:
    HAS_SCRAPER = False
    logger.warning("data_scraper module not available")

try:
    from cv_analyzer import CVAnalyzer
    HAS_CV_ANALYZER = True
except ImportError:
    HAS_CV_ANALYZER = False
    logger.warning("cv_analyzer module not available")

try:
    from matching_engine import score_and_rank
    HAS_ENGINE = True
except ImportError:
    HAS_ENGINE = False
    logger.warning("matching_engine module not available")

try:
    from semantic_matcher import semantic_rank
    HAS_SEMANTIC = True
except ImportError:
    HAS_SEMANTIC = False
    logger.warning("semantic_matcher module not available")

try:
    from job_matcher import JobMatcher
    HAS_JOB_MATCHER = True
except ImportError:
    HAS_JOB_MATCHER = False
    logger.warning("job_matcher module not available")

EGYPT_ALIASES = {"egypt", "cairo", "giza", "alexandria", "مصر", "القاهرة"}

# ══════════════════════════════════════════════════════════════════════════════
# CSS – Daleel Design System (unchanged from original)
# ══════════════════════════════════════════════════════════════════════════════

def _css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700;800&family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
    
    /* Design tokens */
    :root {
        --bg: #09090F;
        --bg2: #0F0F1A;
        --bg3: #141421;
        --bg4: #1A1A2E;
        --bg5: #1F1F38;
        --bdr: rgba(255,255,255,.055);
        --bdr2: rgba(255,255,255,.09);
        --t1: #F0EDE6;
        --t2: #8C8FA8;
        --t3: #3E4160;
        --gold: #F4B942;
        --goldd: rgba(244,185,66,.08);
        --goldb: rgba(244,185,66,.22);
        --goldf: rgba(244,185,66,.04);
        --grn: #2DD4AA;
        --grnd: rgba(45,212,170,.08);
        --red: #F97070;
        --redd: rgba(249,112,112,.08);
        --ff: 'DM Sans', system-ui, sans-serif;
        --fd: 'Playfair Display', Georgia, serif;
        --r: 12px;
    }
    
    *, *::before, *::after { box-sizing: border-box; }
    
    html, body, [data-testid="stApp"], [data-testid="stAppViewContainer"], .main {
        background: var(--bg) !important;
        font-family: var(--ff) !important;
        color: var(--t1) !important;
    }
    
    #MainMenu, header, footer, [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"] {
        display: none !important;
    }
    
    .block-container { padding: 0 !important; max-width: 100% !important; }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: var(--bg2) !important;
        border-right: 1px solid var(--bdr) !important;
        min-width: 264px !important;
        max-width: 264px !important;
    }
    
    /* Primary button */
    .stButton > button {
        background: linear-gradient(135deg, #C8850A, #F4B942) !important;
        border: none !important;
        border-radius: var(--r) !important;
        color: #0A0A14 !important;
        font-family: var(--ff) !important;
        font-size: 13.5px !important;
        font-weight: 700 !important;
        padding: 12px 24px !important;
        box-shadow: 0 4px 20px rgba(244,185,66,.28) !important;
        transition: all .22s !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 28px rgba(244,185,66,.42) !important;
    }
    
    /* Error styling */
    .stAlert {
        border-radius: var(--r) !important;
    }
    
    </style>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# API helpers with improved error handling
# ══════════════════════════════════════════════════════════════════════════════

def _key():
    """Get Groq API key from secrets or environment."""
    try:
        if hasattr(st, 'secrets') and "GROQ_API_KEY" in st.secrets:
            return st.secrets["GROQ_API_KEY"]
    except Exception:
        pass
    return os.getenv("GROQ_API_KEY", "")

def _gh_token():
    """Get GitHub token from secrets or environment."""
    try:
        if hasattr(st, 'secrets') and "GITHUB_TOKEN" in st.secrets:
            return st.secrets["GITHUB_TOKEN"]
    except Exception:
        pass
    return os.getenv("GITHUB_TOKEN", "")

def _groq():
    """Initialize Groq client with error handling."""
    try:
        from groq import Groq
        return Groq(api_key=_key())
    except Exception as e:
        logger.error(f"Failed to initialize Groq client: {e}")
        st.error("Unable to connect to AI service. Please try again later.")
        st.stop()

def _llm(client, msgs, max_tokens=900):
    """
    Groq-only smart fallback chain with better error handling.
    """
    GROQ_MODELS = [
        "llama-3.3-70b-versatile",
        "deepseek-r1-distill-llama-70b",
        "llama-3.1-8b-instant",
    ]
    
    last_error = None
    
    for model in GROQ_MODELS:
        try:
            r = client.chat.completions.create(
                model=model,
                messages=msgs,
                temperature=0.3,
                max_tokens=max_tokens,
            )
            return r.choices[0].message.content
        except Exception as e:
            last_error = e
            err_str = str(e).lower()
            
            # Check for authentication errors
            if any(x in err_str for x in ("api key", "unauthorized", "401", "invalid_api_key")):
                logger.error(f"Authentication error with Groq API: {e}")
                st.error("⚠️ AI service authentication failed. Please contact support.")
                st.stop()
            
            # Rate limit errors
            if "rate" in err_str or "429" in err_str:
                logger.warning(f"Rate limit hit on model {model}: {e}")
                continue
            
            # Other errors - try next model
            logger.warning(f"Model {model} failed: {e}")
            continue
    
    # All models failed
    logger.error(f"All Groq models failed. Last error: {last_error}")
    return "⚠️ AI service is temporarily unavailable. Please try again in a moment."

def _parse_json(text):
    """Parse JSON from LLM response with fallbacks."""
    text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
    
    try:
        return json.loads(text)
    except Exception:
        pass
    
    # Try to extract JSON array or object
    for pat in [r"\[.*\]", r"\{.*\}"]:
        m = re.search(pat, text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except Exception:
                pass
    
    logger.warning(f"Failed to parse JSON from: {text[:200]}")
    return []

# ══════════════════════════════════════════════════════════════════════════════
# Job database helpers (unchanged logic, improved error handling)
# ══════════════════════════════════════════════════════════════════════════════

DATA_DIR = Path("data")
COMBINED = DATA_DIR / "jobs_combined.csv"
CACHE_HOURS = int(os.getenv("CACHE_HOURS", 24))

def _load_combined() -> list:
    """Load combined jobs database."""
    if HAS_SCRAPER:
        try:
            return _ds.load_combined()
        except Exception as e:
            logger.error(f"Data scraper load failed: {e}")
    
    if not COMBINED.exists():
        return []
    
    try:
        import pandas as pd
        df = pd.read_csv(str(COMBINED), on_bad_lines="skip", nrows=5000)
        return df.fillna("").to_dict("records")
    except Exception as e:
        logger.error(f"Failed to load jobs CSV: {e}")
        return []

def _cache_fresh() -> bool:
    """Check if job cache is still fresh."""
    if not COMBINED.exists():
        return False
    
    try:
        age = (datetime.datetime.now() - 
               datetime.datetime.fromtimestamp(COMBINED.stat().st_mtime)).total_seconds()
        return age < CACHE_HOURS * 3600
    except Exception:
        return False

def _auto_build():
    """Auto-build job database with retry logic."""
    if st.session_state.get("db_checked"):
        return
    
    try:
        if _cache_fresh():
            st.session_state.db_checked = True
            return
        
        with st.sidebar:
            ph = st.empty()
            ph.info("🔄 Refreshing job database...")
            
            if HAS_SCRAPER:
                _ds.scrape_and_save(status_ph=ph)
            else:
                _fallback_build(ph)
            
            ph.success("✅ Job database ready")
            time.sleep(2)
            ph.empty()
            st.session_state.db_checked = True
            
    except Exception as e:
        logger.error(f"Auto-build failed: {e}")
        st.sidebar.warning("⚠️ Job database update failed. Using cached data.")

def _fallback_build(ph=None):
    """Fallback job scraper."""
    import requests
    import pandas as pd
    
    def say(m):
        if ph:
            ph.info(m)
    
    jobs = []
    say("📡 Fetching remote jobs...")
    
    try:
        r = requests.get(
            "https://remoteok.com/api",
            headers={"User-Agent": "Daleel/1.1"},
            timeout=14
        )
        r.raise_for_status()
        
        for j in r.json()[:150]:
            if isinstance(j, dict) and "id" in j:
                jobs.append({
                    "title": j.get("position", "")[:60],
                    "company": j.get("company", "")[:40],
                    "description": str(j.get("description", ""))[:400],
                    "location": j.get("location", "Remote"),
                    "salary": "",
                    "url": j.get("url", ""),
                    "source": "RemoteOK"
                })
    except Exception as e:
        logger.error(f"RemoteOK scraping failed: {e}")
    
    DATA_DIR.mkdir(exist_ok=True)
    if jobs:
        pd.DataFrame(jobs).to_csv(str(COMBINED), index=False)
    
    return len(jobs)

# ══════════════════════════════════════════════════════════════════════════════
# Skill expansion for better matching
# ══════════════════════════════════════════════════════════════════════════════

try:
    from matching_engine import SKILL_ALIASES as _SKILL_ALIASES
except ImportError:
    _SKILL_ALIASES = {}

def _expand_skills(skills: list) -> list:
    """Expand user skills to include all known synonyms."""
    expanded = set(s.lower() for s in skills)
    
    for skill in skills:
        canonical = skill.lower().strip()
        for canon, aliases in _SKILL_ALIASES.items():
            if canonical in [a.lower() for a in (aliases or [])] or canonical == canon:
                expanded.update(a.lower() for a in (aliases or []))
                expanded.add(canon)
    
    return list(expanded)

def _diverse_candidates(jobs, skills, roles, location_pref="", n=30):
    """Select diverse candidate jobs for LLM ranking."""
    loc_lower = location_pref.lower() if location_pref else ""
    is_egypt_pref = loc_lower in EGYPT_ALIASES
    
    expanded_skills = _expand_skills(skills)
    
    def _score(j):
        blob = (str(j.get("title", "")) + " " +
                str(j.get("description", "")) + " " +
                str(j.get("location", ""))).lower()
        src = str(j.get("source", "")).lower()
        
        s = sum(2 for sk in expanded_skills if sk in blob)
        s += sum(1 for ro in roles for w in ro.lower().split()
                 if len(w) > 3 and w in blob)
        
        if loc_lower:
            jloc = (j.get("location", "") or "").lower()
            is_remote = "remote" in jloc or "worldwide" in jloc
            
            if is_egypt_pref:
                if any(a in jloc for a in EGYPT_ALIASES) or src == "wuzzuf":
                    s += 15
                elif is_remote:
                    s += 5
                else:
                    s -= 5
            else:
                if loc_lower in jloc:
                    s += 15
                elif is_remote:
                    s += 5
                else:
                    s -= 5
        
        return s
    
    scored = sorted(jobs, key=_score, reverse=True)
    
    # Ensure source diversity
    buckets = {}
    for j in scored:
        src = j.get("source", "Unknown")
        buckets.setdefault(src, []).append(j)
    
    num_src = max(len(buckets), 1)
    per_source = max(3, n // num_src)
    
    diverse, seen = [], set()
    for rnd in range(per_source):
        for src_jobs in buckets.values():
            if rnd < len(src_jobs):
                j = src_jobs[rnd]
                k = (j.get("title", "")[:40].lower(), j.get("company", "")[:30].lower())
                if k not in seen:
                    seen.add(k)
                    diverse.append(j)
                if len(diverse) >= n:
                    break
        if len(diverse) >= n:
            break
    
    # Fill remaining slots
    for j in scored:
        if len(diverse) >= n:
            break
        k = (j.get("title", "")[:40].lower(), j.get("company", "")[:30].lower())
        if k not in seen:
            seen.add(k)
            diverse.append(j)
    
    return diverse[:n]

# ══════════════════════════════════════════════════════════════════════════════
# Job matching with rate limiting check
# ══════════════════════════════════════════════════════════════════════════════

def match_jobs(user_profile: dict, limit: int = 8, location_pref: str = "") -> dict:
    """
    Match jobs to user profile with rate limiting.
    """
    # Check rate limit
    if not rate_limiter.check_rate_limit():
        wait_time = rate_limiter.time_until_reset()
        return {
            "success": False,
            "error": f"⏱️ Rate limit exceeded. Please wait {wait_time} seconds before trying again."
        }
    
    # Route through JobMatcher if available
    if HAS_JOB_MATCHER:
        try:
            matcher = JobMatcher()
            return matcher.match_jobs(user_profile, limit=limit, location_pref=location_pref)
        except Exception as e:
            logger.error(f"JobMatcher failed: {e}")
            # Fall through to inline implementation
    
    # Inline fallback implementation
    all_jobs = _load_combined()
    if not all_jobs:
        return {
            "success": False,
            "error": "Job database is empty. Click 🔄 Refresh Job Database in the sidebar."
        }
    
    skills = [s.lower() for s in user_profile.get("skills", [])]
    roles = [r.lower() for r in user_profile.get("interested_roles", [])]
    
    pipeline_stages = []
    
    # Stage 0: Semantic ranking
    if HAS_SEMANTIC:
        try:
            pool = semantic_rank(all_jobs, user_profile, location_pref=location_pref, top_n=100)
            pipeline_stages.append("🧠 Semantic")
        except Exception as e:
            logger.warning(f"Semantic ranking failed: {e}")
            pool = all_jobs
    else:
        pool = all_jobs
    
    # Stage 1: Deterministic engine
    if HAS_ENGINE:
        try:
            candidates = score_and_rank(pool, user_profile, location_pref=location_pref, top_n=30, source_cap=6)
            pipeline_stages.append("⚙️ Engine")
        except Exception as e:
            logger.warning(f"Engine ranking failed: {e}")
            candidates = _diverse_candidates(pool, skills, roles, location_pref=location_pref, n=30)
    else:
        candidates = _diverse_candidates(pool, skills, roles, location_pref=location_pref, n=30)
    
    pipeline_stages.append("🤖 LLM")
    
    sources_present = sorted({j.get("source", "?") for j in candidates})
    
    # Prepare compact representation for LLM
    compact = []
    for j in candidates:
        entry = {
            "title": str(j.get("title", ""))[:60],
            "company": str(j.get("company", ""))[:40],
            "location": str(j.get("location", ""))[:40],
            "description": str(j.get("description", ""))[:200],
            "salary": str(j.get("salary", ""))[:30],
            "url": str(j.get("url", "")),
            "source": str(j.get("source", "")),
        }
        if "_engine_score" in j:
            entry["pre_score"] = j["_engine_score"]
        if "_matched_skills" in j:
            entry["matched_skills"] = j.get("_matched_skills", [])
        if "_semantic_score" in j:
            entry["semantic_score"] = round(j["_semantic_score"] * 100)
        compact.append(entry)
    
    # Build URL lookup for verification
    url_lookup = {}
    for j in compact:
        real_url = str(j.get("url", "")).strip()
        if real_url.startswith("http"):
            key = (str(j.get("title", ""))[:40].lower(), str(j.get("company", ""))[:30].lower())
            url_lookup[key] = real_url
    
    # Truncate on whole job objects only
    jobs_str = json.dumps(compact, indent=2)
    if len(jobs_str) > 12000:
        truncated = []
        for job in compact:
            candidate_str = json.dumps(truncated + [job], indent=2)
            if len(candidate_str) > 11500:
                break
            truncated.append(job)
        jobs_str = json.dumps(truncated, indent=2)
    
    pipeline_note = (
        "Candidates were pre-filtered by semantic embeddings and a deterministic engine.\n"
        "'semantic_score' (0-100) = cosine similarity. 'pre_score' (0-100) = engine score.\n\n"
        if pipeline_stages else ""
    )
    
    loc_display = location_pref or "Remote / Worldwide"
    is_egypt_pref = location_pref.lower() in EGYPT_ALIASES if location_pref else False
    
    egypt_note = (
        " • Egypt: Cairo, Giza, Alexandria, Wuzzuf-sourced jobs all count as local.\n"
        if is_egypt_pref else ""
    )
    
    client = _groq()
    prompt = (
        f"You are a career advisor. Return ONLY a valid JSON array of the top {limit} best-matching jobs.\n"
        "No markdown. Each object must have exactly these keys:\n"
        '{"title":"","company":"","location":"","salary":"","url":"","source":"",'
        '"match_score":<0-100>,"matched_skills":["skill1"],"missing_skills":["skill1"],'
        '"why_good_fit":"one or two sentences"}\n\n'
        f"{pipeline_note}"
        "RANKING RULES:\n"
        f"1. LOCATION: User prefers '{loc_display}'. Fill slots with local jobs first.\n"
        f"{egypt_note}"
        " NEVER place a different-country job above a local match.\n"
        "2. SKILL MATCH: rank by matched_skills count within the same location tier.\n"
        "3. SOURCE DIVERSITY: prefer different sources when scores are close.\n\n"
        "URL RULE: copy the exact url from the listing data. Do NOT invent URLs.\n"
        "If a listing has no url, use an empty string.\n\n"
        f"Sources: {', '.join(sources_present)}\n\n"
        f"User profile:\n"
        f" Skills: {user_profile.get('skills', [])}\n"
        f" Experience: {user_profile.get('experience_years', 0)} years\n"
        f" Seniority: {user_profile.get('seniority_level', '')}\n"
        f" Roles: {user_profile.get('interested_roles', [])}\n\n"
        f"Candidates ({len(compact)}):\n"
        f"{jobs_str}\n\n"
        "Return ONLY the JSON array."
    )
    
    raw = _llm(client, [{"role": "user", "content": prompt}], max_tokens=1500)
    matches = _parse_json(raw)
    
    if isinstance(matches, dict) and "jobs" in matches:
        matches = matches["jobs"]
    if not isinstance(matches, list):
        matches = []
    
    # Verify and fix URLs
    for m in matches:
        key = (str(m.get("title", ""))[:40].lower(), str(m.get("company", ""))[:30].lower())
        real_url = url_lookup.get(key, "")
        if real_url:
            m["url"] = real_url
        elif not str(m.get("url", "")).startswith("http"):
            m["url"] = ""
    
    return {
        "success": True,
        "matches": matches,
        "total_in_db": len(all_jobs),
        "candidates_evaluated": len(compact),
        "sources_in_candidates": sources_present,
        "pipeline_stages": pipeline_stages,
    }

# ══════════════════════════════════════════════════════════════════════════════
# CV Analysis with improved error handling
# ══════════════════════════════════════════════════════════════════════════════

def analyze_cv(pdf_path: str) -> dict:
    """Analyze CV from PDF with error handling."""
    if HAS_CV_ANALYZER:
        try:
            return CVAnalyzer().analyze_cv(pdf_path)
        except Exception as e:
            logger.error(f"CVAnalyzer failed: {e}")
            # Fall through to inline implementation
    
    # Inline fallback
    try:
        from pypdf import PdfReader
        
        text = "\n".join(p.extract_text() or "" for p in PdfReader(pdf_path).pages)
        
        if not text.strip():
            return {
                "success": False,
                "error": "Could not extract text from this PDF. It may be scanned or image-based."
            }
        
        # Check rate limit
        if not rate_limiter.check_rate_limit():
            wait_time = rate_limiter.time_until_reset()
            return {
                "success": False,
                "error": f"⏱️ Rate limit exceeded. Please wait {wait_time} seconds."
            }
        
        client = _groq()
        prompt = (
            "Analyze this CV thoroughly. Return ONLY a valid JSON object — no markdown.\n\n"
            '{"name":"","summary":"2-3 sentence honest professional summary",'
            '"seniority_level":"Junior|Mid-Level|Senior|Lead","experience_years":<integer>,'
            '"skills":["skill1"],"technologies":["framework"],'
            '"experience":[{"title":"","company":"","duration":""}],'
            '"education":[{"degree":"","field":"","school":""}],'
            '"projects":[{"name":"","description":"","technologies":[""],"url":""}],'
            '"strengths":[""],"improvement_areas":[""]}\n\nCV:\n' + text[:6000]
        )
        
        raw = _llm(client, [{"role": "user", "content": prompt}], max_tokens=1400)
        parsed = _parse_json(raw)
        
        if not parsed or "skills" not in parsed:
            return {
                "success": False,
                "error": "Unable to analyze this CV. Please ensure it's a text-based PDF with clear formatting."
            }
        
        return {"success": True, "analysis": parsed}
        
    except Exception as e:
        logger.error(f"CV analysis failed: {e}")
        return {
            "success": False,
            "error": "An error occurred while analyzing your CV. Please try again."
        }

# ══════════════════════════════════════════════════════════════════════════════
# GitHub Analysis with improved error handling
# ══════════════════════════════════════════════════════════════════════════════

def analyze_github(username: str) -> dict:
    """Analyze GitHub profile with error handling."""
    import requests
    
    hdrs = {"Accept": "application/vnd.github+json"}
    tok = _gh_token()
    if tok:
        hdrs["Authorization"] = f"Bearer {tok}"
    
    base = f"https://api.github.com/users/{username}"
    
    try:
        u = requests.get(base, headers=hdrs, timeout=10)
        
        if u.status_code == 404:
            return {
                "success": False,
                "error": f"GitHub user '{username}' not found. Please check the username."
            }
        
        if u.status_code == 403:
            return {
                "success": False,
                "error": "GitHub API rate limit exceeded. Please try again later or add a GITHUB_TOKEN."
            }
        
        u.raise_for_status()
        user = u.json()
        
    except requests.RequestException as e:
        logger.error(f"GitHub API request failed: {e}")
        return {
            "success": False,
            "error": "Unable to connect to GitHub. Please check your internet connection."
        }
    
    try:
        rr = requests.get(
            f"{base}/repos",
            headers=hdrs,
            params={"per_page": 30, "sort": "pushed"},
            timeout=10
        )
        repos = rr.json() if rr.ok else []
    except Exception:
        repos = []
    
    # Analyze languages
    lang_counts = {}
    for repo in repos[:20]:
        if repo.get("language"):
            lang_counts[repo["language"]] = lang_counts.get(repo["language"], 0) + 1
    
    profile = {
        "login": user.get("login", ""),
        "name": user.get("name", ""),
        "bio": user.get("bio", ""),
        "followers": user.get("followers", 0),
        "following": user.get("following", 0),
        "public_repos": user.get("public_repos", 0),
        "languages": dict(sorted(lang_counts.items(), key=lambda x: -x[1])[:8]),
        "top_repos": [
            {
                "name": r.get("name"),
                "stars": r.get("stargazers_count", 0),
                "description": r.get("description", "")
            }
            for r in repos[:5]
        ],
    }
    
    # Check rate limit
    if not rate_limiter.check_rate_limit():
        wait_time = rate_limiter.time_until_reset()
        return {
            "success": False,
            "error": f"⏱️ Rate limit exceeded. Please wait {wait_time} seconds."
        }
    
    client = _groq()
    prompt = (
        f"Analyze this GitHub profile professionally. Return ONLY valid JSON:\n\n"
        '{"seniority_estimate":"Junior|Mid-Level|Senior|Lead","coding_strength":<0-100>,'
        '"primary_languages":["lang1"],"project_quality":<0-100>,"collaboration_score":<0-100>,'
        '"standout_projects":["project name"],"technical_summary":"2-3 sentences",'
        '"improvement_suggestions":["suggestion1"]}\n\n'
        f"Profile:\n{json.dumps(profile, indent=2)}"
    )
    
    raw = _llm(client, [{"role": "user", "content": prompt}], max_tokens=1000)
    analysis = _parse_json(raw)
    
    if not analysis:
        return {
            "success": False,
            "error": "Unable to analyze GitHub profile at this time."
        }
    
    return {
        "success": True,
        "profile": profile,
        "analysis": analysis
    }

# ══════════════════════════════════════════════════════════════════════════════
# MAIN APP UI
# ══════════════════════════════════════════════════════════════════════════════

def main():
    _css()
    
    # Header
    st.markdown("""
    <div class="dal-hdr">
        <div style="display:flex;align-items:center;gap:14px;position:relative;z-index:1;">
            <div class="dal-logo">🧭</div>
            <div>
                <div class="dal-brand">Daleel <span>AI</span></div>
                <div class="dal-subbrand">Career Intelligence</div>
            </div>
        </div>
        <div style="display:flex;gap:8px;position:relative;z-index:1;">
            <span class="dal-badge live">● Live</span>
            <span class="dal-badge gold">v1.1 Phase 1</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown('<div class="dal-sbar-logo"><div style="text-align:center;font-size:32px;">🧭</div></div>', unsafe_allow_html=True)
        
        st.markdown('<div class="slbl">Navigation</div>', unsafe_allow_html=True)
        
        # Database management
        st.markdown('<div class="sdiv"></div>', unsafe_allow_html=True)
        st.markdown('<div class="slbl">Job Database</div>', unsafe_allow_html=True)
        
        if st.button("🔄 Refresh Job Database"):
            st.session_state.db_checked = False
            _auto_build()
            st.success("Database refreshed!")
        
        # Export features
        st.markdown('<div class="sdiv"></div>', unsafe_allow_html=True)
        st.markdown('<div class="slbl">Export Data</div>', unsafe_allow_html=True)
        
        chat_csv = export_chat_history()
        if chat_csv:
            st.download_button(
                "📥 Download Chat History",
                chat_csv,
                "daleel_chat_history.csv",
                "text/csv"
            )
        
        feedback_csv = export_feedback()
        if feedback_csv:
            st.download_button(
                "📥 Download Feedback",
                feedback_csv,
                "daleel_feedback.csv",
                "text/csv"
            )
        
        # Rate limit status
        st.markdown('<div class="sdiv"></div>', unsafe_allow_html=True)
        st.markdown('<div class="slbl">Status</div>', unsafe_allow_html=True)
        
        remaining = rate_limiter.max_requests - len(st.session_state.get('rate_limit_timestamps', []))
        st.info(f"🔢 Requests remaining: {remaining}/{rate_limiter.max_requests}")
    
    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🧭 Job Matcher", "📄 CV Analyzer", "🐙 GitHub Analyzer", "ℹ️ About"])
    
    with tab1:
        st.markdown("### 🎯 Find Your Perfect Match")
        st.markdown("Tell us about yourself and we'll find the best job opportunities for you.")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            skills_input = st.text_area(
                "Your Skills",
                placeholder="Python, React, Machine Learning, Docker...",
                help="Separate skills with commas"
            )
            
            roles_input = st.text_input(
                "Interested Roles",
                placeholder="Software Engineer, Data Scientist, Product Manager",
                help="Separate roles with commas"
            )
        
        with col2:
            experience_years = st.number_input("Years of Experience", min_value=0, max_value=50, value=3)
            
            seniority = st.selectbox(
                "Seniority Level",
                ["Junior", "Mid-Level", "Senior", "Lead"]
            )
            
            location = st.text_input("Preferred Location", placeholder="Remote, Cairo, New York...")
        
        if st.button("🔍 Find Matching Jobs", type="primary"):
            if not skills_input:
                st.warning("Please enter at least some skills!")
            else:
                skills = [s.strip() for s in skills_input.split(",") if s.strip()]
                roles = [r.strip() for r in roles_input.split(",") if r.strip()] if roles_input else []
                
                profile = {
                    "skills": skills,
                    "experience_years": experience_years,
                    "seniority_level": seniority,
                    "interested_roles": roles
                }
                
                with st.spinner("🔄 Searching thousands of jobs..."):
                    _auto_build()
                    result = match_jobs(profile, limit=8, location_pref=location)
                
                if result.get("success"):
                    st.success(f"✅ Found {len(result['matches'])} matching opportunities!")
                    
                    # Display pipeline info
                    if result.get("pipeline_stages"):
                        st.info(f"**Pipeline:** {' → '.join(result['pipeline_stages'])}")
                    
                    # Display matches
                    for i, job in enumerate(result["matches"], 1):
                        with st.expander(f"**{i}. {job.get('title', 'N/A')}** at {job.get('company', 'N/A')}", expanded=i<=3):
                            col_a, col_b = st.columns([3, 1])
                            
                            with col_a:
                                st.markdown(f"📍 **Location:** {job.get('location', 'N/A')}")
                                if job.get('salary'):
                                    st.markdown(f"💰 **Salary:** {job['salary']}")
                                st.markdown(f"🎯 **Match Score:** {job.get('match_score', 0)}%")
                                st.markdown(f"**Why good fit:** {job.get('why_good_fit', 'N/A')}")
                                
                                if job.get('matched_skills'):
                                    st.markdown("**Matched Skills:**")
                                    st.markdown(" ".join([f'<span class="pill">{s}</span>' for s in job['matched_skills'][:6]]), unsafe_allow_html=True)
                                
                                if job.get('missing_skills'):
                                    st.markdown("**Skills to Learn:**")
                                    st.markdown(" ".join([f'<span class="pill miss">{s}</span>' for s in job['missing_skills'][:4]]), unsafe_allow_html=True)
                            
                            with col_b:
                                if job.get('url'):
                                    st.markdown(f"[🔗 Apply Now]({job['url']})")
                                st.markdown(f"<small>Source: {job.get('source', 'N/A')}</small>", unsafe_allow_html=True)
                else:
                    st.error(result.get("error", "An error occurred"))
    
    with tab2:
        st.markdown("### 📄 CV Analysis")
        st.markdown("Upload your CV and get instant AI-powered feedback.")
        
        uploaded_file = st.file_uploader("Upload your CV (PDF)", type=['pdf'])
        
        if uploaded_file:
            # Save temporarily
            temp_path = Path("temp_cv.pdf")
            temp_path.write_bytes(uploaded_file.read())
            
            if st.button("🔍 Analyze CV", type="primary"):
                with st.spinner("🤖 Analyzing your CV..."):
                    start_time = time.time()
                    result = analyze_cv(str(temp_path))
                    response_time = time.time() - start_time
                
                temp_path.unlink(missing_ok=True)
                
                if result.get("success"):
                    analysis = result["analysis"]
                    
                    st.success("✅ Analysis complete!")
                    
                    # Display results
                    st.markdown(f"### 👤 {analysis.get('name', 'Candidate')}")
                    st.markdown(f"**Summary:** {analysis.get('summary', 'N/A')}")
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Seniority", analysis.get('seniority_level', 'N/A'))
                    col2.metric("Experience", f"{analysis.get('experience_years', 0)} years")
                    col3.metric("Skills", len(analysis.get('skills', [])))
                    
                    with st.expander("💼 Skills & Technologies", expanded=True):
                        if analysis.get('skills'):
                            st.markdown("**Skills:**")
                            st.markdown(" ".join([f'<span class="pill">{s}</span>' for s in analysis['skills'][:15]]), unsafe_allow_html=True)
                        
                        if analysis.get('technologies'):
                            st.markdown("**Technologies:**")
                            st.markdown(" ".join([f'<span class="pill tech">{t}</span>' for t in analysis['technologies'][:12]]), unsafe_allow_html=True)
                    
                    with st.expander("📊 Experience"):
                        for exp in analysis.get('experience', [])[:5]:
                            st.markdown(f"**{exp.get('title', 'N/A')}** at {exp.get('company', 'N/A')}")
                            st.markdown(f"<small>{exp.get('duration', 'N/A')}</small>", unsafe_allow_html=True)
                            st.markdown("---")
                    
                    with st.expander("✨ Strengths & Improvements"):
                        if analysis.get('strengths'):
                            st.markdown("**Strengths:**")
                            for strength in analysis['strengths']:
                                st.markdown(f"✅ {strength}")
                        
                        if analysis.get('improvement_areas'):
                            st.markdown("**Areas for Improvement:**")
                            for area in analysis['improvement_areas']:
                                st.markdown(f"💡 {area}")
                    
                    # Save to database
                    save_chat_message(
                        f"CV Analysis for {uploaded_file.name}",
                        json.dumps(analysis, indent=2),
                        response_time
                    )
                else:
                    st.error(result.get("error", "Analysis failed"))
    
    with tab3:
        st.markdown("### 🐙 GitHub Profile Analysis")
        st.markdown("Get insights into your GitHub coding profile.")
        
        username = st.text_input("GitHub Username", placeholder="octocat")
        
        if st.button("🔍 Analyze Profile", type="primary"):
            if not username:
                st.warning("Please enter a GitHub username!")
            else:
                with st.spinner("🔄 Fetching GitHub data..."):
                    start_time = time.time()
                    result = analyze_github(username.strip())
                    response_time = time.time() - start_time
                
                if result.get("success"):
                    profile = result["profile"]
                    analysis = result["analysis"]
                    
                    st.success("✅ Profile analyzed!")
                    
                    st.markdown(f"### 👤 {profile.get('name', username)}")
                    if profile.get('bio'):
                        st.markdown(f"*{profile['bio']}*")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Repos", profile.get('public_repos', 0))
                    col2.metric("Followers", profile.get('followers', 0))
                    col3.metric("Following", profile.get('following', 0))
                    col4.metric("Coding Strength", f"{analysis.get('coding_strength', 0)}%")
                    
                    with st.expander("💻 Languages & Skills", expanded=True):
                        st.markdown("**Primary Languages:**")
                        for lang in analysis.get('primary_languages', []):
                            st.markdown(f'<span class="pill tech">{lang}</span>', unsafe_allow_html=True)
                        
                        st.markdown("**All Languages:**")
                        for lang, count in profile.get('languages', {}).items():
                            st.markdown(f"• {lang}: {count} repos")
                    
                    with st.expander("⭐ Top Projects"):
                        for repo in profile.get('top_repos', []):
                            st.markdown(f"**{repo['name']}** ⭐ {repo['stars']}")
                            if repo.get('description'):
                                st.markdown(f"<small>{repo['description']}</small>", unsafe_allow_html=True)
                            st.markdown("---")
                    
                    with st.expander("📊 Analysis Summary"):
                        st.markdown(f"**Seniority Estimate:** {analysis.get('seniority_estimate', 'N/A')}")
                        st.markdown(f"**Project Quality:** {analysis.get('project_quality', 0)}%")
                        st.markdown(f"**Collaboration Score:** {analysis.get('collaboration_score', 0)}%")
                        
                        st.markdown("**Technical Summary:**")
                        st.markdown(analysis.get('technical_summary', 'N/A'))
                        
                        if analysis.get('improvement_suggestions'):
                            st.markdown("**Suggestions:**")
                            for suggestion in analysis['improvement_suggestions']:
                                st.markdown(f"💡 {suggestion}")
                    
                    # Save to database
                    save_chat_message(
                        f"GitHub Analysis for {username}",
                        json.dumps({"profile": profile, "analysis": analysis}, indent=2),
                        response_time
                    )
                else:
                    st.error(result.get("error", "Analysis failed"))
    
    with tab4:
        st.markdown("### ℹ️ About Daleel AI")
        
        st.markdown("""
        **Daleel AI** (Arabic: دليل - "guide") is your intelligent career companion, combining cutting-edge AI 
        with real-world job market data to help you navigate your career journey.
        
        #### 🎯 Features
        
        **Phase 1 (Current):**
        - 🔍 **Smart Job Matching** - Graph RAG + semantic search across thousands of opportunities
        - 📄 **CV Analysis** - AI-powered resume feedback and skill assessment
        - 🐙 **GitHub Profiling** - Analyze your coding portfolio and projects
        - 🌍 **Egypt-Focused** - Special integration with Wuzzuf and local job boards
        
        **Coming in Phase 2:**
        - 🎤 Mock interview practice with AI feedback
        - 💼 LinkedIn profile optimization
        - 📚 Personalized learning paths
        - 🌐 Arabic language support
        
        #### 🔒 Privacy & Security
        
        - Your data is stored securely and never shared
        - Rate limiting protects against abuse
        - API keys are encrypted and never exposed
        - All chat history can be exported and deleted
        
        #### 🛠️ Tech Stack
        
        - **AI**: Groq (Llama 3.3, DeepSeek, Qwen)
        - **RAG**: ChromaDB + NetworkX knowledge graphs
        - **Frontend**: Streamlit with custom CSS
        - **Storage**: SQLite for persistence
        
        #### 📞 Support
        
        Having issues? Contact us or submit feedback using the thumbs up/down buttons!
        
        ---
        
        Made with ❤️ by the Daleel team | v1.1 Phase 1 | April 2026
        """)

if __name__ == "__main__":
    main()