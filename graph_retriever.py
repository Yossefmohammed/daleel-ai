"""
graph_retriever.py — PathIQ Hybrid Graph RAG Retriever
=======================================================
Combines ChromaDB vector search with knowledge graph BFS expansion
to retrieve richer, multi-hop context for the LLM.
"""

import re
from typing import Optional

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
        4. Fetch neighbour chunks from vector store
        5. Deduplicate + return combined set
    """

    def __init__(
        self,
        vectorstore,
        graph,                  # networkx.Graph
        k: int = 5,             # vector search top-k
        graph_k: int = 5,       # max extra chunks from graph
        hop_depth: int = 2,     # BFS depth
    ):
        self.vs         = vectorstore
        self.G          = graph
        self.k          = k
        self.graph_k    = graph_k
        self.hop_depth  = hop_depth
        self._nlp       = None

    def _get_nlp(self):
        if self._nlp:
            return self._nlp
        if SPACY_AVAILABLE:
            try:
                self._nlp = spacy.load("en_core_web_sm")
            except OSError:
                pass
        return self._nlp

    def _extract_query_entities(self, query: str) -> list[str]:
        """Extract entities from query for graph lookup."""
        nlp = self._get_nlp()
        if nlp:
            doc = nlp(query[:500])
            return list(set(
                ent.text.lower().strip()
                for ent in doc.ents
                if len(ent.text.strip()) > 2
            ))
        # Fallback: extract capitalized words and tech keywords
        tech = re.findall(
            r'\b(API|Python|JavaScript|React|Docker|AWS|Azure|Wasla|RAG|LLM|fintech)\b',
            query, re.IGNORECASE,
        )
        caps = re.findall(r'\b[A-Z][a-z]{2,}\b', query)
        return list(set(e.lower() for e in tech + caps))

    def _graph_neighbour_chunks(self, entities: list[str]) -> set[str]:
        """BFS from query entities to find related chunk IDs."""
        if not NX_AVAILABLE or self.G is None:
            return set()

        visited_nodes = set()
        chunk_ids     = set()
        frontier      = set(e for e in entities if self.G.has_node(e))

        for _ in range(self.hop_depth):
            next_frontier = set()
            for node in frontier:
                if node in visited_nodes:
                    continue
                visited_nodes.add(node)
                # Collect chunk IDs from this node
                for cid in self.G.nodes[node].get("chunk_ids", []):
                    chunk_ids.add(cid)
                # Expand to neighbours (sorted by edge weight, descending)
                neighbours = sorted(
                    self.G.neighbors(node),
                    key=lambda n: self.G[node][n].get("weight", 1),
                    reverse=True,
                )[:5]
                next_frontier.update(neighbours)
            frontier = next_frontier - visited_nodes

        return chunk_ids

    def _fetch_chunks_by_ids(self, chunk_ids: set, exclude_docs: list) -> list:
        """Fetch chunks from vector store by their chunk IDs."""
        if not chunk_ids:
            return []

        exclude_ids = {
            doc.metadata.get("chunk_id", f"chunk_{i}")
            for i, doc in enumerate(exclude_docs)
        }
        to_fetch = [cid for cid in list(chunk_ids)[:self.graph_k * 2]
                    if cid not in exclude_ids]

        results = []
        for chunk_id in to_fetch[:self.graph_k]:
            try:
                # ChromaDB lookup by metadata filter
                res = self.vs._collection.get(
                    where={"chunk_id": {"$eq": chunk_id}},
                    include=["documents", "metadatas"],
                )
                if res and res.get("documents"):
                    from langchain_core.documents import Document
                    for doc_text, meta in zip(res["documents"], res["metadatas"]):
                        results.append(Document(page_content=doc_text, metadata=meta or {}))
            except Exception:
                pass  # silently skip unavailable chunks

        return results

    def get_relevant_documents(self, query: str) -> list:
        """
        Retrieve documents using hybrid vector + graph search.

        Args:
            query: user's question

        Returns:
            List of LangChain Document objects (deduplicated)
        """
        # 1. Vector MMR search
        try:
            vector_docs = self.vs.max_marginal_relevance_search(query, k=self.k, fetch_k=self.k * 3)
        except Exception:
            try:
                vector_docs = self.vs.similarity_search(query, k=self.k)
            except Exception:
                vector_docs = []

        # 2. Extract entities from query
        entities = self._extract_query_entities(query)

        # 3. Graph BFS
        neighbour_chunk_ids = self._graph_neighbour_chunks(entities)

        # 4. Fetch graph-expanded chunks
        graph_docs = self._fetch_chunks_by_ids(neighbour_chunk_ids, vector_docs)

        # 5. Deduplicate by content hash
        seen     = set()
        combined = []
        for doc in vector_docs + graph_docs:
            key = hash(doc.page_content[:200])
            if key not in seen:
                seen.add(key)
                combined.append(doc)

        return combined[:self.k + self.graph_k]