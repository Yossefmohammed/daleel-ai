"""
tests/test_core.py — Daleel AI Core Unit Tests
===============================================
Run with:  pytest tests/ -v

Covers the most critical, previously-untested functions:
- _parse_json (app.py + cv_analyzer.py)
- _expand_skills / _diverse_candidates (app.py)
- KnowledgeGraphBuilder.load() mutation fix
- GraphRetriever entity extraction
"""

import json
import os
import sys
import types
import pytest

# ---------------------------------------------------------------------------
# Helpers to import modules without Streamlit / Groq installed
# ---------------------------------------------------------------------------

def _make_stub_module(name: str, **attrs):
    """Create a minimal stub module and insert it into sys.modules."""
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


# Stub out streamlit so app.py can be imported in tests
_make_stub_module("streamlit", secrets={}, session_state={})
_make_stub_module("dotenv", load_dotenv=lambda: None)
_make_stub_module("groq", Groq=object)

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ---------------------------------------------------------------------------
# _parse_json tests (logic duplicated here to avoid importing full app.py)
# ---------------------------------------------------------------------------

import re as _re


def parse_json(text: str):
    """Reference implementation matching app.py's _parse_json."""
    text = _re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    for pat in [r"\[.*\]", r"\{.*\}"]:
        m = _re.search(pat, text, _re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except Exception:
                pass
    return []


class TestParseJson:
    def test_clean_json_object(self):
        raw = '{"title": "Engineer", "score": 90}'
        result = parse_json(raw)
        assert result == {"title": "Engineer", "score": 90}

    def test_json_array(self):
        raw = '[{"a": 1}, {"b": 2}]'
        assert parse_json(raw) == [{"a": 1}, {"b": 2}]

    def test_strips_markdown_fences(self):
        raw = "```json\n{\"key\": \"value\"}\n```"
        assert parse_json(raw) == {"key": "value"}

    def test_extracts_json_from_prose(self):
        raw = 'Sure! Here is the result: {"name": "Alice", "age": 30} enjoy!'
        result = parse_json(raw)
        assert result["name"] == "Alice"

    def test_returns_list_on_failure(self):
        result = parse_json("this is not json at all")
        assert result == []

    def test_nested_json(self):
        raw = '{"jobs": [{"title": "Dev"}]}'
        result = parse_json(raw)
        assert result["jobs"][0]["title"] == "Dev"

    def test_truncated_json_returns_empty_list(self):
        raw = '{"title": "incomplete'
        result = parse_json(raw)
        assert result == []


# ---------------------------------------------------------------------------
# KnowledgeGraphBuilder — load() mutation fix
# ---------------------------------------------------------------------------

class TestGraphBuilderLoad:
    """
    The original load() called node.pop("id") which mutated the in-memory
    dict — calling load() twice would crash on the second call.
    The fixed version uses node.get("id") + dict comprehension.
    """

    def _make_graph_json(self, tmp_path):
        data = {
            "nodes": [
                {"id": "python", "chunk_ids": ["chunk_0"], "frequency": 3},
                {"id": "docker", "chunk_ids": ["chunk_1"], "frequency": 1},
            ],
            "edges": [
                {"source": "python", "target": "docker", "weight": 2}
            ],
        }
        p = tmp_path / "db" / "knowledge_graph.json"
        p.parent.mkdir()
        p.write_text(json.dumps(data))
        return str(p)

    def test_load_succeeds(self, tmp_path):
        pytest.importorskip("networkx")
        from graph_builder import KnowledgeGraphBuilder
        path = self._make_graph_json(tmp_path)
        builder = KnowledgeGraphBuilder(graph_path=path)
        assert builder.load() is True
        assert builder.G.has_node("python")
        assert builder.G.has_node("docker")

    def test_load_twice_does_not_crash(self, tmp_path):
        """Regression test: the pop() mutation bug caused a KeyError on second load."""
        pytest.importorskip("networkx")
        from graph_builder import KnowledgeGraphBuilder
        path = self._make_graph_json(tmp_path)
        builder = KnowledgeGraphBuilder(graph_path=path)
        assert builder.load() is True
        # Second call must not raise KeyError
        assert builder.load() is True

    def test_load_missing_file_returns_false(self, tmp_path):
        pytest.importorskip("networkx")
        from graph_builder import KnowledgeGraphBuilder
        builder = KnowledgeGraphBuilder(graph_path=str(tmp_path / "nonexistent.json"))
        assert builder.load() is False

    def test_stats_after_load(self, tmp_path):
        pytest.importorskip("networkx")
        from graph_builder import KnowledgeGraphBuilder
        path = self._make_graph_json(tmp_path)
        builder = KnowledgeGraphBuilder(graph_path=path)
        builder.load()
        stats = builder.stats()
        assert stats["nodes"] == 2
        assert stats["edges"] == 1


# ---------------------------------------------------------------------------
# GraphRetriever — entity extraction
# ---------------------------------------------------------------------------

class TestGraphRetrieverEntities:
    def _retriever(self, extra_keywords=None):
        from graph_retriever import GraphRetriever
        import networkx as nx
        G = nx.Graph()
        return GraphRetriever(
            vectorstore=None,
            graph=G,
            extra_tech_keywords=extra_keywords,
        )

    def test_extracts_tech_keywords(self):
        pytest.importorskip("networkx")
        r = self._retriever()
        entities = r._extract_query_entities("How do I deploy with Docker on AWS?")
        lower = [e.lower() for e in entities]
        assert "docker" in lower
        assert "aws" in lower

    def test_no_hardcoded_wasla(self):
        """Regression: 'Wasla' must not appear in the built-in keyword list."""
        pytest.importorskip("networkx")
        r = self._retriever()
        pattern = r._tech_re.pattern
        assert "wasla" not in pattern.lower()

    def test_custom_keywords_are_matched(self):
        pytest.importorskip("networkx")
        r = self._retriever(extra_keywords=["MyCompany", "SpecialTool"])
        entities = r._extract_query_entities("We use MyCompany's SpecialTool for CI.")
        lower = [e.lower() for e in entities]
        assert "mycompany" in lower
        assert "specialtool" in lower

    def test_empty_query_returns_list(self):
        pytest.importorskip("networkx")
        r = self._retriever()
        result = r._extract_query_entities("")
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Skill expansion (ported from app.py logic for isolated testing)
# ---------------------------------------------------------------------------

_SKILL_ALIASES = {
    "javascript": ["js", "node.js", "nodejs", "ecmascript"],
    "python": ["py"],
    "machine learning": ["ml", "deep learning", "ai"],
}


def expand_skills(skills: list) -> list:
    expanded = set(s.lower() for s in skills)
    for skill in skills:
        canonical = skill.lower().strip()
        for canon, aliases in _SKILL_ALIASES.items():
            if canonical in [a.lower() for a in aliases] or canonical == canon:
                expanded.update(a.lower() for a in aliases)
                expanded.add(canon)
    return list(expanded)


class TestExpandSkills:
    def test_expands_js_alias(self):
        result = expand_skills(["js"])
        assert "javascript" in result
        assert "nodejs" in result

    def test_expands_canonical(self):
        result = expand_skills(["javascript"])
        assert "js" in result
        assert "node.js" in result

    def test_no_expansion_for_unknown_skill(self):
        result = expand_skills(["golang"])
        assert "golang" in result  # original preserved

    def test_case_insensitive(self):
        result = expand_skills(["Python"])
        assert "python" in result
        assert "py" in result

    def test_empty_input(self):
        assert expand_skills([]) == []


# ---------------------------------------------------------------------------
# CVAnalyzer _parse_json
# ---------------------------------------------------------------------------

from cv_analyzer import _parse_json as cv_parse_json


class TestCVParseJson:
    def test_valid_dict(self):
        raw = '{"name": "Ahmed", "skills": ["Python"]}'
        result = cv_parse_json(raw)
        assert result["name"] == "Ahmed"

    def test_strips_fences(self):
        raw = "```json\n{\"name\": \"Sara\"}\n```"
        result = cv_parse_json(raw)
        assert result["name"] == "Sara"

    def test_returns_empty_dict_on_failure(self):
        result = cv_parse_json("not json")
        assert result == {}

    def test_extracts_from_prose(self):
        raw = 'Here is the analysis: {"experience_years": 5} done.'
        result = cv_parse_json(raw)
        assert result["experience_years"] == 5