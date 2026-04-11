"""rag_retriever.py — cosine vector search + NetworkX BFS graph expansion."""
import re, logging
import numpy as np
import networkx as nx
from constant import SKILL_KEYWORDS, VECTOR_K, GRAPH_K, HOP_DEPTH, MAX_CONTEXT

logger = logging.getLogger(__name__)

def _embed(text: str, model) -> np.ndarray:
    return model.encode([text], normalize_embeddings=True,
                        show_progress_bar=False)[0].astype("float32")

def _entities(query: str) -> list:
    q   = query.lower()
    ent = {kw for kw in SKILL_KEYWORDS if kw in q}
    ent |= {w.lower() for w in re.findall(r'\b[A-Z][a-zA-Z]{2,}\b', query) if len(w)<=20}
    return list(ent)

class GraphRAGRetriever:
    def __init__(self, embeddings, chunks, meta, graph, model,
                 k=VECTOR_K, graph_k=GRAPH_K, hop_depth=HOP_DEPTH):
        self.embeddings = embeddings
        self.chunks     = chunks
        self.meta       = meta
        self.graph      = graph
        self.model      = model
        self.k          = k
        self.graph_k    = graph_k
        self.hop_depth  = hop_depth

    def _vector_search(self, query: str):
        q_emb  = _embed(query, self.model)
        scores = self.embeddings @ q_emb
        top_k  = min(self.k, len(scores))
        idx    = np.argsort(scores)[::-1][:top_k]
        return list(idx), scores[idx]

    def _graph_expand(self, seed_idx: list, entities: list) -> list:
        if not self.graph: return []
        nodes = set(self.graph.nodes())
        seeds = [f"chunk_{i}" for i in seed_idx if f"chunk_{i}" in nodes]
        seeds += [e for e in entities if e in nodes]
        extra = set()
        for seed in seeds[:8]:
            try:
                for node in nx.single_source_shortest_path_length(
                        self.graph, seed, cutoff=self.hop_depth):
                    if node.startswith("chunk_"):
                        idx = int(node.split("_")[1])
                        if idx not in seed_idx:
                            extra.add(idx)
                    if len(extra) >= self.graph_k * 2: break
            except Exception: continue
        return list(extra)[:self.graph_k]

    def retrieve(self, query: str):
        vec_idx, _ = self._vector_search(query)
        ents       = _entities(query)
        graph_idx  = self._graph_expand(vec_idx, ents)
        seen   = set(vec_idx)
        all_idx = list(vec_idx)
        for i in graph_idx:
            if i not in seen:
                seen.add(i); all_idx.append(i)
        logger.info(f"GraphRAG: {len(vec_idx)} vector + {len(all_idx)-len(vec_idx)} graph | ents:{ents[:4]}")
        return [self.chunks[i] for i in all_idx], [self.meta[i] for i in all_idx]

    def get_context_string(self, query: str) -> str:
        texts, metas = self.retrieve(query)
        parts, total = [], 0
        for i, (t, m) in enumerate(zip(texts, metas)):
            src   = (m or {}).get("source", "?")
            block = f"[{i+1}] {src}\n{t.strip()}"
            if total + len(block) > MAX_CONTEXT: break
            parts.append(block); total += len(block)
        return "\n\n---\n\n".join(parts)