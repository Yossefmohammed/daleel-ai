"""
Graph RAG Retriever
Combines two retrieval strategies for richer, multi-hop answers:

  Step 1 — Vector search (ChromaDB)
           Finds top-k chunks semantically similar to the query.

  Step 2 — Entity extraction
           Pulls skill/location/role keywords from the query.

  Step 3 — Graph traversal (NetworkX BFS)
           Walks the knowledge graph from query entities outward
           (up to hop_depth hops) to find related chunk IDs.

  Step 4 — Fetch graph neighbors from ChromaDB
           Retrieves those extra chunks from the vector store.

  Step 5 — Deduplicate + rank
           Returns merged, deduplicated context string.
"""

import re
import logging
import networkx as nx

logger = logging.getLogger(__name__)

# Same keyword set as ingest for consistent entity matching
SKILL_KEYWORDS = {
    "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust",
    "react", "vue", "angular", "node", "django", "flask", "fastapi", "spring",
    "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "docker", "kubernetes", "aws", "azure", "gcp", "terraform", "ci/cd",
    "machine learning", "deep learning", "nlp", "data science", "ai",
    "devops", "backend", "frontend", "full stack", "mobile", "ios", "android",
    "remote", "cairo", "egypt", "giza", "alexandria",
    "junior", "senior", "mid-level", "manager", "lead", "intern",
}


def _extract_query_entities(query: str) -> list[str]:
    """Extract entities from the user query to seed graph traversal."""
    q = query.lower()
    found = set()

    for kw in SKILL_KEYWORDS:
        if kw in q:
            found.add(kw)

    caps = re.findall(r'\b[A-Z][a-zA-Z]{2,}\b', query)
    for word in caps:
        found.add(word.lower())

    return list(found)


class GraphRAGRetriever:
    """
    Hybrid retriever: ChromaDB vector search + NetworkX BFS expansion.

    Args:
        collection : ChromaDB collection object
        graph      : NetworkX graph (loaded from db/knowledge_graph.json)
        k          : number of chunks from vector search
        graph_k    : max extra chunks from graph traversal
        hop_depth  : BFS depth in the knowledge graph
    """

    def __init__(self, collection, graph: nx.Graph, k: int = 6, graph_k: int = 6, hop_depth: int = 2):
        self.collection = collection
        self.graph      = graph
        self.k          = k
        self.graph_k    = graph_k
        self.hop_depth  = hop_depth

    def retrieve(self, query: str) -> tuple[list[str], list[dict]]:
        """
        Returns (context_texts, metadata_list).
        context_texts — list of chunk strings
        metadata_list — list of metadata dicts for citations
        """
        # ── Step 1: Vector search ─────────────────────────────────────────────
        try:
            vec_results = self.collection.query(
                query_texts=[query],
                n_results=min(self.k, self.collection.count()),
                include=["documents", "metadatas", "distances"],
            )
            seed_docs  = vec_results["documents"][0]   if vec_results["documents"]  else []
            seed_meta  = vec_results["metadatas"][0]   if vec_results["metadatas"]  else []
            seed_ids   = vec_results["ids"][0]         if vec_results["ids"]        else []
        except Exception as e:
            logger.warning(f"⚠️  Vector search failed: {e}")
            seed_docs, seed_meta, seed_ids = [], [], []

        if not seed_docs:
            return [], []

        # ── Step 2: Entity extraction ─────────────────────────────────────────
        query_entities = _extract_query_entities(query)

        # ── Step 3: BFS graph traversal ───────────────────────────────────────
        neighbor_chunk_ids: set[str] = set()

        if self.graph and query_entities:
            # Find entity nodes that exist in the graph
            graph_nodes = set(self.graph.nodes())
            seed_entities = [e for e in query_entities if e in graph_nodes]

            # Also seed from the vector-found chunk IDs
            seed_entities += [cid for cid in seed_ids if cid in graph_nodes]

            for seed in seed_entities[:8]:   # cap seeds
                try:
                    # BFS up to hop_depth
                    reachable = nx.single_source_shortest_path_length(
                        self.graph, seed, cutoff=self.hop_depth
                    )
                    for node, depth in reachable.items():
                        # Only collect chunk nodes (they start with "chunk_")
                        if node.startswith("chunk_") and node not in seed_ids:
                            neighbor_chunk_ids.add(node)
                            if len(neighbor_chunk_ids) >= self.graph_k * 3:
                                break
                except Exception:
                    continue

        # ── Step 4: Fetch graph neighbors from ChromaDB ───────────────────────
        graph_docs:  list[str]  = []
        graph_metas: list[dict] = []

        if neighbor_chunk_ids:
            fetch_ids = list(neighbor_chunk_ids)[:self.graph_k * 2]
            try:
                gr = self.collection.get(
                    ids=fetch_ids,
                    include=["documents", "metadatas"],
                )
                graph_docs  = gr.get("documents", []) or []
                graph_metas = gr.get("metadatas",  []) or []
            except Exception as e:
                logger.warning(f"⚠️  Graph fetch failed: {e}")

        # ── Step 5: Deduplicate + merge ───────────────────────────────────────
        seen:    set[str]  = set(seed_docs)
        all_docs:  list[str]  = list(seed_docs)
        all_metas: list[dict] = list(seed_meta)

        for doc, meta in zip(graph_docs, graph_metas):
            if doc not in seen and len(all_docs) < self.k + self.graph_k:
                seen.add(doc)
                all_docs.append(doc)
                all_metas.append(meta)

        logger.info(
            f"GraphRAG: {len(seed_docs)} vector + "
            f"{len(all_docs) - len(seed_docs)} graph = "
            f"{len(all_docs)} total chunks | "
            f"entities found: {query_entities[:5]}"
        )
        return all_docs, all_metas

    def get_context_string(self, query: str, max_chars: int = 4000) -> str:
        """
        Run retrieval and return a formatted context string
        ready to be injected into an LLM prompt.
        """
        docs, metas = self.retrieve(query)
        if not docs:
            return ""

        parts = []
        total = 0
        for i, (doc, meta) in enumerate(zip(docs, metas)):
            source = meta.get("source", "?") if meta else "?"
            jtype  = meta.get("type",   "?") if meta else "?"
            header = f"[{i+1}] ({source}, {jtype})"
            block  = f"{header}\n{doc.strip()}"
            if total + len(block) > max_chars:
                break
            parts.append(block)
            total += len(block)

        return "\n\n---\n\n".join(parts)