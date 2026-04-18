# Deployment Guide - Daleel AI

Complete guide for deploying Daleel AI to production environments.

---

## 📋 Pre-Deployment Checklist

Before deploying to any environment:

- [ ] All API keys stored as environment variables (never in code)
- [ ] `.env.example` created with placeholder values
- [ ] `.gitignore` includes `.env`, secrets, and database files
- [ ] No secrets in git history (`git log --all --full-history --source -- **/.env`)
- [ ] Dependencies locked (`pip freeze > requirements.txt`)
- [ ] Security scan passed (`pip-audit`)
- [ ] Rate limiting configured
- [ ] Error handling tested
- [ ] Database migrations tested

---

## 🎈 Streamlit Cloud (Recommended for MVP)

### Pros
- ✅ Free tier available
- ✅ Automatic HTTPS
- ✅ Built-in secrets management
- ✅ Easy deployment from GitHub
- ✅ Auto-deploys on git push

### Cons
- ⚠️ 1GB RAM limit on free tier
- ⚠️ App sleeps after inactivity
- ⚠️ No persistent disk (files reset on restart)

### Setup Steps

1. **Push to GitHub**

```bash
git add .
git commit -m "Prepare for deployment"
git push origin main
```

2. **Deploy on Streamlit Cloud**

- Go to [share.streamlit.io](https://share.streamlit.io)
- Click "New app"
- Select your repository
- Set main file: `app_improved.py`
- Click "Advanced settings"

3. **Configure Secrets**

In the "Secrets" section, add:

```toml
# Required
GROQ_API_KEY = "gsk_your_actual_key_here"

# Optional
GITHUB_TOKEN = "ghp_your_token_here"

# Configuration (optional)
MAX_REQUESTS_PER_MINUTE = "6"
CACHE_HOURS = "24"
MAX_JOB_MATCHES = "8"
```

4. **Deploy**

Click "Deploy" and wait 2-3 minutes.

### Database Persistence Issue

Streamlit Cloud resets the filesystem on each deploy, which means:
- SQLite database is lost
- Chat history disappears

**Solutions:**

A. **Use External Database** (Recommended for production)

```python
# Install in requirements.txt
# pymongo==4.6.0  # for MongoDB
# or
# psycopg2-binary==2.9.9  # for PostgreSQL

# Then replace SQLite code with MongoDB/PostgreSQL
```

B. **Accept Data Loss** (OK for MVP)

Add warning in UI:
```python
st.info("⚠️ Chat history is temporary and resets on app updates.")
```

---

## 🚀 Render (Better for Production)

### Pros
- ✅ Persistent disk support
- ✅ Custom domains
- ✅ More resources than Streamlit Cloud
- ✅ Auto-scaling
- ✅ Logs and monitoring

### Cons
- ⚠️ Paid plans for advanced features
- ⚠️ More complex setup than Streamlit Cloud

### Setup Steps

1. **Create `render.yaml`**

```yaml
services:
  - type: web
    name: daleel-ai
    env: python
    region: oregon
    plan: starter
    buildCommand: pip install -r requirements.txt && python -m spacy download en_core_web_sm
    startCommand: streamlit run app_improved.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
    envVars:
      - key: GROQ_API_KEY
        sync: false
      - key: GITHUB_TOKEN
        sync: false
      - key: MAX_REQUESTS_PER_MINUTE
        value: "6"
      - key: CACHE_HOURS
        value: "24"
    disk:
      name: daleel-data
      mountPath: /opt/render/project/src/db
      sizeGB: 1
```

2. **Connect Repository**

- Go to [render.com](https://render.com)
- Click "New +" → "Web Service"
- Connect your GitHub repository

3. **Configure Environment Variables**

In the Render dashboard:
- Add `GROQ_API_KEY`
- Add `GITHUB_TOKEN` (optional)

4. **Add Persistent Disk**

- Go to your service settings
- Click "Disks"
- Add disk mounted at `/opt/render/project/src/db`
- Size: 1GB minimum

5. **Deploy**

Render will auto-deploy from your `main` branch.

### Custom Domain

1. Go to Settings → Custom Domains
2. Add your domain: `daleel.yourdomain.com`
3. Update DNS:
```
Type: CNAME
Name: daleel
Value: [your-app].onrender.com
```

---

## 🐳 Docker (Self-Hosted)

### Dockerfile

Already included in your repo. To customize:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_sm

# Copy application
COPY . .

# Create necessary directories
RUN mkdir -p db data docs

# Expose port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Run app
CMD ["streamlit", "run", "app_improved.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Build and Run

```bash
# Build image
docker build -t daleel-ai:latest .

# Run with environment file
docker run -d \
  --name daleel-ai \
  -p 8501:8501 \
  --env-file .env \
  -v $(pwd)/db:/app/db \
  -v $(pwd)/data:/app/data \
  daleel-ai:latest

# Check logs
docker logs -f daleel-ai

# Stop
docker stop daleel-ai
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  daleel-ai:
    build: .
    ports:
      - "8501:8501"
    environment:
      - GROQ_API_KEY=${GROQ_API_KEY}
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - MAX_REQUESTS_PER_MINUTE=6
      - CACHE_HOURS=24
    volumes:
      - ./db:/app/db
      - ./data:/app/data
      - ./docs:/app/docs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

Run with:

```bash
docker-compose up -d
```

---

## ☁️ AWS Deployment

### Option 1: EC2

```bash
# Launch Ubuntu EC2 instance
# Install Docker
sudo apt update
sudo apt install -y docker.io docker-compose

# Clone repo
git clone https://github.com/yourusername/daleel-ai.git
cd daleel-ai

# Create .env
nano .env
# Add your keys

# Run with docker-compose
sudo docker-compose up -d

# Configure security group to allow port 8501
```

### Option 2: ECS (Elastic Container Service)

1. Push image to ECR
2. Create ECS task definition
3. Create ECS service
4. Configure load balancer
5. Add auto-scaling

### Option 3: App Runner

1. Build and push Docker image to ECR
2. Create App Runner service
3. Configure environment variables
4. Deploy

---

## 🌐 Azure Deployment

### Azure App Service

```bash
# Install Azure CLI
az login

# Create resource group
az group create --name daleel-rg --location eastus

# Create App Service plan
az appservice plan create \
  --name daleel-plan \
  --resource-group daleel-rg \
  --is-linux \
  --sku B1

# Create web app
az webapp create \
  --name daleel-ai \
  --resource-group daleel-rg \
  --plan daleel-plan \
  --runtime "PYTHON:3.10"

# Configure deployment
az webapp deployment source config \
  --name daleel-ai \
  --resource-group daleel-rg \
  --repo-url https://github.com/yourusername/daleel-ai \
  --branch main \
  --manual-integration

# Set environment variables
az webapp config appsettings set \
  --name daleel-ai \
  --resource-group daleel-rg \
  --settings GROQ_API_KEY="your_key"

# Set startup command
az webapp config set \
  --name daleel-ai \
  --resource-group daleel-rg \
  --startup-file "streamlit run app_improved.py --server.port 8000 --server.address 0.0.0.0"
```

---

## 🔐 Post-Deployment Security

### 1. Enable HTTPS

All platforms above support HTTPS. Ensure:

```python
# Add to app_improved.py if needed
if not st.secrets.get("development_mode"):
    if not st.get_option("server.enableXsrfProtection"):
        st.error("XSRF protection should be enabled in production")
```

### 2. Set Security Headers

For custom deployments, add reverse proxy (nginx):

```nginx
server {
    listen 80;
    server_name daleel.yourdomain.com;
    
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        
        # Security headers
        add_header X-Frame-Options "SAMEORIGIN";
        add_header X-Content-Type-Options "nosniff";
        add_header X-XSS-Protection "1; mode=block";
        add_header Referrer-Policy "strict-origin-when-cross-origin";
    }
}
```

### 3. Database Backups

```bash
# Automate daily backups
crontab -e

# Add this line:
0 2 * * * cp /path/to/db/daleel_data.db /path/to/backups/daleel_$(date +\%Y\%m\%d).db
```

### 4. Monitoring

Set up monitoring:

```python
# Add to requirements.txt
# sentry-sdk==1.40.0

# In app_improved.py
import sentry_sdk

if os.getenv("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        traces_sample_rate=1.0,
    )
```

---

## 📊 Performance Optimization

### 1. Cache Vector Embeddings

```python
@st.cache_resource
def load_vector_store():
    # Your vector store loading code
    pass
```

### 2. Optimize Job Loading

```python
@st.cache_data(ttl=3600)  # Cache for 1 hour
def _load_combined():
    # Your job loading code
    pass
```

### 3. Async API Calls

For future optimization:

```python
import asyncio
import aiohttp

async def fetch_jobs():
    # Async job fetching
    pass
```

---

## 🧪 Testing Before Deploy

```bash
# Run local tests
python -m pytest tests/

# Test with production-like settings
export GROQ_API_KEY="your_key"
export MAX_REQUESTS_PER_MINUTE="6"
streamlit run app_improved.py

# Load testing (optional)
pip install locust
locust -f tests/load_test.py
```

---

## 🆘 Rollback Plan

If deployment fails:

### Streamlit Cloud
1. Go to app settings
2. Click "Reboot app"
3. Or revert git commit and re-deploy

### Render
1. Go to "Deploys" tab
2. Click "Redeploy" on last working version

### Docker
```bash
# List images
docker images

# Revert to previous version
docker run -d --name daleel-ai daleel-ai:v1.0
```

---

## 📞 Deployment Support

**Need help?**

- Check logs first
- Review this guide
- Contact: [support email]

---

*Last Updated: April 2026*