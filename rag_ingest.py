"""rag_ingest.py — pure-NumPy vector store + NetworkX knowledge graph."""
import os, re, json, logging
import numpy as np
import pandas as pd
import networkx as nx
from pathlib import Path
from datetime import datetime
from constant import (DB_DIR, EMBED_PATH, CHUNKS_PATH, GRAPH_PATH,
                      EMBED_MODEL, CHUNK_SIZE, CHUNK_OVERLAP, EMBED_BATCH,
                      SKILL_KEYWORDS, JOB_CSV_PATHS)

logger = logging.getLogger(__name__)

# ── Text utilities ─────────────────────────────────────────────────────────────
def _chunk(text: str) -> list:
    words = text.split()
    out, i = [], 0
    while i < len(words):
        j     = min(i + CHUNK_SIZE, len(words))
        piece = " ".join(words[i:j])
        if len(piece) > 30:
            out.append(piece)
        i += CHUNK_SIZE - CHUNK_OVERLAP
    return out

def extract_entities(text: str) -> list:
    q   = text.lower()
    ent = {kw for kw in SKILL_KEYWORDS if kw in q}
    ent |= {w.lower() for w in re.findall(r'\b[A-Z][a-zA-Z]{2,}\b', text) if len(w) <= 20}
    return list(ent)[:15]

# ── Data loaders ───────────────────────────────────────────────────────────────
def _load_jobs() -> list:
    for path in JOB_CSV_PATHS:
        if not os.path.exists(path):
            continue
        try:
            df = pd.read_csv(path).fillna("")
            docs = []
            for _, r in df.iterrows():
                title   = str(r.get("job_title",   r.get("title",        "Job")))
                company = str(r.get("company",     r.get("company_name", "")))
                loc     = str(r.get("location",    r.get("city",         "")))
                tags    = str(r.get("tags",        r.get("required_skills","")))
                desc    = str(r.get("description", ""))[:300]
                remote  = str(r.get("remote_work", ""))
                salary  = str(r.get("salary_range", r.get("annual_salary_usd","")))
                src     = str(r.get("source", "jobs_csv"))
                url     = str(r.get("url", ""))
                text = (f"Job: {title} | Company: {company} | "
                        f"Location: {loc} {remote} | Skills: {tags} | "
                        f"Salary: {salary} | {desc} | URL: {url}").strip()
                docs.append({"text": text, "job_title": title, "company": company,
                             "location": loc, "url": url, "source": src, "type": "job"})
            logger.info(f"✅ {len(docs)} jobs from {path}")
            return docs
        except Exception as e:
            logger.warning(f"⚠️ {path}: {e}")
    return []

def _load_pdfs() -> list:
    docs = []
    try:
        from pypdf import PdfReader
        for pdf in Path("docs").glob("**/*.pdf"):
            try:
                text = "\n".join(p.extract_text() or "" for p in PdfReader(str(pdf)).pages)
                for ct in _chunk(text):
                    docs.append({"text": ct, "source": pdf.name, "type": "pdf",
                                 "job_title":"","company":"","location":"","url":""})
            except Exception:
                pass
    except ImportError:
        pass
    return docs

# ── Build ──────────────────────────────────────────────────────────────────────
def build_index(progress_callback=None) -> dict:
    from sentence_transformers import SentenceTransformer
    os.makedirs(DB_DIR, exist_ok=True)

    def _p(pct, msg):
        logger.info(f"[{pct}%] {msg}")
        if progress_callback:
            progress_callback(pct, msg)

    _p(5,  "Loading job listings...")
    raw = _load_jobs() + _load_pdfs()
    if not raw:
        raise ValueError("No data found. Scrape jobs first.")

    chunks = []
    for doc in raw:
        if doc["type"] == "job":
            chunks.append(doc)
        else:
            for ct in _chunk(doc["text"]):
                chunks.append({**doc, "text": ct})
    _p(18, f"{len(chunks)} chunks — loading embedding model...")

    model = SentenceTransformer(EMBED_MODEL)
    texts = [c["text"] for c in chunks]
    _p(28, "Embedding... (first run downloads ~80 MB)")

    all_emb = []
    for i in range(0, len(texts), EMBED_BATCH):
        emb = model.encode(texts[i:i+EMBED_BATCH],
                           normalize_embeddings=True, show_progress_bar=False)
        all_emb.append(emb)
        pct = 28 + int(44 * min(i+EMBED_BATCH, len(texts)) / len(texts))
        _p(pct, f"Embedded {min(i+EMBED_BATCH,len(texts))}/{len(texts)}...")

    embeddings = np.vstack(all_emb).astype("float32")
    _p(74, "Saving vector store...")
    np.save(EMBED_PATH, embeddings)
    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        json.dump({"chunks": [c["text"] for c in chunks],
                   "meta": [{k:v for k,v in c.items() if k!="text"} for c in chunks]}, f)

    _p(80, "Building knowledge graph...")
    G = nx.Graph()
    for idx, chunk in enumerate(chunks):
        cid  = f"chunk_{idx}"
        ents = extract_entities(chunk["text"])
        G.add_node(cid, type="chunk")
        for e in ents:
            if not G.has_node(e): G.add_node(e, type="entity")
            G.add_edge(cid, e)
        for i in range(len(ents)):
            for j in range(i+1, len(ents)):
                e1, e2 = ents[i], ents[j]
                if G.has_edge(e1,e2): G[e1][e2]["weight"] = G[e1][e2].get("weight",1)+1
                else:                 G.add_edge(e1, e2, weight=1)

    _p(94, "Saving graph...")
    with open(GRAPH_PATH, "w", encoding="utf-8") as f:
        json.dump(nx.node_link_data(G), f)

    stats = {"chunks": len(chunks), "graph_nodes": G.number_of_nodes(),
             "graph_edges": G.number_of_edges(), "built_at": datetime.now().isoformat()}
    _p(100, f"✅ {len(chunks)} chunks · {G.number_of_nodes()} nodes · {G.number_of_edges()} edges")
    return stats

# ── Loaders ────────────────────────────────────────────────────────────────────
def load_index():
    if not index_exists():
        raise FileNotFoundError("Index not built.")
    embeddings = np.load(EMBED_PATH)
    with open(CHUNKS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    with open(GRAPH_PATH, encoding="utf-8") as f:
        graph = nx.node_link_graph(json.load(f))
    logger.info(f"✅ Loaded {len(data['chunks'])} chunks")
    return embeddings, data["chunks"], data["meta"], graph

def index_exists() -> bool:
    return all(os.path.exists(p) for p in [EMBED_PATH, CHUNKS_PATH, GRAPH_PATH])

def data_is_newer_than_index() -> bool:
    if not index_exists(): return True
    try:
        t = os.path.getmtime(EMBED_PATH)
        return any(os.path.exists(p) and os.path.getmtime(p) > t for p in JOB_CSV_PATHS)
    except Exception:
        return False