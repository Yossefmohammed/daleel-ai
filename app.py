"""
Daleel  –  دليل  –  Career Intelligence Platform  v1.0
=======================================================
Redesigned from Career AI Assistant v7.1
  • Full brand overhaul: "Daleel" (Arabic: guide/compass)
  • Premium gold-on-midnight luxury aesthetic
  • Playfair Display + DM Sans editorial typography
  • Warm amber/gold accent palette
  • Refined geometric micro-details
  • match_jobs() URL lookup keyed by (title, company)
  • URL verification REPLACES hallucinated LLM URLs

Bug fixes applied:
  #1 - job_matcher.py is now imported and used (no longer dead code)
  #2 - JSON truncation now cuts on whole job objects only
  #3 - _parse_json() returns [] on failure (not {})
  #4 - db_checked only set to True on successful build (retries on failure)
  #5 - Fallback candidate path now uses SKILL_ALIASES via matching_engine
"""

import os, re, json, html, datetime, time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(
    page_title="Daleel · دليل",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

try:
    import data_scraper as _ds
    HAS_SCRAPER = True
except ImportError:
    HAS_SCRAPER = False

try:
    from cv_analyzer import CVAnalyzer
    HAS_CV_ANALYZER = True
except ImportError:
    HAS_CV_ANALYZER = False

try:
    from matching_engine import score_and_rank
    HAS_ENGINE = True
except ImportError:
    HAS_ENGINE = False

try:
    from semantic_matcher import semantic_rank
    HAS_SEMANTIC = True
except ImportError:
    HAS_SEMANTIC = False

# ── BUG #1 FIX: Import JobMatcher so job_matcher.py is no longer dead code ──
try:
    from job_matcher import JobMatcher
    HAS_JOB_MATCHER = True
except ImportError:
    HAS_JOB_MATCHER = False

EGYPT_ALIASES = {"egypt", "cairo", "giza", "alexandria", "مصر", "القاهرة"}


# ══════════════════════════════════════════════════════════════════════════════
# CSS  –  Daleel Design System
# ══════════════════════════════════════════════════════════════════════════════
def _css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700;800&family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

/* ── Design tokens ─────────────────────────────────────────────────────── */
:root {
  /* Backgrounds — deep midnight with warm undertones */
  --bg:    #09090F;
  --bg2:   #0F0F1A;
  --bg3:   #141421;
  --bg4:   #1A1A2E;
  --bg5:   #1F1F38;

  /* Borders / overlays */
  --bdr:   rgba(255,255,255,.055);
  --bdr2:  rgba(255,255,255,.09);

  /* Text */
  --t1:    #F0EDE6;
  --t2:    #8C8FA8;
  --t3:    #3E4160;

  /* Gold accent */
  --gold:  #F4B942;
  --goldd: rgba(244,185,66,.08);
  --goldb: rgba(244,185,66,.22);
  --goldf: rgba(244,185,66,.04);

  /* Amber warm */
  --amb:   #E8803A;
  --ambd:  rgba(232,128,58,.08);

  /* Status colours */
  --grn:   #2DD4AA;
  --grnd:  rgba(45,212,170,.08);
  --red:   #F97070;
  --redd:  rgba(249,112,112,.08);
  --sky:   #60B8FF;
  --skyd:  rgba(96,184,255,.08);

  /* Typography */
  --ff:    'DM Sans', system-ui, sans-serif;
  --fd:    'Playfair Display', Georgia, serif;
  --fm:    'DM Mono', monospace;

  /* Radii */
  --r:     12px;
  --rs:    8px;
  --rx:    20px;
}

/* ── Reset ──────────────────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; }

html, body,
[data-testid="stApp"],
[data-testid="stAppViewContainer"],
.main {
  background: var(--bg) !important;
  font-family: var(--ff) !important;
  color: var(--t1) !important;
}

#MainMenu, header, footer,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"] { display: none !important; }

.block-container { padding: 0 !important; max-width: 100% !important; }
section.main > div { padding: 0 !important; }

/* ── Sidebar ────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
  background: var(--bg2) !important;
  border-right: 1px solid var(--bdr) !important;
  min-width: 264px !important;
  max-width: 264px !important;
}
[data-testid="stSidebar"] > div:first-child { padding: 0 !important; }
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span {
  color: var(--t2) !important;
  font-size: 12.5px !important;
}
[data-testid="stSidebar"] .stButton > button {
  background: transparent !important;
  border: 1px solid var(--bdr2) !important;
  border-radius: var(--rs) !important;
  color: var(--t2) !important;
  font-size: 12.5px !important;
  font-weight: 500 !important;
  padding: 9px 14px !important;
  width: 100% !important;
  box-shadow: none !important;
  transition: all .18s !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
  background: var(--bg4) !important;
  border-color: var(--goldb) !important;
  color: var(--gold) !important;
}

/* ── Tabs ───────────────────────────────────────────────────────────────── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
  background: var(--bg2) !important;
  border-bottom: 1px solid var(--bdr) !important;
  padding: 0 24px !important;
  gap: 2px !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
  background: transparent !important;
  border: none !important;
  color: var(--t2) !important;
  font-family: var(--ff) !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  padding: 15px 16px !important;
  border-bottom: 2px solid transparent !important;
  transition: all .2s !important;
  letter-spacing: .01em;
}
[data-testid="stTabs"] [aria-selected="true"] {
  color: var(--gold) !important;
  border-bottom-color: var(--gold) !important;
}
[data-testid="stTabPanel"] {
  background: transparent !important;
  padding: 24px !important;
}

/* ── Inputs ─────────────────────────────────────────────────────────────── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stNumberInput"] input {
  background: var(--bg3) !important;
  border: 1px solid var(--bdr2) !important;
  border-radius: var(--r) !important;
  color: var(--t1) !important;
  font-family: var(--ff) !important;
  font-size: 13.5px !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
  border-color: var(--gold) !important;
  box-shadow: 0 0 0 2px var(--goldd) !important;
}
[data-testid="stTextInput"] label,
[data-testid="stTextArea"] label,
[data-testid="stNumberInput"] label,
[data-testid="stSelectbox"] label,
[data-testid="stMultiSelect"] label {
  color: var(--t2) !important;
  font-size: 12px !important;
  font-weight: 600 !important;
  letter-spacing: .04em !important;
  text-transform: uppercase !important;
}
[data-testid="stFileUploader"] {
  background: var(--bg3) !important;
  border: 1px dashed var(--goldb) !important;
  border-radius: var(--r) !important;
  padding: 18px !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stMultiSelect"] [data-baseweb="select"] > div {
  background: var(--bg3) !important;
  border: 1px solid var(--bdr2) !important;
  border-radius: var(--r) !important;
  color: var(--t1) !important;
}

/* Chip buttons (location quick-select) */
[data-testid="stTabPanel"] [data-testid="stButton"][id*="loc_chip_"] > button,
div[data-testid="column"] button[kind="secondary"] {
  background: var(--bg4) !important;
  border: 1px solid var(--bdr2) !important;
  color: var(--t2) !important;
  font-size: 11.5px !important;
  font-weight: 600 !important;
  padding: 6px 8px !important;
  box-shadow: none !important;
  border-radius: var(--rs) !important;
  letter-spacing: 0 !important;
  transform: none !important;
}
div[data-testid="column"] button[kind="secondary"]:hover {
  background: var(--bg5) !important;
  border-color: var(--goldb) !important;
  color: var(--gold) !important;
  box-shadow: none !important;
  transform: none !important;
}

/* ── Primary button ─────────────────────────────────────────────────────── */
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
  letter-spacing: .02em;
}
.stButton > button:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 28px rgba(244,185,66,.42) !important;
}

/* ── Metrics ────────────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
  background: var(--bg3) !important;
  border: 1px solid var(--bdr) !important;
  border-radius: var(--r) !important;
  padding: 14px 18px !important;
}
[data-testid="stMetricLabel"] { color: var(--t3) !important; font-size: 11px !important; }
[data-testid="stMetricValue"] { color: var(--t1) !important; font-size: 20px !important; }

/* ── Expander / Progress / Download ────────────────────────────────────── */
[data-testid="stExpander"] {
  background: var(--bg3) !important;
  border: 1px solid var(--bdr) !important;
  border-radius: var(--r) !important;
}
.stProgress > div > div { background: var(--gold) !important; }
[data-testid="stDownloadButton"] > button {
  background: transparent !important;
  border: 1px solid var(--bdr2) !important;
  box-shadow: none !important;
  color: var(--t2) !important;
  transform: none !important;
}
hr { border-color: var(--bdr) !important; }

/* ── Custom components ──────────────────────────────────────────────────── */

/* Top header bar */
.dal-hdr {
  background: linear-gradient(180deg, var(--bg2) 0%, rgba(15,15,26,.98) 100%);
  border-bottom: 1px solid var(--bdr);
  padding: 0 28px;
  height: 66px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: relative;
  overflow: hidden;
}
.dal-hdr::before {
  content: '';
  position: absolute;
  left: 0; top: 0; right: 0; bottom: 0;
  background: radial-gradient(ellipse 60% 100% at 15% 50%,
    rgba(244,185,66,.06) 0%, transparent 70%);
  pointer-events: none;
}

/* Logo mark */
.dal-logo {
  width: 42px; height: 42px;
  border-radius: 13px;
  background: linear-gradient(135deg, #C8850A 0%, #F4B942 55%, #FFD580 100%);
  display: flex; align-items: center; justify-content: center;
  font-size: 20px;
  box-shadow: 0 4px 18px rgba(244,185,66,.35),
              0 0 0 1px rgba(244,185,66,.2);
  flex-shrink: 0;
}

/* Brand name */
.dal-brand {
  font-family: var(--fd);
  font-size: 22px;
  font-weight: 700;
  color: var(--t1);
  letter-spacing: -.01em;
  line-height: 1;
}
.dal-brand span {
  color: var(--gold);
}
.dal-subbrand {
  font-size: 10.5px;
  color: var(--t3);
  letter-spacing: .12em;
  text-transform: uppercase;
  margin-top: 2px;
}

/* Status badges */
.dal-badge {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: .06em;
  text-transform: uppercase;
  padding: 4px 12px;
  border-radius: 20px;
  border: 1px solid var(--bdr2);
  color: var(--t3);
  background: var(--bg3);
}
.dal-badge.live {
  background: var(--grnd);
  border-color: rgba(45,212,170,.25);
  color: var(--grn);
}
.dal-badge.gold {
  background: var(--goldd);
  border-color: var(--goldb);
  color: var(--gold);
}

/* Section header */
.sh {
  font-family: var(--fd);
  font-size: 13px;
  font-weight: 600;
  letter-spacing: .06em;
  text-transform: uppercase;
  color: var(--t3);
  margin: 24px 0 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--bdr);
  display: flex;
  align-items: center;
  gap: 8px;
}

/* Divider */
.sdiv { height: 1px; background: var(--bdr); margin: 14px 0; }

/* Sidebar label */
.slbl {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: .1em;
  text-transform: uppercase;
  color: var(--t3);
  padding-bottom: 6px;
}

/* Skill / tag pills */
.pill {
  display: inline-block;
  background: var(--goldd);
  border: 1px solid var(--goldb);
  color: var(--gold);
  font-size: 11px;
  font-weight: 600;
  padding: 3px 11px;
  border-radius: 20px;
  margin: 3px 2px;
}
.pill.tech {
  background: var(--skyd);
  border-color: rgba(96,184,255,.25);
  color: var(--sky);
}
.pill.miss {
  background: var(--redd);
  border-color: rgba(249,112,112,.25);
  color: var(--red);
}
.pill.src {
  background: var(--grnd);
  border-color: rgba(45,212,170,.25);
  color: var(--grn);
}

/* AI response block */
.aib {
  background: var(--bg3);
  border: 1px solid var(--bdr);
  border-left: 3px solid var(--gold);
  border-radius: 0 var(--r) var(--r) var(--r);
  padding: 18px 22px;
  font-size: 13.5px;
  line-height: 1.8;
  color: var(--t1);
  margin: 14px 0;
  position: relative;
}
.aib::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: radial-gradient(ellipse 50% 60% at 0% 0%,
    rgba(244,185,66,.04) 0%, transparent 60%);
  border-radius: inherit;
  pointer-events: none;
}
.ailbl {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: .1em;
  text-transform: uppercase;
  color: var(--gold);
  margin-bottom: 10px;
}

/* Job card */
.jcard {
  background: var(--bg3);
  border: 1px solid var(--bdr);
  border-radius: var(--r);
  padding: 20px 22px;
  margin-bottom: 14px;
  transition: border-color .2s, transform .2s, box-shadow .2s;
  position: relative;
  overflow: hidden;
}
.jcard::before {
  content: '';
  position: absolute;
  top: 0; left: 0; width: 3px; height: 100%;
  background: linear-gradient(180deg, var(--gold), var(--amb));
  opacity: 0;
  transition: opacity .2s;
}
.jcard:hover {
  border-color: var(--goldb);
  transform: translateY(-1px);
  box-shadow: 0 8px 32px rgba(0,0,0,.3);
}
.jcard:hover::before { opacity: 1; }

/* Project card */
.pcard {
  background: var(--bg4);
  border: 1px solid var(--bdr);
  border-left: 3px solid var(--amb);
  border-radius: 0 var(--r) var(--r) var(--r);
  padding: 14px 18px;
  margin-bottom: 10px;
}

/* Scrape log */
.scrape-box {
  background: var(--bg3);
  border: 1px solid var(--goldb);
  border-radius: var(--r);
  padding: 14px 18px;
  margin: 12px 0;
  font-family: var(--fm);
  font-size: 12px;
  color: var(--t2);
  line-height: 2;
}
.scrape-box strong { color: var(--gold); }

/* Form */
[data-testid="stForm"] { border: none !important; padding: 0 !important; }

/* Sidebar logo area */
.dal-sbar-logo {
  padding: 20px 18px 16px;
  border-bottom: 1px solid var(--bdr);
  background: linear-gradient(180deg, rgba(244,185,66,.04) 0%, transparent 100%);
}

/* Gradient ornament lines */
.dal-ornament {
  height: 1px;
  background: linear-gradient(90deg,
    transparent 0%, var(--goldb) 30%, var(--gold) 50%, var(--goldb) 70%, transparent 100%);
  margin: 16px 0;
}

/* Stats row */
.dal-stat {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 5px 0;
  font-size: 12.5px;
  color: var(--t2);
  border-bottom: 1px solid var(--bdr);
}
.dal-stat:last-child { border-bottom: none; }
.dal-stat-val { color: var(--gold); font-weight: 700; }
</style>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# API helpers
# ══════════════════════════════════════════════════════════════════════════════
def _key():
    try:
        if "GROQ_API_KEY" in st.secrets: return st.secrets["GROQ_API_KEY"]
    except Exception: pass
    return os.getenv("GROQ_API_KEY", "")

def _gh_token():
    try:
        if "GITHUB_TOKEN" in st.secrets: return st.secrets["GITHUB_TOKEN"]
    except Exception: pass
    return os.getenv("GITHUB_TOKEN", "")

def _groq():
    from groq import Groq
    k = _key()
    if not k:
        st.error("GROQ_API_KEY not set. Add it to .env or secrets.toml.")
        st.stop()
    return Groq(api_key=k)

def _llm(client, msgs, max_tokens=900):
    """
    Groq-only smart fallback chain.
    Tries models from best quality → fastest, all on the same API key.
    """
    GROQ_MODELS = [
        "llama-3.3-70b-versatile",
        "deepseek-r1-distill-llama-70b",
        "qwen-qwen2-5-72b",
        "llama-3.1-8b-instant",
        "gemma2-9b-it",
    ]

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
            err = str(e).lower()
            if any(x in err for x in ("api key", "unauthorized", "401", "invalid_api_key")):
                st.error("❌ Invalid GROQ_API_KEY. Check your .env or secrets.toml.")
                st.stop()
            continue

    return "⚠️ All Groq models are currently rate-limited. Please wait a moment and try again."


# ── BUG #3 FIX: return [] instead of {} on parse failure ──────────────────
def _parse_json(text):
    text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    for pat in [r"\[.*\]", r"\{.*\}"]:
        m = re.search(pat, text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except Exception:
                pass
    return []   # ← was {}, now [] so downstream isinstance(matches, list) is safer


# ══════════════════════════════════════════════════════════════════════════════
# Job database helpers
# ══════════════════════════════════════════════════════════════════════════════
DATA_DIR    = Path("data")
COMBINED    = DATA_DIR / "jobs_combined.csv"
CACHE_HOURS = 24

def _load_combined() -> list:
    if HAS_SCRAPER:
        return _ds.load_combined()
    if not COMBINED.exists(): return []
    try:
        import pandas as pd
        df = pd.read_csv(str(COMBINED), on_bad_lines="skip", nrows=5000)
        return df.fillna("").to_dict("records")
    except Exception: return []

def _cache_fresh() -> bool:
    if not COMBINED.exists(): return False
    age = (datetime.datetime.now() -
           datetime.datetime.fromtimestamp(COMBINED.stat().st_mtime)).total_seconds()
    return age < CACHE_HOURS * 3600


# ── BUG #4 FIX: db_checked only set on success; retries on next load if failed
def _auto_build():
    if st.session_state.get("db_checked"):
        return
    try:
        if _cache_fresh():
            st.session_state.db_checked = True
            return
        with st.sidebar:
            ph = st.empty()
            ph.warning("🔄 Building job database…")
            if HAS_SCRAPER:
                _ds.scrape_and_save(status_ph=ph)
            else:
                _fallback_build(ph)
            ph.success("✅ Job database ready")
            time.sleep(2)
            ph.empty()
        st.session_state.db_checked = True   # ← only set after successful build
    except Exception as e:
        st.sidebar.warning(f"⚠️ Auto-build failed: {e}")
        # db_checked intentionally NOT set → will retry on next load


def _fallback_build(ph=None):
    import requests, pandas as pd
    def say(m):
        if ph: ph.info(m)
    jobs = []
    say("📡 RemoteOK…")
    try:
        r = requests.get("https://remoteok.com/api",
                         headers={"User-Agent": "Daleel/1.0"}, timeout=14)
        for j in r.json()[:150]:
            if isinstance(j, dict) and "id" in j:
                jobs.append({"title": j.get("position",""), "company": j.get("company",""),
                             "description": str(j.get("description",""))[:400],
                             "location": j.get("location","Remote"), "salary": "",
                             "url": j.get("url",""), "source": "RemoteOK"})
    except Exception: pass
    DATA_DIR.mkdir(exist_ok=True)
    pd.DataFrame(jobs).to_csv(str(COMBINED), index=False)
    return len(jobs)


# ══════════════════════════════════════════════════════════════════════════════
# Diverse candidate selection (fallback only — used when engine unavailable)
# ══════════════════════════════════════════════════════════════════════════════

# ── BUG #5 FIX: import SKILL_ALIASES so this fallback path also benefits ──
try:
    from matching_engine import SKILL_ALIASES as _SKILL_ALIASES
except ImportError:
    _SKILL_ALIASES = {}

def _expand_skills(skills: list) -> list:
    """Expand user skills to include all known synonyms for broader matching."""
    expanded = set(s.lower() for s in skills)
    for skill in skills:
        canonical = skill.lower().strip()
        # Check if this skill maps to a canonical form
        for canon, aliases in _SKILL_ALIASES.items():
            if canonical in [a.lower() for a in aliases] or canonical == canon:
                expanded.update(a.lower() for a in aliases)
                expanded.add(canon)
    return list(expanded)

def _diverse_candidates(jobs, skills, roles, location_pref="", n=30):
    loc_lower     = location_pref.lower() if location_pref else ""
    is_egypt_pref = loc_lower in EGYPT_ALIASES

    # BUG #5 FIX: expand skills with aliases before scoring
    expanded_skills = _expand_skills(skills)

    def _score(j):
        blob = (str(j.get("title","")) + " " +
                str(j.get("description","")) + " " +
                str(j.get("location",""))).lower()
        src  = str(j.get("source","")).lower()
        # Use expanded skills (includes synonyms) for matching
        s    = sum(2 for sk in expanded_skills if sk in blob)
        s   += sum(1 for ro in roles for w in ro.lower().split()
                   if len(w) > 3 and w in blob)
        if loc_lower:
            jloc      = (j.get("location","") or "").lower()
            is_remote = "remote" in jloc or "worldwide" in jloc
            if is_egypt_pref:
                if any(a in jloc for a in EGYPT_ALIASES) or src == "wuzzuf":
                    s += 15
                elif is_remote: s += 5
                else: s -= 5
            else:
                if loc_lower in jloc: s += 15
                elif is_remote: s += 5
                else: s -= 5
        return s

    scored  = sorted(jobs, key=_score, reverse=True)
    buckets = {}
    for j in scored:
        src = j.get("source","Unknown")
        buckets.setdefault(src, []).append(j)

    num_src    = max(len(buckets), 1)
    per_source = max(3, n // num_src)
    diverse, seen = [], set()

    for rnd in range(per_source):
        for src_jobs in buckets.values():
            if rnd < len(src_jobs):
                j = src_jobs[rnd]
                k = (j.get("title","")[:40].lower(), j.get("company","")[:30].lower())
                if k not in seen:
                    seen.add(k); diverse.append(j)
                if len(diverse) >= n: break
        if len(diverse) >= n: break

    for j in scored:
        if len(diverse) >= n: break
        k = (j.get("title","")[:40].lower(), j.get("company","")[:30].lower())
        if k not in seen:
            seen.add(k); diverse.append(j)

    return diverse[:n]


# ══════════════════════════════════════════════════════════════════════════════
# Job matching  –  3-stage pipeline
# ══════════════════════════════════════════════════════════════════════════════

# ── BUG #1 FIX: route through JobMatcher when available ───────────────────
def match_jobs(user_profile: dict, limit: int = 8, location_pref: str = "") -> dict:
    # If job_matcher.py is importable, delegate to it (fixes dead code bug)
    if HAS_JOB_MATCHER:
        try:
            matcher = JobMatcher()
            return matcher.match_jobs(user_profile, limit=limit, location_pref=location_pref)
        except Exception:
            pass  # fall through to inline implementation below

    # ── Inline fallback (used only when job_matcher.py is unavailable) ────
    all_jobs = _load_combined()
    if not all_jobs:
        return {"success": False,
                "error": "Job database is empty. Click 🔄 Refresh Job Database in the sidebar."}

    skills = [s.lower() for s in user_profile.get("skills", [])]
    roles  = [r.lower() for r in user_profile.get("interested_roles", [])]
    pipeline_stages = []

    # Stage 0: Semantic
    if HAS_SEMANTIC:
        try:
            pool = semantic_rank(all_jobs, user_profile,
                                 location_pref=location_pref, top_n=100)
            pipeline_stages.append("🧠 Semantic")
        except Exception:
            pool = all_jobs
    else:
        pool = all_jobs

    # Stage 1: Deterministic engine
    if HAS_ENGINE:
        try:
            candidates = score_and_rank(pool, user_profile,
                                        location_pref=location_pref, top_n=30, source_cap=6)
            pipeline_stages.append("⚙️ Engine")
        except Exception:
            candidates = _diverse_candidates(pool, skills, roles,
                                             location_pref=location_pref, n=30)
    else:
        candidates = _diverse_candidates(pool, skills, roles,
                                         location_pref=location_pref, n=30)

    pipeline_stages.append("🤖 LLM")
    sources_present = sorted({j.get("source","?") for j in candidates})

    compact = []
    for j in candidates:
        entry = {
            "title":       str(j.get("title",""))[:60],
            "company":     str(j.get("company",""))[:40],
            "location":    str(j.get("location",""))[:40],
            "description": str(j.get("description",""))[:200],
            "salary":      str(j.get("salary",""))[:30],
            "url":         str(j.get("url","")),
            "source":      str(j.get("source","")),
        }
        if "_engine_score"   in j: entry["pre_score"]      = j["_engine_score"]
        if "_matched_skills" in j: entry["matched_skills"] = j.get("_matched_skills",[])
        if "_semantic_score" in j: entry["semantic_score"] = round(j["_semantic_score"]*100)
        compact.append(entry)

    # URL lookup (title+company keyed)
    url_lookup: dict = {}
    for j in compact:
        real_url = str(j.get("url","")).strip()
        if real_url.startswith("http"):
            key = (str(j.get("title",""))[:40].lower(),
                   str(j.get("company",""))[:30].lower())
            url_lookup[key] = real_url

    pipeline_note = (
        "Candidates were pre-filtered by semantic embeddings and a deterministic engine.\n"
        "'semantic_score' (0-100) = cosine similarity. 'pre_score' (0-100) = engine score.\n\n"
        if pipeline_stages else ""
    )

    loc_display   = location_pref or "Remote / Worldwide"
    is_egypt_pref = location_pref.lower() in EGYPT_ALIASES if location_pref else False
    egypt_note    = (
        "  • Egypt: Cairo, Giza, Alexandria, Wuzzuf-sourced jobs all count as local.\n"
        if is_egypt_pref else ""
    )

    # ── BUG #2 FIX: truncate on whole job objects only ────────────────────
    jobs_str = json.dumps(compact, indent=2)
    if len(jobs_str) > 12000:
        truncated = []
        for job in compact:
            candidate_str = json.dumps(truncated + [job], indent=2)
            if len(candidate_str) > 11500:
                break
            truncated.append(job)
        jobs_str = json.dumps(truncated, indent=2)

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
        "   NEVER place a different-country job above a local match.\n"
        "2. SKILL MATCH: rank by matched_skills count within the same location tier.\n"
        "3. SOURCE DIVERSITY: prefer different sources when scores are close.\n\n"
        "URL RULE: copy the exact url from the listing data. Do NOT invent URLs.\n"
        "If a listing has no url, use an empty string.\n\n"
        f"Sources: {', '.join(sources_present)}\n\n"
        f"User profile:\n"
        f"  Skills: {user_profile.get('skills',[])}\n"
        f"  Experience: {user_profile.get('experience_years',0)} years\n"
        f"  Seniority: {user_profile.get('seniority_level','')}\n"
        f"  Roles: {user_profile.get('interested_roles',[])}\n\n"
        f"Candidates ({len(compact)}):\n"
        f"{jobs_str}\n\n"   # ← uses safely truncated string (Bug #2 fix)
        "Return ONLY the JSON array."
    )

    raw     = _llm(client, [{"role":"user","content":prompt}], max_tokens=1500)
    matches = _parse_json(raw)
    if isinstance(matches, dict) and "jobs" in matches: matches = matches["jobs"]
    if not isinstance(matches, list): matches = []

    for m in matches:
        key = (str(m.get("title",""))[:40].lower(), str(m.get("company",""))[:30].lower())
        real_url = url_lookup.get(key,"")
        if real_url:
            m["url"] = real_url
        elif not str(m.get("url","")).startswith("http"):
            m["url"] = ""

    return {
        "success":               True,
        "matches":               matches,
        "total_in_db":           len(all_jobs),
        "candidates_evaluated":  len(compact),
        "sources_in_candidates": sources_present,
        "pipeline_stages":       pipeline_stages,
    }


# ══════════════════════════════════════════════════════════════════════════════
# CV analysis
# ══════════════════════════════════════════════════════════════════════════════
def analyze_cv(pdf_path: str) -> dict:
    if HAS_CV_ANALYZER:
        try:
            return CVAnalyzer().analyze_cv(pdf_path)
        except Exception as e:
            return {"success": False, "error": str(e)}

    from pypdf import PdfReader
    text = "\n".join(p.extract_text() or "" for p in PdfReader(pdf_path).pages)
    if not text.strip():
        return {"success": False,
                "error": "Could not read text from this PDF. Make sure it is not scanned."}
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
    raw    = _llm(client, [{"role":"user","content":prompt}], max_tokens=1400)
    parsed = _parse_json(raw)
    if not parsed or "skills" not in parsed:
        return {"success": False, "error": "AI could not parse your CV. Try a cleaner PDF."}
    return {"success": True, "analysis": parsed}


# ══════════════════════════════════════════════════════════════════════════════
# GitHub analysis
# ══════════════════════════════════════════════════════════════════════════════
def analyze_github(username: str) -> dict:
    import requests
    hdrs = {"Accept": "application/vnd.github+json"}
    tok = _gh_token()
    if tok: hdrs["Authorization"] = f"Bearer {tok}"
    base = f"https://api.github.com/users/{username}"
    try:
        u = requests.get(base, headers=hdrs, timeout=10)
        if u.status_code == 404:
            return {"success": False, "error": f"User '{username}' not found on GitHub."}
        u.raise_for_status(); user = u.json()
    except Exception as e:
        return {"success": False, "error": f"GitHub API error: {e}"}
    try:
        rr    = requests.get(f"{base}/repos", headers=hdrs,
                             params={"per_page":30,"sort":"pushed"}, timeout=10)
        repos = rr.json() if rr.ok else []
    except Exception: repos = []
    lang_counts = {}
    for repo in repos[:20]:
        if repo.get("language"):
            lang_counts[repo["language"]] = lang_counts.get(repo["language"],0)+1
    profile = {
        "login": user.get("login",""), "name": user.get("name",""),
        "bio": user.get("bio",""),     "followers": user.get("followers",0),
        "following": user.get("following",0), "public_repos": user.get("public_repos",0),
        "languages": dict(sorted(lang_counts.items(), key=lambda x:-x[1])[:8]),
        "top_repos": [{"name":r.get("name"),"stars":r.get("stargazers_count",0),
                       "description":r.get("description","")} for r in repos[:5]],
    }
    client = _groq()
    prompt = (
        "You are a tech recruiter. Assess this GitHub profile.\n"
        "Return ONLY valid JSON — no markdown.\n\n"
        '{"profile_score":<0-100>,"summary":"3-4 honest sentences",'
        '"strengths":[""],"recommendations":["","",""]}\n\n'
        f"User:{profile['login']}, Bio:{profile.get('bio','—')}, "
        f"Repos:{profile['public_repos']}, Followers:{profile['followers']}, "
        f"Languages:{', '.join(profile['languages'].keys())}, "
        f"Top repos:{json.dumps(profile['top_repos'][:3])}"
    )
    raw = _llm(client, [{"role":"user","content":prompt}], max_tokens=600)
    return {"success": True, "profile": profile, "analysis": _parse_json(raw)}


# ══════════════════════════════════════════════════════════════════════════════
# Chat
# ══════════════════════════════════════════════════════════════════════════════
def _chat_context() -> str:
    parts = []
    if st.session_state.cv_analysis:
        a = st.session_state.cv_analysis.get("analysis", {})
        if isinstance(a, dict):
            parts.append(f"CV Summary: {a.get('summary','')}")
            parts.append(f"Seniority: {a.get('seniority_level','?')}, "
                         f"Experience: {a.get('experience_years','?')} years")
            parts.append(f"Skills: {', '.join(a.get('skills',[]))}")
            parts.append(f"Technologies: {', '.join(a.get('technologies',[]))}")
            parts.append(f"Strengths: {', '.join(a.get('strengths',[]))}")
            parts.append(f"Areas to improve: {', '.join(a.get('improvement_areas',[]))}")
            exp = a.get("experience",[])
            if exp:
                parts.append("Work history: " + " | ".join(
                    f"{e.get('title')} at {e.get('company')} ({e.get('duration','')})"
                    for e in exp[:4] if isinstance(e,dict)))
            projs = a.get("projects",[])
            if projs:
                parts.append("Projects: " + " | ".join(
                    f"{p.get('name')}: {p.get('description','')[:80]}"
                    for p in projs[:5] if isinstance(p,dict)))
            edu = a.get("education",[])
            if edu:
                parts.append("Education: " + " | ".join(
                    f"{e.get('degree')} in {e.get('field')} from {e.get('school')}"
                    for e in edu[:2] if isinstance(e,dict)))
    if st.session_state.github_analysis:
        p   = st.session_state.github_analysis.get("profile",{})
        ana = st.session_state.github_analysis.get("analysis",{})
        parts.append(f"GitHub: {p.get('public_repos',0)} repos, "
                     f"followers: {p.get('followers',0)}, "
                     f"languages: {', '.join(list(p.get('languages',{}).keys()))}")
        if isinstance(ana, dict):
            parts.append(f"GitHub score: {ana.get('profile_score','?')}/100")
            parts.append(f"GitHub recommendations: {', '.join(ana.get('recommendations',[]))}")
    if st.session_state.job_matches:
        ms = st.session_state.job_matches.get("matches",[])
        if ms:
            parts.append(f"All {len(ms)} job matches:\n" + "\n".join(
                f"{j.get('title')} at {j.get('company')} "
                f"({j.get('match_score')}% match, {j.get('location','')}) "
                f"[{j.get('source','')}] - missing: {', '.join(j.get('missing_skills',[]))}"
                for j in ms if isinstance(j,dict)))
    loc = st.session_state.get("job_location_pref","")
    if loc: parts.append(f"Preferred location: {loc}")
    return "\n".join(parts)

def _chat_reply(user_msg: str) -> str:
    client = _groq()
    ctx    = _chat_context()
    system = (
        "You are Daleel, a warm and insightful career guide. "
        "Keep replies concise and conversational — no more than 3 short paragraphs. "
        "Ask at most ONE follow-up question. "
        "Reference the user's actual skills, projects, and job matches by name. "
        "Sound like a knowledgeable mentor, not a chatbot."
        + (f"\n\nWhat you know about this user:\n{ctx}" if ctx else
           "\n\nNo user data yet — encourage them to use the CV or Job tabs first.")
    )
    history = st.session_state.chat_history[-12:]
    msgs    = [{"role":"system","content":system}] + history + \
              [{"role":"user","content":user_msg}]
    return _llm(client, msgs, max_tokens=500)

def _render_chat():
    st.markdown("""
<div style="
  background: linear-gradient(180deg, var(--bg2) 0%, rgba(15,15,26,.99) 100%);
  border-bottom: 1px solid var(--bdr);
  padding: 14px 18px;
  display: flex; align-items: center; gap: 12px;
  flex-shrink: 0;
  position: relative;
  overflow: hidden;
">
  <div style="position:absolute;top:0;left:0;right:0;bottom:0;
    background:radial-gradient(ellipse 80% 120% at 0% 50%,
    rgba(244,185,66,.06) 0%,transparent 60%);pointer-events:none"></div>
  <div style="
    width:34px;height:34px;border-radius:10px;
    background:linear-gradient(135deg,#C8850A,#F4B942);
    display:flex;align-items:center;justify-content:center;font-size:16px;
    box-shadow:0 3px 14px rgba(244,185,66,.3);flex-shrink:0
  ">🧭</div>
  <div>
    <div style="font-family:var(--fd);font-size:14px;font-weight:700;color:var(--t1)">
      Daleel Chat
    </div>
    <div style="font-size:10px;color:var(--t3);letter-spacing:.06em;text-transform:uppercase">
      Your Career Guide · Groq AI
    </div>
  </div>
  <span style="
    margin-left:auto;font-size:9px;font-weight:700;letter-spacing:.06em;
    text-transform:uppercase;
    background:var(--grnd);border:1px solid rgba(45,212,170,.3);
    color:var(--grn);padding:3px 10px;border-radius:10px
  ">● Live</span>
</div>""", unsafe_allow_html=True)

    chat_html = (
        '<div style="overflow-y:auto;max-height:52vh;padding:14px 12px;'
        'display:flex;flex-direction:column;gap:10px">'
    )
    for m in st.session_state.chat_history:
        txt = html.escape(m["content"])
        if m["role"] == "assistant":
            chat_html += (
                f'<div style="background:var(--bg3);border:1px solid var(--bdr);'
                f'border-top-left-radius:4px;border-radius:14px;padding:11px 14px;'
                f'font-size:13px;line-height:1.7;color:var(--t1);max-width:92%">{txt}</div>'
            )
        else:
            chat_html += (
                f'<div style="background:linear-gradient(135deg,#7A4800,#C8850A);'
                f'color:#fff;border-top-right-radius:4px;border-radius:14px;'
                f'padding:11px 14px;font-size:13px;line-height:1.7;'
                f'max-width:92%;margin-left:auto">{txt}</div>'
            )
    chat_html += "</div>"
    st.markdown(chat_html, unsafe_allow_html=True)

    with st.form(key="chat_form", clear_on_submit=True):
        user_input = st.text_input(
            "Message", placeholder="Ask Daleel anything…",
            label_visibility="collapsed", key="chat_input_field",
        )
        col_send, col_clear = st.columns([3, 1])
        with col_send:   submitted = st.form_submit_button("Send ➤", use_container_width=True)
        with col_clear:  cleared   = st.form_submit_button("🗑", use_container_width=True)

    if submitted and (user_input or "").strip():
        with st.spinner("Daleel is thinking…"):
            reply = _chat_reply(user_input.strip())
        st.session_state.chat_history.append({"role":"user","content":user_input.strip()})
        st.session_state.chat_history.append({"role":"assistant","content":reply})
        st.rerun()
    if cleared:
        st.session_state.chat_history = []
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# Session state
# ══════════════════════════════════════════════════════════════════════════════
def _init():
    defaults = {
        "cv_analysis": None, "github_analysis": None,
        "job_matches": None, "db_checked": False,
        "skill_scrape_done": False, "_jobs_skills_shown": False,
        "chat_history": [], "last_scraped_skills": [],
        "job_location_pref": "Egypt",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ── Render helpers ─────────────────────────────────────────────────────────
def _pill(t, k="skill"):
    cls = {"skill":"pill","tech":"pill tech","miss":"pill miss","src":"pill src"}.get(k,"pill")
    return f'<span class="{cls}">{html.escape(str(t))}</span>'

def _pills(items, k="skill"):
    if not items: return '<span style="color:var(--t3);font-size:12px">—</span>'
    return "".join(_pill(i,k) for i in items)

def _sc(s):
    if s >= 80: return "var(--grn)"
    if s >= 60: return "var(--gold)"
    if s >= 40: return "var(--amb)"
    return "var(--red)"

def _dot(col="var(--gold)"):
    return (f'<div style="width:8px;height:8px;border-radius:50%;background:{col};'
            f'margin-top:5px;flex-shrink:0"></div>')

_SRC_COLOURS = {
    "RemoteOK":  "#60B8FF", "Arbeitnow": "#A78BFA", "Remotive":  "#2DD4AA",
    "Jobicy":    "#F4B942", "The Muse":  "#F472B6", "Wuzzuf":    "#FB923C",
    "Himalayas": "#38BDF8", "Local CSV": "#94A3B8",
}

def _src_badge(source: str) -> str:
    col = _SRC_COLOURS.get(source, "#7A8AB0")
    return (f'<span style="font-size:10px;font-weight:700;letter-spacing:.04em;'
            f'padding:2px 9px;border-radius:10px;'
            f'border:1px solid {col}40;color:{col};background:{col}14;margin-left:6px">'
            f'{html.escape(source)}</span>')


# ══════════════════════════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════════════════════════
def _sidebar():
    with st.sidebar:
        st.markdown("""
<div class="dal-sbar-logo">
  <div style="display:flex;align-items:center;gap:12px">
    <div class="dal-logo">🧭</div>
    <div>
      <div class="dal-brand">Da<span>leel</span></div>
      <div class="dal-subbrand" style="font-size:9.5px;color:var(--t3);
        letter-spacing:.1em;text-transform:uppercase;margin-top:3px">
        Career Intelligence
      </div>
    </div>
  </div>
  <div class="dal-ornament" style="margin-top:14px;margin-bottom:0"></div>
  <div style="display:flex;align-items:center;justify-content:space-between;
    margin-top:8px">
    <span style="font-size:10px;color:var(--t3);letter-spacing:.06em;
      text-transform:uppercase">v1.0 · URL Verified</span>
    <span style="font-size:9px;background:var(--goldd);border:1px solid var(--goldb);
      color:var(--gold);padding:2px 9px;border-radius:10px;font-weight:700">
      دليل
    </span>
  </div>
</div>""", unsafe_allow_html=True)

        st.markdown("<div style='padding:12px 16px 0'>", unsafe_allow_html=True)

        st.markdown('<div class="slbl">System Status</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1: st.metric("Groq AI",  "🟢 Ready" if _key()       else "🔴 Missing")
        with c2: st.metric("Scraper",  "🟢 Ready" if HAS_SCRAPER  else "⚪ Basic")
        cnt = len(_load_combined())
        c3, c4 = st.columns(2)
        with c3: st.metric("Jobs DB",  f"🟢 {cnt:,}" if cnt       else "🔴 Empty")
        with c4: st.metric("GitHub",   "🟢" if _gh_token()        else "⚪ Optional")

        st.markdown('<div class="sdiv"></div>', unsafe_allow_html=True)

        st.markdown('<div class="slbl">Matching Pipeline</div>', unsafe_allow_html=True)
        for lbl, active, tip in [
            ("🧠 Semantic (embeddings)", HAS_SEMANTIC, "pip install sentence-transformers"),
            ("⚙️ Keyword Engine",        HAS_ENGINE,   "matching_engine.py required"),
            ("🤖 Groq LLM",             bool(_key()), "GROQ_API_KEY required"),
        ]:
            col = "var(--grn)" if active else "var(--red)"
            st.markdown(
                f'<div style="font-size:12px;color:{col};padding:2px 0">'
                f'{"✅" if active else "❌"} {lbl}</div>'
                + (f'<div style="font-size:10px;color:var(--t3);padding-left:18px;'
                   f'margin-bottom:2px">{tip}</div>' if not active else ""),
                unsafe_allow_html=True,
            )
        if not _key(): st.error("GROQ_API_KEY missing.\nAdd to .env or secrets.toml.")

        st.markdown('<div class="sdiv"></div>', unsafe_allow_html=True)

        st.markdown('<div class="slbl">Job Sources</div>', unsafe_allow_html=True)
        src_counts = {}
        if HAS_SCRAPER and COMBINED.exists():
            try: src_counts = _ds.source_counts()
            except Exception: pass

        sources_cfg = [
            ("RemoteOK",  True),  ("Arbeitnow", True), ("Remotive", True),
            ("Jobicy",    True),  ("The Muse",  True), ("Himalayas",True),
            ("Wuzzuf 🇪🇬", True), ("Local CSV", (DATA_DIR/"jobs.csv").exists()),
        ]
        for src, status in sources_cfg:
            dot   = "🟢" if status else "⚪"
            count = src_counts.get(src, src_counts.get(src.replace(" 🇪🇬",""),0))
            cnt_s = (f' <span style="color:var(--gold);font-weight:700">({count})</span>'
                     if count else "")
            st.markdown(
                f'<div style="font-size:12px;color:var(--t2);padding:2px 0">'
                f'{dot} {src}{cnt_s}</div>',
                unsafe_allow_html=True,
            )

        st.markdown('<div class="sdiv"></div>', unsafe_allow_html=True)

        st.markdown('<div class="slbl">Database</div>', unsafe_allow_html=True)
        if COMBINED.exists():
            age_h = (datetime.datetime.now() -
                     datetime.datetime.fromtimestamp(COMBINED.stat().st_mtime)
                    ).total_seconds() / 3600
            st.caption(f"Cache: {age_h:.0f}h old · refreshes every {CACHE_HOURS}h")

        if st.button("🔄 Refresh Job Database", key="sb_ref", use_container_width=True):
            ph     = st.empty()
            skills = []
            if st.session_state.cv_analysis:
                a = st.session_state.cv_analysis.get("analysis",{})
                if isinstance(a,dict): skills = a.get("skills",[])
            try:
                if HAS_SCRAPER:
                    _ds.scrape_and_save(skills=skills or None, status_ph=ph)
                else:
                    n = _fallback_build(ph)
                    ph.success(f"✅ {n:,} jobs loaded")
            except Exception as e:
                ph.error(f"❌ {e}")

        if st.button("🕷️ Run Full Spider (All Sources)", key="sb_spider", use_container_width=True):
            ph = st.empty()
            try:
                if HAS_SCRAPER:
                    _ds.scrape_and_save(skills=None, status_ph=ph)
                    ph.success("✅ Full spider completed. Job database updated from all sources.")
                else:
                    n = _fallback_build(ph)
                    ph.success(f"✅ Fallback spider loaded {n} jobs from RemoteOK.")
            except Exception as e:
                ph.error(f"❌ Spider error: {e}")
            time.sleep(2)
            ph.empty()

        st.markdown('<div class="sdiv"></div>', unsafe_allow_html=True)

        st.markdown('<div class="slbl">Your Progress</div>', unsafe_allow_html=True)
        for lbl, done in [
            ("📄 CV analyzed",    st.session_state.cv_analysis   is not None),
            ("🐙 GitHub analyzed",st.session_state.github_analysis is not None),
            ("💼 Jobs matched",   st.session_state.job_matches   is not None),
            ("💬 Chat active",    len(st.session_state.chat_history) > 0),
        ]:
            col = "var(--grn)" if done else "var(--t3)"
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;padding:4px 0;'
                f'font-size:12.5px;color:{col}">{"✅" if done else "⬜"} {lbl}</div>',
                unsafe_allow_html=True,
            )

        if st.button("🗑 Clear Session", key="sb_clear", use_container_width=True):
            for k in ["cv_analysis","github_analysis","job_matches",
                      "skill_scrape_done","_jobs_skills_shown",
                      "chat_history","last_scraped_skills"]:
                st.session_state[k] = [] if k in ("chat_history","last_scraped_skills") else None
            if "js_skills_v3" in st.session_state: del st.session_state["js_skills_v3"]
            st.rerun()

        st.markdown('<div class="sdiv"></div>', unsafe_allow_html=True)

        if any([st.session_state.cv_analysis, st.session_state.github_analysis,
                st.session_state.job_matches]):
            st.download_button(
                "📥 Download Report",
                data=json.dumps({
                    "generated_at": datetime.datetime.now().isoformat(),
                    "cv": st.session_state.cv_analysis,
                    "github": st.session_state.github_analysis,
                    "jobs": st.session_state.job_matches,
                }, indent=2, default=str),
                file_name=f"daleel_report_{datetime.date.today()}.json",
                mime="application/json",
                use_container_width=True,
                key="sb_dl",
            )

        with st.expander("⚙️ Setup Guide"):
            st.markdown("""
**`.env`**
```
GROQ_API_KEY=gsk_...
GITHUB_TOKEN=ghp_...  # optional
```
**7 Job Sources:** RemoteOK · Arbeitnow · Remotive · Jobicy · The Muse · Himalayas · Wuzzuf 🇪🇬

**Local CSV:** place `jobs.csv` in the `data/` folder.
""")
        st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Header
# ══════════════════════════════════════════════════════════════════════════════
def _header():
    ready   = any([st.session_state.cv_analysis, st.session_state.github_analysis,
                   st.session_state.job_matches])
    sources = "RemoteOK · Arbeitnow · Remotive · Jobicy · The Muse · Himalayas · Wuzzuf 🇪🇬"
    st.markdown(
        '<div class="dal-hdr">'
        '<div style="display:flex;align-items:center;gap:16px">'
        '<div class="dal-logo">🧭</div>'
        '<div>'
        '<div class="dal-brand">Da<span>leel</span>'
        '<span style="font-family:var(--ff);font-size:13px;font-weight:400;'
        'color:var(--t3);margin-left:10px;letter-spacing:.08em">· دليل</span>'
        '</div>'
        f'<div style="font-size:11px;color:var(--t3);margin-top:2px;letter-spacing:.02em">'
        f'{sources}</div>'
        '</div></div>'
        '<div style="display:flex;gap:8px;align-items:center">'
        + ('<div class="dal-badge live">● Active Session</div>' if ready
           else '<div class="dal-badge">○ No Data Yet</div>')
        + '<div class="dal-badge gold">Groq · LLaMA 3.3</div>'
        + ('<div class="dal-badge">🕷 7 Sources</div>' if HAS_SCRAPER else '')
        + '</div></div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Tab: CV
# ══════════════════════════════════════════════════════════════════════════════
def _tab_cv():
    st.markdown('<div class="sh">📄 CV Analyzer</div>', unsafe_allow_html=True)
    st.markdown(
        '<p style="color:var(--t2);font-size:13.5px;line-height:1.7;margin-bottom:20px">'
        'Upload your PDF resume. Daleel extracts your skills, experience, and projects — '
        'then auto-fills the Job Matcher so you\'re ready in one click.</p>',
        unsafe_allow_html=True,
    )

    cu, cb = st.columns([3, 1])
    with cu: f = st.file_uploader("Choose your CV (PDF)", type=["pdf"], key="cv_file")
    with cb:
        st.write(""); st.write("")
        go = st.button("🔍 Analyze CV", key="btn_cv", use_container_width=True, disabled=f is None)

    if go and f:
        if not _key(): return
        with st.spinner("Reading your CV — extracting skills, projects & experience…"):
            tmp = f"temp_{f.name}"
            with open(tmp, "wb") as fh: fh.write(f.getbuffer())
            res = analyze_cv(tmp)
            os.remove(tmp)
        if res.get("success"):
            st.session_state.cv_analysis        = res
            st.session_state.skill_scrape_done  = False
            st.session_state._jobs_skills_shown = False
            a = res.get("analysis", {})
            if isinstance(a, dict) and a.get("skills"):
                st.session_state["js_skills_v3"] = "\n".join(str(s) for s in a["skills"])
            proj_count = len(a.get("projects",[])) if isinstance(a, dict) else 0
            st.success(f"✅ CV analyzed — {proj_count} project(s) found. "
                       f"Skills auto-filled in the 💼 Job Matcher tab.")
        else:
            st.error(f"❌ {res.get('error')}"); return

    if not st.session_state.cv_analysis:
        st.info("Upload your CV and click **Analyze CV** to get started."); return

    a = st.session_state.cv_analysis.get("analysis", {})
    if isinstance(a, str): a = _parse_json(a) or {}

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Seniority",  a.get("seniority_level","—"))
    with c2: st.metric("Experience", f"{a.get('experience_years','—')} yrs")
    with c3: st.metric("Skills",     len(a.get("skills",[])))
    with c4: st.metric("Projects",   len(a.get("projects",[])))

    if a.get("summary"):
        st.markdown(
            f'<div class="aib"><div class="ailbl">✦ Daleel Summary</div>'
            f'{html.escape(str(a["summary"]))}</div>',
            unsafe_allow_html=True,
        )

    if a.get("skills") or a.get("technologies"):
        st.markdown('<div class="sh">Skills & Technologies</div>', unsafe_allow_html=True)
        st.markdown(
            _pills(a.get("skills",[]),"skill") + _pills(a.get("technologies",[]),"tech"),
            unsafe_allow_html=True,
        )

    if a.get("experience"):
        st.markdown('<div class="sh">Work Experience</div>', unsafe_allow_html=True)
        for e in a["experience"]:
            st.markdown(
                f'<div style="display:flex;gap:12px;align-items:flex-start;margin-bottom:10px">'
                f'{_dot()}'
                f'<div><div style="font-size:13.5px;font-weight:600;color:var(--t1)">'
                f'{html.escape(str(e.get("title","—")))}</div>'
                f'<div style="font-size:12px;color:var(--t2)">'
                f'{html.escape(str(e.get("company","—")))} · {html.escape(str(e.get("duration","")))}'
                f'</div></div></div>',
                unsafe_allow_html=True,
            )

    projects = a.get("projects", [])
    if projects:
        st.markdown('<div class="sh">🚀 Projects</div>', unsafe_allow_html=True)
        for p in projects:
            if not isinstance(p, dict): continue
            tech_pills = "".join(_pill(t,"tech") for t in p.get("technologies",[]))
            url  = str(p.get("url","")).strip()
            name_html = (
                f'<a href="{html.escape(url)}" target="_blank" '
                f'style="color:var(--amb);text-decoration:none;font-weight:700;'
                f'font-family:var(--fd)">{html.escape(str(p.get("name","—")))}</a>'
                if url else
                f'<span style="color:var(--amb);font-weight:700;font-family:var(--fd)">'
                f'{html.escape(str(p.get("name","—")))}</span>'
            )
            st.markdown(
                f'<div class="pcard">'
                f'<div style="font-size:14px;margin-bottom:5px">{name_html}</div>'
                f'<div style="font-size:12.5px;color:var(--t2);line-height:1.65;margin-bottom:7px">'
                f'{html.escape(str(p.get("description","—")))}</div>'
                f'{tech_pills}</div>',
                unsafe_allow_html=True,
            )

    if a.get("education"):
        st.markdown('<div class="sh">🎓 Education</div>', unsafe_allow_html=True)
        for e in a["education"]:
            st.markdown(
                f'<div style="display:flex;gap:12px;align-items:flex-start;margin-bottom:10px">'
                f'{_dot("var(--grn)")}'
                f'<div><div style="font-size:13.5px;font-weight:600;color:var(--t1)">'
                f'{html.escape(str(e.get("degree","—")))} in {html.escape(str(e.get("field","—")))}'
                f'</div>'
                f'<div style="font-size:12px;color:var(--t2)">'
                f'{html.escape(str(e.get("school","—")))}</div></div></div>',
                unsafe_allow_html=True,
            )

    c1, c2 = st.columns(2)
    with c1:
        if a.get("strengths"):
            st.markdown('<div class="sh">💪 Strengths</div>', unsafe_allow_html=True)
            for s in a["strengths"]:
                st.markdown(
                    f'<div style="color:var(--t2);font-size:13px;padding:4px 0">'
                    f'<span style="color:var(--grn)">✓</span> {html.escape(str(s))}</div>',
                    unsafe_allow_html=True,
                )
    with c2:
        if a.get("improvement_areas"):
            st.markdown('<div class="sh">🎯 Growth Areas</div>', unsafe_allow_html=True)
            for g in a["improvement_areas"]:
                st.markdown(
                    f'<div style="color:var(--t2);font-size:13px;padding:4px 0">'
                    f'<span style="color:var(--gold)">→</span> {html.escape(str(g))}</div>',
                    unsafe_allow_html=True,
                )


# ══════════════════════════════════════════════════════════════════════════════
# Tab: GitHub
# ══════════════════════════════════════════════════════════════════════════════
def _tab_github():
    st.markdown('<div class="sh">🐙 GitHub Profile Analysis</div>', unsafe_allow_html=True)
    ci, cb = st.columns([3, 1])
    with ci: uname = st.text_input("GitHub Username", placeholder="e.g. torvalds", key="gh_username")
    with cb:
        st.write(""); st.write("")
        go = st.button("🔍 Analyze", key="btn_gh",
                       use_container_width=True, disabled=not (uname or "").strip())

    if go and (uname or "").strip():
        if not _key(): return
        with st.spinner(f"Analyzing @{uname.strip()}…"):
            res = analyze_github(uname.strip())
        if res.get("success"): st.session_state.github_analysis = res
        else: st.error(f"❌ {res.get('error')}"); return

    if not st.session_state.github_analysis:
        st.info("Enter a GitHub username and click **Analyze**."); return

    data     = st.session_state.github_analysis
    profile  = data.get("profile",  {})
    analysis = data.get("analysis", {})
    if isinstance(analysis, str): analysis = _parse_json(analysis) or {}

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Followers",    profile.get("followers",   0))
    with c2: st.metric("Public Repos", profile.get("public_repos",0))
    with c3: st.metric("Following",    profile.get("following",   0))
    score = analysis.get("profile_score","—") if isinstance(analysis,dict) else "—"
    with c4: st.metric("Profile Score", f"{score}/100")

    summary = analysis.get("summary","") if isinstance(analysis,dict) else str(analysis)
    if summary:
        st.markdown(
            f'<div class="aib"><div class="ailbl">✦ Daleel Assessment</div>'
            f'{html.escape(str(summary))}</div>',
            unsafe_allow_html=True,
        )

    langs = profile.get("languages",{})
    if langs:
        st.markdown('<div class="sh">Top Languages</div>', unsafe_allow_html=True)
        st.bar_chart(langs)

    recs = analysis.get("recommendations",[]) if isinstance(analysis,dict) else []
    if recs:
        st.markdown('<div class="sh">💡 Recommendations</div>', unsafe_allow_html=True)
        for r in recs:
            st.markdown(
                f'<div style="color:var(--t2);font-size:13px;padding:5px 0">'
                f'<span style="color:var(--gold)">→</span> {html.escape(str(r))}</div>',
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# Tab: Job Matcher
# ══════════════════════════════════════════════════════════════════════════════
def _tab_jobs():
    st.markdown('<div class="sh">💼 Job Matcher</div>', unsafe_allow_html=True)
    cnt = len(_load_combined())

    if st.session_state.cv_analysis and not st.session_state._jobs_skills_shown:
        st.success("✅ Skills auto-filled from your CV — edit freely below.")
        st.session_state._jobs_skills_shown = True

    c1, c2 = st.columns(2)
    with c1:
        sr  = st.text_area("Your Skills (one per line)",
                           placeholder="Python\nReact\nSQL",
                           height=130, key="js_skills_v3")
        exp = st.number_input("Years of Experience", 0, 50, 2, key="js_exp")
    with c2:
        sen   = st.selectbox("Seniority Level",
                             ["Junior","Mid-Level","Senior","Lead","Principal"],
                             key="js_sen")
        roles = st.multiselect("Interested Roles", [
            "Full Stack Developer","Backend Engineer","Frontend Developer",
            "Data Scientist","ML Engineer","DevOps Engineer","Product Manager",
            "Mobile Developer","Cloud Architect","QA Engineer",
        ], key="js_roles")

    st.markdown(
        '<div style="margin-top:14px">'
        '<div style="font-size:12px;font-weight:600;letter-spacing:.04em;'
        'text-transform:uppercase;color:var(--t2);margin-bottom:8px">'
        '📍 Where do you want to work?</div>',
        unsafe_allow_html=True,
    )

    QUICK_LOCS = [
        ("🇪🇬 Egypt",   "Egypt"),
        ("🌍 Remote",   "Remote"),
        ("🇺🇸 USA",     "United States"),
        ("🇬🇧 UK",      "United Kingdom"),
        ("🇦🇪 UAE",     "United Arab Emirates"),
        ("🇩🇪 Germany", "Germany"),
        ("🇸🇦 KSA",     "Saudi Arabia"),
        ("🇨🇦 Canada",  "Canada"),
    ]

    chip_cols = st.columns(len(QUICK_LOCS))
    for idx, (label, val) in enumerate(QUICK_LOCS):
        with chip_cols[idx]:
            if st.button(label, key=f"loc_chip_{idx}", use_container_width=True):
                st.session_state["js_loc_text"] = val

    if "js_loc_text" not in st.session_state:
        st.session_state["js_loc_text"] = "Egypt"

    location_pref = st.text_input(
        "location_text",
        value=st.session_state["js_loc_text"],
        placeholder="Type any country, city, or 'Remote'…",
        label_visibility="collapsed",
        key="js_loc_text",
    ).strip()

    loc_lower_hint = location_pref.lower()
    if not location_pref:
        hint = '<span style="color:var(--t3)">No location set — results will be worldwide</span>'
    elif loc_lower_hint in {"remote", "worldwide", "anywhere"}:
        hint = '🌍 <span style="color:var(--t2)">Searching globally for remote-friendly roles</span>'
    elif loc_lower_hint in EGYPT_ALIASES:
        hint = '🇪🇬 <span style="color:var(--amb)">Egypt selected · Wuzzuf scraped · Cairo / Giza / Alexandria all match</span>'
    else:
        hint = (f'🔍 Searching jobs in <strong style="color:var(--gold)">'
                f'{html.escape(location_pref)}</strong>')

    st.markdown(
        f'<div style="font-size:12px;color:var(--t2);margin-top:6px;margin-bottom:4px">'
        f'{hint}</div></div>',
        unsafe_allow_html=True,
    )

    st.session_state.job_location_pref = location_pref
    skills = [s.strip() for s in (sr or "").split("\n") if s.strip()]

    if cnt > 0:
        stages = []
        if HAS_SEMANTIC: stages.append("🧠 Semantic")
        if HAS_ENGINE:   stages.append("⚙️ Engine")
        stages.append("🤖 LLM")
        pipeline_str = " → ".join(stages)
        st.markdown(
            f'<p style="color:var(--t2);font-size:12.5px;margin:10px 0">'
            f'DB: <strong style="color:var(--gold)">{cnt:,} jobs</strong> · 7 sources · '
            f'Pipeline: <strong style="color:var(--gold)">{pipeline_str}</strong></p>',
            unsafe_allow_html=True,
        )
    else:
        st.warning("Job database is empty — clicking **Find My Best Jobs** will scrape it now.")

    go = st.button("🔍 Find My Best Jobs", key="btn_jobs")

    if go:
        if not _key(): return
        if not skills:
            st.warning("Please enter at least one skill."); return

        if HAS_SCRAPER:
            scrape_ph = st.empty()
            log_lines = []

            class _PH:
                def info(self, msg):
                    log_lines.append(msg)
                    scrape_ph.markdown(
                        '<div class="scrape-box">'
                        + "".join(f"<div>{html.escape(l)}</div>" for l in log_lines[-8:])
                        + "</div>",
                        unsafe_allow_html=True,
                    )

            ph_wrapper = _PH()
            ph_wrapper.info(f"🎯 Scraping jobs for: {', '.join(skills)}")
            if location_pref and location_pref != "Remote":
                ph_wrapper.info(f"📍 Location filter: {location_pref}")
            try:
                new_jobs = _ds.scrape_by_skills(skills, limit=60, location=location_pref)
                if new_jobs:
                    by_src = {}
                    for j in new_jobs:
                        by_src[j.get("source","?")] = by_src.get(j.get("source","?"),0)+1
                    bd      = " · ".join(f"{s}:{n}" for s,n in sorted(by_src.items(),key=lambda x:-x[1]))
                    n_saved = _ds.save_jobs(new_jobs)
                    ph_wrapper.info(f"✅ Scraped {len(new_jobs)} fresh jobs → {n_saved:,} total")
                    ph_wrapper.info(f"📊 Sources: {bd}")
                else:
                    ph_wrapper.info("⚠️ Scraper returned 0 jobs — using existing DB")
                time.sleep(0.8)
                scrape_ph.empty()
            except Exception as e:
                scrape_ph.warning(f"⚠️ Scraper error: {e} — using existing DB")

        with st.spinner("🧭 Daleel is finding your best matches…"):
            res = match_jobs(
                user_profile={
                    "skills":           skills,
                    "experience_years": int(exp),
                    "seniority_level":  sen,
                    "interested_roles": roles,
                },
                limit=8,
                location_pref=location_pref,
            )
        if res.get("success"):
            st.session_state.job_matches = res
        else:
            st.error(f"❌ {res.get('error')}"); return

    if not st.session_state.job_matches:
        st.info("Fill in your skills and click **Find My Best Jobs**."); return

    res      = st.session_state.job_matches
    matches  = res.get("matches", [])
    total    = res.get("total_in_db","?")
    evald    = res.get("candidates_evaluated","?")
    sources  = res.get("sources_in_candidates",[])
    p_stages = res.get("pipeline_stages",[])

    if not matches:
        st.warning("No matches found. Try broadening your skills."); return

    src_pills     = "".join(_src_badge(s) for s in sources) if sources else ""
    pipeline_html = (
        '<div style="margin-top:6px;font-size:11px;color:var(--t3)">'
        'Pipeline: <strong style="color:var(--grn)">'
        + " → ".join(p_stages) +
        '</strong></div>'
    ) if p_stages else ""

    st.markdown(
        f'<div class="aib"><div class="ailbl">✦ Results</div>'
        f'Searched <strong>{total:,}</strong> jobs · shortlisted '
        f'<strong>{evald}</strong> candidates from '
        f'<strong>{len(sources)}</strong> sources · '
        f'Daleel picked <strong>{len(matches)}</strong> best fits.'
        f'{pipeline_html}'
        f'<div style="margin-top:10px">Sources: {src_pills}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    for job in matches:
        if not isinstance(job, dict): continue
        score   = int(job.get("match_score",0)); colour = _sc(score)
        sem_s   = job.get("semantic_score")
        matched = job.get("matched_skills",[]); missing = job.get("missing_skills",[])
        why     = job.get("why_good_fit","")
        salary  = str(job.get("salary",""))
        loc     = str(job.get("location",""))
        url     = str(job.get("url","")).strip()
        source  = str(job.get("source",""))

        mp  = "".join(_pill(s,"skill") for s in matched) if matched else ""
        xp  = "".join(_pill(s,"miss")  for s in missing) if missing else ""
        sal_txt = f"  ·  💰 {html.escape(salary)}" if salary not in ("N/A","","nan") else ""
        loc_txt = f"  📍 {html.escape(loc)}" if loc else ""

        title_html = (
            f'<a href="{html.escape(url)}" target="_blank" '
            f'style="color:var(--t1);text-decoration:none;font-family:var(--fd);font-size:15.5px">'
            f'{html.escape(str(job.get("title","—")))}</a>'
            if url.startswith("http") else
            f'<span style="font-family:var(--fd);font-size:15.5px">'
            f'{html.escape(str(job.get("title","—")))}</span>'
        )
        src_b = _src_badge(source) if source else ""

        sem_html = ""
        if sem_s is not None:
            sem_col = _sc(sem_s)
            sem_html = (
                f'<span style="font-size:9px;font-weight:700;padding:2px 8px;'
                f'border-radius:8px;border:1px solid {sem_col}40;'
                f'color:{sem_col};background:{sem_col}14;margin-left:6px">'
                f'🧠 {sem_s}%</span>'
            )

        apply_html = (
            f'<div style="margin-top:12px">'
            f'<a href="{html.escape(url)}" target="_blank" '
            f'style="font-size:12px;font-weight:700;color:#09090F;letter-spacing:.03em;'
            f'background:linear-gradient(135deg,#C8850A,#F4B942);'
            f'padding:7px 18px;border-radius:9px;text-decoration:none;'
            f'box-shadow:0 3px 12px rgba(244,185,66,.3)">Apply Now →</a>'
            f'</div>'
            if url.startswith("http") else
            '<div style="margin-top:10px;font-size:11px;color:var(--t3)">No direct link available</div>'
        )

        st.markdown(f"""
<div class="jcard">
  <div style="display:flex;justify-content:space-between;align-items:flex-start">
    <div style="flex:1">
      <div style="font-size:15.5px;font-weight:700;margin-bottom:2px">
        {title_html}{src_b}{sem_html}
      </div>
      <div style="font-size:12.5px;color:var(--t2);margin-top:3px">
        🏢 {html.escape(str(job.get('company','—')))}{loc_txt}{sal_txt}
      </div>
    </div>
    <div style="text-align:right;flex-shrink:0;margin-left:18px">
      <div style="font-size:26px;font-weight:800;
        font-family:var(--fd);color:{colour};line-height:1">{score}%</div>
      <div style="font-size:9.5px;color:var(--t3);letter-spacing:.05em;
        text-transform:uppercase">Match</div>
    </div>
  </div>
  <div style="background:var(--bg5);border-radius:4px;height:5px;width:100%;margin:10px 0">
    <div style="height:5px;border-radius:4px;width:{score}%;
      background:linear-gradient(90deg,#C8850A,{colour})"></div>
  </div>
  {f'<div style="margin-bottom:7px"><span style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--t3);letter-spacing:.06em">Matched  </span>{mp}</div>' if mp else ""}
  {f'<div style="margin-bottom:9px"><span style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--t3);letter-spacing:.06em">To learn  </span>{xp}</div>' if xp else ""}
  {f'<div style="font-size:13px;color:var(--t2);line-height:1.65;margin-top:8px;font-style:italic">"{html.escape(str(why))}"</div>' if why else ""}
  {apply_html}
</div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Tab: Assessment
# ══════════════════════════════════════════════════════════════════════════════
def _tab_assessment():
    st.markdown('<div class="sh">📊 Full Career Assessment</div>', unsafe_allow_html=True)
    cv_done  = st.session_state.cv_analysis      is not None
    gh_done  = st.session_state.github_analysis  is not None
    job_done = st.session_state.job_matches       is not None

    if not any([cv_done, gh_done, job_done]):
        st.info("Complete at least one analysis first, then come back for your full Daleel report.")
        return

    c1, c2, c3 = st.columns(3)
    with c1: st.metric("CV",     "✅ Done" if cv_done  else "⬜ Pending")
    with c2: st.metric("GitHub", "✅ Done" if gh_done  else "⬜ Pending")
    with c3: st.metric("Jobs",   "✅ Done" if job_done else "⬜ Pending")

    if st.button("✨ Generate My Career Report", key="btn_report"):
        parts = []
        if cv_done:
            a = st.session_state.cv_analysis.get("analysis",{})
            if isinstance(a, dict):
                parts.append(f"CV: {a.get('seniority_level')} developer, "
                             f"{a.get('experience_years')} yrs, "
                             f"skills: {', '.join(a.get('skills',[])[:10])}, "
                             f"summary: {a.get('summary','')}")
                projs = a.get("projects",[])
                if projs:
                    parts.append("Projects: " + ", ".join(
                        p.get("name","") for p in projs[:4] if isinstance(p,dict)))
        if gh_done:
            p = st.session_state.github_analysis.get("profile",{})
            parts.append(f"GitHub: {p.get('public_repos')} repos, "
                         f"languages: {', '.join(list(p.get('languages',{}).keys())[:5])}")
        if job_done:
            m   = st.session_state.job_matches.get("matches",[])
            loc = st.session_state.get("job_location_pref","")
            if m:
                top3 = [f"{j.get('title')} at {j.get('company')} ({j.get('match_score')}%)"
                        for j in m[:3] if isinstance(j,dict)]
                parts.append(f"Top matches: {', '.join(top3)}")
            if loc:
                parts.append(f"Preferred location: {loc}")

        prompt = (
            "Write a personalised career assessment as Daleel, a warm and insightful career guide. "
            "Be honest, specific, and encouraging — like a mentor who truly knows them. "
            "Cover: where they stand today, their strongest assets, best opportunities from their job matches, "
            "key projects demonstrating their skills, "
            "and 3-5 concrete next steps for this month. "
            "Use markdown headers. Be specific — reference real skills, companies, projects by name. "
            "Don't be generic.\n\nData:\n" + "\n".join(parts)
        )
        with st.spinner("🧭 Daleel is writing your personalised report…"):
            text = _llm(_groq(), [
                {"role":"system","content":"You are Daleel, an expert career guide writing a personal assessment."},
                {"role":"user",  "content": prompt},
            ], max_tokens=1100)

        st.markdown(
            '<div class="aib"><div class="ailbl">✦ Your Daleel Career Report</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown(text)

        st.download_button(
            "📥 Download Report",
            data=json.dumps({
                "generated_at": datetime.datetime.now().isoformat(),
                "narrative": text,
                "cv": st.session_state.cv_analysis,
                "github": st.session_state.github_analysis,
                "jobs": st.session_state.job_matches,
            }, indent=2, default=str),
            file_name=f"daleel_report_{datetime.date.today()}.json",
            mime="application/json",
            key="dl_full",
        )


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════
def main():
    _css(); _init()
    _auto_build()
    _sidebar(); _header()

    main_col, chat_col = st.columns([3, 1])
    with main_col:
        t1, t2, t3, t4 = st.tabs([
            "📄  CV Analyzer",
            "🐙  GitHub Profile",
            "💼  Job Matcher",
            "📊  Full Assessment",
        ])
        with t1: _tab_cv()
        with t2: _tab_github()
        with t3: _tab_jobs()
        with t4: _tab_assessment()

    with chat_col:
        _render_chat()


if __name__ == "__main__":
    main()