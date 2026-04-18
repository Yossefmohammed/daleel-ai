# Migration Guide: v1.0 → v1.1

Complete guide for upgrading Daleel AI from v1.0 to v1.1 (Phase 1 Security Update).

---

## 🎯 What Changed?

### Breaking Changes
- ❌ `chat_history.csv` → SQLite database
- ❌ `feedback.csv` → SQLite database
- ❌ `app.py` → `app_improved.py` (new main file)

### New Features
- ✅ Rate limiting (6 req/min)
- ✅ Persistent database storage
- ✅ Better error handling
- ✅ Security hardening
- ✅ Logging system

### Backward Compatibility
- ✅ All old modules still work (`cv_analyzer.py`, `job_matcher.py`, etc.)
- ✅ Job database format unchanged
- ✅ PDF documents in `docs/` folder unchanged
- ✅ ChromaDB vector store compatible

---

## 📋 Pre-Migration Checklist

Before you start:

- [ ] Backup all data files
- [ ] Export current chat history
- [ ] Export current feedback
- [ ] Note your current API keys
- [ ] Check Python version (3.10+ required)

---

## 🔄 Step-by-Step Migration

### Step 1: Backup Current Data

```bash
# Create backup directory
mkdir backup_$(date +%Y%m%d)

# Backup CSV files (if they exist)
cp chat_history.csv backup_$(date +%Y%m%d)/ 2>/dev/null || true
cp feedback.csv backup_$(date +%Y%m%d)/ 2>/dev/null || true

# Backup database
cp -r db backup_$(date +%Y%m%d)/ 2>/dev/null || true

# Backup any custom data
cp -r data backup_$(date +%Y%m%d)/ 2>/dev/null || true
```

### Step 2: Pull Latest Code

```bash
# Fetch latest changes
git fetch origin main

# Check what changed
git diff HEAD origin/main

# Pull updates
git pull origin main
```

Or download manually:
```bash
# Download updated files
curl -O https://raw.githubusercontent.com/Yossefmohammed/daleel-ai/main/app_improved.py
curl -O https://raw.githubusercontent.com/Yossefmohammed/daleel-ai/main/.gitignore
curl -O https://raw.githubusercontent.com/Yossefmohammed/daleel-ai/main/.env.example
```

### Step 3: Update Dependencies

```bash
# Update packages
pip install -r requirements.txt --upgrade

# Verify installations
python -c "import streamlit; import groq; import chromadb; print('✅ All dependencies OK')"
```

### Step 4: Create Environment File

```bash
# Copy template
cp .env.example .env

# Edit with your keys
nano .env
```

Add your keys:
```bash
GROQ_API_KEY=gsk_your_key_here
GITHUB_TOKEN=ghp_your_token_here

# Optional: customize settings
MAX_REQUESTS_PER_MINUTE=6
CACHE_HOURS=24
MAX_JOB_MATCHES=8
```

### Step 5: Migrate CSV Data to SQLite

If you have old CSV files with chat history:

```python
# migration_script.py
import sqlite3
import pandas as pd
from pathlib import Path

def migrate_csv_to_sqlite():
    db_path = Path("db/daleel_data.db")
    db_path.parent.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Create tables (same as in app_improved.py)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            timestamp TEXT,
            user_message TEXT,
            bot_response TEXT,
            response_time REAL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            timestamp TEXT,
            message_id INTEGER,
            feedback_type TEXT,
            comment TEXT
        )
    ''')
    
    # Migrate chat history
    if Path("chat_history.csv").exists():
        df = pd.read_csv("chat_history.csv")
        # Adjust column names if needed
        if 'user_msg' in df.columns:
            df = df.rename(columns={'user_msg': 'user_message', 'bot_msg': 'bot_response'})
        
        # Add missing columns with defaults
        if 'session_id' not in df.columns:
            df['session_id'] = 'migrated'
        if 'response_time' not in df.columns:
            df['response_time'] = 0.0
        
        df.to_sql('chat_history', conn, if_exists='append', index=False)
        print(f"✅ Migrated {len(df)} chat messages")
    
    # Migrate feedback
    if Path("feedback.csv").exists():
        df = pd.read_csv("feedback.csv")
        if 'session_id' not in df.columns:
            df['session_id'] = 'migrated'
        
        df.to_sql('feedback', conn, if_exists='append', index=False)
        print(f"✅ Migrated {len(df)} feedback entries")
    
    conn.commit()
    conn.close()
    print("✅ Migration complete!")

if __name__ == "__main__":
    migrate_csv_to_sqlite()
```

Run migration:
```bash
python migration_script.py
```

### Step 6: Test New Version

```bash
# Run improved version
streamlit run app_improved.py

# Test in browser at http://localhost:8501
```

**Test checklist:**
- [ ] App starts without errors
- [ ] API key validated correctly
- [ ] Job matching works
- [ ] CV analysis works
- [ ] GitHub analysis works
- [ ] Rate limiting triggers after 6 requests
- [ ] Chat history exports correctly
- [ ] Feedback exports correctly

### Step 7: Update Deployment

#### For Streamlit Cloud:

1. Go to your app settings
2. Change main file: `app.py` → `app_improved.py`
3. Update secrets (if needed)
4. Reboot app

#### For Render:

1. Update `startCommand` in dashboard:
```bash
streamlit run app_improved.py --server.port $PORT --server.address 0.0.0.0
```

2. Redeploy

#### For Docker:

```bash
# Rebuild image
docker build -t daleel-ai:v1.1 .

# Stop old container
docker stop daleel-ai
docker rm daleel-ai

# Run new version
docker run -d \
  --name daleel-ai \
  -p 8501:8501 \
  --env-file .env \
  -v $(pwd)/db:/app/db \
  daleel-ai:v1.1
```

---

## ⚠️ Common Migration Issues

### Issue 1: "GROQ_API_KEY not set"

**Cause**: Environment file not loaded

**Fix**:
```bash
# Make sure .env exists and has your key
cat .env | grep GROQ_API_KEY

# If empty, add your key
echo "GROQ_API_KEY=gsk_your_key_here" >> .env
```

### Issue 2: Rate limit immediately triggered

**Cause**: Old timestamps in session state

**Fix**:
```bash
# Clear browser cache and restart app
# Or increase limit in .env:
echo "MAX_REQUESTS_PER_MINUTE=10" >> .env
```

### Issue 3: Database locked error

**Cause**: Multiple instances accessing same SQLite file

**Fix**:
```bash
# Stop all running instances
pkill -f streamlit

# Delete lock file
rm db/*.db-shm db/*.db-wal

# Restart single instance
streamlit run app_improved.py
```

### Issue 4: Import errors

**Cause**: New dependencies not installed

**Fix**:
```bash
# Reinstall all dependencies
pip install -r requirements.txt --force-reinstall

# Or create fresh virtual environment
python -m venv venv_new
source venv_new/bin/activate
pip install -r requirements.txt
```

### Issue 5: CSV export returns empty

**Cause**: Database not migrated

**Fix**:
- Run migration script (Step 5 above)
- Or manually add some test data through the UI

---

## 🔄 Rollback Plan

If v1.1 has issues, rollback to v1.0:

```bash
# Option 1: Git revert
git checkout HEAD~1

# Option 2: Use old file directly
streamlit run app.py  # old version

# Option 3: Restore from backup
cp backup_20260418/app.py .
cp backup_20260418/*.csv .
```

---

## 📊 Verification

After migration, verify:

```bash
# Check database exists
ls -lh db/daleel_data.db

# Check records migrated
sqlite3 db/daleel_data.db "SELECT COUNT(*) FROM chat_history;"
sqlite3 db/daleel_data.db "SELECT COUNT(*) FROM feedback;"

# Check logs
tail -f daleel.log
```

---

## 🎉 Migration Complete!

You should now have:
- ✅ Secure API key management
- ✅ Rate limiting active
- ✅ Persistent database storage
- ✅ Better error handling
- ✅ All old data migrated

---

## 📞 Need Help?

If you encounter issues:

1. Check the logs: `tail -f daleel.log`
2. Review error messages carefully
3. Consult the README: `README_IMPROVED.md`
4. Check security guide: `SECURITY.md`
5. Contact support: [your-email]

---

## 🗓️ Post-Migration Tasks

Within 1 week:

- [ ] Monitor logs for errors
- [ ] Verify rate limiting works
- [ ] Test all features thoroughly
- [ ] Update documentation
- [ ] Notify users of changes
- [ ] Delete old CSV backups (after confirming migration success)

Within 1 month:

- [ ] Consider upgrading to PostgreSQL for production
- [ ] Add monitoring/analytics
- [ ] Implement user authentication (Phase 2)

---

*Migration Guide v1.1 | Last Updated: April 2026*