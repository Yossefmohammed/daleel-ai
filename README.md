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