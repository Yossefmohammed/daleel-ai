from chromadb.config import Settings
import os
import tempfile

# Use a subdirectory of the system temp directory – always writable
DEFAULT_PERSIST_DIR = os.path.join(tempfile.gettempdir(), "wasla_chroma_db")

CHROMA_SETTINGS = Settings(
    chroma_db_impl="duckdb+parquet",
    persist_directory=DEFAULT_PERSIST_DIR,
    anonymized_telemetry=False
)