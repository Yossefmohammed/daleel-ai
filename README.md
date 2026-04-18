# 🧭 Daleel AI – Intelligent Career Platform

> **Phase 1 Security & Stability Update** - Production-ready with rate limiting, persistent storage, and hardened security.

[![Status](https://img.shields.io/badge/Phase%201-Complete-brightgreen)](.) 
[![Security](https://img.shields.io/badge/Security-Hardened-blue)](.) 
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](.) 

---

## 🎯 What Is This?

**Daleel AI** is a dual-purpose AI platform combining:

1. **🕸️ Graph RAG Chatbot** - Answer questions about your company using PDF documents
2. **🎯 Career AI Assistant** - CV analysis, GitHub profiling, and intelligent job matching

---

## ✨ What's New in v1.1 (Phase 1 Security Update)

### 🔒 Security Hardening

- ✅ **API Key Validation** - App won't start without proper credentials
- ✅ **Environment Protection** - `.env` and secrets never committed to git
- ✅ **Rate Limiting** - 6 requests per minute per session (configurable)
- ✅ **Error Sanitization** - No stack traces exposed to users
- ✅ **Logging System** - All errors logged to `daleel.log` for debugging

### 💾 Persistent Storage

- ✅ **SQLite Database** - Chat history and feedback survive restarts
- ✅ **CSV Export** - Download your data anytime
- ✅ **Session Management** - Each user gets a unique session ID

### 🛠️ Code Quality

- ✅ **Better Error Handling** - Specific exception types with user-friendly messages
- ✅ **Graceful Degradation** - App works even if optional modules fail
- ✅ **Improved Logging** - Track what's happening under the hood
- ✅ **Type Safety** - Better validation of LLM JSON responses

---

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.10+
- Groq API key ([get free key](https://console.groq.com/keys))
- GitHub token (optional, for GitHub Analyzer)

### 2. Installation

```bash
# Clone repository
git clone https://github.com/Yossefmohammed/daleel-ai.git
cd daleel-ai

# Install dependencies
pip install -r requirements.txt

# Install spaCy model (for entity extraction)
python -m spacy download en_core_web_sm
```

### 3. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your API keys
nano .env
```

Your `.env` should look like:

```bash
GROQ_API_KEY=gsk_your_actual_key_here
GITHUB_TOKEN=ghp_your_token_here  # Optional

# Optional configuration
MAX_REQUESTS_PER_MINUTE=6
CACHE_HOURS=24
MAX_JOB_MATCHES=8
```

**For Streamlit Cloud deployment:**

1. Go to your app settings
2. Navigate to "Secrets"
3. Add:
```toml
GROQ_API_KEY = "gsk_your_key_here"
GITHUB_TOKEN = "ghp_your_token_here"
```

### 4. Download Job Dataset

Download one of these CSV files and place in `data/jobs.csv`:

- [AI Jobs Market 2025-2026](https://www.kaggle.com/datasets/alitaqishah/ai-jobs-market-2025-2026-salaries)
- [Tech Jobs & Skills](https://www.kaggle.com/datasets/mjawad17/tech-jobs-salaries-and-skills-dataset)
- [LinkedIn Jobs](https://www.kaggle.com/datasets/muqaddasejaz/linkedin-profiles-and-jobs-dataset)

```bash
mkdir data
# Place your downloaded CSV as data/jobs.csv
```

### 5. Add Company PDFs (Optional)

For the Graph RAG chatbot, drop PDFs into `docs/`:

```bash
mkdir docs
cp /path/to/company_handbook.pdf docs/
```

### 6. Run

```bash
streamlit run app_improved.py
```

Visit: `http://localhost:8501`

---

## 📁 Project Structure

```
daleel-ai/
├── app_improved.py         ← Main app (use this instead of app.py)
├── cv_analyzer.py          ← PDF CV parsing
├── github_analyzer.py      ← GitHub API integration
├── job_matcher.py          ← Job matching engine
├── graph_builder.py        ← Knowledge graph builder
├── graph_retriever.py      ← Hybrid retrieval (vector + graph)
├── matching_engine.py      ← Deterministic job scoring
├── semantic_matcher.py     ← Semantic embeddings
├── data_scraper.py         ← Job board scraper
│
├── .env.example            ← Environment template (COPY THIS)
├── .gitignore              ← Security-hardened (prevents key leaks)
├── requirements.txt        ← Python dependencies
├── daleel.log              ← Application logs (auto-generated)
│
├── docs/                   ← Drop PDFs here for chatbot
├── data/
│   └── jobs.csv            ← Job listings (from Kaggle)
└── db/
    ├── daleel_data.db      ← Chat/feedback storage (auto-generated)
    ├── chroma.sqlite3      ← Vector embeddings (auto-generated)
    └── knowledge_graph.json← Entity graph (auto-generated)
```

---

## 🔒 Security Best Practices

### Critical Rules

1. **NEVER commit `.env`** - It contains your API keys
2. **Use `.env.example`** - Share template, not actual keys
3. **Rotate keys if leaked** - Generate new keys immediately
4. **Use environment variables** - Don't hardcode secrets

### Checking for Leaks

Before committing:

```bash
# Make sure .env is ignored
git status

# If .env shows up, add to .gitignore immediately
echo ".env" >> .gitignore
git rm --cached .env  # Remove if already tracked
```

### For Production

- Use Streamlit Cloud secrets or environment variables
- Never store keys in code or config files committed to git
- Enable 2FA on your Groq/GitHub accounts
- Monitor logs for unusual activity

---

## 🎯 Features

### 🔍 Job Matcher

- **Hybrid Search Pipeline**: Semantic → Engine → LLM
- **Egypt-Specific**: Wuzzuf integration, Cairo/Giza/Alexandria filtering
- **Source Diversity**: Mix of RemoteOK, LinkedIn, Wuzzuf, etc.
- **Skill Expansion**: Automatic synonym matching (React → ReactJS, etc.)

### 📄 CV Analyzer

- **PDF Parsing**: Extract text from CVs (PyPDF)
- **AI Analysis**: Skills, experience, education, projects
- **Honest Feedback**: Strengths and improvement areas
- **Seniority Detection**: Junior/Mid/Senior/Lead classification

### 🐙 GitHub Analyzer

- **Profile Stats**: Repos, followers, languages
- **Code Quality**: Project analysis and scoring
- **Recommendations**: What to build next
- **Tech Stack**: Most-used languages and frameworks

---

## 🔧 Configuration

### Rate Limiting

Edit `.env`:

```bash
# Allow 10 requests per minute instead of default 6
MAX_REQUESTS_PER_MINUTE=10
```

### Job Cache Duration

```bash
# Refresh job database every 12 hours instead of 24
CACHE_HOURS=12
```

### Match Results

```bash
# Return top 12 matches instead of default 8
MAX_JOB_MATCHES=12
```

---

## 🐛 Troubleshooting

### "GROQ_API_KEY not set"

**Solution**: Copy `.env.example` to `.env` and add your key

```bash
cp .env.example .env
nano .env  # Add your key
```

### "Rate limit exceeded"

**Solution**: Wait 60 seconds or increase `MAX_REQUESTS_PER_MINUTE` in `.env`

### "No jobs found in database"

**Solution**: 
1. Download jobs CSV from Kaggle
2. Place in `data/jobs.csv`
3. Click "🔄 Refresh Job Database" in sidebar

### "GitHub profile not found"

**Solution**: 
- Check username is correct
- Ensure profile is public
- Add `GITHUB_TOKEN` to avoid rate limits

### SQLite errors

**Solution**: Delete database and restart

```bash
rm db/daleel_data.db
streamlit run app_improved.py
```

---

## 📊 Database Schema

### Chat History

```sql
CREATE TABLE chat_history (
    id INTEGER PRIMARY KEY,
    session_id TEXT,
    timestamp TEXT,
    user_message TEXT,
    bot_response TEXT,
    response_time REAL
);
```

### Feedback

```sql
CREATE TABLE feedback (
    id INTEGER PRIMARY KEY,
    session_id TEXT,
    timestamp TEXT,
    message_id INTEGER,
    feedback_type TEXT,  -- 'positive' or 'negative'
    comment TEXT
);
```

---

## 🚢 Deployment

### Streamlit Cloud

1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect repository
4. Set main file: `app_improved.py`
5. Add secrets:

```toml
GROQ_API_KEY = "gsk_..."
GITHUB_TOKEN = "ghp_..."
```

### Render

1. Connect GitHub repo
2. Build command: 
```bash
pip install -r requirements.txt && python -m spacy download en_core_web_sm
```
3. Start command:
```bash
streamlit run app_improved.py --server.port $PORT --server.address 0.0.0.0
```
4. Add environment variables in dashboard

### Docker

```bash
docker build -t daleel-ai .
docker run -p 8501:8501 --env-file .env daleel-ai
```

---

## 🗺️ Roadmap

### ✅ Phase 1 (Complete)

- Graph RAG chatbot
- CV/GitHub/Job matching
- Security hardening
- Persistent storage
- Rate limiting

### 🔜 Phase 2 (In Progress)

- 🎤 Mock interview practice
- 💼 LinkedIn optimizer
- 📚 Skill gap analysis
- 🌐 Arabic language support

### 🔮 Phase 3 (Planned)

- 💰 Salary prediction ML model
- 🔐 User authentication
- 🌐 REST API (FastAPI)
- ☁️ Production cloud deployment
- 📊 Admin analytics dashboard

---

## 🤝 Contributing

This is a private project. Contact the maintainer for contribution guidelines.

---

## 📄 License

Proprietary. All rights reserved.

---

## 📞 Support

- 📧 Email: [your-email]
- 💬 GitHub Issues: [Report a bug](https://github.com/Yossefmohammed/daleel-ai/issues)
- 📚 Docs: See `/docs` folder

---

## ⚠️ Migration from v1.0 to v1.1

If you're upgrading from the original `app.py`:

1. **Backup your data**
```bash
cp chat_history.csv chat_history_backup.csv
cp feedback.csv feedback_backup.csv
```

2. **Install new requirements**
```bash
pip install -r requirements.txt --upgrade
```

3. **Create .env file**
```bash
cp .env.example .env
# Add your API keys to .env
```

4. **Switch to new app**
```bash
# Old way
streamlit run app.py

# New way
streamlit run app_improved.py
```

5. **Your data will auto-migrate** to SQLite on first run

---

## 🏆 Credits

**Built with:**
- [Groq](https://groq.com) - Fast LLM inference
- [Streamlit](https://streamlit.io) - Web framework
- [ChromaDB](https://www.trychroma.com) - Vector database
- [NetworkX](https://networkx.org) - Knowledge graphs
- [spaCy](https://spacy.io) - NLP & entity extraction

---

**Status:** Phase 1 Complete ✅ | Security Hardened 🔒 | Production Ready 🚀

*Last Updated: April 2026*