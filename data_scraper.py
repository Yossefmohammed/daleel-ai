"""
Data Scraper Module
Scrapes fresh job data from RemoteOK and GitHub Jobs
Combines with Kaggle dataset for comprehensive job database
"""

import requests
import pandas as pd
from datetime import datetime
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RemoteOKScraper:
    """Scrapes jobs from RemoteOK (allows scraping per their ToS)"""
    
    def __init__(self):
        self.api_url = "https://remoteok.com/api/jobs"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    
    def scrape_jobs(self, keywords=None, limit=100):
        """
        Scrape jobs from RemoteOK
        
        Args:
            keywords: Search keywords (e.g., "python")
            limit: Maximum jobs to return
            
        Returns:
            List of job dictionaries
        """
        try:
            params = {
                "category": "programming"
            }
            
            if keywords:
                params["search"] = keywords
            
            logger.info("Fetching jobs from RemoteOK...")
            response = requests.get(self.api_url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            jobs_raw = response.json()
            
            # Standardize format
            jobs_standardized = []
            for job in jobs_raw[:limit]:
                standardized = {
                    "job_title": job.get("title", "Unknown"),
                    "company": job.get("company", "Unknown"),
                    "description": job.get("description", "")[:500],  # Limit description
                    "location": job.get("location", "Remote"),
                    "country": "Remote/Global",
                    "remote_work": "Fully Remote",
                    "url": job.get("url", ""),
                    "posted_date": datetime.now().isoformat(),
                    "salary_range": job.get("salary", "Not specified"),
                    "source": "RemoteOK"
                }
                jobs_standardized.append(standardized)
            
            logger.info(f"✅ Scraped {len(jobs_standardized)} jobs from RemoteOK")
            return jobs_standardized
            
        except Exception as e:
            logger.error(f"❌ Error scraping RemoteOK: {e}")
            return []


class GitHubJobsScraper:
    """Fetches jobs from GitHub Jobs API (no scraping needed - free API)"""
    
    def __init__(self):
        self.api_url = "https://jobs.github.com/positions.json"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    
    def scrape_jobs(self, description="AI", limit=50):
        """
        Fetch jobs from GitHub Jobs API
        
        Args:
            description: Job search term (e.g., "Python", "AI", "Backend")
            limit: Maximum jobs to return
            
        Returns:
            List of job dictionaries
        """
        try:
            params = {
                "description": description,
                "page": 1
            }
            
            logger.info(f"Fetching jobs from GitHub Jobs API for: {description}")
            response = requests.get(self.api_url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            jobs_raw = response.json()
            
            # Standardize format
            jobs_standardized = []
            for job in jobs_raw[:limit]:
                standardized = {
                    "job_title": job.get("title", "Unknown"),
                    "company": job.get("company", "Unknown"),
                    "description": job.get("description", "")[:500],
                    "location": job.get("location", "Unknown"),
                    "country": "USA",  # GitHub Jobs mostly USA
                    "remote_work": "Fully Remote" if "remote" in job.get("title", "").lower() else "On-site",
                    "url": job.get("url", ""),
                    "posted_date": job.get("created_at", datetime.now().isoformat()),
                    "salary_range": "Not specified",
                    "source": "GitHub Jobs"
                }
                jobs_standardized.append(standardized)
            
            logger.info(f"✅ Fetched {len(jobs_standardized)} jobs from GitHub Jobs API")
            return jobs_standardized
            
        except Exception as e:
            logger.error(f"❌ Error fetching GitHub jobs: {e}")
            return []


class DataMerger:
    """Merges Kaggle dataset with scraped data"""
    
    @staticmethod
    def load_kaggle_data(csv_path):
        """Load Kaggle AI Jobs dataset"""
        try:
            logger.info(f"Loading Kaggle data from {csv_path}...")
            df = pd.read_csv(csv_path)
            
            # Use columns as-is (already well-formatted from Kaggle)
            df["description"] = df.get("job_category", "AI").astype(str) + " - " + df.get("required_skills", "").astype(str)
            df["description"] = df["description"].str[:500]
            df["source"] = "Kaggle AI Jobs"
            df["url"] = ""
            
            # Select relevant columns
            cols_to_use = [
                "job_title", "company_size", "job_category", 
                "description", "city", "country", "remote_work",
                "annual_salary_usd", "demand_score", "posting_year", 
                "required_skills", "source", "url"
            ]
            
            # Keep only available columns
            cols_available = [c for c in cols_to_use if c in df.columns]
            df_standardized = df[cols_available].copy()
            
            logger.info(f"✅ Loaded {len(df_standardized)} jobs from Kaggle")
            return df_standardized
            
        except Exception as e:
            logger.error(f"❌ Error loading Kaggle data: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    @staticmethod
    def merge_datasets(kaggle_df, scraped_jobs_list):
        """
        Merge Kaggle dataset with scraped jobs
        
        Args:
            kaggle_df: DataFrame from Kaggle
            scraped_jobs_list: List of dicts from scrapers
            
        Returns:
            Combined DataFrame
        """
        try:
            # Convert scraped jobs to DataFrame
            scraped_df = pd.DataFrame(scraped_jobs_list)
            
            # Combine datasets
            merged = pd.concat([kaggle_df, scraped_df], ignore_index=True)
            
            # Remove duplicates based on title and company
            merged = merged.drop_duplicates(
                subset=["job_title", "company"],
                keep="first"
            )
            
            logger.info(f"✅ Merged datasets: {len(merged)} unique jobs total")
            return merged
            
        except Exception as e:
            logger.error(f"❌ Error merging datasets: {e}")
            return kaggle_df if not kaggle_df.empty else pd.DataFrame()
    
    @staticmethod
    def save_combined_data(df, output_path):
        """Save combined dataset to CSV"""
        try:
            df.to_csv(output_path, index=False)
            logger.info(f"✅ Saved combined data to {output_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Error saving data: {e}")
            return False


def get_combined_jobs(kaggle_path="docs/ai_jobs_market_2025_2026.csv", output_path="data/jobs_combined.csv"):
    """
    Main function: Get combined job data from Kaggle + Scraping
    Falls back to Kaggle-only if scraping fails
    
    Returns:
        DataFrame with all jobs
    """
    logger.info("🔄 Starting data collection...")
    
    # Load Kaggle data (PRIMARY)
    kaggle_df = DataMerger.load_kaggle_data(kaggle_path)
    
    if kaggle_df.empty:
        logger.warning("⚠️  Could not load Kaggle data")
        return pd.DataFrame()
    
    # Scrape fresh data (OPTIONAL - for enhancement)
    logger.info("\n📡 Attempting to scrape fresh data...")
    all_scraped = []
    
    try:
        remote_ok_scraper = RemoteOKScraper()
        remote_ok_jobs = remote_ok_scraper.scrape_jobs(keywords="AI", limit=50)
        all_scraped.extend(remote_ok_jobs)
    except Exception as e:
        logger.warning(f"⚠️  RemoteOK scraping unavailable (offline?): {type(e).__name__}")
    
    try:
        github_scraper = GitHubJobsScraper()
        github_jobs = github_scraper.scrape_jobs(description="AI", limit=50)
        all_scraped.extend(github_jobs)
    except Exception as e:
        logger.warning(f"⚠️  GitHub Jobs API unavailable (offline?): {type(e).__name__}")
    
    logger.info(f"📊 Total fresh jobs scraped: {len(all_scraped)}")
    
    # Merge with Kaggle (or use Kaggle-only if scraping failed)
    merged_df = DataMerger.merge_datasets(kaggle_df, all_scraped)
    
    # Save combined data
    DataMerger.save_combined_data(merged_df, output_path)
    
    logger.info(f"\n✅ ✅ COMPLETE! Total jobs available: {len(merged_df)}")
    logger.info(f"📁 Data saved to: {output_path}")
    return merged_df


if __name__ == "__main__":
    # Run the scraper
    df = get_combined_jobs()
    print(f"\nDataset shape: {df.shape}")
    print(f"\nSample jobs:\n{df.head()}")
