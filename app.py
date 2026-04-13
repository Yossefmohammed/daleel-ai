"""
Career AI Assistant  –  Fixed Version
======================================
FIXES:
  1. Chat panel is a real Streamlit right-side column (no broken HTML/JS injection)
  2. Groq API is called from Python (server-side) — reliable, no CORS issues
  3. data_scraper.py is properly imported with graceful fallback
  4. Chat is always visible in the right panel (Copilot-style split layout)
  5. scrape_by_skills() called when CV skills are extracted
"""

import os, re, json, html, datetime, time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(page_title="Career AI", page_icon="🎯",
                   layout="wide", initial_sidebar_state="expanded")

# ── Try importing data_scraper (optional module) ──────────────────────────────
try:
    import data_scraper as _ds
    HAS_SCRAPER = True
except ImportError:
    HAS_SCRAPER = False

# ══════════════════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════════════════
def _css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
:root{
  --n:#080c18;--n2:#0d1326;--n3:#111829;--n4:#172035;--n5:#1e2d47;
  --L:rgba(255,255,255,.06);--L2:rgba(255,255,255,.10);
  --t1:#e8eeff;--t2:#7a8ab0;--t3:#3d4a6a;
  --c:#00d9ff;--cd:rgba(0,217,255,.08);--cb:rgba(0,217,255,.20);
  --g:#34d399;--a:#fbbf24;--r:#f87171;
  --ff:'Plus Jakarta Sans',system-ui,sans-serif;--fm:'JetBrains Mono',monospace;--R:14px;--Rs:9px;
}
*,*::before,*::after{box-sizing:border-box}
html,body,[data-testid="stApp"],[data-testid="stAppViewContainer"],.main{
  background:var(--n)!important;font-family:var(--ff)!important;color:var(--t1)!important}
#MainMenu,header,footer,[data-testid="stToolbar"],[data-testid="stDecoration"],
[data-testid="stStatusWidget"]{display:none!important}
.block-container{padding:0!important;max-width:100%!important}
section.main>div{padding:0!important}
[data-testid="stSidebar"]{background:var(--n2)!important;border-right:1px solid var(--L)!important;
  min-width:260px!important;max-width:260px!important}
[data-testid="stSidebar"]>div:first-child{padding:0!important}
[data-testid="stSidebar"] label,[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span{color:var(--t2)!important;font-size:12.5px!important}
[data-testid="stSidebar"] .stButton>button{
  background:transparent!important;border:1px solid var(--L2)!important;
  border-radius:var(--Rs)!important;color:var(--t2)!important;font-size:12.5px!important;
  font-weight:500!important;padding:9px 14px!important;width:100%!important;
  box-shadow:none!important;transition:all .18s!important}
[data-testid="stSidebar"] .stButton>button:hover{
  background:var(--n4)!important;border-color:var(--cb)!important;color:var(--t1)!important}
[data-testid="stTabs"] [data-baseweb="tab-list"]{
  background:var(--n2)!important;border-bottom:1px solid var(--L)!important;
  padding:0 20px!important;gap:2px!important}
[data-testid="stTabs"] [data-baseweb="tab"]{
  background:transparent!important;border:none!important;color:var(--t2)!important;
  font-size:13px!important;font-weight:600!important;padding:14px 14px!important;
  border-bottom:2px solid transparent!important}
[data-testid="stTabs"] [aria-selected="true"]{
  color:var(--c)!important;border-bottom-color:var(--c)!important}
[data-testid="stTabPanel"]{background:transparent!important;padding:20px!important}
[data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea,
[data-testid="stNumberInput"] input{
  background:var(--n3)!important;border:1px solid var(--L2)!important;
  border-radius:var(--R)!important;color:var(--t1)!important;font-size:13.5px!important}
[data-testid="stTextInput"] input:focus,[data-testid="stTextArea"] textarea:focus{
  border-color:var(--c)!important;box-shadow:0 0 0 2px var(--cd)!important}
[data-testid="stTextInput"] label,[data-testid="stTextArea"] label,
[data-testid="stNumberInput"] label,[data-testid="stSelectbox"] label,
[data-testid="stMultiSelect"] label{color:var(--t2)!important;font-size:12.5px!important;font-weight:600!important}
[data-testid="stFileUploader"]{
  background:var(--n3)!important;border:1px dashed var(--cb)!important;
  border-radius:var(--R)!important;padding:16px!important}
[data-testid="stSelectbox"] [data-baseweb="select"]>div,
[data-testid="stMultiSelect"] [data-baseweb="select"]>div{
  background:var(--n3)!important;border:1px solid var(--L2)!important;
  border-radius:var(--R)!important;color:var(--t1)!important}
.stButton>button{
  background:linear-gradient(135deg,#007acc,#00d9ff)!important;border:none!important;
  border-radius:var(--R)!important;color:var(--n)!important;font-size:13.5px!important;
  font-weight:700!important;padding:11px 22px!important;transition:all .2s!important;
  box-shadow:0 4px 14px rgba(0,217,255,.25)!important}
.stButton>button:hover{transform:translateY(-2px)!important;box-shadow:0 6px 20px rgba(0,217,255,.4)!important}
[data-testid="stMetric"]{
  background:var(--n3)!important;border:1px solid var(--L)!important;
  border-radius:var(--R)!important;padding:14px 18px!important}
[data-testid="stMetricLabel"]{color:var(--t3)!important;font-size:11px!important}
[data-testid="stMetricValue"]{color:var(--t1)!important;font-size:20px!important}
[data-testid="stExpander"]{background:var(--n3)!important;border:1px solid var(--L)!important;border-radius:var(--R)!important}
.stProgress>div>div{background:var(--c)!important}
[data-testid="stDownloadButton"]>button{
  background:transparent!important;border:1px solid var(--L2)!important;
  box-shadow:none!important;color:var(--t2)!important;transform:none!important}
hr{border-color:var(--L)!important}
/* Custom classes */
.hdr{background:var(--n2);border-bottom:1px solid var(--L);padding:0 20px;height:60px;
  display:flex;align-items:center;justify-content:space-between}
.badge{font-size:10px;font-weight:600;padding:4px 10px;border-radius:20px;
  border:1px solid var(--L2);color:var(--t3);background:var(--n3)}
.badge.live{background:rgba(52,211,153,.10);border-color:rgba(52,211,153,.25);color:#34d399}
.pill{display:inline-block;background:var(--cd);border:1px solid var(--cb);color:var(--c);
  font-size:11px;font-weight:600;padding:3px 10px;border-radius:20px;margin:3px 2px}
.pill.tech{background:rgba(251,191,36,.08);border-color:rgba(251,191,36,.25);color:#fbbf24}
.pill.miss{background:rgba(248,113,113,.08);border-color:rgba(248,113,113,.25);color:#f87171}
.aib{background:var(--n3);border:1px solid var(--L);border-left:3px solid var(--c);
  border-radius:0 var(--R) var(--R) var(--R);padding:16px 20px;font-size:13.5px;
  line-height:1.75;color:var(--t1);margin:12px 0}
.ailbl{font-size:10px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;color:var(--c);margin-bottom:8px}
.jcard{background:var(--n3);border:1px solid var(--L);border-radius:var(--R);
  padding:18px 20px;margin-bottom:12px;transition:border-color .18s}
.jcard:hover{border-color:var(--cb)}
.sh{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
  color:var(--t3);margin:20px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--L)}
.sdiv{height:1px;background:var(--L);margin:12px 0}
.slbl{font-size:10px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;
  color:var(--t3);padding-bottom:6px}
/* ─── Chat panel ─── */
.chat-panel{
  background:var(--n2);border-left:1px solid var(--L);height:calc(100vh - 60px);
  display:flex;flex-direction:column;position:sticky;top:60px;overflow:hidden}
.chat-hdr{
  background:linear-gradient(135deg,rgba(0,122,204,.15),rgba(0,217,255,.08));
  border-bottom:1px solid var(--L);padding:14px 16px;flex-shrink:0}
.chat-msgs{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:10px}
.chat-msg-bot{
  background:var(--n3);border:1px solid var(--L);border-top-left-radius:4px;
  border-radius:14px;padding:10px 13px;font-size:13px;line-height:1.65;
  color:var(--t1);max-width:90%;align-self:flex-start}
.chat-msg-usr{
  background:linear-gradient(135deg,#00527a,#007cc2);color:#fff;
  border-top-right-radius:4px;border-radius:14px;padding:10px 13px;
  font-size:13px;line-height:1.65;max-width:90%;align-self:flex-end;margin-left:auto}
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
        st.error("GROQ_API_KEY not set. Add it to .env or secrets.toml."); st.stop()
    return Groq(api_key=k)

def _llm(client, msgs, max_tokens=900):
    for model in ["llama-3.3-70b-versatile", "gemma2-9b-it"]:
        try:
            r = client.chat.completions.create(
                model=model, messages=msgs, temperature=0.3, max_tokens=max_tokens)
            return r.choices[0].message.content
        except Exception:
            continue
    return "Sorry, couldn't reach the AI right now."

def _parse_json(text):
    text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
    try: return json.loads(text)
    except Exception: pass
    for pat in [r"\[.*\]", r"\{.*\}"]:
        m = re.search(pat, text, re.DOTALL)
        if m:
            try: return json.loads(m.group())
            except Exception: pass
    return {}


# ══════════════════════════════════════════════════════════════════════════════
# Job database
# ══════════════════════════════════════════════════════════════════════════════
DATA_DIR    = Path("data")
COMBINED    = DATA_DIR / "jobs_combined.csv"
CACHE_HOURS = 24

def _scrape_remoteok(keywords: str = "", limit: int = 150) -> list:
    import requests
    try:
        params = {"tags": keywords} if keywords else {}
        r = requests.get("https://remoteok.com/api", params=params,
                         headers={"User-Agent": "CareerAI/1.0"}, timeout=14)
        r.raise_for_status()
        jobs = []
        for j in r.json()[:limit]:
            if not isinstance(j, dict) or "id" not in j: continue
            jobs.append({
                "title":       j.get("position") or j.get("title", ""),
                "company":     j.get("company", ""),
                "description": str(j.get("description") or " ".join(j.get("tags",[])))[:400],
                "location":    j.get("location", "Remote"),
                "salary":      str(j.get("salary", "")),
                "url":         j.get("url", ""),
                "source":      "RemoteOK",
            })
        return jobs
    except Exception: return []

def _scrape_arbeitnow(limit: int = 150) -> list:
    import requests
    jobs = []
    try:
        for page in range(1, 4):
            r = requests.get("https://www.arbeitnow.com/api/job-board-api",
                             params={"page": page},
                             headers={"Accept": "application/json"}, timeout=14)
            r.raise_for_status()
            data = r.json().get("data", [])
            if not data: break
            for j in data:
                jobs.append({
                    "title":       j.get("title", ""),
                    "company":     j.get("company_name", ""),
                    "description": str(j.get("description") or "")[:400],
                    "location":    j.get("location", ""),
                    "salary":      "",
                    "url":         j.get("url", ""),
                    "source":      "Arbeitnow",
                })
            if len(jobs) >= limit: break
        return jobs[:limit]
    except Exception: return []

def _load_local_csv() -> list:
    import pandas as pd
    col_map = {
        "job_title":"title","position":"title","role":"title",
        "company_name":"company","employer":"company",
        "job_description":"description","responsibilities":"description",
        "job_location":"location","city":"location",
        "salary_in_usd":"salary","salary_estimate":"salary",
        "annual_salary_usd":"salary","avg_salary":"salary",
    }
    search_paths = [DATA_DIR/"jobs.csv"] + list(Path("docs").glob("*.csv")) if Path("docs").exists() else [DATA_DIR/"jobs.csv"]
    for p in search_paths:
        if not p.exists(): continue
        try:
            df = pd.read_csv(str(p), on_bad_lines="skip", nrows=2000)
            df.columns = [c.lower().strip() for c in df.columns]
            df = df.rename(columns={k:v for k,v in col_map.items() if k in df.columns})
            df = df.fillna("")
            for col in ["title","company","description","location","salary"]:
                if col not in df.columns: df[col] = ""
            df["source"] = "Local CSV"; df["url"] = ""
            return df[["title","company","description","location","salary","url","source"]].to_dict("records")
        except Exception: continue
    return []

def _cache_fresh() -> bool:
    if not COMBINED.exists(): return False
    age = (datetime.datetime.now() -
           datetime.datetime.fromtimestamp(COMBINED.stat().st_mtime)).total_seconds()
    return age < CACHE_HOURS * 3600

def _save_combined(jobs: list):
    import pandas as pd
    DATA_DIR.mkdir(exist_ok=True)
    pd.DataFrame(jobs).to_csv(str(COMBINED), index=False)

def _load_combined() -> list:
    import pandas as pd
    if not COMBINED.exists(): return []
    try:
        df = pd.read_csv(str(COMBINED), on_bad_lines="skip", nrows=3000)
        return df.fillna("").to_dict("records")
    except Exception: return []

def build_job_database(skills: list = None, status_ph=None) -> int:
    def say(m):
        if status_ph: status_ph.info(m)

    all_jobs = []

    # Try data_scraper module first if available
    if HAS_SCRAPER and skills:
        say(f"🕷️ data_scraper: scraping by skills {skills[:3]}…")
        try:
            scraped = _ds.scrape_by_skills(skills[:6])
            if scraped:
                all_jobs.extend(scraped)
                say(f"✅ data_scraper returned {len(scraped)} jobs")
        except Exception as e:
            say(f"⚠️ data_scraper error: {e} — falling back to APIs")

    if skills and not all_jobs:
        for sk in skills[:3]:
            say(f"📡 RemoteOK: searching '{sk}'…")
            all_jobs.extend(_scrape_remoteok(keywords=sk, limit=60))
        all_jobs.extend(_scrape_remoteok(keywords="+".join(skills[:4]), limit=60))
    else:
        say("📡 Scraping RemoteOK (general)…")
        all_jobs.extend(_scrape_remoteok(limit=150))

    say(f"✅ RemoteOK: {len(all_jobs)} jobs. Trying Arbeitnow…")
    anow = _scrape_arbeitnow()
    all_jobs.extend(anow)
    say(f"✅ Arbeitnow: {len(anow)} jobs. Loading local CSV…")
    all_jobs.extend(_load_local_csv())
    say("🔧 Deduplicating…")

    seen, unique = set(), []
    for j in all_jobs:
        k = (str(j.get("title","")).lower()[:40], str(j.get("company","")).lower()[:30])
        if k not in seen:
            seen.add(k); unique.append(j)
    _save_combined(unique)
    return len(unique)

def _auto_build():
    if st.session_state.get("db_checked"): return
    st.session_state.db_checked = True
    if _cache_fresh(): return
    with st.sidebar:
        ph = st.empty()
        ph.warning("🔄 Building job database…")
        try:
            n = build_job_database()
            ph.success(f"✅ {n:,} jobs ready")
            time.sleep(2)
        except Exception as e:
            ph.warning(f"⚠️ {e}")
        finally:
            ph.empty()


# ══════════════════════════════════════════════════════════════════════════════
# CV analysis
# ══════════════════════════════════════════════════════════════════════════════
def _pdf_text(path: str) -> str:
    from pypdf import PdfReader
    return "\n".join(p.extract_text() or "" for p in PdfReader(path).pages)

def analyze_cv(pdf_path: str) -> dict:
    text = _pdf_text(pdf_path)
    if not text.strip():
        return {"success": False,
                "error": "Could not read text from this PDF. Make sure it is not a scanned image."}
    client = _groq()
    prompt = (
        "Analyze this CV. Return ONLY a valid JSON object — no markdown, no text outside the JSON.\n\n"
        '{"name":"","summary":"2-3 sentence honest professional summary",'
        '"seniority_level":"Junior|Mid-Level|Senior|Lead","experience_years":<integer>,'
        '"skills":["skill1"],"technologies":["framework"],'
        '"experience":[{"title":"Job Title","company":"Company","duration":"2021-2023"}],'
        '"education":[{"degree":"BSc","field":"CS","school":"University"}],'
        '"strengths":["strength1"],"improvement_areas":["area1"]}\n\nCV:\n' + text[:3500]
    )
    raw = _llm(client, [{"role": "user", "content": prompt}], max_tokens=1200)
    parsed = _parse_json(raw)
    if not parsed or "skills" not in parsed:
        return {"success": False, "error": "AI could not parse your CV. Try a cleaner text-based PDF."}
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
        rr = requests.get(f"{base}/repos", headers=hdrs,
                          params={"per_page": 30, "sort": "pushed"}, timeout=10)
        repos = rr.json() if rr.ok else []
    except Exception:
        repos = []
    lang_counts: dict = {}
    for repo in repos[:20]:
        if repo.get("language"):
            lang_counts[repo["language"]] = lang_counts.get(repo["language"], 0) + 1
    profile = {
        "login": user.get("login", ""), "name": user.get("name", ""),
        "bio": user.get("bio", ""), "followers": user.get("followers", 0),
        "following": user.get("following", 0), "public_repos": user.get("public_repos", 0),
        "languages": dict(sorted(lang_counts.items(), key=lambda x: -x[1])[:8]),
        "top_repos": [{"name": r.get("name"), "stars": r.get("stargazers_count", 0),
                       "description": r.get("description", "")} for r in repos[:5]],
    }
    client = _groq()
    prompt = (
        "You are a tech recruiter. Assess this GitHub profile.\n"
        "Return ONLY valid JSON — no markdown.\n\n"
        '{"profile_score":<integer 0-100>,"summary":"3-4 honest sentences",'
        '"strengths":["point1","point2"],"recommendations":["tip1","tip2","tip3"]}\n\n'
        f"Username:{profile['login']},Bio:{profile.get('bio','—')},"
        f"Repos:{profile['public_repos']},Followers:{profile['followers']},"
        f"Top languages:{', '.join(profile['languages'].keys())},"
        f"Top repos:{json.dumps(profile['top_repos'][:3])}"
    )
    raw = _llm(client, [{"role": "user", "content": prompt}], max_tokens=600)
    return {"success": True, "profile": profile, "analysis": _parse_json(raw)}


# ══════════════════════════════════════════════════════════════════════════════
# Job matching
# ══════════════════════════════════════════════════════════════════════════════
def match_jobs(user_profile: dict, limit: int = 8) -> dict:
    jobs = _load_combined()
    if not jobs:
        return {"success": False,
                "error": "Job database is empty. Click 🔄 Refresh Job Database in the sidebar."}
    skills = [s.lower() for s in user_profile.get("skills", [])]
    roles  = [r.lower() for r in user_profile.get("interested_roles", [])]

    def _score(j):
        blob = (str(j.get("title", "")) + " " + str(j.get("description", ""))).lower()
        s = sum(2 for sk in skills if sk in blob)
        s += sum(1 for ro in roles for w in ro.split() if len(w) > 3 and w in blob)
        return s

    top25 = sorted(jobs, key=_score, reverse=True)[:25]
    compact = [{"title": str(j.get("title",""))[:60], "company": str(j.get("company",""))[:40],
                "location": str(j.get("location",""))[:30],
                "description": str(j.get("description",""))[:200],
                "salary": str(j.get("salary",""))[:30]} for j in top25]
    client = _groq()
    prompt = (
        f"You are a career advisor. Return ONLY a valid JSON array of top {limit} best-matching jobs.\n"
        "No markdown. Each object:\n"
        '{"title":"","company":"","location":"","salary":"","match_score":<0-100>,'
        '"matched_skills":[],"missing_skills":[],"why_good_fit":"one sentence"}\n\n'
        f"User: skills={user_profile.get('skills',[])}, "
        f"exp={user_profile.get('experience_years',0)} yrs, "
        f"seniority={user_profile.get('seniority_level','')}, "
        f"roles={user_profile.get('interested_roles',[])}\n\n"
        f"Jobs:\n{json.dumps(compact,indent=2)[:4000]}\n\nReturn ONLY the JSON array."
    )
    raw = _llm(client, [{"role": "user", "content": prompt}], max_tokens=1400)
    matches = _parse_json(raw)
    if isinstance(matches, dict) and "jobs" in matches: matches = matches["jobs"]
    if not isinstance(matches, list): matches = []
    return {"success": True, "matches": matches,
            "total_in_db": len(jobs), "candidates_evaluated": len(compact)}


# ══════════════════════════════════════════════════════════════════════════════
# Chat  (Python-side, server-driven — no broken JS)
# ══════════════════════════════════════════════════════════════════════════════
def _build_chat_context() -> str:
    parts = []
    if st.session_state.cv_analysis:
        a = st.session_state.cv_analysis.get("analysis", {})
        if isinstance(a, dict):
            parts.append(
                f"CV: {a.get('seniority_level','?')}, "
                f"{a.get('experience_years','?')} yrs exp, "
                f"skills: {', '.join(a.get('skills',[])[:10])}, "
                f"summary: {a.get('summary','')}"
            )
    if st.session_state.github_analysis:
        p = st.session_state.github_analysis.get("profile", {})
        parts.append(
            f"GitHub: {p.get('public_repos',0)} repos, "
            f"top langs: {', '.join(list(p.get('languages',{}).keys())[:5])}"
        )
    if st.session_state.job_matches:
        m = st.session_state.job_matches.get("matches", [])
        if m and isinstance(m[0], dict):
            t = m[0]
            parts.append(
                f"Top job match: {t.get('title','')} at {t.get('company','')} "
                f"({t.get('match_score','')}% match)"
            )
    return "\n".join(parts)

def _chat_response(user_msg: str) -> str:
    """Call Groq from Python — always works, no CORS/JS issues."""
    client = _groq()
    ctx = _build_chat_context()
    system = (
        "You are Career AI — a warm, expert career advisor. "
        "Give honest, specific, actionable advice in a conversational tone like a smart mentor. "
        "Keep answers concise and focused. Use bullet points only for lists of 3+ items. "
        "Never say 'As an AI'. Be direct and real."
        + (f"\n\nContext about this user:\n{ctx}" if ctx else "")
    )
    history = st.session_state.chat_history[-12:]  # keep last 12 turns
    messages = [{"role": "system", "content": system}] + history + [{"role": "user", "content": user_msg}]
    return _llm(client, messages, max_tokens=500)

def _render_chat_panel():
    """Renders the right-side chat column."""
    st.markdown("""
<div class="chat-hdr">
  <div style="display:flex;align-items:center;gap:10px">
    <div style="width:32px;height:32px;border-radius:9px;background:linear-gradient(135deg,#007acc,#00d9ff);
      display:flex;align-items:center;justify-content:center;font-size:15px">🎯</div>
    <div>
      <div style="font-size:13.5px;font-weight:700;color:#e8eeff">Career AI Chat</div>
      <div style="font-size:10px;color:#3d4a6a">Your personal career advisor</div>
    </div>
    <div style="margin-left:auto">
      <span style="font-size:9px;background:rgba(52,211,153,.15);border:1px solid rgba(52,211,153,.3);
        color:#34d399;padding:2px 8px;border-radius:10px;font-weight:700">● LIVE</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    # Message history
    msgs_html = '<div style="display:flex;flex-direction:column;gap:10px;padding:14px;'
    msgs_html += 'overflow-y:auto;max-height:calc(100vh - 240px)">'
    for m in st.session_state.chat_history:
        role = m["role"]
        text = html.escape(m["content"])
        if role == "assistant":
            msgs_html += f'<div class="chat-msg-bot">{text}</div>'
        else:
            msgs_html += f'<div class="chat-msg-usr">{text}</div>'
    if not st.session_state.chat_history:
        ctx = _build_chat_context()
        greet = ("Hey! 👋 I can see you've been working through your profile. What would you like to explore?"
                 if ctx else
                 "Hey! 👋 I'm your Career AI advisor. Ask me anything — CV tips, job search, salary negotiation, skill gaps, interview prep…")
        msgs_html += f'<div class="chat-msg-bot">{html.escape(greet)}</div>'
    msgs_html += '</div>'
    st.markdown(msgs_html, unsafe_allow_html=True)

    # Quick chips
    chips = ["Improve my CV", "Skills to learn", "Negotiate salary", "Am I senior-ready?"]
    cols = st.columns(2)
    for i, chip in enumerate(chips):
        with cols[i % 2]:
            if st.button(chip, key=f"chip_{chip}", use_container_width=True):
                with st.spinner("Thinking…"):
                    reply = _chat_response(chip)
                st.session_state.chat_history.append({"role": "user", "content": chip})
                st.session_state.chat_history.append({"role": "assistant", "content": reply})
                st.rerun()

    # Input box
    user_input = st.text_input(
        "Ask your career question…",
        key="chat_input_field",
        placeholder="e.g. What jobs match my Python skills?",
        label_visibility="collapsed"
    )
    send = st.button("Send ➤", key="chat_send", use_container_width=True)
    if send and user_input.strip():
        with st.spinner("Thinking…"):
            reply = _chat_response(user_input.strip())
        st.session_state.chat_history.append({"role": "user", "content": user_input.strip()})
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        st.rerun()
    if st.button("🗑 Clear Chat", key="chat_clear", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# Session state init
# ══════════════════════════════════════════════════════════════════════════════
def _init():
    defaults = {
        "cv_analysis": None,
        "github_analysis": None,
        "job_matches": None,
        "db_checked": False,
        "skill_scrape_done": False,
        "_jobs_skills_shown": False,
        "chat_history": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ══════════════════════════════════════════════════════════════════════════════
# Render helpers
# ══════════════════════════════════════════════════════════════════════════════
def _pill(t, k="skill"):
    cls = {"skill": "pill", "tech": "pill tech", "miss": "pill miss"}.get(k, "pill")
    return f'<span class="{cls}">{html.escape(str(t))}</span>'

def _pills(items, k="skill"):
    if not items: return '<span style="color:var(--t3);font-size:12px">none found</span>'
    return "".join(_pill(i, k) for i in items)

def _sc(s):
    if s >= 80: return "#34d399"
    if s >= 60: return "#00d9ff"
    if s >= 40: return "#fbbf24"
    return "#f87171"

def _dot(col="#00d9ff"):
    return (f'<div style="width:9px;height:9px;border-radius:50%;background:{col};'
            f'margin-top:4px;flex-shrink:0"></div>')


# ══════════════════════════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════════════════════════
def _sidebar():
    with st.sidebar:
        st.markdown(
            '<div style="padding:18px 16px 14px;border-bottom:1px solid rgba(255,255,255,.06)">'
            '<div style="display:flex;align-items:center;gap:12px">'
            '<div style="width:38px;height:38px;border-radius:12px;background:linear-gradient(135deg,#007acc,#00d9ff);'
            'display:flex;align-items:center;justify-content:center;font-size:18px">🎯</div>'
            '<div><div style="font-size:14px;font-weight:800;color:#e8eeff">Career AI</div>'
            '<div style="font-size:10px;color:#00d9ff;background:rgba(0,217,255,.08);padding:2px 8px;'
            'border-radius:20px;border:1px solid rgba(0,217,255,.2);display:inline-block;font-weight:600;margin-top:2px">'
            'Phase 1 · MVP</div></div></div></div>',
            unsafe_allow_html=True,
        )
        st.markdown("<div style='padding:12px 14px 0'>", unsafe_allow_html=True)
        st.markdown('<div class="slbl">Status</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1: st.metric("Groq AI", "🟢 Ready" if _key() else "🔴 Missing")
        with c2: st.metric("GitHub", "🟢" if _gh_token() else "⚪ Optional")
        cnt = len(_load_combined())
        scraper_status = "🟢 Ready" if HAS_SCRAPER else "⚪ N/A"
        c3, c4 = st.columns(2)
        with c3: st.metric("Jobs DB", f"🟢 {cnt:,}" if cnt else "🔴 Empty")
        with c4: st.metric("Scraper", scraper_status)

        if not _key():
            st.error("GROQ_API_KEY missing.\nAdd to .env or secrets.toml.")

        st.markdown('<div class="sdiv"></div>', unsafe_allow_html=True)
        st.markdown('<div class="slbl">Job Database</div>', unsafe_allow_html=True)
        if COMBINED.exists():
            age_h = (datetime.datetime.now() -
                     datetime.datetime.fromtimestamp(COMBINED.stat().st_mtime)).total_seconds() / 3600
            st.caption(f"Cache: {age_h:.0f}h old  ·  refreshes every {CACHE_HOURS}h")
        if st.button("🔄 Refresh Job Database", key="sb_ref", use_container_width=True):
            ph = st.empty()
            skills = []
            if st.session_state.cv_analysis:
                a = st.session_state.cv_analysis.get("analysis", {})
                if isinstance(a, dict): skills = a.get("skills", [])[:6]
            try:
                n = build_job_database(skills=skills, status_ph=ph)
                ph.success(f"✅ Done — {n:,} jobs{' (skill-targeted)' if skills else ''}")
            except Exception as e:
                ph.error(f"❌ {e}")

        st.markdown('<div class="sdiv"></div>', unsafe_allow_html=True)
        st.markdown('<div class="slbl">Your Progress</div>', unsafe_allow_html=True)
        for lbl, done in [("📄 CV analyzed", st.session_state.cv_analysis is not None),
                          ("🐙 GitHub analyzed", st.session_state.github_analysis is not None),
                          ("💼 Jobs matched", st.session_state.job_matches is not None),
                          ("💬 Chat active", len(st.session_state.chat_history) > 0)]:
            col = "#34d399" if done else "var(--t3)"
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;padding:4px 0;'
                f'font-size:12.5px;color:{col}">{"✅" if done else "⬜"} {lbl}</div>',
                unsafe_allow_html=True)

        if st.button("🗑 Clear Session", key="sb_clear", use_container_width=True):
            st.session_state.cv_analysis = None
            st.session_state.github_analysis = None
            st.session_state.job_matches = None
            st.session_state.skill_scrape_done = False
            st.session_state._jobs_skills_shown = False
            st.session_state.chat_history = []
            if "js_skills_v3" in st.session_state:
                del st.session_state["js_skills_v3"]
            st.rerun()

        st.markdown('<div class="sdiv"></div>', unsafe_allow_html=True)
        if any([st.session_state.cv_analysis, st.session_state.github_analysis, st.session_state.job_matches]):
            st.download_button(
                "📥 Download Report",
                data=json.dumps({
                    "generated_at": datetime.datetime.now().isoformat(),
                    "cv": st.session_state.cv_analysis,
                    "github": st.session_state.github_analysis,
                    "jobs": st.session_state.job_matches,
                }, indent=2, default=str),
                file_name=f"career_report_{datetime.date.today()}.json",
                mime="application/json", use_container_width=True, key="sb_dl")

        with st.expander("⚙️ Setup Guide"):
            st.markdown("""
**`.env` (local)**
```
GROQ_API_KEY=gsk_...
GITHUB_TOKEN=ghp_...
```
**`secrets.toml` (Streamlit Cloud)**
```toml
GROQ_API_KEY = "gsk_..."
```
**data_scraper.py**: Place your `data_scraper.py` in the same folder.
It needs a `scrape_by_skills(skills: list) -> list` function.
""")
        st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Header
# ══════════════════════════════════════════════════════════════════════════════
def _header():
    ready = any([st.session_state.cv_analysis, st.session_state.github_analysis,
                 st.session_state.job_matches])
    st.markdown(
        '<div class="hdr"><div style="display:flex;align-items:center;gap:14px">'
        '<div style="width:38px;height:38px;border-radius:12px;background:linear-gradient(135deg,#007acc,#00d9ff);'
        'display:flex;align-items:center;justify-content:center;font-size:18px">🎯</div>'
        '<div><div style="font-size:16px;font-weight:800;color:var(--t1)">Career AI Assistant</div>'
        '<div style="font-size:11px;color:var(--t3);margin-top:1px">CV · GitHub · Job Matching · Chat</div>'
        '</div></div><div style="display:flex;gap:8px">'
        + ('<div class="badge live">● Session Active</div>' if ready else '<div class="badge">○ No Data Yet</div>')
        + '<div class="badge">Groq · LLaMA 3.3</div>'
        + (f'<div class="badge">🕷️ Scraper Ready</div>' if HAS_SCRAPER else '')
        + '</div></div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Tab: CV
# ══════════════════════════════════════════════════════════════════════════════
def _tab_cv():
    st.markdown('<div class="sh">📄 CV Analyzer</div>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t2);font-size:13px;margin-bottom:18px">Upload your PDF CV for a full breakdown. Skills auto-fill the Job Matcher and trigger a targeted scrape.</p>', unsafe_allow_html=True)
    cu, cb = st.columns([3, 1])
    with cu: f = st.file_uploader("Choose your CV (PDF)", type=["pdf"], key="cv_file")
    with cb:
        st.write(""); st.write("")
        go = st.button("🔍 Analyze CV", key="btn_cv", use_container_width=True, disabled=f is None)
    if go and f:
        if not _key(): return
        with st.spinner("Reading your CV…"):
            tmp = f"temp_{f.name}"
            with open(tmp, "wb") as fh: fh.write(f.getbuffer())
            res = analyze_cv(tmp); os.remove(tmp)
            if res.get("success"):
                st.session_state.cv_analysis = res
                st.session_state.skill_scrape_done = False
                st.session_state._jobs_skills_shown = False
                a = res.get("analysis", {})
                if isinstance(a, dict):
                    skills_list = a.get("skills", [])
                    if skills_list:
                        st.session_state["js_skills_v3"] = "\n".join(str(s) for s in skills_list)
                st.success("✅ CV analyzed! Skills auto-filled in the 💼 Job Matcher tab.")
            else:
                st.error(f"❌ {res.get('error')}"); return

    # Trigger targeted scrape
    if (st.session_state.cv_analysis and
            not st.session_state.skill_scrape_done and
            not _cache_fresh()):
        a = st.session_state.cv_analysis.get("analysis", {})
        skills = a.get("skills", [])[:6] if isinstance(a, dict) else []
        if skills:
            with st.spinner(f"🔍 Scraping jobs for: {', '.join(skills[:3])}…"):
                try:
                    n = build_job_database(skills=skills)
                    st.session_state.skill_scrape_done = True
                    st.toast(f"✅ Found {n:,} targeted jobs!", icon="💼")
                except Exception:
                    st.session_state.skill_scrape_done = True

    if not st.session_state.cv_analysis:
        st.info("Upload your CV and click **Analyze CV** to get started."); return

    a = st.session_state.cv_analysis.get("analysis", {})
    if isinstance(a, str): a = _parse_json(a) or {}
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Seniority", a.get("seniority_level", "—"))
    with c2: st.metric("Experience", f"{a.get('experience_years','—')} yrs")
    with c3: st.metric("Skills", len(a.get("skills", [])))
    if a.get("summary"):
        st.markdown(f'<div class="aib"><div class="ailbl">🤖 AI Summary</div>{html.escape(str(a["summary"]))}</div>', unsafe_allow_html=True)
    if a.get("skills") or a.get("technologies"):
        st.markdown('<div class="sh">Skills & Technologies</div>', unsafe_allow_html=True)
        st.markdown(_pills(a.get("skills", []), "skill") + _pills(a.get("technologies", []), "tech"), unsafe_allow_html=True)
    if a.get("experience"):
        st.markdown('<div class="sh">Work Experience</div>', unsafe_allow_html=True)
        for e in a["experience"]:
            st.markdown(
                f'<div style="display:flex;gap:12px;align-items:flex-start;margin-bottom:10px">{_dot()}'
                f'<div><div style="font-size:13.5px;font-weight:600;color:var(--t1)">{html.escape(str(e.get("title","—")))}</div>'
                f'<div style="font-size:12px;color:var(--t2)">{html.escape(str(e.get("company","—")))} · {html.escape(str(e.get("duration","")))}</div>'
                f'</div></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if a.get("strengths"):
            st.markdown('<div class="sh">💪 Strengths</div>', unsafe_allow_html=True)
            for s in a["strengths"]: st.markdown(f'<div style="color:var(--t2);font-size:13px;padding:3px 0">✅ {html.escape(str(s))}</div>', unsafe_allow_html=True)
    with c2:
        if a.get("improvement_areas"):
            st.markdown('<div class="sh">🎯 To Improve</div>', unsafe_allow_html=True)
            for g in a["improvement_areas"]: st.markdown(f'<div style="color:var(--t2);font-size:13px;padding:3px 0">→ {html.escape(str(g))}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Tab: GitHub
# ══════════════════════════════════════════════════════════════════════════════
def _tab_github():
    st.markdown('<div class="sh">🐙 GitHub Profile Analysis</div>', unsafe_allow_html=True)
    ci, cb = st.columns([3, 1])
    with ci: uname = st.text_input("GitHub Username", placeholder="e.g. torvalds", key="gh_username")
    with cb:
        st.write(""); st.write("")
        go = st.button("🔍 Analyze", key="btn_gh", use_container_width=True, disabled=not (uname or "").strip())
    if go and (uname or "").strip():
        if not _key(): return
        with st.spinner(f"Fetching @{uname.strip()}…"):
            res = analyze_github(uname.strip())
            if res.get("success"): st.session_state.github_analysis = res
            else:
                st.error(f"❌ {res.get('error')}"); return
    if not st.session_state.github_analysis:
        st.info("Enter a GitHub username and click **Analyze**."); return
    data = st.session_state.github_analysis
    profile = data.get("profile", {}); analysis = data.get("analysis", {})
    if isinstance(analysis, str): analysis = _parse_json(analysis) or {}
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Followers", profile.get("followers", 0))
    with c2: st.metric("Public Repos", profile.get("public_repos", 0))
    with c3: st.metric("Following", profile.get("following", 0))
    score = analysis.get("profile_score", "—") if isinstance(analysis, dict) else "—"
    with c4: st.metric("Profile Score", f"{score}/100")
    summary = analysis.get("summary", "") if isinstance(analysis, dict) else str(analysis)
    if summary:
        st.markdown(f'<div class="aib"><div class="ailbl">🤖 AI Assessment</div>{html.escape(str(summary))}</div>', unsafe_allow_html=True)
    langs = profile.get("languages", {})
    if langs:
        st.markdown('<div class="sh">Top Languages</div>', unsafe_allow_html=True)
        st.bar_chart(langs)
    recs = analysis.get("recommendations", []) if isinstance(analysis, dict) else []
    if recs:
        st.markdown('<div class="sh">💡 Recommendations</div>', unsafe_allow_html=True)
        for r in recs: st.markdown(f'<div style="color:var(--t2);font-size:13px;padding:4px 0">→ {html.escape(str(r))}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Tab: Job Matcher
# ══════════════════════════════════════════════════════════════════════════════
def _tab_jobs():
    st.markdown('<div class="sh">💼 Job Matcher</div>', unsafe_allow_html=True)
    cnt = len(_load_combined())
    if cnt == 0:
        st.warning("**Job database is empty.** Click **🔄 Refresh Job Database** in the sidebar, or analyze your CV first.")
    else:
        st.markdown(f'<p style="color:var(--t2);font-size:13px;margin-bottom:18px">Searching <strong style="color:var(--c)">{cnt:,} jobs</strong>. Skills are auto-filled from your CV.</p>', unsafe_allow_html=True)
    if st.session_state.cv_analysis and not st.session_state._jobs_skills_shown:
        st.success("✅ Skills auto-filled from your CV — edit freely below.")
        st.session_state._jobs_skills_shown = True
    c1, c2 = st.columns(2)
    with c1:
        sr = st.text_area("Your Skills (one per line)", placeholder="Python\nReact\nSQL",
                          height=140, key="js_skills_v3")
        exp = st.number_input("Years of Experience", 0, 50, 2, key="js_exp")
    with c2:
        sen = st.selectbox("Seniority Level", ["Junior","Mid-Level","Senior","Lead","Principal"], key="js_sen")
        roles = st.multiselect("Interested Roles",
            ["Full Stack Developer","Backend Engineer","Frontend Developer","Data Scientist",
             "ML Engineer","DevOps Engineer","Product Manager","Mobile Developer","Cloud Architect"],
            key="js_roles")
    go = st.button("🔍 Find My Best Jobs", key="btn_jobs", disabled=(cnt == 0))
    if go:
        if not _key(): return
        skills = [s.strip() for s in sr.split("\n") if s.strip()]
        if not skills: st.warning("Please enter at least one skill."); return
        with st.spinner("Scanning jobs and ranking with AI…"):
            res = match_jobs({"skills": skills, "experience_years": int(exp),
                              "seniority_level": sen, "interested_roles": roles})
        if res.get("success"): st.session_state.job_matches = res
        else: st.error(f"❌ {res.get('error')}"); return
    if not st.session_state.job_matches:
        if cnt > 0: st.info("Fill in your profile and click **Find My Best Jobs**."); return
        return
    res = st.session_state.job_matches
    matches = res.get("matches", [])
    total = res.get("total_in_db", "?"); evald = res.get("candidates_evaluated", "?")
    if not matches: st.warning("No matches found. Try broadening your skills."); return
    st.markdown(f'<div class="aib"><div class="ailbl">Results</div>Out of <strong>{total:,}</strong> jobs, picked these <strong>{len(matches)}</strong> best fits.</div>', unsafe_allow_html=True)
    for job in matches:
        if not isinstance(job, dict): continue
        score = int(job.get("match_score", 0)); colour = _sc(score)
        matched = job.get("matched_skills", []); missing = job.get("missing_skills", [])
        why = job.get("why_good_fit", ""); salary = str(job.get("salary", ""))
        loc = str(job.get("location", "")); url = str(job.get("url", ""))
        mp = "".join(_pill(s, "skill") for s in matched) if matched else ""
        xp = "".join(_pill(s, "miss") for s in missing) if missing else ""
        sal_txt = f'  ·  💰 {html.escape(salary)}' if salary not in ("N/A","","nan") else ""
        loc_txt = f'  📍 {html.escape(loc)}' if loc else ""
        title_html = (f'<a href="{html.escape(url)}" target="_blank" style="color:var(--t1);text-decoration:none">{html.escape(str(job.get("title","—")))}</a>'
                      if url else html.escape(str(job.get("title","—"))))
        st.markdown(f"""
<div class="jcard">
  <div style="display:flex;justify-content:space-between;align-items:flex-start">
    <div><div style="font-size:15px;font-weight:700">{title_html}</div>
    <div style="font-size:12px;color:var(--t2);margin-top:2px">🏢 {html.escape(str(job.get('company','—')))}{loc_txt}{sal_txt}</div></div>
    <div style="text-align:right;flex-shrink:0;margin-left:16px">
      <div style="font-size:22px;font-weight:800;color:{colour}">{score}%</div>
      <div style="font-size:10px;color:var(--t3)">match</div></div></div>
  <div style="background:var(--n5);border-radius:4px;height:6px;width:100%;margin:8px 0">
    <div style="height:6px;border-radius:4px;width:{score}%;background:linear-gradient(90deg,#007acc,{colour})"></div></div>
  {f'<div style="margin-bottom:6px"><span style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--t3)">Matched  </span>{mp}</div>' if mp else ""}
  {f'<div style="margin-bottom:8px"><span style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--t3)">To learn  </span>{xp}</div>' if xp else ""}
  {f'<div style="font-size:13px;color:var(--t2);line-height:1.6;margin-top:6px">💬 {html.escape(str(why))}</div>' if why else ""}
  {f'<div style="margin-top:10px"><a href="{html.escape(url)}" target="_blank" style="font-size:11px;color:var(--c);font-weight:600">🔗 View Job →</a></div>' if url else ""}
</div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Tab: Assessment
# ══════════════════════════════════════════════════════════════════════════════
def _tab_assessment():
    st.markdown('<div class="sh">📊 Full Career Assessment</div>', unsafe_allow_html=True)
    cv_done = st.session_state.cv_analysis is not None
    gh_done = st.session_state.github_analysis is not None
    job_done = st.session_state.job_matches is not None
    if not any([cv_done, gh_done, job_done]):
        st.info("Complete at least one analysis first, then come back for your full report."); return
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("CV", "✅ Done" if cv_done else "⬜ Pending")
    with c2: st.metric("GitHub", "✅ Done" if gh_done else "⬜ Pending")
    with c3: st.metric("Jobs", "✅ Done" if job_done else "⬜ Pending")
    if st.button("✨ Write My Career Report", key="btn_report"):
        parts = []
        if cv_done:
            a = st.session_state.cv_analysis.get("analysis", {})
            if isinstance(a, dict):
                parts.append(f"CV: {a.get('seniority_level')} dev, {a.get('experience_years')} yrs, skills: {', '.join(a.get('skills',[])[:10])}, summary: {a.get('summary','')}")
        if gh_done:
            p = st.session_state.github_analysis.get("profile", {})
            parts.append(f"GitHub: {p.get('public_repos')} repos, languages: {', '.join(list(p.get('languages',{}).keys())[:5])}")
        if job_done:
            m = st.session_state.job_matches.get("matches", [])
            if m:
                top3 = [f"{j.get('title')} at {j.get('company')} ({j.get('match_score')}%)" for j in m[:3] if isinstance(j, dict)]
                parts.append(f"Top jobs: {', '.join(top3)}")
        prompt = ("Write a personalised career assessment. Sound like a mentor — warm, honest, specific. "
                  "Cover: where they are now, strongest assets, best opportunities, 3-5 concrete next steps this month. "
                  "Use markdown headers. Don't be generic.\n\nData:\n" + "\n".join(parts))
        with st.spinner("Writing your personalised report…"):
            text = _llm(_groq(), [
                {"role": "system", "content": "You are an expert career advisor writing a personal assessment."},
                {"role": "user", "content": prompt}
            ], max_tokens=1100)
        st.markdown('<div class="aib"><div class="ailbl">🤖 Your Career Report</div></div>', unsafe_allow_html=True)
        st.markdown(text)
        st.download_button("📥 Download Report",
            data=json.dumps({"generated_at": datetime.datetime.now().isoformat(), "narrative": text,
                             "cv": st.session_state.cv_analysis, "github": st.session_state.github_analysis,
                             "jobs": st.session_state.job_matches}, indent=2, default=str),
            file_name=f"career_report_{datetime.date.today()}.json", mime="application/json", key="dl_full")


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════
def main():
    _css()
    _init()
    _auto_build()
    _sidebar()
    _header()

    # Split layout: left = tabs (3/4), right = chat panel (1/4)
    main_col, chat_col = st.columns([3, 1])

    with main_col:
        t1, t2, t3, t4 = st.tabs(["📄  CV Analyzer", "🐙  GitHub Profile", "💼  Job Matcher", "📊  Full Assessment"])
        with t1: _tab_cv()
        with t2: _tab_github()
        with t3: _tab_jobs()
        with t4: _tab_assessment()

    with chat_col:
        st.markdown('<div class="chat-panel">', unsafe_allow_html=True)
        _render_chat_panel()
        st.markdown('</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()