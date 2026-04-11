"""
Graph RAG Retriever — pure NumPy cosine search + NetworkX BFS
No ChromaDB, no protobuf.
"""

import re, logging
import numpy as np
import networkx as nx

logger = logging.getLogger(__name__)

SKILL_KEYWORDS = {
    "python","javascript","typescript","java","c++","c#","go","rust",
    "react","vue","angular","node","django","flask","fastapi","spring",
    "sql","postgresql","mysql","mongodb","redis","elasticsearch",
    "docker","kubernetes","aws","azure","gcp","terraform",
    "machine learning","deep learning","nlp","data science","ai",
    "devops","backend","frontend","full stack","mobile","ios","android",
    "remote","cairo","egypt","giza","alexandria",
    "junior","senior","mid-level","manager","lead","intern",
}

def _embed(text: str, model) -> np.ndarray:
    emb = model.encode([text], normalize_embeddings=True, show_progress_bar=False)
    return emb[0].astype("float32")

def _query_entities(query: str) -> list:
    q = query.lower()
    found = {kw for kw in SKILL_KEYWORDS if kw in q}
    found |= {w.lower() for w in re.findall(r'\b[A-Z][a-zA-Z]{2,}\b', query) if len(w) <= 20}
    return list(found)


class GraphRAGRetriever:
    """
    Hybrid: cosine vector search  +  BFS knowledge graph expansion.

    embeddings : np.ndarray  shape (N, dim), L2-normalised
    chunks     : list[str]   raw text for each row in embeddings
    meta       : list[dict]  metadata for each chunk
    graph      : nx.Graph    entity-chunk co-occurrence graph
    model      : SentenceTransformer instance
    k          : top-k from vector search
    graph_k    : max extra chunks from graph
    hop_depth  : BFS hops
    """

    def __init__(self, embeddings, chunks, meta, graph, model,
                 k=6, graph_k=6, hop_depth=2):
        self.embeddings = embeddings
        self.chunks     = chunks
        self.meta       = meta
        self.graph      = graph
        self.model      = model
        self.k          = k
        self.graph_k    = graph_k
        self.hop_depth  = hop_depth

    # ── Vector search ─────────────────────────────────────────────────────────
    def _vector_search(self, query: str) -> tuple:
        q_emb = _embed(query, self.model)
        scores = self.embeddings @ q_emb          # cosine (embeddings are normalised)
        top_k  = min(self.k, len(scores))
        idx    = np.argsort(scores)[::-1][:top_k]
        return list(idx), scores[idx]

    # ── Graph BFS ─────────────────────────────────────────────────────────────
    def _graph_expand(self, seed_indices: list, query_entities: list) -> list:
        if not self.graph:
            return []
        graph_nodes = set(self.graph.nodes())
        seeds = [f"chunk_{i}" for i in seed_indices if f"chunk_{i}" in graph_nodes]
        seeds += [e for e in query_entities if e in graph_nodes]

        neighbor_ids = set()
        for seed in seeds[:8]:
            try:
                reachable = nx.single_source_shortest_path_length(
                    self.graph, seed, cutoff=self.hop_depth
                )
                for node in reachable:
                    if node.startswith("chunk_"):
                        idx = int(node.split("_")[1])
                        if idx not in seed_indices:
                            neighbor_ids.add(idx)
                        if len(neighbor_ids) >= self.graph_k * 2:
                            break
            except Exception:
                continue

        return list(neighbor_ids)[:self.graph_k]

    # ── Main retrieve ─────────────────────────────────────────────────────────
    def retrieve(self, query: str) -> tuple:
        """Returns (texts list, metas list)."""
        vec_idx, vec_scores = self._vector_search(query)
        entities             = _query_entities(query)
        graph_idx            = self._graph_expand(vec_idx, entities)

        # Merge — vector results first (ranked), then graph extras
        seen   = set(vec_idx)
        all_idx = list(vec_idx)
        for i in graph_idx:
            if i not in seen:
                seen.add(i)
                all_idx.append(i)

        texts = [self.chunks[i] for i in all_idx]
        metas = [self.meta[i]   for i in all_idx]

        logger.info(
            f"GraphRAG: {len(vec_idx)} vector + {len(all_idx)-len(vec_idx)} graph "
            f"= {len(all_idx)} chunks | entities: {entities[:5]}"
        )
        return texts, metas

    def get_context_string(self, query: str, max_chars: int = 4000) -> str:
        texts, metas = self.retrieve(query)
        parts, total = [], 0
        for i, (text, meta) in enumerate(zip(texts, metas)):
            src   = meta.get("source", "?")
            jtype = meta.get("type",   "?")
            block = f"[{i+1}] ({src} · {jtype})\n{text.strip()}"
            if total + len(block) > max_chars:
                break
            parts.append(block)
            total += len(block)
        return "\n\n---\n\n".join(parts)