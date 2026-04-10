"""
graph_builder.py
================
Graph RAG: Entity extraction + knowledge graph construction.
Uses spaCy NER + a lightweight LLM call to extract (entity, relation, entity) triples.
The graph is stored in-memory with NetworkX and persisted as JSON.
"""

import json
import re
import os
import networkx as nx
from pathlib import Path
from collections import defaultdict
from typing import List, Tuple, Dict, Optional

# ── Optional spaCy import ──────────────────────────────────────────────────────
try:
    import spacy
    _SPACY_AVAILABLE = True
except ImportError:
    _SPACY_AVAILABLE = False

GRAPH_PATH = "db/knowledge_graph.json"


# ══════════════════════════════════════════════════════════════════════════════
# Entity extraction helpers
# ══════════════════════════════════════════════════════════════════════════════

def _extract_entities_spacy(text: str, nlp) -> List[Tuple[str, str]]:
    """Return [(entity_text, entity_label), ...] using spaCy NER."""
    doc = nlp(text[:100_000])          # spaCy has token limits
    seen = set()
    entities = []
    for ent in doc.ents:
        key = (ent.text.strip().lower(), ent.label_)
        if key not in seen:
            seen.add(key)
            entities.append((ent.text.strip(), ent.label_))
    return entities


def _extract_entities_regex(text: str) -> List[Tuple[str, str]]:
    """
    Fallback regex-based entity extraction when spaCy is unavailable.
    Looks for capitalised noun phrases and common domain keywords.
    """
    entities = []

    # Capitalised multi-word phrases (likely proper nouns / product names)
    caps_pattern = re.compile(r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,3})\b')
    for m in caps_pattern.finditer(text):
        phrase = m.group(1).strip()
        if len(phrase) > 2:
            entities.append((phrase, "ENTITY"))

    # Domain-specific patterns
    domain_keywords = [
        r'\b(API|SDK|ML|AI|LLM|RAG|NLP|UI|UX)\b',
        r'\b(fintech|e-commerce|SaaS|B2B|B2C)\b',
    ]
    for pat in domain_keywords:
        for m in re.finditer(pat, text, re.IGNORECASE):
            entities.append((m.group(0), "DOMAIN"))

    # Deduplicate
    seen = set()
    unique = []
    for e in entities:
        k = e[0].lower()
        if k not in seen:
            seen.add(k)
            unique.append(e)
    return unique


def _build_cooccurrence_edges(
    entities: List[Tuple[str, str]],
    chunk_id: str,
    window: int = 5
) -> List[Tuple[str, str, str]]:
    """
    Build (head, relation, tail) triples from entity co-occurrence inside a
    sliding window of `window` entities.
    """
    triples = []
    ent_texts = [e[0] for e in entities]
    for i, head in enumerate(ent_texts):
        for j in range(i + 1, min(i + window, len(ent_texts))):
            tail = ent_texts[j]
            if head.lower() != tail.lower():
                triples.append((head, "co-occurs-with", tail))
    return triples


# ══════════════════════════════════════════════════════════════════════════════
# Main builder
# ══════════════════════════════════════════════════════════════════════════════

class KnowledgeGraphBuilder:
    """
    Builds and persists a knowledge graph from LangChain Document chunks.

    Graph schema
    ────────────
    Nodes: entity texts (normalised to lower-case)
        attrs: label (NER type), mentions (list of chunk_ids)
    Edges: (head, tail)
        attrs: relation, chunk_ids
    """

    def __init__(self, graph_path: str = GRAPH_PATH):
        self.graph_path = graph_path
        self.G: nx.Graph = nx.Graph()
        self._nlp = None
        self._load_spacy()

    # ── spaCy init ─────────────────────────────────────────────────────────────

    def _load_spacy(self):
        if not _SPACY_AVAILABLE:
            return
        models = ["en_core_web_sm", "en_core_web_md"]
        for model in models:
            try:
                self._nlp = spacy.load(model)
                return
            except OSError:
                continue
        # spaCy installed but no model downloaded
        self._nlp = None

    # ── Extraction ─────────────────────────────────────────────────────────────

    def _extract_entities(self, text: str) -> List[Tuple[str, str]]:
        if self._nlp:
            return _extract_entities_spacy(text, self._nlp)
        return _extract_entities_regex(text)

    # ── Graph building ─────────────────────────────────────────────────────────

    def build_from_documents(self, documents: list, progress_callback=None):
        """
        Ingest a list of LangChain Document objects into the knowledge graph.
        progress_callback(i, total) is called each step if provided.
        """
        total = len(documents)
        for idx, doc in enumerate(documents):
            chunk_id = f"chunk_{idx}"
            text = doc.page_content
            entities = self._extract_entities(text)

            # Add nodes
            for ent_text, ent_label in entities:
                node_key = ent_text.lower()
                if self.G.has_node(node_key):
                    self.G.nodes[node_key]["mentions"].append(chunk_id)
                else:
                    self.G.add_node(
                        node_key,
                        display=ent_text,
                        label=ent_label,
                        mentions=[chunk_id],
                    )

            # Add edges (co-occurrence)
            triples = _build_cooccurrence_edges(entities, chunk_id)
            for head, relation, tail in triples:
                h, t = head.lower(), tail.lower()
                if self.G.has_edge(h, t):
                    self.G[h][t]["weight"] += 1
                    if chunk_id not in self.G[h][t]["chunk_ids"]:
                        self.G[h][t]["chunk_ids"].append(chunk_id)
                else:
                    self.G.add_edge(h, t, relation=relation, weight=1, chunk_ids=[chunk_id])

            if progress_callback:
                progress_callback(idx + 1, total)

        self.save()
        return self.G

    # ── Persistence ────────────────────────────────────────────────────────────

    def save(self):
        Path(self.graph_path).parent.mkdir(parents=True, exist_ok=True)
        data = nx.node_link_data(self.G)
        with open(self.graph_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self) -> bool:
        """Load graph from disk. Returns True if successful."""
        if not os.path.exists(self.graph_path):
            return False
        try:
            with open(self.graph_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.G = nx.node_link_graph(data)
            return True
        except Exception:
            return False

    # ── Stats ──────────────────────────────────────────────────────────────────

    def stats(self) -> Dict:
        return {
            "nodes": self.G.number_of_nodes(),
            "edges": self.G.number_of_edges(),
        }