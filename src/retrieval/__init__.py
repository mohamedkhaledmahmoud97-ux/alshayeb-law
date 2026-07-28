"""
Retrieval package for ALSHAYEB LAW.

Provides:
    RetrievalResult   — Dataclass for a single retrieved chunk with metadata.
    Retriever         — Query → normalize → encode → FAISS search → filter → rank.
"""

from src.retrieval.result_types import RetrievalResult
from src.retrieval.retriever import Retriever

__all__ = [
    "RetrievalResult",
    "Retriever",
]

