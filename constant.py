from chromadb.config import Settings
import os

CHROMA_SETTINGS = Settings(
    chroma_db_impl="duck_db+parquet",
    persist_directory="/tmp/db",  # Streamlit Cloud allows writing here
    anonymized_telemetry=False
)
