"""
graph_builder.py — PathIQ Knowledge Graph Builder
==================================================
Builds an entity co-occurrence knowledge graph from document chunks.
Used by GraphRetriever to expand vector search results.
"""

import os
import json
import re
from pathlib import Path
from collections import defaultdict
from typing import Callable, Optional

GRAPH_PATH = "db/knowledge_graph.json"

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


class KnowledgeGraphBuilder:
    """
    Builds and persists a knowledge graph from document chunks.

    Nodes  = named entities (ORG, PERSON, PRODUCT, GPE, TECH keywords)
    Edges  = co-occurrence within the same chunk (weighted by frequency)
    Each node stores a list of chunk IDs it appears in.
    """

    def __init__(self, graph_path: str = GRAPH_PATH):
        self.graph_path = graph_path
        self.G = nx.Graph() if NX_AVAILABLE else None
        self._nlp = None

    def _get_nlp(self):
        if self._nlp:
            return self._nlp
        if SPACY_AVAILABLE:
            try:
                self._nlp = spacy.load("en_core_web_sm")
                return self._nlp
            except OSError:
                pass
        return None

    def _extract_entities(self, text: str) -> list[str]:
        """Extract named entities from text using spaCy or regex fallback."""
        nlp = self._get_nlp()
        if nlp:
            doc = nlp(text[:1000])  # limit for speed
            entities = [
                ent.text.lower().strip()
                for ent in doc.ents
                if ent.label_ in {"ORG", "PERSON", "PRODUCT", "GPE", "WORK_OF_ART", "EVENT"}
                and len(ent.text.strip()) > 2
            ]
            return list(set(entities))

        # Regex fallback: extract capitalized phrases and tech keywords
        tech_pattern = r'\b(API|REST|GraphQL|Python|JavaScript|React|Django|FastAPI|Docker|'
        tech_pattern += r'Kubernetes|AWS|Azure|GCP|Postgres|MongoDB|Redis|Git|CI/CD|LLM|RAG|'
        tech_pattern += r'Wasla|fintech|startup|enterprise)\b'
        cap_pattern   = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'

        entities = re.findall(tech_pattern, text, re.IGNORECASE)
        entities += re.findall(cap_pattern, text)
        return list(set(e.lower().strip() for e in entities if len(e) > 2))[:15]

    def build_from_documents(
        self,
        chunks: list,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        """
        Build graph from a list of LangChain Document chunks.

        Args:
            chunks: list of Document objects with .page_content and .metadata
            progress_callback: optional fn(done, total) for progress reporting
        """
        if not NX_AVAILABLE:
            raise ImportError("Install networkx: pip install networkx")

        self.G = nx.Graph()
        total = len(chunks)

        for i, chunk in enumerate(chunks):
            chunk_id  = f"chunk_{i}"
            text      = chunk.page_content
            entities  = self._extract_entities(text)

            # Add/update nodes
            for ent in entities:
                if self.G.has_node(ent):
                    self.G.nodes[ent]["chunk_ids"].append(chunk_id)
                    self.G.nodes[ent]["frequency"] += 1
                else:
                    self.G.add_node(ent, chunk_ids=[chunk_id], frequency=1)

            # Add co-occurrence edges
            for j, e1 in enumerate(entities):
                for e2 in entities[j+1:]:
                    if self.G.has_edge(e1, e2):
                        self.G[e1][e2]["weight"] += 1
                    else:
                        self.G.add_edge(e1, e2, weight=1)

            if progress_callback:
                progress_callback(i + 1, total)

        self._save()

    def _save(self):
        Path(self.graph_path).parent.mkdir(parents=True, exist_ok=True)
        data = {
            "nodes": [
                {"id": n, **self.G.nodes[n]} for n in self.G.nodes
            ],
            "edges": [
                {"source": u, "target": v, **self.G[u][v]}
                for u, v in self.G.edges
            ],
        }
        # Convert chunk_ids lists to JSON-serializable form
        for node in data["nodes"]:
            node["chunk_ids"] = list(node.get("chunk_ids", []))

        with open(self.graph_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self) -> bool:
        """Load graph from JSON. Returns True if successful."""
        if not NX_AVAILABLE:
            return False
        if not Path(self.graph_path).exists():
            return False
        try:
            with open(self.graph_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.G = nx.Graph()
            for node in data.get("nodes", []):
                nid = node.pop("id")
                self.G.add_node(nid, **node)
            for edge in data.get("edges", []):
                self.G.add_edge(edge["source"], edge["target"],
                                weight=edge.get("weight", 1))
            return True
        except Exception:
            return False

    def stats(self) -> dict:
        if not self.G:
            return {"nodes": 0, "edges": 0}
        return {"nodes": self.G.number_of_nodes(), "edges": self.G.number_of_edges()}