# PathIQ — Career Intelligence Platform

> AI-powered career assistant with Graph RAG, CV analysis, GitHub profiling, and intelligent job matching.

---

## What is PathIQ?

PathIQ is a multi-service career intelligence platform built on:

- **Groq LLaMA 3.3-70b** — fast, high-quality LLM responses
- **Graph RAG** — hybrid retrieval combining ChromaDB vector search + NetworkX knowledge graph traversal
- **5 specialized service chats** — each tab is a focused AI assistant with its own context and prompting

---

## Services

| Service | What it does |
|---|---|
| **CV Analyzer** | Extract skills, score your CV, get rewrite suggestions |
| **Code Profile** | Score your GitHub across consistency, depth, visibility, docs |
| **Job Matcher** | Match your profile against a jobs database with fit scores |
| **Full Assessment** | Synthesize all data into a PathIQ Career Intelligence Report |
| **Knowledge Chat** | Graph RAG Q&A over your company/project document base |

---

## Quick Start

### 1. Clone and install

```bash
git clone <your-repo>
cd pathiq

pip install -r requirements.txt
```

### 2. Set up API keys

```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

Get a free Groq API key at [console.groq.com](https://console.groq.com).

### 3. (Optional) Add documents for Knowledge Chat

```bash
mkdir docs
# Copy your PDF files into docs/
python ingest.py
```

### 4. (Optional) Add jobs database for Job Matcher

Download one of these Kaggle datasets and save as `data/jobs.csv`:

| Dataset | Size | Best for |
|---|---|---|
| [Tech Jobs](https://www.kaggle.com/datasets/andrewmvd/tech-jobs) | ~5,000 rows | ✅ Start here |
| [Data Science Salaries](https://www.kaggle.com/datasets/ruchi798/data-science-job-salaries) | ~600 rows | ML/Data roles |
| [LinkedIn Job Postings](https://www.kaggle.com/datasets/arjunprasadsarkhel/linkedin-job-postings) | ~30,000 rows | All industries |

### 5. Run

```bash
streamlit run app.py
```

Open: [http://localhost:8501](http://localhost:8501)

---

## Project Structure

```
pathiq/
├── app.py                 # Main Streamlit app — PathIQ UI
├── cv_analyzer.py         # PDF CV parsing & AI analysis
├── github_analyzer.py     # GitHub API + profile scoring
├── job_matcher.py         # Job matching engine
├── graph_builder.py       # Knowledge graph construction
├── graph_retriever.py     # Hybrid RAG retriever
├── ingest.py              # Document ingestion pipeline
├── constant.py            # Global configuration
├── requirements.txt
├── Dockerfile
├── .env.example
├── .streamlit/
│   ├── config.toml        # Dark theme config
│   └── secrets.toml.example
├── docs/                  # ← Drop your PDFs here
├── data/
│   └── jobs.csv           # ← Download from Kaggle
└── db/                    # Auto-created by ingest.py
    ├── chroma.sqlite3
    └── knowledge_graph.json
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | ✅ Yes | Get free at console.groq.com |
| `GITHUB_TOKEN` | Optional | Raises GitHub API rate limit 60 → 5000/hr |

---

## Deployment

### Streamlit Cloud

1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect repo, set `app.py` as main file
4. Add secrets in the Streamlit Cloud dashboard

### Docker

```bash
docker build -t pathiq .
docker run -p 8501:8501 --env-file .env pathiq
```

---

## Graph RAG Architecture

```
User query
    │
    ├─► Vector search (ChromaDB MMR) ──► top-5 chunks
    │
    ├─► Entity extraction (spaCy NER)
    │       └─► query entities: ["Python", "Wasla", "API", …]
    │
    └─► Graph BFS (NetworkX, depth=2) ──► neighbour chunk IDs
                                              └─► fetch from ChromaDB
                                                      └─► +5 extra chunks

All chunks → deduplicate → LLM context → Groq → answer
```

---

## Roadmap

- [x] Phase 1: CV Analyzer, GitHub Profile, Job Matcher, Assessment, RAG Chat
- [ ] Phase 2: Mock Interview Practice
- [ ] Phase 2: LinkedIn Optimizer
- [ ] Phase 2: Skill Roadmap Generator
- [ ] Phase 3: Salary Prediction Model
- [ ] Phase 3: Application Tracker

---

## Name

**PathIQ** = Career Path + Intelligence Quotient.  
Alternative names considered: *Nexus Career*, *Ascend AI*, *Meridian AI*, *Launchpad AI*.

---

**Built with:** Streamlit · Groq · LangChain · ChromaDB · NetworkX · sentence-transformers