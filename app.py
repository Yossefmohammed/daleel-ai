"""
Career AI Assistant  –  fully self-contained
=============================================
No imports from cv_analyzer.py / job_matcher.py / data_scraper.py.
All analysis logic lives here, so there are zero ImportError surprises.

Auto-scraping
─────────────
On first load (or when cache > 24 h old) the app silently scrapes
RemoteOK + Arbeitnow (both free, no API key needed) and saves to
data/jobs_combined.csv.  Scraping does NOT run on every job search.
"""

import os, re, json, html, datetime, time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
load_dotenv()

# ── page config (must be the very first Streamlit call) ────────────────────
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
html,body,[data-testid="stApp"],[data-testid="stAppViewContainer"],.main{background:var(--n)!important;font-family:var(--ff)!important;color:var(--t1)!important}
#MainMenu,header,footer,[data-testid="stToolbar"],[data-testid="stDecoration"],[data-testid="stStatusWidget"]{display:none!important}
.block-container{padding:0!important;max-width:100%!important}
section.main>div{padding:0!important}
[data-testid="stSidebar"]{background:var(--n2)!important;border-right:1px solid var(--L)!important;min-width:268px!important;max-width:268px!important}
[data-testid="stSidebar"]>div:first-child{padding:0!important}
[data-testid="stSidebar"] label,[data-testid="stSidebar"] p,[data-testid="stSidebar"] span{color:var(--t2)!important;font-size:12.5px!important}
[data-testid="stSidebar"] .stButton>button{background:transparent!important;border:1px solid var(--L2)!important;border-radius:var(--Rs)!important;color:var(--t2)!important;font-family:var(--ff)!important;font-size:12.5px!important;font-weight:500!important;padding:9px 14px!important;width:100%!important;transition:all .18s!important}
[data-testid="stSidebar"] .stButton>button:hover{background:var(--n4)!important;border-color:var(--cb)!important;color:var(--t1)!important}
[data-testid="stSidebar"] [data-testid="stMetricValue"]{color:var(--t1)!important;font-size:15px!important}
[data-testid="stSidebar"] [data-testid="stMetricLabel"]{color:var(--t3)!important;font-size:10px!important}
[data-testid="stTabs"] [data-baseweb="tab-list"]{background:var(--n2)!important;border-bottom:1px solid var(--L)!important;padding:0 28px!important;gap:2px!important}
[data-testid="stTabs"] [data-baseweb="tab"]{background:transparent!important;border:none!important;color:var(--t2)!important;font-family:var(--ff)!important;font-size:13px!important;font-weight:600!important;padding:14px 16px!important;border-bottom:2px solid transparent!important;transition:all .18s!important}
[data-testid="stTabs"] [data-baseweb="tab"]:hover{color:var(--t1)!important}
[data-testid="stTabs"] [aria-selected="true"]{color:var(--c)!important;border-bottom-color:var(--c)!important}
[data-testid="stTabPanel"]{background:transparent!important;padding:28px!important}
[data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea,[data-testid="stNumberInput"] input{background:var(--n3)!important;border:1px solid var(--L2)!important;border-radius:var(--R)!important;color:var(--t1)!important;font-family:var(--ff)!important;font-size:13.5px!important;caret-color:var(--c)!important}
[data-testid="stTextInput"] input:focus,[data-testid="stTextArea"] textarea:focus{border-color:var(--c)!important;box-shadow:0 0 0 2px var(--cd)!important;outline:none!important}
[data-testid="stTextInput"] label,[data-testid="stTextArea"] label,[data-testid="stNumberInput"] label,[data-testid="stSelectbox"] label,[data-testid="stMultiSelect"] label{color:var(--t2)!important;font-size:12.5px!important;font-weight:600!important}
[data-testid="stFileUploader"]{background:var(--n3)!important;border:1px dashed var(--cb)!important;border-radius:var(--R)!important;padding:16px!important}
[data-testid="stSelectbox"] [data-baseweb="select"]>div,[data-testid="stMultiSelect"] [data-baseweb="select"]>div{background:var(--n3)!important;border:1px solid var(--L2)!important;border-radius:var(--R)!important;color:var(--t1)!important}
.stButton>button{background:linear-gradient(135deg,#007acc,#00d9ff)!important;border:none!important;border-radius:var(--R)!important;color:var(--n)!important;font-family:var(--ff)!important;font-size:13.5px!important;font-weight:700!important;padding:11px 22px!important;transition:all .2s!important;box-shadow:0 4px 14px rgba(0,217,255,.25)!important}
.stButton>button:hover{transform:translateY(-2px)!important;box-shadow:0 6px 20px rgba(0,217,255,.4)!important}
.stButton>button:active{transform:translateY(0)!important}
.stButton>button:disabled{opacity:.4!important;transform:none!important}
[data-testid="stMetric"]{background:var(--n3)!important;border:1px solid var(--L)!important;border-radius:var(--R)!important;padding:14px 18px!important}
[data-testid="stMetricLabel"]{color:var(--t3)!important;font-size:11px!important}
[data-testid="stMetricValue"]{color:var(--t1)!important;font-size:22px!important}
[data-testid="stExpander"]{background:var(--n3)!important;border:1px solid var(--L)!important;border-radius:var(--R)!important}
[data-testid="stExpander"] summary{color:var(--t2)!important;font-size:12.5px!important}
[data-testid="stChatInput"]{background:var(--n3)!important;border:1px solid var(--L2)!important;border-radius:var(--R)!important;margin:0 0 12px!important}
[data-testid="stChatInput"]:focus-within{border-color:var(--c)!important;box-shadow:0 0 0 2px var(--cd)!important}
[data-testid="stChatInput"] textarea{background:transparent!important;border:none!important;color:var(--t1)!important;font-family:var(--ff)!important;font-size:13.5px!important;caret-color:var(--c)!important}
[data-testid="stChatInput"] textarea::placeholder{color:var(--t3)!important}
[data-testid="stChatInput"] button{background:linear-gradient(135deg,#007acc,#00d9ff)!important;border:none!important;border-radius:9px!important;color:var(--n)!important}
[data-testid="stChatMessageContent"]{color:var(--t1)!important;font-size:13.5px!important;line-height:1.7!important;font-family:var(--ff)!important}
[data-testid="stChatMessage"]{background:var(--n3)!important;border:1px solid var(--L)!important;border-radius:16px!important;padding:4px 8px!important;margin:6px 0!important}
.stProgress>div>div{background:var(--c)!important}
[data-testid="stDownloadButton"]>button{background:transparent!important;border:1px solid var(--L2)!important;box-shadow:none!important;color:var(--t2)!important}
[data-testid="stDownloadButton"]>button:hover{border-color:var(--cb)!important;color:var(--c)!important;transform:none!important;box-shadow:none!important}
hr{border-color:var(--L)!important}
.hdr{background:var(--n2);border-bottom:1px solid var(--L);padding:0 28px;height:64px;display:flex;align-items:center;justify-content:space-between}
.hgem{width:42px;height:42px;border-radius:12px;background:linear-gradient(135deg,#007acc,#00d9ff);display:flex;align-items:center;justify-content:center;font-size:20px;box-shadow:0 4px 14px rgba(0,217,255,.25)}
.badge{font-size:10px;font-weight:600;padding:4px 10px;border-radius:20px;border:1px solid var(--L2);color:var(--t3);background:var(--n3)}
.badge.live{background:rgba(52,211,153,.10);border-color:rgba(52,211,153,.25);color:#34d399}
.pill{display:inline-block;background:var(--cd);border:1px solid var(--cb);color:var(--c);font-size:11px;font-weight:600;padding:3px 10px;border-radius:20px;margin:3px 2px;font-family:var(--fm)}
.pill.tech{background:rgba(251,191,36,.08);border-color:rgba(251,191,36,.25);color:#fbbf24}
.pill.miss{background:rgba(248,113,113,.08);border-color:rgba(248,113,113,.25);color:#f87171}
.aib{background:var(--n3);border:1px solid var(--L);border-left:3px solid var(--c);border-radius:0 var(--R) var(--R) var(--R);padding:16px 20px;font-size:13.5px;line-height:1.75;color:var(--t1);margin:12px 0}
.ailbl{font-size:10px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;color:var(--c);margin-bottom:8px}
.jcard{background:var(--n3);border:1px solid var(--L);border-radius:var(--R);padding:20px 22px;margin-bottom:14px;transition:border-color .18s}
.jcard:hover{border-color:var(--cb)}
.sh{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--t3);margin:22px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--L)}
.sdiv{height:1px;background:var(--L);margin:12px 0}
.slbl{font-size:10px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;color:var(--t3);padding-bottom:6px}
</style>""", unsafe_allow_html=True)


# ── API key helpers ────────────────────────────────────────────────────────
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
# Job database
# ══════════════════════════════════════════════════════════════════════════════
DATA_DIR    = Path("data")
COMBINED    = DATA_DIR / "jobs_combined.csv"
CACHE_HOURS = 24

def _scrape_remoteok(limit=120):
    import requests
    try:
        r = requests.get("https://remoteok.com/api",
                         headers={"User-Agent":"CareerAI/1.0"}, timeout=12)
        r.raise_for_status()
        jobs = []
        for j in r.json()[:limit]:
            if not isinstance(j, dict) or "id" not in j: continue
            jobs.append({"title": j.get("position") or j.get("title",""),
                         "company": j.get("company",""),
                         "description": str(j.get("description") or j.get("tags",""))[:400],
                         "location": j.get("location","Remote"),
                         "salary": str(j.get("salary","")), "url": j.get("url",""),
                         "source": "RemoteOK"})
        return jobs
    except Exception: return []

def _scrape_arbeitnow(limit=120):
    import requests
    jobs = []
    try:
        for page in range(1, 4):
            r = requests.get("https://www.arbeitnow.com/api/job-board-api",
                             params={"page": page},
                             headers={"Accept":"application/json"}, timeout=12)
            r.raise_for_status()
            data = r.json().get("data", [])
            if not data: break
            for j in data:
                jobs.append({"title": j.get("title",""), "company": j.get("company_name",""),
                              "description": str(j.get("description") or "")[:400],
                              "location": j.get("location",""), "salary": "",
                              "url": j.get("url",""), "source": "Arbeitnow"})
            if len(jobs) >= limit: break
        return jobs[:limit]
    except Exception: return []

def _load_local_csv():
    import pandas as pd
    col_map = {"job_title":"title","position":"title","role":"title",
               "company_name":"company","employer":"company",
               "job_description":"description","responsibilities":"description",
               "job_location":"location","city":"location",
               "salary_in_usd":"salary","salary_estimate":"salary",
               "annual_salary_usd":"salary","avg_salary":"salary"}
    candidates = [DATA_DIR/"jobs.csv", Path("docs")/"ai_jobs_market_2025_2026.csv"]
    candidates += list(Path("docs").glob("*.csv"))
    for p in candidates:
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

def _cache_fresh():
    if not COMBINED.exists(): return False
    age = (datetime.datetime.now() -
           datetime.datetime.fromtimestamp(COMBINED.stat().st_mtime)).total_seconds()
    return age < CACHE_HOURS * 3600

def _save_combined(jobs):
    import pandas as pd
    DATA_DIR.mkdir(exist_ok=True)
    pd.DataFrame(jobs).to_csv(str(COMBINED), index=False)

def _load_combined():
    import pandas as pd
    if not COMBINED.exists(): return []
    try:
        df = pd.read_csv(str(COMBINED), on_bad_lines="skip", nrows=3000)
        return df.fillna("").to_dict("records")
    except Exception: return []

def build_job_database(status_ph=None):
    def say(m):
        if status_ph: status_ph.info(m)
    all_jobs = []
    say("📡 Scraping RemoteOK…")
    rok = _scrape_remoteok(); all_jobs.extend(rok)
    say(f"✅ RemoteOK: {len(rok)} jobs. Trying Arbeitnow…")
    anow = _scrape_arbeitnow(); all_jobs.extend(anow)
    say(f"✅ Arbeitnow: {len(anow)} jobs. Checking local CSV…")
    local = _load_local_csv(); all_jobs.extend(local)
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
def _pdf_text(path):
    from pypdf import PdfReader
    return "\n".join(p.extract_text() or "" for p in PdfReader(path).pages)

def analyze_cv(pdf_path):
    text = _pdf_text(pdf_path)
    if not text.strip():
        return {"success": False,
                "error": "Could not read text from this PDF. Make sure it's not a scanned image."}
    client = _groq()
    prompt = (
        "Analyze this CV. Return ONLY a valid JSON object — no markdown, no text outside the JSON.\n\n"
        '{"name":"candidate name or empty","summary":"2-3 sentence honest professional summary",'
        '"seniority_level":"Junior|Mid-Level|Senior|Lead","experience_years":<integer>,'
        '"skills":["skill1"],"technologies":["framework"],'
        '"experience":[{"title":"Job Title","company":"Company","duration":"2021-2023"}],'
        '"education":[{"degree":"BSc","field":"CS","school":"University"}],'
        '"strengths":["strength1"],"improvement_areas":["area1"]}\n\nCV:\n' + text[:3500]
    )
    raw = _llm(client, [{"role":"user","content":prompt}], max_tokens=1200)
    parsed = _parse_json(raw)
    if not parsed or "skills" not in parsed:
        return {"success":False,"error":"AI could not parse your CV. Try a cleaner, text-based PDF."}
    return {"success":True,"analysis":parsed}


# ══════════════════════════════════════════════════════════════════════════════
# GitHub analysis
# ══════════════════════════════════════════════════════════════════════════════
def analyze_github(username):
    import requests
    hdrs = {"Accept":"application/vnd.github+json"}
    tok = _gh_token()
    if tok: hdrs["Authorization"] = f"Bearer {tok}"
    base = f"https://api.github.com/users/{username}"
    try:
        u = requests.get(base, headers=hdrs, timeout=10)
        if u.status_code == 404:
            return {"success":False,"error":f"User '{username}' not found on GitHub."}
        u.raise_for_status(); user = u.json()
    except Exception as e:
        return {"success":False,"error":f"GitHub API error: {e}"}
    try:
        rr = requests.get(f"{base}/repos", headers=hdrs,
                          params={"per_page":30,"sort":"pushed"}, timeout=10)
        repos = rr.json() if rr.ok else []
    except Exception: repos = []
    lang_counts = {}
    for repo in repos[:20]:
        if repo.get("language"):
            lang_counts[repo["language"]] = lang_counts.get(repo["language"],0)+1
    profile = {"login":user.get("login",""),"name":user.get("name",""),
               "bio":user.get("bio",""),"followers":user.get("followers",0),
               "following":user.get("following",0),"public_repos":user.get("public_repos",0),
               "languages":dict(sorted(lang_counts.items(),key=lambda x:-x[1])[:8]),
               "top_repos":[{"name":r.get("name"),"stars":r.get("stargazers_count",0),
                              "description":r.get("description","")} for r in repos[:5]]}
    client = _groq()
    prompt = (
        "You are a tech recruiter. Assess this GitHub profile.\n"
        "Return ONLY valid JSON — no markdown.\n\n"
        '{"profile_score":<integer 0-100>,"summary":"3-4 honest sentences",'
        '"strengths":["point1","point2"],"recommendations":["tip1","tip2","tip3"]}\n\n'
        f"Username: {profile['login']}, Bio: {profile.get('bio','—')}, "
        f"Repos: {profile['public_repos']}, Followers: {profile['followers']}, "
        f"Top languages: {', '.join(profile['languages'].keys())}, "
        f"Top repos: {json.dumps(profile['top_repos'][:3])}"
    )
    raw = _llm(client, [{"role":"user","content":prompt}], max_tokens=600)
    return {"success":True,"profile":profile,"analysis":_parse_json(raw)}


# ══════════════════════════════════════════════════════════════════════════════
# Job matching
# ══════════════════════════════════════════════════════════════════════════════
def match_jobs(user_profile, limit=8):
    jobs = _load_combined()
    if not jobs:
        return {"success":False,
                "error":"Job database is empty. Click Refresh Job Database in the sidebar."}
    skills = [s.lower() for s in user_profile.get("skills",[])]
    roles  = [r.lower() for r in user_profile.get("interested_roles",[])]
    def _score(j):
        blob = (str(j.get("title",""))+" "+str(j.get("description",""))).lower()
        s = sum(2 for sk in skills if sk in blob)
        s += sum(1 for ro in roles for w in ro.split() if len(w)>3 and w in blob)
        return s
    top25 = sorted(jobs,key=_score,reverse=True)[:25]
    compact = [{"title":str(j.get("title",""))[:60],"company":str(j.get("company",""))[:40],
                "location":str(j.get("location",""))[:30],
                "description":str(j.get("description",""))[:200],
                "salary":str(j.get("salary",""))[:30]} for j in top25]
    client = _groq()
    prompt = (
        f"You are a career advisor. Return ONLY a valid JSON array of top {limit} best-matching jobs.\n"
        "No markdown. Each object must have exactly:\n"
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
    if isinstance(matches,dict) and "jobs" in matches: matches=matches["jobs"]
    if not isinstance(matches,list): matches=[]
    return {"success":True,"matches":matches,"total_in_db":len(jobs),"candidates_evaluated":len(compact)}


# ══════════════════════════════════════════════════════════════════════════════
# Session state
# ══════════════════════════════════════════════════════════════════════════════
def _init():
    for k,v in {"cv_analysis":None,"github_analysis":None,"job_matches":None,
                "chat_messages":[],"db_checked":False}.items():
        if k not in st.session_state: st.session_state[k]=v


# ── Render helpers ─────────────────────────────────────────────────────────
def _pill(t, k="skill"):
    cls={"skill":"pill","tech":"pill tech","miss":"pill miss"}.get(k,"pill")
    return f'<span class="{cls}">{html.escape(str(t))}</span>'
def _pills(items,k="skill"):
    if not items: return '<span style="color:var(--t3);font-size:12px">none found</span>'
    return "".join(_pill(i,k) for i in items)
def _sc(s):
    if s>=80: return "#34d399"
    if s>=60: return "#00d9ff"
    if s>=40: return "#fbbf24"
    return "#f87171"
def _dot(col="#00d9ff"):
    return f'<div style="width:9px;height:9px;border-radius:50%;background:{col};margin-top:4px;flex-shrink:0"></div>'


# ══════════════════════════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════════════════════════
def _sidebar():
    with st.sidebar:
        st.markdown(
            '<div style="padding:20px 16px 14px;border-bottom:1px solid rgba(255,255,255,.06)">'
            '<div style="display:flex;align-items:center;gap:12px">'
            '<div style="width:40px;height:40px;border-radius:12px;background:linear-gradient(135deg,#007acc,#00d9ff);'
            'display:flex;align-items:center;justify-content:center;font-size:20px;box-shadow:0 4px 14px rgba(0,217,255,.25)">🎯</div>'
            '<div><div style="font-size:15px;font-weight:800;color:#e8eeff;letter-spacing:-.3px">Career AI</div>'
            '<div style="font-size:10px;color:#00d9ff;background:rgba(0,217,255,.08);padding:2px 8px;border-radius:20px;'
            'border:1px solid rgba(0,217,255,.2);display:inline-block;font-weight:600;margin-top:2px">Phase 1 · MVP</div>'
            '</div></div></div>', unsafe_allow_html=True)
        st.markdown("<div style='padding:14px 14px 0'>", unsafe_allow_html=True)
        st.markdown('<div class="slbl">Status</div>', unsafe_allow_html=True)
        c1,c2=st.columns(2)
        with c1: st.metric("Groq AI","🟢 Ready" if _key() else "🔴 Missing")
        with c2: st.metric("GitHub","🟢" if _gh_token() else "⚪ Optional")
        cnt=len(_load_combined())
        st.metric("Job Database",f"🟢 {cnt:,} jobs" if cnt else "🔴 Empty")
        if not _key(): st.error("GROQ_API_KEY missing.\nAdd to .env or Streamlit secrets.")
        st.markdown('<div class="sdiv"></div>', unsafe_allow_html=True)
        st.markdown('<div class="slbl">Job Database</div>', unsafe_allow_html=True)
        if COMBINED.exists():
            age_h=(datetime.datetime.now()-datetime.datetime.fromtimestamp(COMBINED.stat().st_mtime)).total_seconds()/3600
            st.caption(f"Cache: {age_h:.0f}h old  ·  refreshes every {CACHE_HOURS}h")
        if st.button("🔄 Refresh Job Database",key="sb_ref",use_container_width=True):
            ph=st.empty()
            try:
                n=build_job_database(ph); ph.success(f"✅ Done — {n:,} jobs saved")
            except Exception as e: ph.error(f"❌ {e}")
        st.markdown('<div class="sdiv"></div>', unsafe_allow_html=True)
        st.markdown('<div class="slbl">Your Progress</div>', unsafe_allow_html=True)
        for lbl,done in [("📄 CV analyzed",st.session_state.cv_analysis is not None),
                          ("🐙 GitHub analyzed",st.session_state.github_analysis is not None),
                          ("💼 Jobs matched",st.session_state.job_matches is not None)]:
            col="#34d399" if done else "var(--t3)"
            st.markdown(f'<div style="display:flex;align-items:center;gap:8px;padding:4px 0;font-size:12.5px;color:{col}">{"✅" if done else "⬜"} {lbl}</div>',unsafe_allow_html=True)
        if st.button("🗑 Clear Session",key="sb_clear",use_container_width=True):
            st.session_state.cv_analysis=None; st.session_state.github_analysis=None
            st.session_state.job_matches=None; st.session_state.chat_messages=[]; st.rerun()
        st.markdown('<div class="sdiv"></div>', unsafe_allow_html=True)
        if any([st.session_state.cv_analysis,st.session_state.github_analysis,st.session_state.job_matches]):
            st.download_button("📥 Download Report",
                data=json.dumps({"generated_at":datetime.datetime.now().isoformat(),
                                  "cv":st.session_state.cv_analysis,
                                  "github":st.session_state.github_analysis,
                                  "jobs":st.session_state.job_matches},indent=2,default=str),
                file_name=f"career_report_{datetime.date.today()}.json",
                mime="application/json",use_container_width=True,key="sb_dl")
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
**Job database** — optional  
Save any Kaggle jobs CSV as `data/jobs.csv`.  
App auto-scrapes RemoteOK + Arbeitnow on first load.
""")
        st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Header
# ══════════════════════════════════════════════════════════════════════════════
def _header():
    ready=any([st.session_state.cv_analysis,st.session_state.github_analysis,st.session_state.job_matches])
    st.markdown(
        '<div class="hdr"><div style="display:flex;align-items:center;gap:14px">'
        '<div class="hgem">🎯</div>'
        '<div><div style="font-size:17px;font-weight:800;color:var(--t1);letter-spacing:-.3px">Career AI Assistant</div>'
        '<div style="font-size:11px;color:var(--t3);margin-top:2px">CV · GitHub · Job Matching · Career Chat</div>'
        '</div></div><div style="display:flex;gap:8px">'
        +('<div class="badge live">● Session Active</div>' if ready else '<div class="badge">○ No Data Yet</div>')
        +'<div class="badge">Groq · LLaMA 3.3</div></div></div>',unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Tab: CV Analyzer
# ══════════════════════════════════════════════════════════════════════════════
def _tab_cv():
    st.markdown('<div class="sh">📄 CV Analyzer</div>',unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t2);font-size:13px;margin-bottom:18px">Upload your PDF and I\'ll give you a plain-English breakdown — skills, experience, strengths, and what to work on.</p>',unsafe_allow_html=True)
    cu,cb=st.columns([3,1])
    with cu: f=st.file_uploader("Choose your CV (PDF)",type=["pdf"],key="cv_file")
    with cb:
        st.write(""); st.write("")
        go=st.button("🔍 Analyze CV",key="btn_cv",use_container_width=True,disabled=f is None)
    if go and f:
        if not _key(): return
        with st.spinner("Reading your CV…"):
            tmp=f"temp_{f.name}"
            with open(tmp,"wb") as fh: fh.write(f.getbuffer())
            res=analyze_cv(tmp); os.remove(tmp)
            if res.get("success"): st.session_state.cv_analysis=res
            else: st.error(f"❌ {res.get('error')}"); return
    if not st.session_state.cv_analysis:
        st.info("Upload your CV and click **Analyze CV** to get started."); return
    a=st.session_state.cv_analysis.get("analysis",{})
    if isinstance(a,str): a=_parse_json(a) or {}
    c1,c2,c3=st.columns(3)
    with c1: st.metric("Seniority",a.get("seniority_level","—"))
    with c2: st.metric("Experience",f"{a.get('experience_years','—')} yrs")
    with c3: st.metric("Skills",len(a.get("skills",[])))
    if a.get("summary"):
        st.markdown(f'<div class="aib"><div class="ailbl">🤖 AI Summary</div>{html.escape(str(a["summary"]))}</div>',unsafe_allow_html=True)
    if a.get("skills") or a.get("technologies"):
        st.markdown('<div class="sh">Skills & Technologies</div>',unsafe_allow_html=True)
        st.markdown(_pills(a.get("skills",[]),"skill")+_pills(a.get("technologies",[]),"tech"),unsafe_allow_html=True)
    if a.get("experience"):
        st.markdown('<div class="sh">Work Experience</div>',unsafe_allow_html=True)
        for e in a["experience"]:
            st.markdown(f'<div style="display:flex;gap:12px;align-items:flex-start;margin-bottom:10px">{_dot()}'
                        f'<div><div style="font-size:13.5px;font-weight:600;color:var(--t1)">{html.escape(str(e.get("title","—")))}</div>'
                        f'<div style="font-size:12px;color:var(--t2)">{html.escape(str(e.get("company","—")))} · {html.escape(str(e.get("duration","")))}</div>'
                        f'</div></div>',unsafe_allow_html=True)
    if a.get("education"):
        st.markdown('<div class="sh">Education</div>',unsafe_allow_html=True)
        for e in a["education"]:
            st.markdown(f'<div style="display:flex;gap:12px;align-items:flex-start;margin-bottom:10px">{_dot("#34d399")}'
                        f'<div><div style="font-size:13.5px;font-weight:600;color:var(--t1)">{html.escape(str(e.get("degree","")))}{" "+html.escape(str(e.get("field","")))}</div>'
                        f'<div style="font-size:12px;color:var(--t2)">{html.escape(str(e.get("school","—")))}</div>'
                        f'</div></div>',unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        if a.get("strengths"):
            st.markdown('<div class="sh">💪 Strengths</div>',unsafe_allow_html=True)
            for s in a["strengths"]: st.markdown(f'<div style="color:var(--t2);font-size:13px;padding:3px 0">✅ {html.escape(str(s))}</div>',unsafe_allow_html=True)
    with c2:
        if a.get("improvement_areas"):
            st.markdown('<div class="sh">🎯 To Improve</div>',unsafe_allow_html=True)
            for g in a["improvement_areas"]: st.markdown(f'<div style="color:var(--t2);font-size:13px;padding:3px 0">→ {html.escape(str(g))}</div>',unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Tab: GitHub
# ══════════════════════════════════════════════════════════════════════════════
def _tab_github():
    st.markdown('<div class="sh">🐙 GitHub Profile Analysis</div>',unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t2);font-size:13px;margin-bottom:18px">Enter any public GitHub username for an honest, plain-English assessment with a score and tips.</p>',unsafe_allow_html=True)
    ci,cb=st.columns([3,1])
    with ci: uname=st.text_input("GitHub Username",placeholder="e.g. torvalds",key="gh_username")
    with cb:
        st.write(""); st.write("")
        go=st.button("🔍 Analyze",key="btn_gh",use_container_width=True,disabled=not (uname or "").strip())
    if go and (uname or "").strip():
        if not _key(): return
        with st.spinner(f"Fetching @{uname.strip()}…"):
            res=analyze_github(uname.strip())
            if res.get("success"): st.session_state.github_analysis=res
            else:
                st.error(f"❌ {res.get('error')}")
                st.info("Make sure the username is correct and the profile is public.")
                return
    if not st.session_state.github_analysis:
        st.info("Enter a GitHub username and click **Analyze**."); return
    data=st.session_state.github_analysis; profile=data.get("profile",{}); analysis=data.get("analysis",{})
    if isinstance(analysis,str): analysis=_parse_json(analysis) or {}
    c1,c2,c3,c4=st.columns(4)
    with c1: st.metric("Followers",profile.get("followers",0))
    with c2: st.metric("Public Repos",profile.get("public_repos",0))
    with c3: st.metric("Following",profile.get("following",0))
    score=analysis.get("profile_score","—") if isinstance(analysis,dict) else "—"
    with c4: st.metric("Profile Score",f"{score}/100" if str(score).isdigit() else score)
    summary=analysis.get("summary","") if isinstance(analysis,dict) else str(analysis)
    if summary:
        st.markdown(f'<div class="aib"><div class="ailbl">🤖 AI Assessment</div>{html.escape(str(summary))}</div>',unsafe_allow_html=True)
    langs=profile.get("languages",{})
    if langs:
        st.markdown('<div class="sh">Top Languages</div>',unsafe_allow_html=True)
        st.bar_chart(langs)
    recs=analysis.get("recommendations",[]) if isinstance(analysis,dict) else []
    if recs:
        st.markdown('<div class="sh">💡 Recommendations</div>',unsafe_allow_html=True)
        for r in recs: st.markdown(f'<div style="color:var(--t2);font-size:13px;padding:4px 0">→ {html.escape(str(r))}</div>',unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Tab: Job Matcher
# ══════════════════════════════════════════════════════════════════════════════
def _tab_jobs():
    st.markdown('<div class="sh">💼 Job Matcher</div>',unsafe_allow_html=True)
    cnt=len(_load_combined())
    if cnt==0:
        st.warning("**Job database is empty.** Click **🔄 Refresh Job Database** in the sidebar to auto-scrape free jobs.")
    else:
        st.markdown(f'<p style="color:var(--t2);font-size:13px;margin-bottom:18px">Searching <strong style="color:var(--c)">{cnt:,} jobs</strong>. Fill in your profile and I\'ll rank the best fits and explain each one.</p>',unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        sr=st.text_area("Your Skills (one per line)",placeholder="Python\nReact\nSQL",height=120,key="js_skills")
        exp=st.number_input("Years of Experience",0,50,2,key="js_exp")
    with c2:
        sen=st.selectbox("Seniority Level",["Junior","Mid-Level","Senior","Lead","Principal"],key="js_sen")
        roles=st.multiselect("Interested Roles",
            ["Full Stack Developer","Backend Engineer","Frontend Developer","Data Scientist",
             "ML Engineer","DevOps Engineer","Product Manager","Mobile Developer","Cloud Architect"],key="js_roles")
    go=st.button("🔍 Find My Best Jobs",key="btn_jobs",disabled=(cnt==0))
    if go:
        if not _key(): return
        skills=[s.strip() for s in sr.split("\n") if s.strip()]
        if not skills: st.warning("Please enter at least one skill."); return
        with st.spinner("Scanning jobs and ranking with AI…"):
            res=match_jobs({"skills":skills,"experience_years":int(exp),
                            "seniority_level":sen.lower().replace("-","_"),"interested_roles":roles})
        if res.get("success"): st.session_state.job_matches=res
        else: st.error(f"❌ {res.get('error')}"); return
    if not st.session_state.job_matches:
        if cnt>0: st.info("Fill in your profile and click **Find My Best Jobs**."); return
        return
    res=st.session_state.job_matches; matches=res.get("matches",[]); total=res.get("total_in_db","?"); evald=res.get("candidates_evaluated","?")
    if not matches: st.warning("No matches found. Try broadening your skills."); return
    st.markdown(f'<div class="aib"><div class="ailbl">Results</div>Out of <strong>{total:,}</strong> jobs, the AI shortlisted <strong>{evald}</strong> candidates and picked these <strong>{len(matches)}</strong> best fits for you.</div>',unsafe_allow_html=True)
    for job in matches:
        if not isinstance(job,dict): continue
        score=int(job.get("match_score",0)); colour=_sc(score)
        matched=job.get("matched_skills",[]); missing=job.get("missing_skills",[])
        why=job.get("why_good_fit",""); salary=str(job.get("salary","")); loc=str(job.get("location",""))
        mp="".join(_pill(s,"skill") for s in matched) if matched else ""
        xp="".join(_pill(s,"miss") for s in missing) if missing else ""
        sal_txt=f'  ·  💰 {html.escape(salary)}' if salary not in ("N/A","","nan") else ""
        loc_txt=f'  📍 {html.escape(loc)}' if loc else ""
        st.markdown(f"""
<div class="jcard">
  <div style="display:flex;justify-content:space-between;align-items:flex-start">
    <div><div style="font-size:15px;font-weight:700;color:var(--t1)">{html.escape(str(job.get('title','—')))}</div>
    <div style="font-size:12px;color:var(--t2);margin-top:2px">🏢 {html.escape(str(job.get('company','—')))}{loc_txt}{sal_txt}</div></div>
    <div style="text-align:right;flex-shrink:0;margin-left:16px">
      <div style="font-size:22px;font-weight:800;color:{colour}">{score}%</div>
      <div style="font-size:10px;color:var(--t3)">match</div></div></div>
  <div style="background:var(--n5);border-radius:4px;height:6px;width:100%;margin:8px 0">
    <div style="height:6px;border-radius:4px;width:{score}%;background:linear-gradient(90deg,#007acc,{colour})"></div></div>
  {f'<div style="margin-bottom:6px"><span style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--t3);letter-spacing:.07em">Matched  </span>{mp}</div>' if mp else ""}
  {f'<div style="margin-bottom:8px"><span style="font-size:10px;font-weight:700;text-transform:uppercase;color:var(--t3);letter-spacing:.07em">Skills to learn  </span>{xp}</div>' if xp else ""}
  {f'<div style="font-size:13px;color:var(--t2);line-height:1.6;margin-top:6px">💬 {html.escape(str(why))}</div>' if why else ""}
</div>""",unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Tab: Career Chat
# ══════════════════════════════════════════════════════════════════════════════
def _tab_chat():
    st.markdown('<div class="sh">💬 Career Chat</div>',unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t2);font-size:13px;margin-bottom:18px">Ask me anything — interview prep, which skills to learn, salary negotiation, career pivots. I\'ll use your data if you\'ve already run any analyses.</p>',unsafe_allow_html=True)
    if not st.session_state.chat_messages:
        starters=["How can I improve my CV?","What skills should I learn next?","How do I negotiate my salary?","Am I ready for a senior role?"]
        cols=st.columns(len(starters))
        for col,q in zip(cols,starters):
            with col:
                if st.button(q,key=f"chip_{q[:12]}",use_container_width=True):
                    st.session_state.chat_messages.append({"role":"user","content":q}); st.rerun()
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"],avatar="🧑" if msg["role"]=="user" else "🎯"): st.markdown(msg["content"])
    user_input=st.chat_input("Ask me anything about your career…")
    if user_input and user_input.strip():
        q=user_input.strip()
        st.session_state.chat_messages.append({"role":"user","content":q})
        ctx=[]
        if st.session_state.cv_analysis:
            a=st.session_state.cv_analysis.get("analysis",{})
            if isinstance(a,dict): ctx.append(f"CV: {a.get('seniority_level','?')}, {a.get('experience_years','?')} yrs, skills: {', '.join(a.get('skills',[])[:10])}")
        if st.session_state.github_analysis:
            p=st.session_state.github_analysis.get("profile",{})
            ctx.append(f"GitHub: {p.get('public_repos',0)} repos, languages: {', '.join(list(p.get('languages',{}).keys())[:5])}")
        if st.session_state.job_matches:
            m=st.session_state.job_matches.get("matches",[])
            if m and isinstance(m[0],dict):
                t=m[0]; ctx.append(f"Top job: {t.get('title','')} at {t.get('company','')} ({t.get('match_score','')}%)")
        system=("You are a warm, expert career advisor. Give honest, specific, actionable advice in a conversational tone. "
                "Like a smart mentor, not a chatbot. Use bullet points only for lists of 3+. Never say 'As an AI'. Be direct."
                +(f"\n\nUser context:\n"+"\n".join(ctx) if ctx else ""))
        messages=[{"role":"system","content":system}]
        for m in st.session_state.chat_messages[-12:]: messages.append({"role":m["role"],"content":m["content"]})
        with st.chat_message("assistant",avatar="🎯"):
            with st.spinner("Thinking…"):
                reply=_llm(_groq(),messages,max_tokens=700)
            st.markdown(reply)
            st.session_state.chat_messages.append({"role":"assistant","content":reply})


# ══════════════════════════════════════════════════════════════════════════════
# Tab: Full Assessment
# ══════════════════════════════════════════════════════════════════════════════
def _tab_assessment():
    st.markdown('<div class="sh">📊 Full Career Assessment</div>',unsafe_allow_html=True)
    cv_done=st.session_state.cv_analysis is not None
    gh_done=st.session_state.github_analysis is not None
    job_done=st.session_state.job_matches is not None
    if not any([cv_done,gh_done,job_done]):
        st.info("Complete at least one analysis in the other tabs first."); return
    c1,c2,c3=st.columns(3)
    with c1: st.metric("CV","✅ Done" if cv_done else "⬜ Pending")
    with c2: st.metric("GitHub","✅ Done" if gh_done else "⬜ Pending")
    with c3: st.metric("Jobs","✅ Done" if job_done else "⬜ Pending")
    if st.button("✨ Write My Career Report",key="btn_report"):
        parts=[]
        if cv_done:
            a=st.session_state.cv_analysis.get("analysis",{})
            if isinstance(a,dict): parts.append(f"CV: {a.get('seniority_level')} dev, {a.get('experience_years')} yrs, skills: {', '.join(a.get('skills',[])[:10])}, summary: {a.get('summary','')}")
        if gh_done:
            p=st.session_state.github_analysis.get("profile",{})
            parts.append(f"GitHub: {p.get('public_repos')} repos, languages: {', '.join(list(p.get('languages',{}).keys())[:5])}")
        if job_done:
            m=st.session_state.job_matches.get("matches",[])
            if m:
                top3=[f"{j.get('title')} at {j.get('company')} ({j.get('match_score')}%)" for j in m[:3] if isinstance(j,dict)]
                parts.append(f"Top jobs: {', '.join(top3)}")
        prompt=("Write a personalised career assessment. Sound like a mentor — warm, honest, specific. "
                "Cover: where they are now, strongest assets, best opportunities, 3-5 concrete next steps this month. "
                "Use markdown headers. Don't be generic.\n\nData:\n"+"\n".join(parts))
        with st.spinner("Writing your personalised report…"):
            text=_llm(_groq(),[{"role":"system","content":"You are an expert career advisor writing a personal assessment."},
                               {"role":"user","content":prompt}],max_tokens=1100)
        st.markdown('<div class="aib"><div class="ailbl">🤖 Your Career Report</div></div>',unsafe_allow_html=True)
        st.markdown(text)
        st.download_button("📥 Download Report (JSON)",
            data=json.dumps({"generated_at":datetime.datetime.now().isoformat(),"narrative":text,
                              "cv":st.session_state.cv_analysis,"github":st.session_state.github_analysis,
                              "jobs":st.session_state.job_matches},indent=2,default=str),
            file_name=f"career_report_{datetime.date.today()}.json",mime="application/json",key="dl_full")
    else:
        if cv_done:
            a=st.session_state.cv_analysis.get("analysis",{})
            if isinstance(a,dict) and a.get("summary"):
                st.markdown('<div class="sh">📄 CV Summary</div>',unsafe_allow_html=True)
                st.markdown(f'<div class="aib">{html.escape(a["summary"])}</div>',unsafe_allow_html=True)
        if job_done:
            m=[j for j in st.session_state.job_matches.get("matches",[]) if isinstance(j,dict)][:3]
            if m:
                st.markdown('<div class="sh">💼 Top Job Matches</div>',unsafe_allow_html=True)
                for j in m:
                    s=int(j.get("match_score",0))
                    st.markdown(f'<div style="display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid var(--L)">'
                                f'<div style="font-size:22px;font-weight:800;color:{_sc(s)}">{s}%</div>'
                                f'<div><div style="font-size:13.5px;font-weight:600;color:var(--t1)">{html.escape(str(j.get("title","—")))}</div>'
                                f'<div style="font-size:12px;color:var(--t2)">{html.escape(str(j.get("company","—")))}</div></div></div>',unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════
def main():
    _css(); _init()
    _auto_build()   # scrape on first load if cache stale
    _sidebar(); _header()
    t1,t2,t3,t4,t5=st.tabs(["📄  CV Analyzer","🐙  GitHub Profile","💼  Job Matcher","💬  Career Chat","📊  Full Assessment"])
    with t1: _tab_cv()
    with t2: _tab_github()
    with t3: _tab_jobs()
    with t4: _tab_chat()
    with t5: _tab_assessment()

if __name__=="__main__":
    main()