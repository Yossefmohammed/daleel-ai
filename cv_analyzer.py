"""
CV Analyzer Module
Analyzes PDF CVs and extracts:
- Skills
- Experience
- Education
- Job titles
- Technologies
"""

import os
from pypdf import PdfReader
from langchain_core.prompts import PromptTemplate
from langchain_community.llms import Groq

class CVAnalyzer:
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        self.llm = Groq(api_key=self.groq_api_key, model_name="mixtral-8x7b-32768")
        
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text content from PDF file"""
        try:
            reader = PdfReader(pdf_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text
        except Exception as e:
            return f"Error reading PDF: {str(e)}"
    
    def analyze_cv(self, pdf_path: str) -> dict:
        """Analyze CV and extract structured information"""
        
        # Extract text from PDF
        cv_text = self.extract_text_from_pdf(pdf_path)
        
        if "Error" in cv_text:
            return {"error": cv_text}
        
        # Create analysis prompt
        analysis_prompt = PromptTemplate(
            input_variables=["cv_text"],
            template="""
Analyze this CV and extract the following information in JSON format:
{{
    "skills": ["list of technical and soft skills"],
    "experience": [
        {{"title": "job title", "company": "company name", "duration": "years"}}
    ],
    "education": [
        {{"degree": "degree", "field": "field of study", "school": "institution"}}
    ],
    "technologies": ["programming languages, frameworks, tools"],
    "seniority_level": "junior/mid/senior",
    "summary": "brief professional summary"
}}

CV Content:
{cv_text}

Return ONLY valid JSON, no additional text.
            """
        )
        
        # Format and call LLM
        formatted_prompt = analysis_prompt.format(cv_text=cv_text[:2000])  # Limit to 2000 chars
        
        try:
            response = self.llm.invoke(formatted_prompt)
            return {
                "raw_text": cv_text,
                "analysis": response,
                "success": True
            }
        except Exception as e:
            return {
                "error": f"Error analyzing CV: {str(e)}",
                "success": False
            }


if __name__ == "__main__":
    analyzer = CVAnalyzer()
    print("CV Analyzer initialized successfully")
