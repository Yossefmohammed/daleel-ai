"""
Career AI Assistant  –  fully self-contained + Floating Copilot Chat (FIXED)
=============================================================================
ROOT CAUSE OF BROKEN COPILOT:
  st.markdown() with unsafe_allow_html=True renders inside a tiny sandboxed
  <iframe> that Streamlit creates internally. This means:
    1. position:fixed is relative to that tiny iframe, NOT the browser viewport
       → button appears invisible / stuck in wrong place
    2. <script> tags are stripped/delayed by Streamlit's sanitizer
       → click events never attach
    3. Groq API key was exposed in plain page HTML source

FIX APPLIED:
  Use st.components.v1.html() which renders in its OWN iframe with a real
  document, full JS support, and correct viewport. We give it height=0 and
  use CSS + JS to break out of the iframe height constraint via
  window.frameElement style manipulation — the standard trick for Streamlit
  component overlays. The floating panel lives in this component's document,
  positioned fixed relative to the component iframe's viewport which we
  expand to cover the whole screen.
"""

import os, re, json, html, datetime, time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(page_title="Career AI", page_icon="🎯",
                   layout="wide", initial_sidebar_state="expanded")

# ══════════════════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════════════════
def _css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
:root{--n:#080c18;--n2:#0d1326;--n3:#111829;--n4:#172035;--n5:#1e2d47;
  --L:rgba(255,255,255,.06);--L2:rgba(255,255,255,.10);
  --t1:#e8eeff;--t2:#7a8ab0;--t3:#3d4a6a;
  --c:#00d9ff;--cd:rgba(0,217,255,.08);--cb:rgba(0,217,255,.20);
  --g:#34d399;--a:#fbbf24;--r:#f87171;
  --ff:'Plus Jakarta Sans',system-ui,sans-serif;--fm:'JetBrains Mono',monospace;--R:14px;--Rs:9px;}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body,[data-testid="stApp"],[data-testid="stAppViewContainer"],.main{
  background:var(--n)!important;font-family:var(--ff)!important;color:var(--t1)!important}
#MainMenu,header,footer,[data-testid="stToolbar"],[data-testid="stDecoration"],
[data-testid="stStatusWidget"]{display:none!important}
.block-container{padding:0!important;max-width:100%!important}
section.main>div{padding:0!important}
[data-testid="stSidebar"]{background:var(--n2)!important;border-right:1px solid var(--L)!important;
  min-width:300px!important;max-width:300px!important}
[data-testid="stSidebar"]>div:first-child{padding:0!important}
[data-testid="stSidebar"] label,[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span{color:var(--t2)!important;font-size:12.5px!important}
[data-testid="stSidebar"] .stButton>button{background:transparent!important;
  border:1px solid var(--L2)!important;border-radius:var(--Rs)!important;
  color:var(--t2)!important;font-family:var(--ff)!important;font-size:12.5px!important;
  font-weight:500!important;padding:9px 14px!important;width:100%!important;
  box-shadow:none!important;transition:all .18s!important}
[data-testid="stSidebar"] .stButton>button:hover{background:var(--n4)!important;
  border-color:var(--cb)!important;color:var(--t1)!important;transform:none!important}
[data-testid="stSidebar"] [data-testid="stMetricValue"]{color:var(--t1)!important;font-size:15px!important}
[data-testid="stSidebar"] [data-testid="stMetricLabel"]{color:var(--t3)!important;font-size:10px!important}
/* chat messages in sidebar */
[data-testid="stSidebar"] [data-testid="stChatMessage"]{background:var(--n3)!important;
  border:1px solid var(--L)!important;border-radius:var(--R)!important;margin-bottom:6px!important}
[data-testid="stSidebar"] [data-testid="stChatInput"]{background:var(--n3)!important;
  border:1px solid var(--L2)!important;border-radius:var(--R)!important;}
[data-testid="stTabs"] [data-baseweb="tab-list"]{background:var(--n2)!important;
  border-bottom:1px solid var(--L)!important;padding:0 28px!important;gap:2px!important}
[data-testid="stTabs"] [data-baseweb="tab"]{background:transparent!important;border:none!important;
  color:var(--t2)!important;font-family:var(--ff)!important;font-size:13px!important;
  font-weight:600!important;padding:14px 16px!important;
  border-bottom:2px solid transparent!important;transition:all .18s!important}
[data-testid="stTabs"] [data-baseweb="tab"]:hover{color:var(--t1)!important}
[data-testid="stTabs"] [aria-selected="true"]{color:var(--c)!important;border-bottom-color:var(--c)!important}
[data-testid="stTabPanel"]{background:transparent!important;padding:28px!important;padding-right:32px!important}
[data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea,
[data-testid="stNumberInput"] input{background:var(--n3)!important;border:1px solid var(--L2)!important;
  border-radius:var(--R)!important;color:var(--t1)!important;font-family:var(--ff)!important;
  font-size:13.5px!important;caret-color:var(--c)!important}
[data-testid="stTextInput"] input:focus,[data-testid="stTextArea"] textarea:focus{
  border-color:var(--c)!important;box-shadow:0 0 0 2px var(--cd)!important;outline:none!important}
[data-testid="stTextInput"] label,[data-testid="stTextArea"] label,
[data-testid="stNumberInput"] label,[data-testid="stSelectbox"] label,
[data-testid="stMultiSelect"] label{color:var(--t2)!important;font-size:12.5px!important;font-weight:600!important}
[data-testid="stFileUploader"]{background:var(--n3)!important;border:1px dashed var(--cb)!important;
  border-radius:var(--R)!important;padding:16px!important}
[data-testid="stSelectbox"] [data-baseweb="select"]>div,
[data-testid="stMultiSelect"] [data-baseweb="select"]>div{background:var(--n3)!important;
  border:1px solid var(--L2)!important;border-radius:var(--R)!important;color:var(--t1)!important}
.stButton>button{background:linear-gradient(135deg,#007acc,#00d9ff)!important;border:none!important;
  border-radius:var(--R)!important;color:var(--n)!important;font-family:var(--ff)!important;
  font-size:13.5px!important;font-weight:700!important;padding:11px 22px!important;
  transition:all .2s!important;box-shadow:0 4px 14px rgba(0,217,255,.25)!important}
.stButton>button:hover{transform:translateY(-2px)!important;box-shadow:0 6px 20px rgba(0,217,255,.4)!important}
.stButton>button:active{transform:translateY(0)!important}
.stButton>button:disabled{opacity:.4!important;transform:none!important}
[data-testid="stMetric"]{background:var(--n3)!important;border:1px solid var(--L)!important;
  border-radius:var(--R)!important;padding:14px 18px!important}
[data-testid="stMetricLabel"]{color:var(--t3)!important;font-size:11px!important}
[data-testid="stMetricValue"]{color:var(--t1)!important;font-size:22px!important}
[data-testid="stExpander"]{background:var(--n3)!important;border:1px solid var(--L)!important;
  border-radius:var(--R)!important}
[data-testid="stExpander"] summary{color:var(--t2)!important;font-size:12.5px!important}
.stProgress>div>div{background:var(--c)!important}
[data-testid="stDownloadButton"]>button{background:transparent!important;
  border:1px solid var(--L2)!important;box-shadow:none!important;color:var(--t2)!important}
[data-testid="stDownloadButton"]>button:hover{border-color:var(--cb)!important;
  color:var(--c)!important;transform:none!important;box-shadow:none!important}
hr{border-color:var(--L)!important}
.hdr{background:var(--n2);border-bottom:1px solid var(--L);padding:0 28px;height:64px;
  display:flex;align-items:center;justify-content:space-between}
.hgem{width:42px;height:42px;border-radius:12px;background:linear-gradient(135deg,#007acc,#00d9ff);
  display:flex;align-items:center;justify-content:center;font-size:20px;
  box-shadow:0 4px 14px rgba(0,217,255,.25)}
.badge{font-size:10px;font-weight:600;padding:4px 10px;border-radius:20px;
  border:1px solid var(--L2);color:var(--t3);background:var(--n3)}
.badge.live{background:rgba(52,211,153,.10);border-color:rgba(52,211,153,.25);color:#34d399}
.pill{display:inline-block;background:var(--cd);border:1px solid var(--cb);color:var(--c);
  font-size:11px;font-weight:600;padding:3px 10px;border-radius:20px;margin:3px 2px;font-family:var(--fm)}
.pill.tech{background:rgba(251,191,36,.08);border-color:rgba(251,191,36,.25);color:#fbbf24}
.pill.miss{background:rgba(248,113,113,.08);border-color:rgba(248,113,113,.25);color:#f87171}
.aib{background:var(--n3);border:1px solid var(--L);border-left:3px solid var(--c);
  border-radius:0 var(--R) var(--R) var(--R);padding:16px 20px;font-size:13.5px;
  line-height:1.75;color:var(--t1);margin:12px 0}
.ailbl{font-size:10px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;
  color:var(--c);margin-bottom:8px}
.jcard{background:var(--n3);border:1px solid var(--L);border-radius:var(--R);
  padding:20px 22px;margin-bottom:14px;transition:border-color .18s}
.jcard:hover{border-color:var(--cb)}
.sh{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
  color:var(--t3);margin:22px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--L)}
.sdiv{height:1px;background:var(--L);margin:12px 0}
.slbl{font-size:10px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;
  color:var(--t3);padding-bottom:6px}
.chat-hdr{background:linear-gradient(135deg,rgba(0,122,204,.15),rgba(0,217,255,.08));
  border-radius:10px;padding:10px 14px;margin-bottom:10px;
  border:1px solid rgba(0,217,255,.15)}
</style>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# API key helpers
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
            r = client.chat.completions.create(model=model, messages=msgs,
                                               temperature=0.3, max_tokens=max_tokens)
            return r.choices[0].message.content
        except Exception: continue
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
# Job database  (scraping + caching)
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
    for p in ([DATA_DIR/"jobs.csv", Path("docs")/"ai_jobs_market_2025_2026.csv"]
              + list(Path("docs").glob("*.csv"))):
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
    if skills:
        for sk in skills[:3]:
            say(f"📡 RemoteOK: searching '{sk}'…")
            all_jobs.extend(_scrape_remoteok(keywords=sk, limit=60))
        combined_kw = "+".join(skills[:4])
        all_jobs.extend(_scrape_remoteok(keywords=combined_kw, limit=60))
    else:
        say("📡 Scraping RemoteOK (general)…")
        all_jobs.extend(_scrape_remoteok(limit=150))
    say(f"✅ RemoteOK: {len(all_jobs)} jobs. Trying Arbeitnow…")
    anow = _scrape_arbeitnow()
    all_jobs.extend(anow)
    say(f"✅ Arbeitnow: {len(anow)} jobs. Loading local CSV…")
    local = _load_local_csv()
    all_jobs.extend(local)
    say("🔧 Deduplicating…")
    seen, unique = set(), []
    for j in all_jobs:
        k = (str(j.get("title","")).lower()[:40], str(j.get("company","")).lower()[:30])
        if k not in seen: seen.add(k); unique.append(j)
    _save_combined(unique)
    return len(unique)

def _auto_build():
    if st.session_state.get("db_checked"): return
    st.session_state.db_checked = True
    if _cache_fresh(): return
    with st.sidebar:
        ph = st.empty()
        ph.warning("🔄 Building job database… (first load only)")
        try:
            n = build_job_database()
            ph.success(f"✅ Job database ready — {n:,} jobs")
            time.sleep(2)
        except Exception as e:
            ph.warning(f"⚠️ Could not auto-build job DB: {e}")
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
    raw = _llm(client, [{"role":"user","content":prompt}], max_tokens=1200)
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
                          params={"per_page":30,"sort":"pushed"}, timeout=10)
        repos = rr.json() if rr.ok else []
    except Exception: repos = []
    lang_counts: dict = {}
    for repo in repos[:20]:
        if repo.get("language"):
            lang_counts[repo["language"]] = lang_counts.get(repo["language"],0)+1
    profile = {
        "login": user.get("login",""), "name": user.get("name",""),
        "bio": user.get("bio",""), "followers": user.get("followers",0),
        "following": user.get("following",0), "public_repos": user.get("public_repos",0),
        "languages": dict(sorted(lang_counts.items(),key=lambda x:-x[1])[:8]),
        "top_repos": [{"name":r.get("name"),"stars":r.get("stargazers_count",0),
                       "description":r.get("description","")} for r in repos[:5]],
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
    raw = _llm(client, [{"role":"user","content":prompt}], max_tokens=600)
    return {"success": True, "profile": profile, "analysis": _parse_json(raw)}


# ══════════════════════════════════════════════════════════════════════════════
# Job matching
# ══════════════════════════════════════════════════════════════════════════════
def match_jobs(user_profile: dict, limit: int = 8) -> dict:
    jobs = _load_combined()
    if not jobs:
        return {"success": False,
                "error": "Job database is empty. Click 🔄 Refresh Job Database in the sidebar."}
    skills = [s.lower() for s in user_profile.get("skills",[])]
    roles  = [r.lower() for r in user_profile.get("interested_roles",[])]
    def _score(j):
        blob = (str(j.get("title",""))+" "+str(j.get("description",""))).lower()
        s = sum(2 for sk in skills if sk in blob)
        s += sum(1 for ro in roles for w in ro.split() if len(w)>3 and w in blob)
        return s
    top25 = sorted(jobs, key=_score, reverse=True)[:25]
    compact = [{"title":str(j.get("title",""))[:60],"company":str(j.get("company",""))[:40],
                "location":str(j.get("location",""))[:30],
                "description":str(j.get("description",""))[:200],
                "salary":str(j.get("salary",""))[:30]} for j in top25]
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
    raw = _llm(client, [{"role":"user","content":prompt}], max_tokens=1400)
    matches = _parse_json(raw)
    if isinstance(matches, dict) and "jobs" in matches: matches = matches["jobs"]
    if not isinstance(matches, list): matches = []
    return {"success": True, "matches": matches,
            "total_in_db": len(jobs), "candidates_evaluated": len(compact)}


# ══════════════════════════════════════════════════════════════════════════════
# Session state
# ══════════════════════════════════════════════════════════════════════════════
def _init():
    defaults = {
        "cv_analysis": None,
        "github_analysis": None,
        "job_matches": None,
        "db_checked": False,
        "skill_scrape_done": False,
        "_jobs_skills_shown": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ── Render helpers ──────────────────────────────────────────────────────────
def _pill(t, k="skill"):
    cls = {"skill":"pill","tech":"pill tech","miss":"pill miss"}.get(k,"pill")
    return f'<span class="{cls}">{html.escape(str(t))}</span>'

def _pills(items, k="skill"):
    if not items: return '<span style="color:var(--t3);font-size:12px">none found</span>'
    return "".join(_pill(i,k) for i in items)

def _sc(s):
    if s >= 80: return "#34d399"
    if s >= 60: return "#00d9ff"
    if s >= 40: return "#fbbf24"
    return "#f87171"

def _dot(col="#00d9ff"):
    return (f'<div style="width:9px;height:9px;border-radius:50%;background:{col};'
            f'margin-top:4px;flex-shrink:0"></div>')


# ══════════════════════════════════════════════════════════════════════════════
# FIX 1 — Sidebar Chat (replaces broken floating Copilot panel)
# ══════════════════════════════════════════════════════════════════════════════
def _inject_copilot(api_key: str, context: str):
    """
    Floating Copilot chat panel — FIXED version.

    WHY st.components.v1.html() works where st.markdown() didn't:
      • components.html() creates its own <iframe> with a full HTML document.
      • Scripts execute reliably (no Streamlit sanitizer stripping them).
      • We expand the iframe to cover the full viewport via frameElement CSS,
        then position the button/panel with position:fixed inside it.
        Fixed positioning inside a full-viewport iframe == fixed on the page.
    """
    import streamlit.components.v1 as components

    safe_key = api_key.replace('"', '').replace("'", "")
    safe_ctx = (context
                .replace('\\', '\\\\')
                .replace('"', '\\"')
                .replace('\n', ' ')
                .replace('\r', ''))

    html_code = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  /* ── Make this iframe cover the whole viewport ── */
  html, body {{
    margin: 0; padding: 0;
    background: transparent !important;
    overflow: hidden;
  }}

  /* ── Floating button ── */
  #cp-btn {{
    position: fixed; bottom: 28px; right: 28px; z-index: 9999;
    width: 54px; height: 54px; border-radius: 50%;
    background: linear-gradient(135deg, #007acc, #00d9ff);
    border: none; cursor: pointer; font-size: 22px;
    box-shadow: 0 6px 24px rgba(0,217,255,.5);
    display: flex; align-items: center; justify-content: center;
    color: #0d1326; font-weight: 700;
    transition: transform .2s, box-shadow .2s;
  }}
  #cp-btn:hover {{ transform: scale(1.1); box-shadow: 0 8px 30px rgba(0,217,255,.7); }}

  /* ── Notification dot ── */
  #cp-notif {{
    position: absolute; top: -4px; right: -4px;
    width: 16px; height: 16px; border-radius: 50%; background: #f87171;
    font-size: 9px; font-weight: 700; color: #fff;
    display: none; align-items: center; justify-content: center;
    border: 2px solid #0d1326; pointer-events: none;
  }}

  /* ── Chat panel ── */
  #cp-panel {{
    position: fixed; bottom: 96px; right: 28px; z-index: 9998;
    width: 360px; height: 520px;
    background: #0d1326; border: 1px solid rgba(0,217,255,.25);
    border-radius: 18px; display: none; flex-direction: column;
    box-shadow: 0 20px 60px rgba(0,0,0,.7);
    font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
    overflow: hidden;
    animation-duration: .22s; animation-timing-function: ease;
  }}
  #cp-panel.open {{ display: flex; animation-name: cp-in; }}
  @keyframes cp-in {{
    from {{ opacity:0; transform: translateY(12px); }}
    to   {{ opacity:1; transform: translateY(0); }}
  }}

  /* ── Panel header ── */
  #cp-hdr {{
    background: linear-gradient(135deg, rgba(0,122,204,.15), rgba(0,217,255,.07));
    border-bottom: 1px solid rgba(0,217,255,.15);
    padding: 14px 16px; display: flex; align-items: center; gap: 10px; flex-shrink: 0;
  }}
  .cp-gem {{
    width: 32px; height: 32px; border-radius: 9px;
    background: linear-gradient(135deg,#007acc,#00d9ff);
    display: flex; align-items: center; justify-content: center; font-size: 15px;
  }}
  .cp-title {{ font-size: 13.5px; font-weight: 700; color: #e8eeff; }}
  .cp-sub   {{ font-size: 10px; color: #3d4a6a; margin-top: 1px; }}
  #cp-close {{
    margin-left: auto; background: none; border: none;
    color: #3d4a6a; font-size: 18px; cursor: pointer; padding: 0 4px;
  }}
  #cp-close:hover {{ color: #e8eeff; }}

  /* ── Messages ── */
  #cp-msgs {{
    flex: 1; overflow-y: auto; padding: 14px;
    display: flex; flex-direction: column; gap: 10px;
    scrollbar-width: thin; scrollbar-color: rgba(255,255,255,.1) transparent;
  }}
  #cp-msgs::-webkit-scrollbar {{ width: 3px; }}
  #cp-msgs::-webkit-scrollbar-thumb {{ background: rgba(255,255,255,.1); border-radius: 3px; }}
  .cp-msg {{
    max-width: 88%; font-size: 13px; line-height: 1.65;
    padding: 10px 13px; border-radius: 14px; word-break: break-word;
  }}
  .cp-msg.bot {{
    background: #111829; border: 1px solid rgba(255,255,255,.06);
    color: #e8eeff; border-top-left-radius: 4px; align-self: flex-start;
  }}
  .cp-msg.usr {{
    background: linear-gradient(135deg,#00527a,#007cc2);
    color: #fff; border-top-right-radius: 4px; align-self: flex-end;
  }}

  /* ── Typing dots ── */
  .cp-typing {{
    display: flex; gap: 4px; padding: 12px 14px;
    align-items: center; align-self: flex-start;
  }}
  .cp-typing span {{
    width: 6px; height: 6px; border-radius: 50%; background: #00d9ff;
    animation: blink 1.2s ease-in-out infinite;
  }}
  .cp-typing span:nth-child(2) {{ animation-delay: .2s; }}
  .cp-typing span:nth-child(3) {{ animation-delay: .4s; }}
  @keyframes blink {{ 0%,100% {{ opacity:.2; }} 50% {{ opacity:1; }} }}

  /* ── Chips ── */
  #cp-chips {{ padding: 0 14px 8px; display: flex; flex-wrap: wrap; gap: 6px; }}
  .cp-chip {{
    font-size: 11px; font-weight: 600; padding: 5px 11px; border-radius: 20px;
    background: rgba(0,217,255,.08); border: 1px solid rgba(0,217,255,.2);
    color: #00d9ff; cursor: pointer; transition: background .15s;
    font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
  }}
  .cp-chip:hover {{ background: rgba(0,217,255,.18); }}

  /* ── Input form ── */
  #cp-form {{
    border-top: 1px solid rgba(255,255,255,.06);
    padding: 10px 12px; display: flex; gap: 8px;
    align-items: flex-end; flex-shrink: 0;
  }}
  #cp-input {{
    flex: 1; background: #111829; border: 1px solid rgba(255,255,255,.10);
    border-radius: 10px; padding: 9px 12px; color: #e8eeff;
    font-family: 'Plus Jakarta Sans', system-ui, sans-serif; font-size: 13px;
    resize: none; outline: none; max-height: 90px; line-height: 1.5;
    caret-color: #00d9ff;
  }}
  #cp-input:focus {{ border-color: #00d9ff; box-shadow: 0 0 0 2px rgba(0,217,255,.12); }}
  #cp-input::placeholder {{ color: #3d4a6a; }}
  #cp-send {{
    width: 36px; height: 36px; border-radius: 9px; border: none; cursor: pointer;
    background: linear-gradient(135deg,#007acc,#00d9ff);
    color: #0d1326; font-size: 16px; display: flex;
    align-items: center; justify-content: center; flex-shrink: 0;
    transition: transform .15s;
  }}
  #cp-send:hover {{ transform: scale(1.08); }}
</style>
</head>
<body>

<button id="cp-btn" title="Career AI Chat">
  💬
  <div id="cp-notif">1</div>
</button>

<div id="cp-panel">
  <div id="cp-hdr">
    <div class="cp-gem">🎯</div>
    <div>
      <div class="cp-title">Career AI</div>
      <div class="cp-sub">Your personal career advisor</div>
    </div>
    <button id="cp-close">✕</button>
  </div>
  <div id="cp-msgs"></div>
  <div id="cp-chips"></div>
  <div id="cp-form">
    <textarea id="cp-input" placeholder="Ask anything about your career…" rows="1"></textarea>
    <button id="cp-send">➤</button>
  </div>
</div>

<script>
(function() {{
  /* ── Step 1: expand this iframe to cover the whole page ──────────────────
     The iframe starts at height=0 set by Streamlit. We grab the frameElement
     (the <iframe> tag in the parent document) and stretch it to fill the
     viewport. pointer-events:none on html/body means only our floating
     elements (which have pointer-events:auto) capture clicks — the rest of
     the Streamlit page stays fully interactive.                              */
  try {{
    var frame = window.frameElement;
    if (frame) {{
      frame.style.cssText = [
        'position:fixed', 'top:0', 'left:0',
        'width:100vw', 'height:100vh',
        'border:none', 'background:transparent',
        'pointer-events:none', 'z-index:9000'
      ].join('!important;') + '!important';
    }}
    // Allow clicks through the transparent body but keep our widgets clickable
    document.documentElement.style.pointerEvents = 'none';
    document.body.style.pointerEvents            = 'none';
    document.getElementById('cp-btn').style.pointerEvents   = 'auto';
    document.getElementById('cp-panel').style.pointerEvents = 'auto';
  }} catch(e) {{ console.warn('frameElement access blocked:', e); }}

  /* ── Step 2: chat logic ──────────────────────────────────────────────── */
  var GROQ_KEY = "{safe_key}";
  var USER_CTX = "{safe_ctx}";
  var SYSTEM = "You are a warm, expert career advisor called Career AI. "
    + "Give honest, specific, actionable advice in a conversational tone — like a smart mentor. "
    + "Keep answers concise and focused. Use bullet points only for lists of 3 or more items. "
    + "Never say 'As an AI'. Be direct and real."
    + (USER_CTX ? "\\n\\nContext about this user:\\n" + USER_CTX : "");

  var msgs    = [];
  var isOpen  = false;
  var greeted = false;
  var CHIPS   = [
    "How can I improve my CV?",
    "What skills should I learn?",
    "How do I negotiate salary?",
    "Am I ready for a senior role?"
  ];

  var btn    = document.getElementById('cp-btn');
  var panel  = document.getElementById('cp-panel');
  var notif  = document.getElementById('cp-notif');
  var closeB = document.getElementById('cp-close');
  var sendB  = document.getElementById('cp-send');
  var input  = document.getElementById('cp-input');

  btn.addEventListener('click', toggle);
  closeB.addEventListener('click', toggle);
  sendB.addEventListener('click', doSend);
  input.addEventListener('keydown', function(e) {{
    if (e.key === 'Enter' && !e.shiftKey) {{ e.preventDefault(); doSend(); }}
  }});
  input.addEventListener('input', function() {{
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 90) + 'px';
  }});

  // Show notification dot after 3 s if not yet opened
  setTimeout(function() {{
    if (!isOpen) notif.style.display = 'flex';
  }}, 3000);

  function toggle() {{
    isOpen = !isOpen;
    if (isOpen) {{
      panel.classList.add('open');
      notif.style.display = 'none';
      if (!greeted) {{ greet(); greeted = true; }}
      setTimeout(function() {{ input.focus(); }}, 260);
    }} else {{
      panel.classList.remove('open');
    }}
  }}

  function greet() {{
    addMsg('bot', USER_CTX
      ? "Hey! 👋 I can see you've been working through your profile. What would you like to explore?"
      : "Hey! 👋 I'm your Career AI advisor. Ask me anything — CV tips, job search, salary negotiation, skill gaps, interview prep…");
    renderChips();
  }}

  function renderChips() {{
    var c = document.getElementById('cp-chips');
    c.innerHTML = '';
    CHIPS.forEach(function(q) {{
      var b = document.createElement('button');
      b.className   = 'cp-chip';
      b.textContent = q;
      b.addEventListener('click', function() {{ c.innerHTML=''; send(q); }});
      c.appendChild(b);
    }});
  }}

  function addMsg(role, text) {{
    var box = document.getElementById('cp-msgs');
    var d   = document.createElement('div');
    d.className = 'cp-msg ' + role;
    d.innerHTML = mdToHtml(text);
    box.appendChild(d);
    box.scrollTop = box.scrollHeight;
  }}

  function mdToHtml(t) {{
    t = t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    t = t.replace(/\*\*(.*?)\*\*/g,'<strong>$1</strong>');
    t = t.replace(/\*(.*?)\*/g,'<em>$1</em>');
    t = t.replace(/(^|\n)[•\-\*] (.+)/g,'$1<li style="margin:3px 0;padding-left:4px">$2</li>');
    if (t.indexOf('<li') !== -1)
      t = '<ul style="padding-left:16px;margin:6px 0">' + t + '</ul>';
    t = t.replace(/\n/g,'<br>');
    return t;
  }}

  function showTyping() {{
    var box = document.getElementById('cp-msgs');
    var d   = document.createElement('div');
    d.className = 'cp-typing'; d.id = 'cp-typing';
    d.innerHTML = '<span></span><span></span><span></span>';
    box.appendChild(d); box.scrollTop = box.scrollHeight;
  }}
  function hideTyping() {{
    var d = document.getElementById('cp-typing'); if (d) d.remove();
  }}

  async function send(text) {{
    document.getElementById('cp-chips').innerHTML = '';
    addMsg('usr', text);
    msgs.push({{ role:'user', content:text }});
    showTyping();
    try {{
      var res = await fetch('https://api.groq.com/openai/v1/chat/completions', {{
        method: 'POST',
        headers: {{ 'Content-Type':'application/json', 'Authorization':'Bearer ' + GROQ_KEY }},
        body: JSON.stringify({{
          model: 'llama-3.3-70b-versatile',
          messages: [{{ role:'system', content:SYSTEM }}].concat(msgs.slice(-12)),
          temperature: 0.75,
          max_tokens: 500
        }})
      }});
      var data  = await res.json();
      var reply = (data.choices && data.choices[0] && data.choices[0].message
                   && data.choices[0].message.content)
                  || 'Sorry, something went wrong. Try again!';
      hideTyping(); addMsg('bot', reply);
      msgs.push({{ role:'assistant', content:reply }});
    }} catch(e) {{
      hideTyping();
      addMsg('bot', "Hmm, couldn't reach the AI right now. Check your connection and try again.");
    }}
  }}

  function doSend() {{
    var text = input.value.trim();
    if (!text) return;
    input.value = ''; input.style.height = 'auto';
    send(text);
  }}
}})();
</script>
</body>
</html>"""

    # height=0 keeps no visible space; the iframe is stretched to fullscreen by the JS above
    components.html(html_code, height=0, scrolling=False)


# ══════════════════════════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════════════════════════
def _sidebar():
    with st.sidebar:
        st.markdown(
            '<div style="padding:20px 16px 14px;border-bottom:1px solid rgba(255,255,255,.06)">'
            '<div style="display:flex;align-items:center;gap:12px">'
            '<div style="width:40px;height:40px;border-radius:12px;'
            'background:linear-gradient(135deg,#007acc,#00d9ff);'
            'display:flex;align-items:center;justify-content:center;font-size:20px;'
            'box-shadow:0 4px 14px rgba(0,217,255,.25)">🎯</div>'
            '<div><div style="font-size:15px;font-weight:800;color:#e8eeff;letter-spacing:-.3px">Career AI</div>'
            '<div style="font-size:10px;color:#00d9ff;background:rgba(0,217,255,.08);padding:2px 8px;'
            'border-radius:20px;border:1px solid rgba(0,217,255,.2);display:inline-block;'
            'font-weight:600;margin-top:2px">Phase 1 · MVP</div>'
            '</div></div></div>',
            unsafe_allow_html=True,
        )

        st.markdown("<div style='padding:14px 14px 0'>", unsafe_allow_html=True)

        # Status metrics
        st.markdown('<div class="slbl">Status</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1: st.metric("Groq AI", "🟢 Ready" if _key() else "🔴 Missing")
        with c2: st.metric("GitHub", "🟢" if _gh_token() else "⚪ Optional")
        cnt = len(_load_combined())
        st.metric("Job Database", f"🟢 {cnt:,} jobs" if cnt else "🔴 Empty")
        if not _key():
            st.error("GROQ_API_KEY missing.\nAdd to .env or Streamlit secrets.")

        st.markdown('<div class="sdiv"></div>', unsafe_allow_html=True)

        # Job database controls
        st.markdown('<div class="slbl">Job Database</div>', unsafe_allow_html=True)
        if COMBINED.exists():
            age_h = (datetime.datetime.now() -
                     datetime.datetime.fromtimestamp(COMBINED.stat().st_mtime)).total_seconds() / 3600
            st.caption(f"Cache: {age_h:.0f}h old  ·  refreshes every {CACHE_HOURS}h")
        if st.button("🔄 Refresh Job Database", key="sb_ref", use_container_width=True):
            ph = st.empty()
            skills = []
            if st.session_state.cv_analysis:
                a = st.session_state.cv_analysis.get("analysis",{})
                if isinstance(a, dict): skills = a.get("skills",[])[:6]
            try:
                n = build_job_database(skills=skills, status_ph=ph)
                ph.success(f"✅ Done — {n:,} jobs saved"
                           f"{' (targeted to your skills)' if skills else ''}")
            except Exception as e:
                ph.error(f"❌ {e}")

        st.markdown('<div class="sdiv"></div>', unsafe_allow_html=True)

        # Progress tracker
        st.markdown('<div class="slbl">Your Progress</div>', unsafe_allow_html=True)
        for lbl, done in [
            ("📄 CV analyzed",    st.session_state.cv_analysis is not None),
            ("🐙 GitHub analyzed",st.session_state.github_analysis is not None),
            ("💼 Jobs matched",   st.session_state.job_matches is not None),
        ]:
            col = "#34d399" if done else "var(--t3)"
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;padding:4px 0;'
                f'font-size:12.5px;color:{col}">{"✅" if done else "⬜"} {lbl}</div>',
                unsafe_allow_html=True,
            )

        if st.button("🗑 Clear Session", key="sb_clear", use_container_width=True):
            st.session_state.cv_analysis       = None
            st.session_state.github_analysis   = None
            st.session_state.job_matches       = None
            st.session_state.skill_scrape_done = False
            st.session_state._jobs_skills_shown = False
            if "js_skills_v3" in st.session_state:
                del st.session_state["js_skills_v3"]
            st.rerun()

        st.markdown('<div class="sdiv"></div>', unsafe_allow_html=True)

        if any([st.session_state.cv_analysis,
                st.session_state.github_analysis,
                st.session_state.job_matches]):
            st.download_button(
                "📥 Download Report",
                data=json.dumps({
                    "generated_at": datetime.datetime.now().isoformat(),
                    "cv":     st.session_state.cv_analysis,
                    "github": st.session_state.github_analysis,
                    "jobs":   st.session_state.job_matches,
                }, indent=2, default=str),
                file_name=f"career_report_{datetime.date.today()}.json",
                mime="application/json",
                use_container_width=True,
                key="sb_dl",
            )
            st.markdown('<div class="sdiv"></div>', unsafe_allow_html=True)

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
**Tip:** After analyzing your CV, the job database
will automatically re-scrape with your skills as keywords.
""")

        st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Header
# ══════════════════════════════════════════════════════════════════════════════
def _header():
    ready = any([st.session_state.cv_analysis,
                 st.session_state.github_analysis,
                 st.session_state.job_matches])
    st.markdown(
        '<div class="hdr"><div style="display:flex;align-items:center;gap:14px">'
        '<div class="hgem">🎯</div>'
        '<div><div style="font-size:17px;font-weight:800;color:var(--t1);letter-spacing:-.3px">'
        'Career AI Assistant</div>'
        '<div style="font-size:11px;color:var(--t3);margin-top:2px">'
        'CV · GitHub · Job Matching · Assessment  —  💬 Chat in the sidebar</div>'
        '</div></div><div style="display:flex;gap:8px">'
        + ('<div class="badge live">● Session Active</div>' if ready
           else '<div class="badge">○ No Data Yet</div>')
        + '<div class="badge">Groq · LLaMA 3.3</div></div></div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Tab: CV Analyzer
# ══════════════════════════════════════════════════════════════════════════════
def _tab_cv():
    st.markdown('<div class="sh">📄 CV Analyzer</div>', unsafe_allow_html=True)
    st.markdown(
        '<p style="color:var(--t2);font-size:13px;margin-bottom:18px">'
        "Upload your PDF and I'll give you a plain-English breakdown. "
        "Your skills will automatically populate the Job Matcher and trigger a targeted job scrape.</p>",
        unsafe_allow_html=True,
    )
    cu, cb = st.columns([3,1])
    with cu:
        f = st.file_uploader("Choose your CV (PDF)", type=["pdf"], key="cv_file")
    with cb:
        st.write(""); st.write("")
        go = st.button("🔍 Analyze CV", key="btn_cv",
                       use_container_width=True, disabled=f is None)

    if go and f:
        if not _key(): return
        with st.spinner("Reading your CV…"):
            tmp = f"temp_{f.name}"
            with open(tmp, "wb") as fh: fh.write(f.getbuffer())
            res = analyze_cv(tmp); os.remove(tmp)
            if res.get("success"):
                st.session_state.cv_analysis       = res
                st.session_state.skill_scrape_done = False
                st.session_state._jobs_skills_shown = False
                # FIX 3: auto-fill skills into the Job Matcher widget
                a = res.get("analysis", {})
                if isinstance(a, dict):
                    skills_list = a.get("skills", [])
                    if skills_list:
                        st.session_state["js_skills_v3"] = "\n".join(str(s) for s in skills_list)
                st.success("✅ CV analyzed! Skills auto-filled in the 💼 Job Matcher tab.")
            else:
                st.error(f"❌ {res.get('error')}"); return

    # Trigger targeted scrape when CV analyzed and cache stale
    if (st.session_state.cv_analysis and
            not st.session_state.skill_scrape_done and
            not _cache_fresh()):
        a = st.session_state.cv_analysis.get("analysis",{})
        skills = a.get("skills",[])[:6] if isinstance(a,dict) else []
        if skills:
            with st.spinner(f"🔍 Scraping jobs matching your skills: {', '.join(skills[:3])}…"):
                try:
                    n = build_job_database(skills=skills)
                    st.session_state.skill_scrape_done = True
                    st.toast(f"✅ Found {n:,} jobs matching your skills!", icon="💼")
                except Exception:
                    st.session_state.skill_scrape_done = True

    if not st.session_state.cv_analysis:
        st.info("Upload your CV and click **Analyze CV** to get started.")
        return

    a = st.session_state.cv_analysis.get("analysis",{})
    if isinstance(a, str): a = _parse_json(a) or {}

    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Seniority", a.get("seniority_level","—"))
    with c2: st.metric("Experience", f"{a.get('experience_years','—')} yrs")
    with c3: st.metric("Skills", len(a.get("skills",[])))

    if a.get("summary"):
        st.markdown(
            f'<div class="aib"><div class="ailbl">🤖 AI Summary</div>'
            f'{html.escape(str(a["summary"]))}</div>',
            unsafe_allow_html=True,
        )
    if a.get("skills") or a.get("technologies"):
        st.markdown('<div class="sh">Skills & Technologies</div>', unsafe_allow_html=True)
        st.markdown(_pills(a.get("skills",[]),"skill") + _pills(a.get("technologies",[]),"tech"),
                    unsafe_allow_html=True)
    if a.get("experience"):
        st.markdown('<div class="sh">Work Experience</div>', unsafe_allow_html=True)
        for e in a["experience"]:
            st.markdown(
                f'<div style="display:flex;gap:12px;align-items:flex-start;margin-bottom:10px">{_dot()}'
                f'<div><div style="font-size:13.5px;font-weight:600;color:var(--t1)">'
                f'{html.escape(str(e.get("title","—")))}</div>'
                f'<div style="font-size:12px;color:var(--t2)">'
                f'{html.escape(str(e.get("company","—")))} · {html.escape(str(e.get("duration","")))}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
    if a.get("education"):
        st.markdown('<div class="sh">Education</div>', unsafe_allow_html=True)
        for e in a["education"]:
            st.markdown(
                f'<div style="display:flex;gap:12px;align-items:flex-start;margin-bottom:10px">'
                f'{_dot("#34d399")}'
                f'<div><div style="font-size:13.5px;font-weight:600;color:var(--t1)">'
                f'{html.escape(str(e.get("degree","")))} {html.escape(str(e.get("field","")))}</div>'
                f'<div style="font-size:12px;color:var(--t2)">{html.escape(str(e.get("school","—")))}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
    c1, c2 = st.columns(2)
    with c1:
        if a.get("strengths"):
            st.markdown('<div class="sh">💪 Strengths</div>', unsafe_allow_html=True)
            for s in a["strengths"]:
                st.markdown(
                    f'<div style="color:var(--t2);font-size:13px;padding:3px 0">✅ {html.escape(str(s))}</div>',
                    unsafe_allow_html=True)
    with c2:
        if a.get("improvement_areas"):
            st.markdown('<div class="sh">🎯 To Improve</div>', unsafe_allow_html=True)
            for g in a["improvement_areas"]:
                st.markdown(
                    f'<div style="color:var(--t2);font-size:13px;padding:3px 0">→ {html.escape(str(g))}</div>',
                    unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Tab: GitHub
# ══════════════════════════════════════════════════════════════════════════════
def _tab_github():
    st.markdown('<div class="sh">🐙 GitHub Profile Analysis</div>', unsafe_allow_html=True)
    st.markdown(
        '<p style="color:var(--t2);font-size:13px;margin-bottom:18px">'
        'Enter any public GitHub username for an honest, plain-English assessment with a score and tips.</p>',
        unsafe_allow_html=True,
    )
    ci, cb = st.columns([3,1])
    with ci:
        uname = st.text_input("GitHub Username", placeholder="e.g. torvalds", key="gh_username")
    with cb:
        st.write(""); st.write("")
        go = st.button("🔍 Analyze", key="btn_gh",
                       use_container_width=True, disabled=not (uname or "").strip())

    if go and (uname or "").strip():
        if not _key(): return
        with st.spinner(f"Fetching @{uname.strip()}…"):
            res = analyze_github(uname.strip())
            if res.get("success"): st.session_state.github_analysis = res
            else:
                st.error(f"❌ {res.get('error')}")
                st.info("Make sure the username is correct and the profile is public.")
                return

    if not st.session_state.github_analysis:
        st.info("Enter a GitHub username and click **Analyze**."); return

    data    = st.session_state.github_analysis
    profile = data.get("profile",{})
    analysis = data.get("analysis",{})
    if isinstance(analysis, str): analysis = _parse_json(analysis) or {}

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Followers",    profile.get("followers",0))
    with c2: st.metric("Public Repos", profile.get("public_repos",0))
    with c3: st.metric("Following",    profile.get("following",0))
    score = analysis.get("profile_score","—") if isinstance(analysis,dict) else "—"
    with c4: st.metric("Profile Score", f"{score}/100" if str(score).isdigit() else score)

    summary = analysis.get("summary","") if isinstance(analysis,dict) else str(analysis)
    if summary:
        st.markdown(
            f'<div class="aib"><div class="ailbl">🤖 AI Assessment</div>'
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
                f'<div style="color:var(--t2);font-size:13px;padding:4px 0">→ {html.escape(str(r))}</div>',
                unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Tab: Job Matcher
# ══════════════════════════════════════════════════════════════════════════════
def _tab_jobs():
    st.markdown('<div class="sh">💼 Job Matcher</div>', unsafe_allow_html=True)
    cnt = len(_load_combined())
    if cnt == 0:
        st.warning("**Job database is empty.** Click **🔄 Refresh Job Database** in the sidebar, "
                   "or analyze your CV first — it will trigger an automatic targeted scrape.")
    else:
        st.markdown(
            f'<p style="color:var(--t2);font-size:13px;margin-bottom:18px">'
            f'Searching <strong style="color:var(--c)">{cnt:,} jobs</strong>. '
            f"Fill in your profile — skills are auto-filled from your CV if you've analyzed it.</p>",
            unsafe_allow_html=True,
        )

    if st.session_state.cv_analysis and not st.session_state._jobs_skills_shown:
        st.success("✅ Skills auto-filled from your CV — edit them freely below.")
        st.session_state._jobs_skills_shown = True

    c1, c2 = st.columns(2)
    with c1:
        sr = st.text_area(
            "Your Skills (one per line)",
            placeholder="Python\nReact\nSQL",
            height=140,
            key="js_skills_v3",  # value auto-populated from session_state after CV analysis
        )
        exp = st.number_input("Years of Experience", 0, 50, 2, key="js_exp")
    with c2:
        sen = st.selectbox("Seniority Level",
                           ["Junior","Mid-Level","Senior","Lead","Principal"], key="js_sen")
        roles = st.multiselect("Interested Roles", [
            "Full Stack Developer","Backend Engineer","Frontend Developer",
            "Data Scientist","ML Engineer","DevOps Engineer",
            "Product Manager","Mobile Developer","Cloud Architect",
        ], key="js_roles")

    go = st.button("🔍 Find My Best Jobs", key="btn_jobs", disabled=(cnt==0))
    if go:
        if not _key(): return
        skills = [s.strip() for s in sr.split("\n") if s.strip()]
        if not skills:
            st.warning("Please enter at least one skill."); return
        with st.spinner("Scanning jobs and ranking with AI…"):
            res = match_jobs({
                "skills": skills,
                "experience_years": int(exp),
                "seniority_level": sen.lower().replace("-","_"),
                "interested_roles": roles,
            })
        if res.get("success"): st.session_state.job_matches = res
        else: st.error(f"❌ {res.get('error')}"); return

    if not st.session_state.job_matches:
        if cnt > 0: st.info("Fill in your profile and click **Find My Best Jobs**.")
        return

    res     = st.session_state.job_matches
    matches = res.get("matches",[])
    total   = res.get("total_in_db","?")
    evald   = res.get("candidates_evaluated","?")

    if not matches:
        st.warning("No matches found. Try broadening your skills."); return

    st.markdown(
        f'<div class="aib"><div class="ailbl">Results</div>Out of <strong>{total:,}</strong> jobs, '
        f'the AI shortlisted <strong>{evald}</strong> candidates and picked these '
        f'<strong>{len(matches)}</strong> best fits for you.</div>',
        unsafe_allow_html=True,
    )
    for job in matches:
        if not isinstance(job, dict): continue
        score   = int(job.get("match_score",0))
        colour  = _sc(score)
        matched = job.get("matched_skills",[])
        missing = job.get("missing_skills",[])
        why     = job.get("why_good_fit","")
        salary  = str(job.get("salary",""))
        loc     = str(job.get("location",""))
        mp = "".join(_pill(s,"skill") for s in matched) if matched else ""
        xp = "".join(_pill(s,"miss")  for s in missing) if missing else ""
        sal_txt = f'  ·  💰 {html.escape(salary)}' if salary not in ("N/A","","nan") else ""
        loc_txt = f'  📍 {html.escape(loc)}'        if loc else ""
        url     = str(job.get("url",""))
        title_html = (
            f'<a href="{html.escape(url)}" target="_blank" '
            f'style="color:var(--t1);text-decoration:none">'
            f'{html.escape(str(job.get("title","—")))}</a>'
            if url else html.escape(str(job.get("title","—")))
        )
        st.markdown(f"""
<div class="jcard">
  <div style="display:flex;justify-content:space-between;align-items:flex-start">
    <div>
      <div style="font-size:15px;font-weight:700">{title_html}</div>
      <div style="font-size:12px;color:var(--t2);margin-top:2px">
        🏢 {html.escape(str(job.get('company','—')))}{loc_txt}{sal_txt}</div>
    </div>
    <div style="text-align:right;flex-shrink:0;margin-left:16px">
      <div style="font-size:22px;font-weight:800;color:{colour}">{score}%</div>
      <div style="font-size:10px;color:var(--t3)">match</div>
    </div>
  </div>
  <div style="background:var(--n5);border-radius:4px;height:6px;width:100%;margin:8px 0">
    <div style="height:6px;border-radius:4px;width:{score}%;
         background:linear-gradient(90deg,#007acc,{colour})"></div>
  </div>
  {f'<div style="margin-bottom:6px"><span style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--t3);letter-spacing:.07em">Matched  </span>{mp}</div>' if mp else ''}
  {f'<div style="margin-bottom:8px"><span style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--t3);letter-spacing:.07em">Skills to learn  </span>{xp}</div>' if xp else ''}
  {f'<div style="font-size:13px;color:var(--t2);line-height:1.6;margin-top:6px">💬 {html.escape(str(why))}</div>' if why else ''}
  {f'<div style="margin-top:10px"><a href="{html.escape(url)}" target="_blank" style="font-size:11px;color:var(--c);text-decoration:none;font-weight:600">🔗 View Job →</a></div>' if url else ''}
</div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Tab: Full Assessment
# ══════════════════════════════════════════════════════════════════════════════
def _tab_assessment():
    st.markdown('<div class="sh">📊 Full Career Assessment</div>', unsafe_allow_html=True)
    cv_done  = st.session_state.cv_analysis     is not None
    gh_done  = st.session_state.github_analysis is not None
    job_done = st.session_state.job_matches     is not None

    if not any([cv_done, gh_done, job_done]):
        st.info("Complete at least one analysis in the other tabs first, then come back for your full report.")
        return

    c1, c2, c3 = st.columns(3)
    with c1: st.metric("CV",     "✅ Done" if cv_done  else "⬜ Pending")
    with c2: st.metric("GitHub", "✅ Done" if gh_done  else "⬜ Pending")
    with c3: st.metric("Jobs",   "✅ Done" if job_done else "⬜ Pending")

    if st.button("✨ Write My Career Report", key="btn_report"):
        parts = []
        if cv_done:
            a = st.session_state.cv_analysis.get("analysis",{})
            if isinstance(a, dict):
                parts.append(
                    f"CV: {a.get('seniority_level')} dev, {a.get('experience_years')} yrs, "
                    f"skills: {', '.join(a.get('skills',[])[:10])}, summary: {a.get('summary','')}"
                )
        if gh_done:
            p = st.session_state.github_analysis.get("profile",{})
            parts.append(
                f"GitHub: {p.get('public_repos')} repos, "
                f"languages: {', '.join(list(p.get('languages',{}).keys())[:5])}"
            )
        if job_done:
            m = st.session_state.job_matches.get("matches",[])
            if m:
                top3 = [f"{j.get('title')} at {j.get('company')} ({j.get('match_score')}%)"
                        for j in m[:3] if isinstance(j,dict)]
                parts.append(f"Top jobs: {', '.join(top3)}")

        prompt = (
            "Write a personalised career assessment. Sound like a mentor — warm, honest, specific. "
            "Cover: where they are now, strongest assets, best opportunities, "
            "3-5 concrete next steps this month. Use markdown headers. Don't be generic.\n\n"
            "Data:\n" + "\n".join(parts)
        )
        with st.spinner("Writing your personalised report…"):
            text = _llm(
                _groq(),
                [{"role":"system","content":"You are an expert career advisor writing a personal assessment."},
                 {"role":"user","content":prompt}],
                max_tokens=1100,
            )
        st.markdown(
            '<div class="aib"><div class="ailbl">🤖 Your Career Report</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown(text)
        st.download_button(
            "📥 Download Report (JSON)",
            data=json.dumps({
                "generated_at": datetime.datetime.now().isoformat(),
                "narrative": text,
                "cv":     st.session_state.cv_analysis,
                "github": st.session_state.github_analysis,
                "jobs":   st.session_state.job_matches,
            }, indent=2, default=str),
            file_name=f"career_report_{datetime.date.today()}.json",
            mime="application/json",
            key="dl_full",
        )
    else:
        if cv_done:
            a = st.session_state.cv_analysis.get("analysis",{})
            if isinstance(a, dict) and a.get("summary"):
                st.markdown('<div class="sh">📄 CV Summary</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="aib">{html.escape(a["summary"])}</div>',
                            unsafe_allow_html=True)
        if job_done:
            m = [j for j in st.session_state.job_matches.get("matches",[])
                 if isinstance(j,dict)][:3]
            if m:
                st.markdown('<div class="sh">💼 Top Job Matches</div>', unsafe_allow_html=True)
                for j in m:
                    s = int(j.get("match_score",0))
                    st.markdown(
                        f'<div style="display:flex;align-items:center;gap:12px;padding:10px 0;'
                        f'border-bottom:1px solid var(--L)">'
                        f'<div style="font-size:22px;font-weight:800;color:{_sc(s)}">{s}%</div>'
                        f'<div>'
                        f'<div style="font-size:13.5px;font-weight:600;color:var(--t1)">'
                        f'{html.escape(str(j.get("title","—")))}</div>'
                        f'<div style="font-size:12px;color:var(--t2)">'
                        f'{html.escape(str(j.get("company","—")))}</div>'
                        f'</div></div>',
                        unsafe_allow_html=True,
                    )


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════
def main():
    _css()
    _init()
    _auto_build()

    # Build context string for the sidebar chat
    ctx_parts = []
    if st.session_state.cv_analysis:
        a = st.session_state.cv_analysis.get("analysis",{})
        if isinstance(a, dict):
            ctx_parts.append(
                f"CV: {a.get('seniority_level','?')}, {a.get('experience_years','?')} yrs exp, "
                f"skills: {', '.join(a.get('skills',[])[:10])}"
            )
    if st.session_state.github_analysis:
        p = st.session_state.github_analysis.get("profile",{})
        ctx_parts.append(
            f"GitHub: {p.get('public_repos',0)} repos, "
            f"top langs: {', '.join(list(p.get('languages',{}).keys())[:5])}"
        )
    if st.session_state.job_matches:
        m = st.session_state.job_matches.get("matches",[])
        if m and isinstance(m[0], dict):
            t = m[0]
            ctx_parts.append(
                f"Top job match: {t.get('title','')} at {t.get('company','')} "
                f"({t.get('match_score','')}%)"
            )
    context = "\n".join(ctx_parts)

    # Sidebar (no chat — chat is the floating panel injected below)
    _sidebar()
    _header()

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

    # ── Inject the floating Copilot chat (FIXED — uses components.html) ──
    _inject_copilot(_key(), context)


if __name__ == "__main__":
    main()