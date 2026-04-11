"""
cv_analyzer.py — PathIQ CV Analysis Engine
==========================================
Extracts structured career data from PDF CVs using Groq LLaMA.
"""

import os
import json
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class CVAnalyzer:
    """
    Analyzes PDF CVs and returns structured career intelligence:
    skills, experience, education, seniority level, and improvement suggestions.
    """

    SYSTEM_PROMPT = """You are PathIQ's CV Intelligence Engine — a world-class career analyst.
Extract and analyze the CV text provided. Return ONLY a valid JSON object.
No markdown, no code fences, no preamble. Pure JSON.

Required structure:
{
  "name": "Candidate full name or 'Unknown'",
  "title": "Current/target job title",
  "seniority": "junior|mid|senior|staff|principal",
  "years_experience": <integer>,
  "summary_quality": "poor|fair|good|excellent",
  "skills": {
    "languages": ["Python", "JavaScript", ...],
    "frameworks": ["React", "FastAPI", ...],
    "tools": ["Docker", "Postgres", ...],
    "soft": ["leadership", "communication", ...]
  },
  "experience": [
    {
      "title": "Role title",
      "company": "Company name",
      "duration": "2021–2023",
      "highlights": ["achievement 1", "achievement 2"],
      "impact_score": 1-10
    }
  ],
  "education": [
    {"degree": "BSc Computer Science", "institution": "University Name", "year": "2019"}
  ],
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "gaps": ["gap 1", "gap 2", "gap 3"],
  "rewrite_suggestions": [
    {"section": "Summary", "issue": "Too generic", "fix": "Suggested rewrite..."},
    {"section": "Experience bullet", "issue": "Task not outcome", "fix": "Better version..."}
  ],
  "overall_score": 1-100,
  "market_fit": ["Role A", "Role B", "Role C"]
}"""

    def __init__(self):
        self._llm = None

    def _get_llm(self):
        if self._llm:
            return self._llm
        try:
            from groq import Groq
        except ImportError:
            raise ImportError("Install groq: pip install groq")

        key = None
        try:
            import streamlit as st
            key = st.secrets.get("GROQ_API_KEY")
        except Exception:
            pass
        if not key:
            key = os.getenv("GROQ_API_KEY")
        if not key:
            raise ValueError("GROQ_API_KEY not found in environment or secrets")

        self._llm = Groq(api_key=key)
        return self._llm

    def _extract_text(self, pdf_path: str) -> str:
        """Extract text from PDF using PyMuPDF (fitz) or pdfplumber fallback."""
        text = ""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(pdf_path)
            for page in doc:
                text += page.get_text()
            doc.close()
            return text.strip()
        except ImportError:
            pass

        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text.strip()
        except ImportError:
            pass

        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(pdf_path)
            for page in reader.pages:
                text += page.extract_text() or ""
            return text.strip()
        except ImportError:
            pass

        raise ImportError(
            "No PDF library found. Install one of: pymupdf, pdfplumber, PyPDF2"
        )

    def analyze_cv(self, pdf_path: str) -> dict:
        """
        Analyze a CV PDF and return structured career intelligence.

        Returns:
            {
              "success": bool,
              "analysis": dict,   # structured CV data
              "raw_text": str,    # extracted CV text
              "error": str        # only if success=False
            }
        """
        if not Path(pdf_path).exists():
            return {"success": False, "error": f"File not found: {pdf_path}"}

        try:
            raw_text = self._extract_text(pdf_path)
        except Exception as e:
            return {"success": False, "error": f"PDF extraction failed: {e}"}

        if len(raw_text.strip()) < 50:
            return {"success": False, "error": "Could not extract readable text from PDF"}

        # Truncate to avoid token limits (keep ~6000 chars)
        truncated = raw_text[:6000]

        prompt = f"""Analyze this CV and return structured JSON as specified:

CV TEXT:
{truncated}

Return ONLY the JSON object. No explanation, no markdown."""

        try:
            client = self._get_llm()
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=1500,
            )
            raw_json = response.choices[0].message.content.strip()

            # Clean markdown fences if present
            raw_json = re.sub(r"```(?:json)?\s*", "", raw_json).strip()
            raw_json = raw_json.strip("`").strip()

            analysis = json.loads(raw_json)
            return {
                "success": True,
                "analysis": analysis,
                "raw_text": raw_text[:500] + "...",  # preview only
            }

        except json.JSONDecodeError as e:
            return {"success": False, "error": f"JSON parse error: {e}. Try uploading a cleaner PDF."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_score_summary(self, analysis: dict) -> dict:
        """Return a simple score card from analysis dict."""
        return {
            "overall_score": analysis.get("overall_score", 0),
            "seniority":     analysis.get("seniority", "unknown"),
            "years":         analysis.get("years_experience", 0),
            "top_skills":    analysis.get("skills", {}).get("languages", [])[:5],
            "gaps_count":    len(analysis.get("gaps", [])),
            "market_fit":    analysis.get("market_fit", [])[:3],
        }