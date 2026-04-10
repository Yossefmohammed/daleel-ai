"""
graph_retriever.py
==================
Graph RAG retrieval strategy.

For a given query the retriever:
  1. Runs standard vector similarity search → seed chunks
  2. Extracts entities from the query
  3. Expands via the knowledge graph: for each query entity, walks up to
     `hop_depth` hops and collects neighbouring chunk IDs
  4. Fetches those chunks from the vector store (by metadata id)
  5. Returns a merged, deduplicated, re-ranked list of Documents
"""

import re
from typing import List, Optional
from langchain_core.documents import Document
import networkx as nx


class GraphRetriever:
    """
    Hybrid retriever that combines dense vector search with graph traversal.

    Parameters
    ----------
    vectorstore : ChromaDB vectorstore (langchain wrapper)
    graph       : nx.Graph built by KnowledgeGraphBuilder
    k           : top-k chunks from vector search
    graph_k     : max extra chunks harvested from graph expansion
    hop_depth   : BFS depth when walking the knowledge graph
    """

    def __init__(
        self,
        vectorstore,
        graph: nx.Graph,
        k: int = 5,
        graph_k: int = 5,
        hop_depth: int = 2,
    ):
        self.vs = vectorstore
        self.G = graph
        self.k = k
        self.graph_k = graph_k
        self.hop_depth = hop_depth

    # ── Public API ─────────────────────────────────────────────────────────────

    def get_relevant_documents(self, query: str) -> List[Document]:
        """Return hybrid-retrieved documents for the query."""
        # 1. Vector retrieval (seed)
        vector_docs = self._vector_search(query)

        # 2. Extract query entities and graph-expand
        query_entities = self._extract_query_entities(query)
        graph_chunk_ids = self._graph_expand(query_entities)

        # 3. Fetch graph-sourced chunks that aren't already in vector_docs
        existing_ids = {self._doc_id(d) for d in vector_docs}
        graph_docs = self._fetch_by_chunk_ids(graph_chunk_ids, exclude=existing_ids)

        # 4. Merge: vector docs first, then graph-augmented docs
        merged = vector_docs + graph_docs[: self.graph_k]
        return merged

    # Alias so it can be used as a LangChain-compatible retriever
    def invoke(self, query: str) -> List[Document]:
        return self.get_relevant_documents(query)

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _vector_search(self, query: str) -> List[Document]:
        try:
            retriever = self.vs.as_retriever(
                search_type="mmr",
                search_kwargs={"k": self.k, "fetch_k": self.k * 3},
            )
            return retriever.get_relevant_documents(query)
        except Exception:
            # Fallback to similarity search
            return self.vs.similarity_search(query, k=self.k)

    def _extract_query_entities(self, query: str) -> List[str]:
        """
        Simple entity extraction from the query string.
        Returns lower-cased tokens / phrases that appear as graph nodes.
        """
        if self.G.number_of_nodes() == 0:
            return []

        found = []
        query_lower = query.lower()

        # Check every node label against the query
        for node in self.G.nodes():
            # node keys are lower-cased
            if node in query_lower:
                found.append(node)

        # Also try individual words
        words = re.findall(r'\b\w{3,}\b', query_lower)
        for w in words:
            if w in self.G.nodes and w not in found:
                found.append(w)

        return found

    def _graph_expand(self, entities: List[str]) -> List[str]:
        """
        BFS expansion from query entities.
        Returns a flat list of chunk_ids (from node mentions + edge chunk_ids).
        """
        chunk_ids = []
        visited_nodes = set()

        for entity in entities:
            if entity not in self.G:
                continue
            # BFS up to hop_depth
            bfs_nodes = nx.single_source_shortest_path_length(
                self.G, entity, cutoff=self.hop_depth
            )
            for node, depth in bfs_nodes.items():
                if node in visited_nodes:
                    continue
                visited_nodes.add(node)
                # Collect chunk ids from node
                node_data = self.G.nodes[node]
                chunk_ids.extend(node_data.get("mentions", []))

                # Collect chunk ids from edges
                for nbr in self.G.neighbors(node):
                    edge_data = self.G[node][nbr]
                    chunk_ids.extend(edge_data.get("chunk_ids", []))

        # Deduplicate while preserving order
        seen = set()
        unique = []
        for cid in chunk_ids:
            if cid not in seen:
                seen.add(cid)
                unique.append(cid)
        return unique

    def _fetch_by_chunk_ids(
        self, chunk_ids: List[str], exclude: set
    ) -> List[Document]:
        """
        Retrieve documents from ChromaDB by their chunk IDs.
        Falls back to empty list if the store doesn't support id-based lookup.
        """
        if not chunk_ids:
            return []

        docs = []
        try:
            # ChromaDB supports `get` with ids
            collection = self.vs._collection
            # Convert chunk_ids to int offsets for Chroma (it stores them as str ids)
            result = collection.get(ids=chunk_ids, include=["documents", "metadatas"])
            for text, meta in zip(result["documents"], result["metadatas"]):
                doc = Document(page_content=text, metadata=meta or {})
                if self._doc_id(doc) not in exclude:
                    docs.append(doc)
        except Exception:
            pass
        return docs

    def _doc_id(self, doc: Document) -> str:
        return doc.page_content[:80]  # use content prefix as surrogate id


# ── Convenience factory ────────────────────────────────────────────────────────

def build_graph_retriever(vectorstore, graph: nx.Graph, **kwargs) -> GraphRetriever:
    return GraphRetriever(vectorstore=vectorstore, graph=graph, **kwargs)