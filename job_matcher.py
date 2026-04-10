"""
Job Matcher Module
Matches user profile with jobs using:
- Kaggle job datasets
- Skill matching
- Experience level matching
- Location matching (when available)
"""

import os
import json
import pandas as pd
from langchain_core.prompts import PromptTemplate
from langchain_community.llms import Groq


class JobMatcher:
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        self.llm = Groq(api_key=self.groq_api_key, model_name="mixtral-8x7b-32768")
        
        # Load or initialize job database (will be populated from Kaggle)
        self.job_database = self._load_job_database()
    
    def _load_job_database(self) -> list:
        """Load job database from combined CSV (Kaggle + Scraped)"""
        jobs = []
        
        # Priority: Try combined dataset first, fallback to single source
        db_paths = [
            "data/jobs_combined.csv",      # Primary: Combined Kaggle + scraped
            "data/jobs.csv",                # Fallback: Single source
            "docs/ai_jobs_market_2025_2026.csv"  # Fallback: Original Kaggle
        ]
        
        for db_path in db_paths:
            if os.path.exists(db_path):
                try:
                    df = pd.read_csv(db_path)
                    jobs = df.to_dict('records')
                    print(f"✅ Loaded {len(jobs)} jobs from {db_path}")
                    return jobs
                except Exception as e:
                    print(f"⚠️  Error loading {db_path}: {e}")
        
        print("⚠️  No job database found. Please run data_scraper.py first.")
        return jobs
    
    def match_jobs(self, user_profile: dict, limit: int = 10) -> dict:
        """
        Match user profile with relevant jobs
        
        Args:
            user_profile: {
                "skills": ["list of skills"],
                "experience_years": int,
                "seniority_level": "junior/mid/senior",
                "interested_roles": ["list of roles"]
            }
            limit: number of results to return
        """
        
        if not self.job_database:
            return {
                "error": "Job database not loaded. Please add Kaggle CSV files to data/ folder",
                "success": False
            }
        
        # Create matching prompt
        matching_prompt = PromptTemplate(
            input_variables=["user_profile", "job_database"],
            template="""
Match this user profile with suitable jobs from the database.

User Profile:
{user_profile}

Job Database (sample):
{job_database}

Return a JSON array of top matching jobs with:
{{
    "jobs": [
        {{
            "job_title": "title",
            "company": "company name",
            "match_score": "0-100",
            "reason": "why this is a good match",
            "required_skills": ["skills"],
            "nice_to_have": ["skills"]
        }}
    ],
    "summary": "overall matching insights"
}}

Return ONLY valid JSON, no additional text.
            """
        )
        
        # Prepare data for LLM
        db_sample = json.dumps(self.job_database[:5], indent=2)  # Show sample
        formatted_prompt = matching_prompt.format(
            user_profile=json.dumps(user_profile, indent=2),
            job_database=db_sample
        )
        
        try:
            response = self.llm.invoke(formatted_prompt)
            return {
                "matches": response,
                "user_profile": user_profile,
                "success": True
            }
        except Exception as e:
            return {
                "error": f"Error matching jobs: {str(e)}",
                "success": False
            }
    
    def explain_gap(self, user_skills: list, job_requirements: dict) -> dict:
        """Identify skill gaps between user and target job"""
        
        gap_prompt = PromptTemplate(
            input_variables=["user_skills", "job_requirements"],
            template="""
Analyze the skill gap between a user and job requirements.

User Skills:
{user_skills}

Job Requirements:
{job_requirements}

Return JSON with:
{{
    "matching_skills": ["skills they have"],
    "missing_skills": ["skills to learn"],
    "learning_path": ["recommended learning progression"],
    "time_to_readiness": "estimated months",
    "resources": ["courses, tutorials, practice suggestions"]
}}

Return ONLY valid JSON, no additional text.
            """
        )
        
        formatted_prompt = gap_prompt.format(
            user_skills=json.dumps(user_skills),
            job_requirements=json.dumps(job_requirements)
        )
        
        try:
            response = self.llm.invoke(formatted_prompt)
            return {
                "gap_analysis": response,
                "success": True
            }
        except Exception as e:
            return {
                "error": f"Error analyzing gap: {str(e)}",
                "success": False
            }


if __name__ == "__main__":
    matcher = JobMatcher()
    
    sample_profile = {
        "skills": ["Python", "JavaScript", "React"],
        "experience_years": 2,
        "seniority_level": "mid",
        "interested_roles": ["Full Stack Developer", "Backend Engineer"]
    }
    
    result = matcher.match_jobs(sample_profile)
    print(result)
