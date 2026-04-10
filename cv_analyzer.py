"""
CV Analyzer Module
Analyzes PDF CVs and extracts skills, experience, education, technologies.
"""

import os
import json
from pypdf import PdfReader
from groq import Groq


class CVAnalyzer:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        try:
            reader = PdfReader(pdf_path)
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            return f"Error reading PDF: {e}"

    def analyze_cv(self, pdf_path: str) -> dict:
        cv_text = self.extract_text_from_pdf(pdf_path)
        if cv_text.startswith("Error"):
            return {"success": False, "error": cv_text}

        prompt = f"""Analyze this CV and return ONLY a valid JSON object with exactly these keys:
{{
  "skills": ["list of technical and soft skills"],
  "experience": [{{"title": "job title", "company": "company name", "duration": "e.g. 2 years"}}],
  "education": [{{"degree": "degree", "field": "field of study", "school": "institution name"}}],
  "technologies": ["programming languages, frameworks, tools"],
  "seniority_level": "junior or mid or senior",
  "summary": "2-3 sentence professional summary"
}}

CV Content:
{cv_text[:3000]}

Return ONLY the JSON object, no markdown, no extra text."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=1000,
            )
            raw = response.choices[0].message.content.strip()
            # Try to parse as JSON for structured display
            try:
                parsed = json.loads(raw)
                return {"success": True, "analysis": parsed}
            except json.JSONDecodeError:
                # Return raw string if JSON parse fails
                return {"success": True, "analysis": raw}
        except Exception as e:
            return {"success": False, "error": str(e)}