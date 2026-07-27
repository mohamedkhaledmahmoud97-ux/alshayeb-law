"""
Global constants for ALSHAYEB LAW.
"""

from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATASETS_DIR = PROJECT_ROOT / "datasets"
BENCHMARKS_DIR = PROJECT_ROOT / "benchmarks"
DOCS_DIR = PROJECT_ROOT / "docs"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
CANONICAL_STORE_DIR = OUTPUTS_DIR / "canonical"

# Canonical dataset file (single source of truth — do not use the two redundant copies)
STATUTE_DATASET = DATASETS_DIR / "Egyptian_legal_laws.json"

# Supported document formats
SUPPORTED_DOCUMENTS = [
    ".pdf",
    ".docx",
    ".txt",
    ".md",
]

# Supported languages
SUPPORTED_LANGUAGES = [
    "ar",
    "en",
]

# Default embedding model
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-m3"

# Default vector database
DEFAULT_VECTOR_DB = "FAISS"

# Project version
PROJECT_VERSION = "0.1.0"
