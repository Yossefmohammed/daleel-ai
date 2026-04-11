FROM python:3.11-slim

WORKDIR /app

# System deps for PDF parsing and chromadb
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Optional: pre-download spaCy model
# RUN python -m spacy download en_core_web_sm

# Copy app source
COPY . .

# Create required directories
RUN mkdir -p docs data db .streamlit

# Expose Streamlit port
EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", \
            "--server.port=8501", \
            "--server.address=0.0.0.0", \
            "--server.headless=true"]