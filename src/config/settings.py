from pathlib import Path

from dotenv import load_dotenv

# Project root directory
BASE_DIR = Path(__file__).resolve().parents[2]

# Load environment variables
load_dotenv(BASE_DIR / ".env")


class Settings:
    """Application settings."""

    APP_NAME = "ALSHAYEB LAW"
    VERSION = "0.1.0"

    HOST = "127.0.0.1"
    PORT = 8000

    EMBEDDING_MODEL = "BAAI/bge-m3"

    VECTOR_DATABASE = "FAISS"


settings = Settings()
