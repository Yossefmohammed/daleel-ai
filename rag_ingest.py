"""
RAG Ingest — pure NumPy vector store (no ChromaDB, no protobuf issues)

Builds two indexes:
  1. NumPy embedding matrix  → db/embeddings.npy + db/chunks.json
  2. NetworkX knowledge graph → db/knowledge_graph.json
"""

import os, re, json, logging
import numpy as np
import pandas as pd
import networkx as nx
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

DB_DIR      = "db"
EMBED_PATH  = os.path.join(DB_DIR, "embeddings.npy")
CHUNKS_PATH = os.path.join(DB_DIR, "chunks.json")
GRAPH_PATH  = os.path.join(DB_DIR, "knowledge_graph.json")
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

JOB_CSV_PATHS = [
    "data/jobs_combined.csv",
    "data/jobs.csv",
    "docs/ai_jobs_market_2025_2026.csv",
]

SKILL_KEYWORDS = {
    "python","javascript","typescript","java","c++","c#","go","rust",
    "react","vue","angular","node","django","flask","fastapi","spring",
    "sql","postgresql","mysql","mongodb","redis","elasticsearch",
    "docker","kubernetes","aws","azure","gcp","terraform","ci/cd",
    "machine learning","deep learning","nlp","data science","ai",
    "devops","backend","frontend","full stack","mobile","ios","android",
    "remote","cairo","egypt","giza","alexandria","maadi","heliopolis",
    "junior","senior","mid-level","manager","lead","intern",
}

def _chunk_text(text, size=400, overlap=80):
    words = text.split()
    chunks, start = [], 0
    while start < len(words):
        end   = min(start + size, len(words))
        chunk = " ".join(words[start:end])
        if len(chunk.strip()) > 30:
            chunks.append(chunk)
        start += size - overlap
    return chunks

def extract_entities(text):
    q = text.lower()
    found = {kw for kw in SKILL_KEYWORDS if kw in q}
    found |= {w.lower() for w in re.findall(r'\b[A-Z][a-zA-Z]{2,}\b', text) if len(w) <= 20}
    return list(found)[:15]

def _load_jobs():
    for path in JOB_CSV_PATHS:
        if not os.path.exists(path):
            continue
        try:
            df = pd.read_csv(path).fillna("")
            docs = []
            for _, r in df.iterrows():
                title    = str(r.get("job_title",   r.get("title",        "Job")))
                company  = str(r.get("company",     r.get("company_name", "")))
                location = str(r.get("location",    r.get("city",         "")))
                tags     = str(r.get("tags",        r.get("required_skills", "")))
                desc     = str(r.get("description", ""))[:300]
                remote   = str(r.get("remote_work", ""))
                salary   = str(r.get("salary_range", r.get("annual_salary_usd", "")))
                source   = str(r.get("source", "jobs_csv"))
                url      = str(r.get("url", ""))
                text = (f"Job: {title} | Company: {company} | Location: {location} {remote} | "
                        f"Skills: {tags} | Salary: {salary} | Info: {desc} | URL: {url}").strip()
                docs.append({"text": text, "job_title": title, "company": company,
                             "location": location, "url": url, "source": source, "type": "job"})
            logger.info(f"✅ {len(docs)} jobs from {path}")
            return docs
        except Exception as e:
            logger.warning(f"⚠️  {path}: {e}")
    return []

def _load_pdfs():
    docs = []
    try:
        from pypdf import PdfReader
        for pdf in Path("docs").glob("**/*.pdf"):
            try:
                text = "\n".join(p.extract_text() or "" for p in PdfReader(str(pdf)).pages)
                for ct in _chunk_text(text):
                    docs.append({"text": ct, "source": pdf.name, "type": "pdf",
                                 "job_title": "", "company": "", "location": "", "url": ""})
            except Exception:
                pass
    except ImportError:
        pass
    return docs

def build_index(progress_callback=None):
    from sentence_transformers import SentenceTransformer
    os.makedirs(DB_DIR, exist_ok=True)

    def _p(pct, msg):
        logger.info(f"[{pct}%] {msg}")
        if progress_callback:
            progress_callback(pct, msg)

    _p(5,  "Loading jobs...")
    raw = _load_jobs() + _load_pdfs()
    if not raw:
        raise ValueError("No data — scrape jobs first.")

    chunks = []
    for doc in raw:
        if doc["type"] == "job":
            chunks.append(doc)
        else:
            for ct in _chunk_text(doc["text"]):
                chunks.append({**doc, "text": ct})

    _p(20, f"{len(chunks)} chunks — loading embedding model...")
    model = SentenceTransformer(EMBED_MODEL)

    _p(30, "Embedding... (first run downloads ~80 MB model)")
    texts = [c["text"] for c in chunks]
    BATCH = 256
    all_emb = []
    for i in range(0, len(texts), BATCH):
        emb = model.encode(texts[i:i+BATCH], normalize_embeddings=True, show_progress_bar=False)
        all_emb.append(emb)
        _p(30 + int(42 * min(i+BATCH, len(texts)) / len(texts)),
           f"Embedded {min(i+BATCH, len(texts))}/{len(texts)}...")

    embeddings = np.vstack(all_emb).astype("float32")

    _p(74, "Saving vector store...")
    np.save(EMBED_PATH, embeddings)
    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        json.dump({"chunks": [c["text"] for c in chunks],
                   "meta":   [{k:v for k,v in c.items() if k != "text"} for c in chunks]}, f)

    _p(80, "Building knowledge graph...")
    G = nx.Graph()
    for idx, chunk in enumerate(chunks):
        cid = f"chunk_{idx}"
        ents = extract_entities(chunk["text"])
        G.add_node(cid, type="chunk")
        for e in ents:
            if not G.has_node(e): G.add_node(e, type="entity")
            G.add_edge(cid, e)
        for i in range(len(ents)):
            for j in range(i+1, len(ents)):
                e1, e2 = ents[i], ents[j]
                if G.has_edge(e1, e2): G[e1][e2]["weight"] = G[e1][e2].get("weight",1) + 1
                else:                  G.add_edge(e1, e2, weight=1)

    _p(95, "Saving graph...")
    with open(GRAPH_PATH, "w", encoding="utf-8") as f:
        json.dump(nx.node_link_data(G), f)

    stats = {"chunks": len(chunks), "graph_nodes": G.number_of_nodes(),
             "graph_edges": G.number_of_edges(), "built_at": datetime.now().isoformat()}
    _p(100, f"✅ {len(chunks)} chunks · {G.number_of_nodes()} nodes · {G.number_of_edges()} edges")
    return stats

def load_index():
    if not index_exists():
        raise FileNotFoundError("Index not built.")
    embeddings = np.load(EMBED_PATH)
    with open(CHUNKS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    with open(GRAPH_PATH, encoding="utf-8") as f:
        graph = nx.node_link_graph(json.load(f))
    logger.info(f"✅ Index loaded — {len(data['chunks'])} chunks")
    return embeddings, data["chunks"], data["meta"], graph

def index_exists():
    return all(os.path.exists(p) for p in [EMBED_PATH, CHUNKS_PATH, GRAPH_PATH])

def data_is_newer_than_index():
    if not index_exists():
        return True
    try:
        idx_mtime = os.path.getmtime(EMBED_PATH)
        return any(os.path.exists(p) and os.path.getmtime(p) > idx_mtime for p in JOB_CSV_PATHS)
    except Exception:
        return False