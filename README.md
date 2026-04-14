# 🧭 Daleel AI – Intelligent Chatbot & Career Assistant

> **Dual-purpose AI platform:** A Graph RAG-powered company chatbot for your company **plus** a Career AI Assistant (CV analysis, GitHub profiling, and job matching).

![Status](https://img.shields.io/badge/Phase%201-Complete-brightgreen) ![Status](https://img.shields.io/badge/Graph%20RAG-Active-blue) ![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![Streamlit](https://img.shields.io/badge/Streamlit-UI-red)

---

## 📌 What Is This?

This repo contains **two integrated AI modules** running in a single Streamlit app:

| Module | Description |
|--------|-------------|
| 🕸️ **Daleel AI Chatbot** | Graph RAG chatbot that answers questions about your company using your internal PDF documents. Uses ChromaDB + NetworkX knowledge graph for multi-hop retrieval. |
| 🎯 **Career AI Assistant** | MVP tool that analyzes CVs, GitHub profiles, and matches users to job opportunities. Powered by Groq LLMs. |

---

## ✅ Phase 1 – Completed Features

### 🕸️ Daleel AI Chatbot (Graph RAG)
- PDF ingestion with ChromaDB vector store
- Entity extraction & knowledge graph construction (NetworkX + spaCy)
- Hybrid retrieval: vector similarity + graph neighbour expansion (BFS depth=2)
- Multi-hop question answering with Groq LLM
- Conversation history tracking + feedback export (CSV)
- Dark-themed Streamlit UI with real-time graph stats

### 🎯 Career AI Assistant
- **📄 CV Analyzer** – Extracts skills, experience, and education from PDF CVs
- **🐙 GitHub Profile Analyzer** – Assesses coding profile via GitHub API
- **💼 Job Matcher** – Matches user profile to jobs from a Kaggle CSV dataset
- **📊 Full Assessment** – Compiles all analyses into one career report

---

## 🗂️ Project Structure

```
daleel-ai/
├── app.py                  ← Main Streamlit app (Graph RAG chatbot + Career tabs)
├── cv_analyzer.py          ← PDF CV parsing & LLM analysis
├── github_analyzer.py      ← GitHub API integration
├── job_matcher.py          ← Job matching engine (Kaggle CSV)
├── graph_builder.py        ← Entity extraction + knowledge graph builder
├── graph_retriever.py      ← Hybrid vector + graph retrieval engine
├── ingest.py               ← Builds ChromaDB + knowledge graph from PDFs
├── constant.py             ← App-wide constants
├── data_scraper.py         ← Web scraper for additional data
├── requirements.txt        ← Python dependencies
├── runtime.txt             ← Python version pin
├── Dockerfile              ← Container deployment config
├── .devcontainer/          ← Dev container setup
├── docs/                   ← ⬅ Drop your PDFs here (for the chatbot)
├── data/
│   └── jobs.csv            ← ⬅ Download from Kaggle (for job matcher)
└── db/
    ├── chroma.sqlite3      ← ChromaDB vector store (auto-generated)
    └── knowledge_graph.json← Knowledge graph (auto-generated)
```

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+
- Groq API key (free tier available)
- GitHub token (optional, for GitHub Analyzer tab)

### 2. Installation

```bash
git clone https://github.com/Yossefmohammed/daleel-ai.git
cd daleel-ai

pip install -r requirements.txt

# Install spaCy NER model (for better entity extraction)
python -m spacy download en_core_web_sm
```

### 3. Environment Setup

Create a `.streamlit/secrets.toml` file:

```toml
GROQ_API_KEY = "gsk_your_key_here"
GITHUB_TOKEN = "ghp_your_token_here"  # Optional
```

Or use a `.env` file:

```env
GROQ_API_KEY=gsk_your_key_here
GITHUB_TOKEN=ghp_your_token_here
```

### 4. Kaggle Dataset (for Job Matcher)

Download one of these datasets and place it in `data/jobs.csv`:

| Dataset |
|---------|
| [AI Jobs Market 2025-2026 Salaries](https://www.kaggle.com/datasets/alitaqishah/ai-jobs-market-2025-2026-salaries)
| [Tech Jobs, Salaries, and Skills Dataset](https://www.kaggle.com/datasets/mjawad17/tech-jobs-salaries-and-skills-dataset) 
| [LinkedIn Profiles and Jobs Dataset](https://www.kaggle.com/datasets/muqaddasejaz/linkedin-profiles-and-jobs-dataset)

```bash
mkdir data
# Place your downloaded CSV here as data/jobs.csv
```

### 5. Add PDFs (for Daleel AI Chatbot)

Drop your company's PDF documents into the `docs/` folder. The app auto-ingests them on first run.

### 6. Run

```bash
streamlit run app.py
```

App available at: `http://localhost:8501`

---

## 🔄 How Graph RAG Works

```
User Query
    │
    ├─► Vector Search (ChromaDB MMR, k=5)
    │         └─► Seed chunks
    │
    ├─► Entity Extraction (spaCy NER / regex fallback)
    │         └─► Query entities: ["Daleel", "fintech", "API", …]
    │
    └─► Graph Traversal (NetworkX BFS, depth=2)
              └─► Neighbour chunk IDs
                      └─► Extra chunks from ChromaDB (graph_k=5)

All chunks → Deduplicate → Format as context → Groq LLM → Answer
```

**Why Graph RAG is better than flat RAG:**
- Handles multi-hop questions (e.g., "What fintech services does your company offer via API?")
- Surfaces related chunks that pure cosine similarity misses
- Zero extra hallucination — still grounded in your documents

### Graph Retriever Configuration (`graph_retriever.py`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `k` | 5 | Top-k chunks from vector search |
| `graph_k` | 5 | Max extra chunks from graph traversal |
| `hop_depth` | 2 | BFS depth in the knowledge graph |

---

## 🔧 Troubleshooting

**`GROQ_API_KEY not found`** → Create `.streamlit/secrets.toml` with your key.

**`ModuleNotFoundError`** → Run `pip install -r requirements.txt --force-reinstall`

**`No jobs found in database`** → Verify `data/jobs.csv` exists with columns `job_title`, `company`, `description`.

**`GitHub profile not found`** → Ensure the username is correct and the profile is public.

**Slow responses** → CV analysis: 5–10s | GitHub: 3–5s | Job matching: 5–10s — all normal (LLM processing).

---

## 📋 API Requirements

| Service | Requirement | Cost |
|---------|-------------|------|
| **Groq** | Free API key | Free (1000 req/hr on free tier) |
| **GitHub** | Personal access token | Free |
| **Kaggle** | CSV download | Free |

---

## ☁️ Deployment

Daleel AI is deployed on **two platforms**:

---

### 🎈 Streamlit Cloud

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) and click **New app**
3. Select your repo, branch (`main`), and set the main file to `app.py`
4. Under **Advanced settings → Secrets**, add:

```toml
GROQ_API_KEY = "gsk_your_key_here"
GITHUB_TOKEN = "ghp_your_token_here"
```

5. Click **Deploy** — done!

> ⚠️ Streamlit Cloud does **not** persist files between restarts. Store `chat_history.csv` and `feedback.csv` in a database or external storage for production use.

---

### 🚀 Render

1. Push your code to GitHub
2. Go to [render.com](https://render.com) → **New → Web Service**
3. Connect your GitHub repo
4. Set the following:

| Field | Value |
|-------|-------|
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt && python -m spacy download en_core_web_sm` |
| **Start Command** | `streamlit run app.py --server.port $PORT --server.address 0.0.0.0` |

5. Under **Environment Variables**, add:

```
GROQ_API_KEY = gsk_your_key_here
GITHUB_TOKEN = ghp_your_token_here
```

6. Click **Create Web Service**

> ✅ Render supports a persistent disk — attach one under **Disks** so your `db/` (ChromaDB + knowledge graph) survives deploys without needing to re-ingest PDFs every time.

---

### 🐳 Docker (Local / Self-hosted)

```bash
docker build -t daleel-ai .
docker run -p 8501:8501 daleel-ai
```

---

## 📥 Export Features

From the sidebar you can download:
- **💬 Chat History** (`chat_history.csv`) — all Q&A pairs with timestamps
- **👍 Feedback Data** (`feedback.csv`) — user thumbs up/down responses

---

## 🗺️ Roadmap

### ✅ Phase 1 – Complete
- Graph RAG chatbot (ChromaDB + NetworkX)
- CV Analyzer, GitHub Analyzer, Job Matcher
- Streamlit UI with dark theme
- Feedback & chat history CSV export

### 🔜 Phase 2 – In Progress
- [ ] **Mock Interview Practice** – Coding challenges + behavioral Q&A + AI feedback
- [ ] **LinkedIn Profile Optimizer** – Headline, summary & skills improvement suggestions
- [ ] **Skill Gap Analysis** – Personalized learning paths + course recommendations
- [ ] **Arabic Language Support** – Bilingual chatbot (AR/EN) for local users
- [ ] **Admin Dashboard** – Feedback analytics, conversation metrics, heatmaps

### 🔮 Phase 3 – Planned
- [ ] **Salary Prediction Model** – ML-based salary estimator from job + profile data
- [ ] **User Authentication** – Login/signup so users can save their session and history
- [ ] **REST API (FastAPI)** – Expose chatbot and career tools as API endpoints
- [ ] **Production Cloud Deployment** – AWS/Azure with CI/CD pipeline
- [ ] **Graph RAG v2** – Larger hop depth, named entity disambiguation, relation types

---

## 📄 License

This project is proprietary to your company. Contact the maintainer for access or contributions.

---

**Status:** Phase 1 MVP ✅ | Graph RAG Active ✅ | Last Updated: April 2026