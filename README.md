# 🎯 Career AI Assistant - Phase 1

AI-powered career tool combining CV analysis, GitHub profiling, and intelligent job matching.

## 📋 Phase 1: MVP Features

- **📄 CV Analyzer** - Extracts skills, experience, education from PDF CVs
- **🐙 GitHub Profile Analysis** - Analyzes coding profile using GitHub API
- **💼 Job Matcher** - Matches user profile with recommended jobs
- **📊 Full Assessment** - Comprehensive career report combining all data

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+
- GitHub account (for API access)
- Kaggle account (for job datasets)
- Groq API key

### 2. Installation

```bash
# Navigate to project
cd career-ai-assistant

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
```

### 3. Environment Setup

Create `.env` file:
```
GROQ_API_KEY=your_groq_api_key_here
GITHUB_TOKEN=your_github_token_here  # Optional but recommended
```

**Get your API keys:**
- [Groq API](https://groq.com) - Free tier available
- [GitHub Token](https://github.com/settings/tokens) - Generate personal access token

### 4. Kaggle Datasets - Phase 1

Download **ONE** of these datasets and place in `data/` folder as `jobs.csv`:

#### Option A: Data Science Job Salaries (Recommended for ML roles)
```
Dataset: https://www.kaggle.com/datasets/ruchi798/data-science-job-salaries
File: ds_salaries.csv
Rename to: data/jobs.csv
Size: ~600 rows
Best for: ML Engineers, Data Scientists
```

#### Option B: Tech Jobs (Broad tech industry) ⭐ **RECOMMENDED FOR START**
```
Dataset: https://www.kaggle.com/datasets/andrewmvd/tech-jobs
File: jobs_data.csv
Rename to: data/jobs.csv
Size: ~5,000 rows
Best for: Full Stack, Backend, Frontend developers
```

#### Option C: LinkedIn Job Postings (Most comprehensive)
```
Dataset: https://www.kaggle.com/datasets/arjunprasadsarkhel/linkedin-job-postings
File: LinkedIn_job_postings_Feb_2024.csv
Rename to: data/jobs.csv
Size: ~30,000 rows
Best for: All roles and industries
```

**Setup Steps:**
```bash
# 1. Download dataset from Kaggle
# 2. Create data folder
mkdir data

# 3. Place CSV in data/ folder and verify
ls data/jobs.csv
```

### 5. Run the App

```bash
streamlit run app.py
```

The app will be available at: `http://localhost:8501`

---

## 📊 Kaggle Datasets Comparison

| Dataset | Rows | Focus | Best For |
|---------|------|-------|----------|
| Data Science Job Salaries | 600+ | ML/Data | ML Engineers, Data Scientists |
| **Tech Jobs** | 5,000+ | General Tech | ✅ **START HERE** |
| LinkedIn Jobs | 30,000+ | All Industries | Comprehensive |

**Recommendation:** Start with **Tech Jobs** - balanced size, good diversity, stable format

---

## 🏗️ Project Structure

```
career-ai-assistant/
├── app.py                 # Main Streamlit app (4 tabs)
├── cv_analyzer.py        # PDF CV parsing & analysis
├── github_analyzer.py    # GitHub API integration
├── job_matcher.py        # Job matching engine
├── requirements.txt      # Python dependencies
├── .env                  # API keys (create manually)
├── README.md             # This file
├── data/
│   └── jobs.csv          # ⬅️ Download from Kaggle HERE
└── temp_*.pdf           # Temporary CV uploads (auto-cleaned)
```

---

## 🔄 Feature Walkthrough

### 1. 📄 CV Analyzer Tab
**What it does:**
- Upload your PDF CV
- Extracts structured data using LLM
- Returns: JSON with skills, experience, education, seniority level

**Input:** PDF file
**Output:** Analyzed profile data
**Time:** ~5-10 seconds per CV

### 2. 🐙 GitHub Analyzer Tab
**What it does:**
- Enter your GitHub username
- Fetches public profile via GitHub API
- Analyzes: repos, languages, followers, contribution count
- Returns: profile strength score and recommendations

**Input:** GitHub username (must be public)
**Output:** Profile metrics + AI analysis
**Time:** ~3-5 seconds

### 3. 💼 Job Matcher Tab
**What it does:**
- Enter your skills, experience, seniority
- Compares against job database
- Returns: recommended jobs with match scores

**Input:** Skills, experience years, seniority level
**Output:** Job recommendations with match explanations
**Requirements:** `data/jobs.csv` must be present
**Time:** ~5-10 seconds

### 4. 📊 Full Assessment Tab
**What it does:**
- Combines all analyses into one report
- Shows CV analysis + GitHub profile + job matches
- Provides holistic career insights

**Requirements:** Complete at least one analysis first

---

## 💾 How to Download Kaggle Datasets

### Method 1: Kaggle CLI (Fastest)
```bash
# Install Kaggle CLI
pip install kaggle

# Download API key from https://www.kaggle.com/settings/account
# Save to ~/.kaggle/kaggle.json

# Download dataset
kaggle datasets download -d andrewmvd/tech-jobs

# Extract
unzip tech-jobs.zip -d data/

# Rename to jobs.csv
mv data/jobs_data.csv data/jobs.csv
```

### Method 2: Manual Download (Web UI)
1. Go to: https://www.kaggle.com/datasets/andrewmvd/tech-jobs
2. Click "Download" button
3. Extract ZIP file
4. Copy `jobs_data.csv` to `data/` folder
5. Rename to `jobs.csv`

### Method 3: Kaggle Browser (No CLI)
1. Visit Kaggle dataset page
2. Click "Download"
3. Extract and place file in `data/` folder as `jobs.csv`

---

## 🔧 Troubleshooting

### Error: "GROQ_API_KEY not found"
**Solution:**
```bash
# Create .env file
echo "GROQ_API_KEY=sk-..." > .env
echo "GITHUB_TOKEN=ghp_..." >> .env
```

### Error: "ModuleNotFoundError: langchain"
**Solution:**
```bash
pip install -r requirements.txt --force-reinstall
```

### Error: "No jobs found in database"
**Solution:**
1. Verify `data/jobs.csv` exists
2. Check file has columns: `job_title`, `company`, `description`
3. Try different Kaggle dataset if current one doesn't work

### Error: "GitHub profile not found"
**Solution:**
1. Double-check GitHub username spelling
2. Ensure profile is PUBLIC (not private)
3. Try with different user first to test (e.g., `torvalds`)

### App runs but features slow
**Solution:**
- CV analysis takes 5-10s (normal, LLM processing)
- GitHub takes 3-5s (API call + analysis)
- Job matching takes 5-10s (database search + scoring)

All operations show "⏳ Analyzing..." spinner

---

## 📋 Phase 1 Checklist

- [x] CV Parser (PDF extraction)
- [x] GitHub Integration (API + analysis)
- [x] Job Matcher (Kaggle data)
- [x] Streamlit UI (Multi-tab)
- [x] Session persistence
- [x] Error handling
- [ ] **Phase 2:** Mock Interview
- [ ] **Phase 2:** LinkedIn Optimizer
- [ ] **Phase 2:** Learning Roadmap
- [ ] **Phase 3:** Salary Predictions

---

## 🎯 What Comes in Phase 2

1. **Mock Interview Practice**
   - Coding challenges
   - Behavioral question preparation
   - Interview feedback

2. **LinkedIn Optimizer**
   - Profile improvement suggestions
   - Headline recommendations
   - Summary writing assistance

3. **Skill Gap Analysis**
   - Detailed learning paths
   - Course recommendations
   - Timeline to new role

---

## 🔑 API Requirements

| Service | Requirement | Cost | Notes |
|---------|--|--|--|
| **Groq** | Free API key | Free | Core LLM (required) |
| **GitHub** | Personal token | Free | Optional but recommended |
| **Kaggle** | CSV download | Free | Job database |

---

## 📧 Support & FAQ

**Q: Do I need a GitHub account to use CV analyzer?**
A: No, GitHub is only needed for the GitHub Profile tab. CV and Job Matcher work without it.

**Q: What's the token limit per API call?**
A: Groq free tier: 1000 requests/hour. Each analysis uses ~1-2 requests.

**Q: Can I use my own job database?**
A: Yes! Replace `data/jobs.csv` with your own CSV (same format).

**Q: How long does analysis take?**
A: CV: 5-10s | GitHub: 3-5s | Job Matcher: 5-10s (all include LLM processing)

---

## 📄 Sample .env File

```bash
# Required
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxx

# Optional but recommended
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxx

# App settings (optional)
DEBUG=false
LOG_LEVEL=INFO
```

---

## 🚀 Deployment (Coming Soon)

- Streamlit Cloud: `streamlit run app.py`
- Docker: `docker build -t career-assistant .`
- AWS/Azure: Docker deployment

---

**Status:** Phase 1 MVP ✅ | Last Updated: April 2026
# Wasla AI – Graph RAG Upgrade

> Converts your existing flat-RAG chatbot into a **Graph RAG** system:
> *ChromaDB vector search* + *entity knowledge graph traversal* for richer, multi-hop answers.

---

## What changed

| | Original RAG | Graph RAG |
|---|---|---|
| **Retrieval** | Vector similarity only | Vector similarity + graph neighbour expansion |
| **Storage** | `db/` (ChromaDB) | `db/` (ChromaDB) + `db/knowledge_graph.json` |
| **New files** | — | `graph_builder.py`, `graph_retriever.py` |
| **Changed files** | `app.py`, `ingest.py` | `app.py`, `ingest.py` (replaced) |
| **New deps** | — | `networkx`, `spacy` |

---

## New file layout

```
yossefbot/
├── app.py                        ← replaced (Graph RAG UI)
├── ingest.py                     ← replaced (builds graph + vector DB)
├── graph_builder.py              ← NEW: entity extraction + graph construction
├── graph_retriever.py            ← NEW: hybrid vector + graph retrieval
├── constant.py                   ← unchanged
├── requirements.txt              ← updated
├── docs/                         ← put your PDFs here
└── db/
    ├── chroma.sqlite3            ← ChromaDB (vector store)
    └── knowledge_graph.json      ← NEW: knowledge graph
```

---

## Installation

```bash
# 1. Install Python packages
pip install -r requirements.txt

# 2. Install spaCy NER model (recommended for better entity extraction)
python -m spacy download en_core_web_sm
```

---

## Usage

### 1. Add PDFs
Drop your PDF files into the `docs/` folder.

### 2. Build the index (first time)
```bash
python ingest.py
```
This creates **both** the ChromaDB vector store and the knowledge graph JSON.

Or click **"🚀 Build Graph RAG Index"** inside the Streamlit sidebar.

### 3. Run the app
```bash
streamlit run app.py
```

---

## How Graph RAG works

```
User query
    │
    ├─► Vector search (ChromaDB MMR)
    │       └─► seed chunks (k=5)
    │
    ├─► Entity extraction (spaCy NER or regex fallback)
    │       └─► query entities: ["Wasla", "fintech", "API", …]
    │
    └─► Graph traversal (NetworkX BFS, depth=2)
            └─► neighbour chunk IDs
                    └─► fetch from ChromaDB
                            └─► extra chunks (graph_k=5)

All chunks → deduplicate → format as context → Groq LLM → answer
```

### Why it's better
- **Multi-hop questions**: "What fintech services does Wasla offer that involve APIs?" – the graph connects *fintech → Wasla → API* even if no single chunk contains all three terms.
- **Richer context**: graph expansion surfaces related chunks not found by pure cosine similarity.
- **Zero hallucination increase**: still grounded in your documents.

---

## Configuration (graph_retriever.py)

| Parameter | Default | Description |
|---|---|---|
| `k` | 5 | Top-k from vector search |
| `graph_k` | 5 | Max extra chunks from graph |
| `hop_depth` | 2 | BFS depth in knowledge graph |

Increase `hop_depth` to 3 for denser, more exploratory retrieval on large document sets.

---

## Secrets (unchanged)

`streamlit/secrets.toml`:
```toml
GROQ_API_KEY = "gsk_..."
```