"""
graph_builder.py — Daleel AI Knowledge Graph Builder
=====================================================
Builds an entity co-occurrence knowledge graph from document chunks.
Used by GraphRetriever to expand vector search results.

Improvements over original:
- Removed hardcoded "Wasla" company name from entity regex
- Fixed node.pop("id") mutation bug in load() — now uses node.get() + exclusion
- Raised NLP text limit from 1,000 → 3,000 chars for better entity coverage
- Added logging instead of silent failures
- Made tech_keywords configurable via constructor
"""

import json
import logging
import re
from pathlib import Path
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)

GRAPH_PATH = "db/knowledge_graph.json"

# Default tech keywords — no company-specific names here.
# Pass custom_keywords to KnowledgeGraphBuilder.__init__() to extend.
DEFAULT_TECH_KEYWORDS = [
    "API", "REST", "GraphQL", "Python", "JavaScript", "TypeScript",
    "React", "Vue", "Angular", "Django", "FastAPI", "Flask",
    "Docker", "Kubernetes", "AWS", "Azure", "GCP",
    "Postgres", "PostgreSQL", "MongoDB", "Redis", "MySQL",
    "Git", "CI/CD", "LLM", "RAG", "fintech", "startup", "enterprise",
    "machine learning", "deep learning", "NLP", "computer vision",
]

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

    Nodes = named entities (ORG, PERSON, PRODUCT, GPE, TECH keywords)
    Edges = co-occurrence within the same chunk (weighted by frequency)
    Each node stores a list of chunk IDs it appears in.

    Args:
        graph_path: where to persist the JSON graph
        custom_keywords: additional tech/domain keywords to extract
                         (merged with DEFAULT_TECH_KEYWORDS)
    """

    def __init__(
        self,
        graph_path: str = GRAPH_PATH,
        custom_keywords: Optional[List[str]] = None,
    ):
        self.graph_path = graph_path
        self.G = nx.Graph() if NX_AVAILABLE else None
        self._nlp = None

        keywords = list(DEFAULT_TECH_KEYWORDS)
        if custom_keywords:
            keywords.extend(custom_keywords)
        # Build a single regex from the keyword list (escaped, sorted longest-first)
        escaped = sorted(
            (re.escape(kw) for kw in set(keywords)),
            key=len,
            reverse=True,
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
                return self._nlp
            except OSError:
                logger.warning("spaCy model 'en_core_web_sm' not found. "
                               "Run: python -m spacy download en_core_web_sm")
        return None

    def _extract_entities(self, text: str) -> List[str]:
        """
        Extract named entities from text using spaCy or regex fallback.

        Limit raised to 3,000 chars (was 1,000) so entities from longer
        chunks are not silently missed.
        """
        nlp = self._get_nlp()
        if nlp:
            doc = nlp(text[:3000])
            entities = [
                ent.text.lower().strip()
                for ent in doc.ents
                if ent.label_ in {
                    "ORG", "PERSON", "PRODUCT", "GPE",
                    "WORK_OF_ART", "EVENT",
                }
                and len(ent.text.strip()) > 2
            ]
            # Also pull tech keywords (spaCy often misses these)
            entities += [
                m.group().lower()
                for m in self._tech_re.finditer(text[:3000])
            ]
            return list(set(entities))

        # Regex-only fallback
        tech_hits = [m.group().lower() for m in self._tech_re.finditer(text)]
        cap_hits = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text)
        combined = tech_hits + [e.lower().strip() for e in cap_hits if len(e) > 2]
        return list(set(combined))[:20]

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

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
            chunk_id = f"chunk_{i}"
            text = chunk.page_content
            entities = self._extract_entities(text)

            for ent in entities:
                if self.G.has_node(ent):
                    self.G.nodes[ent]["chunk_ids"].append(chunk_id)
                    self.G.nodes[ent]["frequency"] += 1
                else:
                    self.G.add_node(ent, chunk_ids=[chunk_id], frequency=1)

            for j, e1 in enumerate(entities):
                for e2 in entities[j + 1:]:
                    if self.G.has_edge(e1, e2):
                        self.G[e1][e2]["weight"] += 1
                    else:
                        self.G.add_edge(e1, e2, weight=1)

            if progress_callback:
                progress_callback(i + 1, total)

        self._save()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save(self) -> None:
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
        for node in data["nodes"]:
            node["chunk_ids"] = list(node.get("chunk_ids", []))

        with open(self.graph_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("Graph saved: %s nodes, %s edges → %s",
                    self.G.number_of_nodes(), self.G.number_of_edges(),
                    self.graph_path)

    def load(self) -> bool:
        """
        Load graph from JSON. Returns True if successful.

        FIX: original code called node.pop("id") which mutated the dict
        from json.load() — on a second call the key was already gone.
        Now we use node.get("id") and build attrs without "id".
        """
        if not NX_AVAILABLE:
            return False
        if not Path(self.graph_path).exists():
            return False

        try:
            with open(self.graph_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.G = nx.Graph()

            for node in data.get("nodes", []):
                nid = node.get("id")          # ← get, not pop
                if nid is None:
                    continue
                attrs = {k: v for k, v in node.items() if k != "id"}
                self.G.add_node(nid, **attrs)

            for edge in data.get("edges", []):
                self.G.add_edge(
                    edge["source"],
                    edge["target"],
                    weight=edge.get("weight", 1),
                )
            return True

        except Exception as exc:
            logger.error("Failed to load graph from %s: %s", self.graph_path, exc)
            return False

    def stats(self) -> dict:
        if not self.G:
            return {"nodes": 0, "edges": 0}
        return {
            "nodes": self.G.number_of_nodes(),
            "edges": self.G.number_of_edges(),
        }