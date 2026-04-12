"""
CV Analyzer  –  fixed
=====================
Uses the groq package directly (langchain_community.llms.Groq does not exist).
Returns a proper parsed dict, not a raw string.
"""

import os
import re
import json

from pypdf import PdfReader


def _groq_client():
    from groq import Groq
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise ValueError("GROQ_API_KEY not set")
    return Groq(api_key=key)


def _call_llm(client, prompt: str, max_tokens: int = 1200) -> str:
    """Call Groq LLM and return text content."""
    for model in ["llama-3.3-70b-versatile", "gemma2-9b-it"]:
        try:
            r = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=max_tokens,
            )
            return r.choices[0].message.content
        except Exception:
            continue
    raise RuntimeError("All Groq models failed.")


def _parse_json(text: str) -> dict:
    """Extract JSON from LLM response, stripping markdown fences."""
    text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find the first {...} block
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return json.loads(m.group())
        return {"raw_response": text}


class CVAnalyzer:
    def __init__(self):
        self.client = _groq_client()

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        reader = PdfReader(pdf_path)
        return "\n".join(p.extract_text() or "" for p in reader.pages)

    def analyze_cv(self, pdf_path: str) -> dict:
        cv_text = self.extract_text_from_pdf(pdf_path)
        if not cv_text.strip():
            return {"success": False, "error": "Could not extract text from PDF."}

        prompt = f"""Analyze this CV and return ONLY a valid JSON object — no markdown, no extra text.

JSON schema:
{{
  "name": "candidate full name or empty string",
  "summary": "2-3 sentence professional summary",
  "seniority_level": "Junior | Mid-Level | Senior | Lead",
  "experience_years": <integer>,
  "skills": ["skill1", "skill2", ...],
  "technologies": ["tech1", "tech2", ...],
  "experience": [
    {{"title": "Job Title", "company": "Company", "duration": "e.g. 2021-2023"}}
  ],
  "education": [
    {{"degree": "BSc", "field": "Computer Science", "school": "University Name"}}
  ],
  "strengths": ["strength1", "strength2"],
  "improvement_areas": ["area1", "area2"]
}}

CV:
{cv_text[:3000]}
"""

        try:
            raw = _call_llm(self.client, prompt)
            analysis = _parse_json(raw)
            return {"success": True, "analysis": analysis}
        except Exception as e:
            return {"success": False, "error": str(e)}