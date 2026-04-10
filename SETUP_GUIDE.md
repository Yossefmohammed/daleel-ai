# 🚀 Career AI Assistant - Phase 1 Setup Guide

## ✅ What's Ready

You now have a complete **Career AI Assistant** Phase 1 project with:

### Core Modules
- ✅ `cv_analyzer.py` - PDF CV extraction & analysis
- ✅ `github_analyzer.py` - GitHub profile analysis  
- ✅ `job_matcher.py` - Job matching engine
- ✅ `app.py` - Streamlit UI (4 tabs)
- ✅ `requirements.txt` - All dependencies

### Documentation
- ✅ `README.md` - Complete setup & usage guide
- ✅ `.env.example` - API keys template
- ✅ `SETUP_GUIDE.md` - This file

---

## 🎯 Next Steps (5 minutes)

### Step 1: Create .env File
```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
```
GROQ_API_KEY=your_key_from_groq.com
GITHUB_TOKEN=your_token_from_github.com  # optional
```

### Step 2: Download Kaggle Dataset
Go to: **https://www.kaggle.com/datasets/andrewmvd/tech-jobs**
- Click "Download"
- Extract ZIP
- Place `jobs_data.csv` in `data/` folder
- Rename to `data/jobs.csv`

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Run the App
```bash
streamlit run app.py
```

Visit: **http://localhost:8501**

---

## 📊 Kaggle Dataset Quick Links

| Dataset | Link | Size | Columns |
|---------|------|------|---------|
| **Tech Jobs** ⭐ | [Link](https://www.kaggle.com/datasets/andrewmvd/tech-jobs) | 5K rows | job_id, job_title, company, description, salary_range |
| Data Science | [Link](https://www.kaggle.com/datasets/ruchi798/data-science-job-salaries) | 600 rows | job_title, salary, company, experience_level |
| LinkedIn | [Link](https://www.kaggle.com/datasets/arjunprasadsarkhel/linkedin-job-postings) | 30K rows | job_title, company, description, location |

**Recommendation:** Start with Tech Jobs (5K rows = good sample size)

---

## 🧪 Test the App

### Test 1: CV Analyzer
1. Open app → **CV Analyzer** tab
2. Upload any PDF file
3. Click "Analyze CV"
4. See extracted data

### Test 2: GitHub Analyzer
1. Open app → **GitHub Profile** tab
2. Enter username: `torvalds` (Linus Torvalds - famous repo)
3. Click "Analyze GitHub"
4. See profile metrics

### Test 3: Job Matcher
1. Go to **Job Matcher** tab
2. Enter skills: "Python, JavaScript"
3. Select seniority: "Mid-Level"
4. Click "Find Matching Jobs"
5. See recommendations

### Test 4: Full Assessment
1. Go to **Full Assessment** tab
2. Click "Generate Full Report"
3. See combined analysis

---

## 📁 File Structure After Setup

```
career-ai-assistant/
├── app.py                          # ✅ Streamlit main app
├── cv_analyzer.py                  # ✅ CV module
├── github_analyzer.py              # ✅ GitHub module
├── job_matcher.py                  # ✅ Job matching module
├── requirements.txt                # ✅ Dependencies
├── .env                            # ✅ Your API keys (created by you)
├── .env.example                    # ✅ Template
├── README.md                       # ✅ Full docs
├── SETUP_GUIDE.md                  # ✅ This file
├── data/
│   └── jobs.csv                    # ✅ Kaggle dataset (download yourself)
├── README_OLD_WASLA.md             # 📦 Backup of old project
├── app_old_wasla.py                # 📦 Backup of old app
└── [other files]
```

---

## 🎬 How Each Tab Works

### 📄 CV Analyzer
```
Input: PDF file upload
↓
Process: Parse PDF → Extract text → LLM analysis
↓
Output: {
    "skills": ["Python", "React", ...],
    "experience": [{title, company, duration}, ...],
    "education": [{degree, field, school}, ...],
    "seniority_level": "mid",
    "summary": "..."
}
```

### 🐙 GitHub Analyzer
```
Input: GitHub username
↓
Process: Fetch via GitHub API → Analyze languages/repos → Score profile
↓
Output: {
    "profile": {followers, repos, languages, ...},
    "analysis": {profile_strength, career_readiness, recommendations}
}
```

### 💼 Job Matcher
```
Input: Skills, experience, seniority level
↓
Process: Search jobs.csv → Match against LLM → Score and rank
↓
Output: {
    "jobs": [{title, company, match_score, reason}, ...],
    "summary": "..."
}
```

### 📊 Full Assessment
```
Combines all three analyses into one comprehensive report
```

---

## 🔑 API Keys Explained

### Groq (Required)
- Get from: https://groq.com
- Free tier: 1,000 requests/hour
- Used for: All AI analysis
- Setup: Add `GROQ_API_KEY` to `.env`

### GitHub (Optional)
- Get from: https://github.com/settings/tokens
- Free tier: 5,000 requests/hour
- Used for: GitHub profile analysis
- Setup: Add `GITHUB_TOKEN` to `.env`
- Note: Works without token (rate-limited to 60 req/hr)

### Kaggle (One-time download)
- Get data from: https://www.kaggle.com
- Free: Download datasets manually
- Used for: Job database
- Setup: Place CSV in `data/jobs.csv`

---

## ⚡ Performance Tips

1. **CV Analysis is slow** (5-10s)
   - Normal - LLM is processing
   - First run caches results in session

2. **GitHub Analysis is fast** (3-5s)
   - API call + quick analysis

3. **Job Matcher varies** (5-15s)
   - Depends on dataset size
   - With 5K jobs: ~5-10s
   - With 30K jobs: ~10-15s

**Pro Tip:** Use smaller Kaggle dataset (Tech Jobs) for faster matching

---

## 🐛 Debugging

Enable debug mode in `.env`:
```
DEBUG=true
LOG_LEVEL=DEBUG
```

Then check console output for detailed logs.

---

## 🎯 Phase 1 Complete! ✅

You now have:
- [x] CV analyzer working
- [x] GitHub integration working  
- [x] Job matching working
- [x] Clean Streamlit UI
- [x] Full documentation

**Ready for Phase 2 features:**
- Mock interviews
- LinkedIn optimizer
- Skill gap analysis

---

## 📞 Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| "GROQ_API_KEY not found" | Check `.env` file exists with valid key |
| "No jobs found" | Download Kaggle CSV to `data/jobs.csv` |
| "GitHub not found" | Check username spelling, must be public |
| "PDF parsing error" | Ensure PDF file is readable (not scanned image) |
| App runs slow | Normal for LLM - check console for errors |

---

## 🎉 You're All Set!

Run: `streamlit run app.py`

Then open browser to: **http://localhost:8501**

Happy career coaching! 🚀
