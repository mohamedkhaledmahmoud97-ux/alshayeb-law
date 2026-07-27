"""
BGE-M3 encoder wrapper for ALSHAYEB LAW.

Wraps BAAI/bge-m3 (FlagEmbedding / sentence-transformers) for consistent,
L2-normalized encode calls used by the embedding pipeline and the retriever.

Design decisions (Phase 4):
    - Model: BAAI/bge-m3 (ADR-011)
    - L2 normalization applied to ALL output vectors before returning
    - Device auto-selected: CUDA if available, otherwise CPU
    - Batch size configurable; default 32

ADR-015 compliance:
    The encoder itself is normalization-agnostic. Arabic normalization
    (normalize_arabic) must be applied by the CALLER before passing text
    to encode_documents() or encode_query().  This module never calls
    normalize_arabic — doing so here would violate the single-responsibility
    principle and make the encoder unusable for non-Arabic text in future.
"""

from __future__ import annotations

import logging
from typing import Sequence

import numpy as np

logger = logging.getLogger(__name__)

_EMBEDDING_DIM = 1024
_MODEL_NAME = "BAAI/bge-m3"


class BGEEncoder:
    """
    Thin wrapper around BAAI/bge-m3 for document and query encoding.

    All returned vectors are L2-normalized float32 numpy arrays, making
    them ready for inner-product (cosine) similarity search in FAISS
    IndexFlatIP without any further transformation.

    Usage::

        encoder = BGEEncoder()
        doc_vectors = encoder.encode_documents(["text1", "text2"])
        query_vector = encoder.encode_query("query text")

    Args:
        model_name : HuggingFace model identifier. Default BAAI/bge-m3.
        batch_size : Encoding batch size. Reduce if OOM on CPU. Default 32.
        device     : "cuda", "cpu", or None (auto-select). Default None.
        show_progress_bar : Show tqdm progress bar during encoding. Default True.
    """

    def __init__(
        self,
        model_name: str = _MODEL_NAME,
        batch_size: int = 32,
        device: str | None = None,
        *,
        show_progress_bar: bool = True,
    ) -> None:
        self._model_name = model_name
        self._batch_size = batch_size
        self._show_progress_bar = show_progress_bar
        self._model = self._load_model(model_name, device)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_model(model_name: str, device: str | None):
        """Load model from HuggingFace Hub or local cache."""
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is required. "
                "Install it with: pip install sentence-transformers"
            ) from exc

        try:
            import torch

            if device is None:
                device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            device = "cpu"

        logger.info("Loading embedding model %s on device=%s", model_name, device)
        try:
            model = SentenceTransformer(model_name, device=device)
        except OSError as exc:
            raise OSError(
                f"Failed to load embedding model '{model_name}'. "
                "Ensure the model is downloaded or HuggingFace Hub is accessible. "
                f"Original error: {exc}"
            ) from exc

        logger.info(
            "Model loaded. Embedding dimension: %d",
            model.get_sentence_embedding_dimension(),
        )
        return model

    @staticmethod
    def _l2_normalize(vectors: np.ndarray) -> np.ndarray:
        """L2-normalize a float32 array row-wise. Safe against zero vectors."""
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        # Avoid division by zero for degenerate zero vectors
        norms = np.where(norms == 0.0, 1.0, norms)
        return (vectors / norms).astype(np.float32)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def embedding_dim(self) -> int:
        """Embedding dimension of the loaded model (should be 1024 for BGE-M3)."""
        return self._model.get_sentence_embedding_dimension()

    @property
    def model_name(self) -> str:
        """HuggingFace model identifier."""
        return self._model_name

    def encode_documents(self, texts: Sequence[str]) -> np.ndarray:
        """
        Encode a list of document strings into L2-normalized dense vectors.

        The caller is responsible for applying normalize_arabic() to texts
        before passing them here (ADR-015).

        Args:
            texts: Sequence of strings to encode.

        Returns:
            float32 numpy array of shape (len(texts), embedding_dim).
            All rows are L2-normalized.
        """
        if not texts:
            return np.empty((0, self.embedding_dim), dtype=np.float32)

        raw: np.ndarray = self._model.encode(
            list(texts),
            batch_size=self._batch_size,
            show_progress_bar=self._show_progress_bar,
            convert_to_numpy=True,
            normalize_embeddings=False,  # we normalize ourselves for explicit control
        )
        return self._l2_normalize(raw.astype(np.float32))

    def encode_query(self, text: str) -> np.ndarray:
        """
        Encode a single query string into an L2-normalized dense vector.

        The caller is responsible for applying normalize_arabic() to text
        before passing it here (ADR-015).

        Args:
            text: Single query string to encode.

        Returns:
            float32 numpy array of shape (1, embedding_dim), L2-normalized.
        """
        if not text or not text.strip():
            raise ValueError("Query text must not be empty.")

        raw: np.ndarray = self._model.encode(
            [text],
            batch_size=1,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=False,
        )
        return self._l2_normalize(raw.astype(np.float32))
