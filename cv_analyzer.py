"""cv_analyzer.py — rich structured CV analysis with impact scores."""
import os, json, re
from groq import Groq
from constant import GROQ_MODEL, GROQ_MODEL_FALLBACK, CV_TEXT_LIMIT

def _extract_text(pdf_path: str) -> str:
    for extractor in [_fitz, _pdfplumber, _pypdf]:
        try:
            text = extractor(pdf_path)
            if text and text.strip() and not text.startswith("ERROR"):
                return text
        except Exception:
            pass
    return "ERROR: Could not extract PDF text."

def _fitz(p):
    import fitz
    doc = fitz.open(p)
    t   = "\n".join(page.get_text() for page in doc)
    doc.close()
    return t

def _pdfplumber(p):
    import pdfplumber
    with pdfplumber.open(p) as pdf:
        return "\n".join(pg.extract_text() or "" for pg in pdf.pages)

def _pypdf(p):
    from pypdf import PdfReader
    return "\n".join(pg.extract_text() or "" for pg in PdfReader(p).pages)

def _parse_json(raw: str) -> dict:
    raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`")
    try:    return json.loads(raw)
    except Exception: pass
    m = re.search(r'\{[\s\S]+\}', raw)
    if m:
        try: return json.loads(m.group())
        except Exception: pass
    return {}

SCHEMA = """{
  "name": "candidate name or empty",
  "overall_score": <1-100 integer>,
  "seniority_level": "junior|mid|senior|lead|principal",
  "years_experience": <number>,
  "skills": {
    "languages":    ["list"],
    "frameworks":   ["list"],
    "databases":    ["list"],
    "cloud_devops": ["list"],
    "soft_skills":  ["list"]
  },
  "experience": [
    {
      "title":        "job title",
      "company":      "company",
      "duration":     "e.g. 2 years",
      "impact_score": <1-10 integer>,
      "highlights":   ["key achievement"]
    }
  ],
  "education": [{"degree":"","field":"","school":"","year":""}],
  "skill_gaps":            ["skills missing for next level"],
  "rewrite_suggestions":   ["concrete CV improvements, max 4"],
  "market_fit_roles":      ["3-5 suited roles"],
  "summary": "2-sentence honest professional summary"
}"""

class CVAnalyzer:
    def __init__(self):
        key = os.getenv("GROQ_API_KEY", "")
        if not key:
            raise ValueError("GROQ_API_KEY not set")
        self.client = Groq(api_key=key)

    def analyze_cv(self, pdf_path: str) -> dict:
        text = _extract_text(pdf_path)
        if text.startswith("ERROR"):
            return {"success": False, "error": text}

        prompt = (
            "You are an expert technical recruiter. Analyze this CV.\n"
            "Return ONLY a valid JSON object — no markdown, no prose.\n\n"
            f"CV TEXT:\n{text[:CV_TEXT_LIMIT]}\n\n"
            f"JSON SCHEMA (fill every field):\n{SCHEMA}"
        )

        for model in [GROQ_MODEL, GROQ_MODEL_FALLBACK]:
            try:
                r = self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.15, max_tokens=1400,
                )
                parsed = _parse_json(r.choices[0].message.content)
                if parsed:
                    return {"success": True, "analysis": parsed}
            except Exception:
                continue
        return {"success": False, "error": "All models failed."}