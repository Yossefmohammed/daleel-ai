import os
from chromadb.config import Settings

if "STREAMLIT_CLOUD" in os.environ:
    CHROMA_SETTINGS = Settings(
        chroma_db_impl="duck_db+parquet",
        persist_directory=None,  # in-memory
        anonymized_telemetry=False
    )
else:
    CHROMA_SETTINGS = Settings(
        chroma_db_impl="duck_db+parquet",
        persist_directory="db",  # local persistence
        anonymized_telemetry=False
    )
