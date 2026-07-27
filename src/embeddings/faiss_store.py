"""
FAISS index encapsulation for ALSHAYEB LAW.

Wraps all FAISS read/write/search operations behind a clean interface.
The embedding pipeline and retriever interact with the FAISS index
exclusively through this class.

Design decisions (Phase 4):
    - Index type: IndexFlatIP (exact inner product = cosine on L2-normalized
      vectors). Selected over IVF/HNSW because exact search at 8,340 vectors
      is fast (<5ms CPU) and avoids recall loss from approximation. (ADR-010)
    - L2 normalization: Vectors added via add() are L2-normalized by FAISSStore
      as a safety net, but callers (BGEEncoder) already normalize.
    - Dimension: 1024 (BAAI/bge-m3 output). Enforced at construction time.
    - Metadata alignment: index position N ↔ metadata_list[N].
      FAISSStore does not manage metadata — that is the pipeline's responsibility.

Scalability path (documented in Phase4_Design_Document.md §9.2):
    IndexFlatIP → IndexIVFFlat → IndexIVFPQ
    Migration requires only changing the index constructor in build_new() —
    the rest of the codebase is unaffected.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

_EMBEDDING_DIM = 1024


class FAISSStore:
    """
    Encapsulates a FAISS IndexFlatIP for cosine-similarity search.

    Two construction paths:
        FAISSStore.build_new(dim)  — create an empty index
        FAISSStore.load(path)      — load an existing index from disk

    The index is kept in memory. Persist with save().

    Positions in the FAISS index correspond 1-to-1 with positions in the
    metadata list managed by EmbeddingPipeline. Callers must never add
    vectors out of order.
    """

    def __init__(self, index) -> None:
        """
        Wrap an existing FAISS index object.

        Prefer FAISSStore.build_new() or FAISSStore.load() over this
        constructor directly.
        """
        self._index = index

    # ------------------------------------------------------------------
    # Factory methods
    # ------------------------------------------------------------------

    @classmethod
    def build_new(cls, dim: int = _EMBEDDING_DIM) -> "FAISSStore":
        """
        Create an empty IndexFlatIP index.

        Args:
            dim: Embedding dimension. Must match the encoder output. Default 1024.

        Returns:
            FAISSStore wrapping an empty IndexFlatIP.
        """
        import faiss  # type: ignore[import]

        index = faiss.IndexFlatIP(dim)
        logger.info("Created new FAISS IndexFlatIP (dim=%d)", dim)
        return cls(index)

    @classmethod
    def load(cls, path: Path) -> "FAISSStore":
        """
        Load a FAISS index from disk and validate it.

        Args:
            path: Path to the .faiss binary file.

        Returns:
            FAISSStore wrapping the loaded index.

        Raises:
            FileNotFoundError: If the file does not exist.
            RuntimeError: If the loaded index has 0 dimensions (corrupt file).
        """
        import faiss  # type: ignore[import]

        if not path.exists():
            raise FileNotFoundError(
                f"FAISS index not found at '{path}'. "
                "Run the embedding pipeline first: "
                "  py -3 scripts/run_embedding_pipeline.py"
            )

        logger.info("Loading FAISS index from %s", path)
        index = faiss.read_index(str(path))

        if index.d == 0:
            raise RuntimeError(
                f"Loaded FAISS index at '{path}' has dimension 0. "
                "The file may be corrupt. Re-run the embedding pipeline."
            )

        logger.info(
            "FAISS index loaded: ntotal=%d, dim=%d", index.ntotal, index.d
        )
        return cls(index)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def d(self) -> int:
        """Embedding dimension of the index."""
        return self._index.d

    @property
    def ntotal(self) -> int:
        """Number of vectors currently in the index."""
        return self._index.ntotal

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def add(self, vectors: np.ndarray) -> None:
        """
        Add L2-normalized float32 vectors to the index.

        Vectors are re-normalized here as a safety net in case the caller
        did not normalize. The BGEEncoder already normalizes, so in practice
        this is a no-op normalization (norms already ~1.0).

        Args:
            vectors: float32 numpy array of shape (n, d).

        Raises:
            ValueError: If the vector dimension does not match the index.
        """
        if vectors.ndim != 2 or vectors.shape[1] != self._index.d:
            raise ValueError(
                f"Expected vectors of shape (n, {self._index.d}), "
                f"got {vectors.shape}."
            )

        # Safety-net L2 normalization
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.where(norms == 0.0, 1.0, norms)
        normalized = (vectors / norms).astype(np.float32)

        self._index.add(normalized)
        logger.debug("Added %d vectors to FAISS index (ntotal=%d)", len(vectors), self.ntotal)

    def search(
        self, query_vector: np.ndarray, k: int
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Search the index for the k nearest neighbors.

        Args:
            query_vector: float32 array of shape (1, d), L2-normalized.
            k: Number of neighbors to return.

        Returns:
            (distances, indices) — both float32/int64 arrays of shape (1, k).
            Distances are inner-product scores in [-1, 1] (cosine similarity).
            Indices are integer positions in the index (-1 = not found).

        Raises:
            ValueError: If the query vector has the wrong dimension.
        """
        if query_vector.ndim != 2 or query_vector.shape[1] != self._index.d:
            raise ValueError(
                f"Expected query_vector of shape (1, {self._index.d}), "
                f"got {query_vector.shape}."
            )

        effective_k = min(k, self.ntotal)
        if effective_k == 0:
            empty = np.empty((1, 0), dtype=np.float32)
            empty_idx = np.empty((1, 0), dtype=np.int64)
            return empty, empty_idx

        distances, indices = self._index.search(query_vector, effective_k)
        return distances, indices

    def save(self, path: Path) -> None:
        """
        Persist the index to disk as a FAISS binary file.

        Args:
            path: Destination path (e.g. outputs/faiss/index.faiss).
                  Parent directories are created if they do not exist.

        Raises:
            OSError: If the file cannot be written (e.g. disk full).
        """
        import faiss  # type: ignore[import]

        path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(
            "Saving FAISS index to %s (ntotal=%d, dim=%d)",
            path, self.ntotal, self.d,
        )
        faiss.write_index(self._index, str(path))
        logger.info("FAISS index saved successfully.")
