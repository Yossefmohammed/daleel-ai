"""
GitHub Analyzer Module
Analyzes GitHub profiles using GitHub API:
- Languages used
- Contributions
- Repository topics
- Starred repos
- Overall profile strength
"""

import os
from github import Github
from langchain_core.prompts import PromptTemplate
from langchain_community.llms import Groq


class GitHubAnalyzer:
    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        
        if self.github_token:
            self.github = Github(self.github_token)
        else:
            self.github = Github()  # Limited requests without token
            
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        self.llm = Groq(api_key=self.groq_api_key, model_name="mixtral-8x7b-32768")
    
    def get_user_profile(self, username: str) -> dict:
        """Fetch GitHub user profile information"""
        try:
            user = self.github.get_user(username)
            
            # Extract languages from repositories
            languages = {}
            repos = user.get_repos(sort="updated")
            
            for repo in repos[:20]:  # Check last 20 repos
                if repo.language:
                    languages[repo.language] = languages.get(repo.language, 0) + 1
            
            profile_data = {
                "username": user.login,
                "name": user.name,
                "bio": user.bio,
                "followers": user.followers,
                "following": user.following,
                "public_repos": user.public_repos,
                "languages": languages,
                "company": user.company,
                "location": user.location,
                "blog": user.blog,
                "twitter": user.twitter_login,
                "created_at": user.created_at,
                "success": True
            }
            return profile_data
            
        except Exception as e:
            return {
                "error": f"Error fetching GitHub profile: {str(e)}",
                "success": False
            }
    
    def analyze_github_profile(self, username: str) -> dict:
        """Analyze GitHub profile and generate insights"""
        
        profile_data = self.get_user_profile(username)
        
        if not profile_data.get("success"):
            return profile_data
        
        # Create analysis prompt
        analysis_prompt = PromptTemplate(
            input_variables=["profile_data"],
            template="""
Analyze this GitHub profile and provide structured insights:

Profile Data:
{profile_data}

Return a JSON response with:
{{
    "profile_strength": "1-10 score",
    "top_skills": ["list of detected programming skills"],
    "contribution_level": "active/moderate/low",
    "project_quality": "assessment based on repos and followers",
    "recommendations": ["suggestions for improvement"],
    "career_readiness": "junior/mid/senior based on profile"
}}

Return ONLY valid JSON, no additional text.
            """
        )
        
        # Format and call LLM
        formatted_prompt = analysis_prompt.format(profile_data=str(profile_data))
        
        try:
            response = self.llm.invoke(formatted_prompt)
            return {
                "profile": profile_data,
                "analysis": response,
                "success": True
            }
        except Exception as e:
            return {
                "error": f"Error analyzing profile: {str(e)}",
                "success": False
            }


if __name__ == "__main__":
    analyzer = GitHubAnalyzer()
    result = analyzer.analyze_github_profile("torvalds")  # Test with Linus Torvalds
    print(result)
