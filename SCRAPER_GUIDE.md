# Data Scraper Guide

## Overview
The `data_scraper.py` module combines the Kaggle AI Jobs dataset with fresher data from web scraping (currently RemoteOK and GitHub Jobs).

## Usage

### Option 1: Quick Start (Recommended)
```bash
python data_scraper.py
```

This will:
1. ✅ Load 1,500 AI jobs from Kaggle (`docs/ai_jobs_market_2025_2026.csv`)
2. 📡 Attempt to scrape RemoteOK API for fresh programming jobs
3. 📡 Attempt to fetch jobs from GitHub Jobs API  
4. 🔄 Merge all data and remove duplicates
5. 💾 Save to `data/jobs_combined.csv`

### Option 2: Programmatic Usage
```python
from data_scraper import get_combined_jobs

# Load and combine data
df = get_combined_jobs(
    kaggle_path="docs/ai_jobs_market_2025_2026.csv",
    output_path="data/jobs_combined.csv"
)

print(f"Total jobs: {len(df)}")
print(df.head())
```

## Data Sources

| Source | Jobs | Update Frequency | Status |
|--------|------|------------------|--------|
| **Kaggle** (Primary) | 1,500 | Manual | ✅ Always available |
| **RemoteOK API** | ~50 | Real-time | ⚠️ Optional (requires internet) |
| **GitHub Jobs API** | ~50 | Real-time | ⚠️ Optional (requires internet) |

## Output Format

The combined dataset includes:
- `job_title` - Job title
- `company_size` - Company size (Startup, SME, etc.)
- `job_category` - AI Engineering, Data Science, etc.
- `description` - Job description (first 500 chars)
- `city` - Job location city
- `country` - Job location country
- `remote_work` - Remote status
- `annual_salary_usd` - Annual salary
- `demand_score` - Market demand (0-100)
- `posting_year` - Year posted
- `required_skills` - Required skills (pipe-separated)
- `source` - Data source (Kaggle/RemoteOK/GitHub Jobs)
- `url` - Job URL (if available)

## Fallback Behavior

If scraping APIs are unavailable (no internet, API down, etc.):
- ✅ Kaggle data will still load (primary source)
- ⚠️ Scraping will be skipped gracefully
- 💾 Combined dataset will use Kaggle data only

This ensures the app works offline!

## Customization

### Add New Data Sources
Edit `data_scraper.py` to create new scraper classes:

```python
class MyJobScraper:
    def scrape_jobs(self, **kwargs):
        # Your scraping logic here
        return [
            {
                "job_title": "...",
                "company": "...",
                "description": "...",
                # ... other fields
                "source": "MySource"
            }
        ]
```

Then add to `get_combined_jobs()`:
```python
my_scraper = MyJobScraper()
my_jobs = my_scraper.scrape_jobs()
all_scraped.extend(my_jobs)
```

## Troubleshooting

### "Could not load Kaggle data"
- Ensure `docs/ai_jobs_market_2025_2026.csv` exists
- Check file is not corrupted: `python -c "import pandas as pd; print(pd.read_csv('docs/ai_jobs_market_2025_2026.csv').shape)"`

### Scraping returns "Error"
- Check internet connection
- RemoteOK and GitHub Jobs APIs may be temporarily down
- This is OK - Kaggle data will still be used

### Empty dataset saved
- Kaggle data failed to load - see above troubleshooting

## Integration with Job Matcher

The [job_matcher.py](job_matcher.py) automatically loads from `data/jobs_combined.csv` when available:

```python
from job_matcher import JobMatcher

matcher = JobMatcher()
# Will use combined dataset automatically
```

## Scheduling Updates

To update data daily, create a cron job (Linux/Mac) or scheduled task (Windows):

### Windows Task Scheduler
```cmd
schtasks /create /tn "Daily Job Update" /tr "python C:\path\to\data_scraper.py" /sc daily /st 02:00
```

### Linux/Mac Crontab  
```bash
0 2 * * * cd /path/to/project && python data_scraper.py
```

## Performance Notes

- Kaggle load: < 1 second
- RemoteOK scraping: 2-5 seconds (or graceful timeout)
- GitHub Jobs API: 1-3 seconds (or graceful timeout)
- Data merge: < 1 second
- **Total time: ~5 seconds max**

The scraper is efficient and won't block your app!
