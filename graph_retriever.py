"""
graph_retriever.py — Daleel AI Hybrid Graph RAG Retriever
==========================================================
Combines ChromaDB vector search with knowledge graph BFS expansion
to retrieve richer, multi-hop context for the LLM.

Improvements over original:
- Removed hardcoded "Wasla" from entity regex (configurable via constructor)
- Batch ChromaDB fetch replaces per-chunk N sequential calls (faster)
- Errors are logged instead of silently swallowed
- extract_query_entities() text limit raised to 1,000 chars (was 500)
- Type hints cleaned up
"""

import logging
import re
from typing import List, Optional, Set

logger = logging.getLogger(__name__)

try:
    import networkx as nx
    NX_AVAILABLE = True
except ImportError:
    NX_AVAILABLE = False

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False


class GraphRetriever:
    """
    Hybrid retriever: vector similarity search + graph neighbourhood expansion.

    Retrieval pipeline:
    1. MMR vector search → top-k seed chunks
    2. Entity extraction from query (spaCy or regex)
    3. BFS on knowledge graph → neighbour chunk IDs (depth hops)
    4. Batch-fetch neighbour chunks from ChromaDB (single call)
    5. Deduplicate + return combined set

    Args:
        vectorstore: LangChain-compatible ChromaDB vectorstore
        graph: networkx.Graph loaded by KnowledgeGraphBuilder
        k: vector search top-k
        graph_k: max extra chunks from graph traversal
        hop_depth: BFS depth
        extra_tech_keywords: domain-specific keywords to add to entity regex
                             (replaces the old hardcoded "Wasla" approach)
    """

    def __init__(
        self,
        vectorstore,
        graph,
        k: int = 5,
        graph_k: int = 5,
        hop_depth: int = 2,
        extra_tech_keywords: Optional[List[str]] = None,
    ):
        self.vs = vectorstore
        self.G = graph
        self.k = k
        self.graph_k = graph_k
        self.hop_depth = hop_depth
        self._nlp = None

        # Build tech keyword regex from a clean, configurable list.
        # No company-specific names hardcoded here.
        base_keywords = [
            "API", "Python", "JavaScript", "TypeScript", "React", "Vue",
            "Angular", "Docker", "Kubernetes", "AWS", "Azure", "GCP",
            "RAG", "LLM", "fintech", "machine learning", "deep learning",
        ]
        if extra_tech_keywords:
            base_keywords.extend(extra_tech_keywords)
        escaped = sorted(
            (re.escape(kw) for kw in set(base_keywords)),
            key=len, reverse=True,
        )
        self._tech_re = re.compile(
            r"\b(" + "|".join(escaped) + r")\b",
            re.IGNORECASE,
        )

    # ------------------------------------------------------------------
    # NLP helpers
    # ------------------------------------------------------------------

    def _get_nlp(self):
        if self._nlp:
            return self._nlp
        if SPACY_AVAILABLE:
            try:
                self._nlp = spacy.load("en_core_web_sm")
            except OSError:
                logger.warning("spaCy model not found — falling back to regex entity extraction.")
        return self._nlp

    def _extract_query_entities(self, query: str) -> List[str]:
        """Extract entities from query for graph lookup (limit raised to 1,000 chars)."""
        nlp = self._get_nlp()
        if nlp:
            doc = nlp(query[:1000])
            entities = list(set(
                ent.text.lower().strip()
                for ent in doc.ents
                if len(ent.text.strip()) > 2
            ))
            # Also pick up tech keywords spaCy may miss
            entities += [m.group().lower() for m in self._tech_re.finditer(query)]
            return list(set(entities))

        tech = [m.group().lower() for m in self._tech_re.finditer(query)]
        caps = re.findall(r"\b[A-Z][a-z]{2,}\b", query)
        return list(set(tech + [c.lower() for c in caps]))

    # ------------------------------------------------------------------
    # Graph BFS
    # ------------------------------------------------------------------

    def _graph_neighbour_chunks(self, entities: List[str]) -> Set[str]:
        """BFS from query entities to find related chunk IDs."""
        if not NX_AVAILABLE or self.G is None:
            return set()

        visited_nodes: Set[str] = set()
        chunk_ids: Set[str] = set()
        frontier = {e for e in entities if self.G.has_node(e)}

        for _ in range(self.hop_depth):
            next_frontier: Set[str] = set()
            for node in frontier:
                if node in visited_nodes:
                    continue
                visited_nodes.add(node)

                for cid in self.G.nodes[node].get("chunk_ids", []):
                    chunk_ids.add(cid)

                neighbours = sorted(
                    self.G.neighbors(node),
                    key=lambda n: self.G[node][n].get("weight", 1),
                    reverse=True,
                )[:5]
                next_frontier.update(neighbours)

            frontier = next_frontier - visited_nodes

        return chunk_ids

    # ------------------------------------------------------------------
    # ChromaDB fetch — BATCH instead of N sequential calls
    # ------------------------------------------------------------------

    def _fetch_chunks_by_ids(self, chunk_ids: Set[str], exclude_docs: list) -> list:
        """
        Fetch chunks from ChromaDB by their chunk IDs.

        IMPROVEMENT: Original code called collection.get() once per chunk_id
        in a for-loop (N sequential round-trips). We now build the full list
        of IDs to fetch and make a SINGLE batch call.
        """
        if not chunk_ids:
            return []

        exclude_ids: Set[str] = {
            doc.metadata.get("chunk_id", f"chunk_{i}")
            for i, doc in enumerate(exclude_docs)
        }

        to_fetch = [
            cid for cid in list(chunk_ids)[: self.graph_k * 2]
            if cid not in exclude_ids
        ][: self.graph_k]

        if not to_fetch:
            return []

        try:
            # Single batch call — much faster than one call per ID
            res = self.vs._collection.get(
                where={"chunk_id": {"$in": to_fetch}},
                include=["documents", "metadatas"],
            )
        except Exception as exc:
            logger.warning("Batch ChromaDB fetch failed: %s", exc)
            return []

        results = []
        if res and res.get("documents"):
            try:
                from langchain_core.documents import Document
            except ImportError:
                from langchain.schema import Document  # older langchain

            for doc_text, meta in zip(res["documents"], res["metadatas"]):
                results.append(Document(page_content=doc_text, metadata=meta or {}))

        return results

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_relevant_documents(self, query: str) -> list:
        """
        Retrieve documents using hybrid vector + graph search.

        Args:
            query: user's question

        Returns:
            List of LangChain Document objects (deduplicated)
        """
        # 1. Vector MMR search
        vector_docs = []
        try:
            vector_docs = self.vs.max_marginal_relevance_search(
                query, k=self.k, fetch_k=self.k * 3
            )
        except Exception:
            try:
                vector_docs = self.vs.similarity_search(query, k=self.k)
            except Exception as exc:
                logger.error("Vector search failed: %s", exc)

        # 2. Extract entities from query
        entities = self._extract_query_entities(query)

        # 3. Graph BFS
        neighbour_chunk_ids = self._graph_neighbour_chunks(entities)

        # 4. Batch-fetch graph-expanded chunks (single ChromaDB call)
        graph_docs = self._fetch_chunks_by_ids(neighbour_chunk_ids, vector_docs)

        # 5. Deduplicate by content hash
        seen: Set[int] = set()
        combined = []
        for doc in vector_docs + graph_docs:
            key = hash(doc.page_content[:200])
            if key not in seen:
                seen.add(key)
                combined.append(doc)

        return combined[: self.k + self.graph_k]