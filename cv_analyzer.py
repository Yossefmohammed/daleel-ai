"""
cv_analyzer.py — Daleel AI CV Analyzer
========================================
Extracts structured career data from a PDF CV using Groq LLMs.

Improvements over original:
- Supports st.secrets (Streamlit Cloud) AND os.getenv (local .env)
- Text limit raised from 6,000 → 8,000 chars for long CVs
- Model fallback chain matches the one in app.py (consistent)
- Detailed logging instead of silent failures
- _parse_json returns {} on failure (not raw_response string) so callers
  can safely do 'if not analysis or "skills" not in analysis'
- Added page-count guard: warns if PDF appears to be scanned (no text)
"""

import json
import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Groq models to try in order of quality → speed
_GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "deepseek-r1-distill-llama-70b",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
]

_CV_TEXT_LIMIT = 8_000   # chars sent to LLM (raised from 6,000)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _get_api_key() -> str:
    """Read GROQ_API_KEY from Streamlit secrets or environment."""
    try:
        import streamlit as st
        if "GROQ_API_KEY" in st.secrets:
            return st.secrets["GROQ_API_KEY"]
    except Exception:
        pass
    return os.getenv("GROQ_API_KEY", "")


def _groq_client():
    from groq import Groq
    key = _get_api_key()
    if not key:
        raise ValueError(
            "GROQ_API_KEY is not set. "
            "Add it to .streamlit/secrets.toml or your .env file."
        )
    return Groq(api_key=key)


def _call_llm(client, prompt: str, max_tokens: int = 1600) -> str:
    """Call Groq with a model fallback chain. Raises RuntimeError if all fail."""
    last_err: Optional[Exception] = None
    for model in _GROQ_MODELS:
        try:
            r = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=max_tokens,
            )
            return r.choices[0].message.content
        except Exception as exc:
            err_str = str(exc).lower()
            if any(x in err_str for x in ("api key", "unauthorized", "401")):
                raise ValueError(f"Invalid GROQ_API_KEY: {exc}") from exc
            logger.warning("Model %s failed: %s — trying next.", model, exc)
            last_err = exc

    raise RuntimeError(f"All Groq models failed. Last error: {last_err}")


def _parse_json(text: str) -> dict:
    """
    Extract a JSON object from LLM response, stripping markdown fences.
    Returns {} on failure (not a dict with 'raw_response') so callers
    can safely check 'if not result'.
    """
    text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find the first {...} block
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass

    logger.warning("Could not parse JSON from LLM response. Raw: %s", text[:300])
    return {}


# ------------------------------------------------------------------
# Main class
# ------------------------------------------------------------------

class CVAnalyzer:
    """
    Analyzes a PDF CV and returns a structured dict with career data.

    Usage:
        analyzer = CVAnalyzer()
        result = analyzer.analyze_cv("path/to/cv.pdf")
        if result["success"]:
            profile = result["analysis"]
    """

    def __init__(self):
        self.client = _groq_client()

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract all text from a PDF, returning a single string."""
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        pages_text = []
        for page in reader.pages:
            text = page.extract_text() or ""
            pages_text.append(text)

        full_text = "\n".join(pages_text)
        if not full_text.strip() and len(reader.pages) > 0:
            logger.warning(
                "PDF has %d page(s) but no extractable text. "
                "It may be a scanned/image-based PDF.",
                len(reader.pages),
            )
        return full_text

    def analyze_cv(self, pdf_path: str) -> dict:
        """
        Analyze a CV PDF and return structured career data.

        Returns:
            {
                "success": True,
                "analysis": { ... structured fields ... }
            }
            or
            {
                "success": False,
                "error": "human-readable message"
            }
        """
        try:
            cv_text = self.extract_text_from_pdf(pdf_path)
        except Exception as exc:
            return {"success": False, "error": f"Could not read PDF: {exc}"}

        if not cv_text.strip():
            return {
                "success": False,
                "error": (
                    "No text could be extracted from this PDF. "
                    "Make sure it is not a scanned/image-only document."
                ),
            }

        prompt = f"""Analyze this CV thoroughly and return ONLY a valid JSON object.
No markdown, no explanation, no text outside the JSON braces.

Read the ENTIRE CV including all projects, side-projects, and personal work.
Do NOT leave any array empty if the CV contains that information.

JSON schema — fill every field you can find evidence for:
{{
  "name": "candidate full name or empty string",
  "summary": "2-3 sentence honest professional summary",
  "seniority_level": "Junior | Mid-Level | Senior | Lead",
  "experience_years": <integer>,
  "skills": ["skill1", "skill2"],
  "technologies": ["framework1", "library1"],
  "experience": [
    {{"title": "Job Title", "company": "Company Name", "duration": "e.g. 2021-2023"}}
  ],
  "education": [
    {{"degree": "BSc", "field": "Computer Science", "school": "University Name"}}
  ],
  "projects": [
    {{
      "name": "Project Name",
      "description": "What it does and what problem it solves — 1-2 sentences",
      "technologies": ["tech1", "tech2"],
      "url": "link if present or empty string"
    }}
  ],
  "strengths": ["strength1", "strength2"],
  "improvement_areas": ["area1", "area2"]
}}

CV text (up to {_CV_TEXT_LIMIT} chars):
{cv_text[:_CV_TEXT_LIMIT]}
"""

        try:
            raw = _call_llm(self.client, prompt)
        except Exception as exc:
            return {"success": False, "error": str(exc)}

        analysis = _parse_json(raw)
        if not analysis or "skills" not in analysis:
            return {
                "success": False,
                "error": (
                    "The AI could not parse a valid career profile from your CV. "
                    "Try uploading a cleaner, text-based PDF."
                ),
            }

        return {"success": True, "analysis": analysis}