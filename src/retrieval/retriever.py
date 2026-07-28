"""
Retrieval Engine for ALSHAYEB LAW.

Implements dense retrieval over the FAISS vector index built by the Phase 4
embedding pipeline.  Produces ranked RetrievalResult objects that can be
consumed by the Phase 5 Reranker or directly by downstream components.

Lifecycle (Phase4_Design_Document.md §4.2):
    1. normalize_arabic(query) — in-memory only (ADR-015)
    2. Encode normalized query with BAAI/bge-m3
    3. FAISS similarity search with over-fetch (k × 3)
    4. Reconstruct full chunk metadata from metadata.pkl
    5. Apply scope_flag filter (ADR-013)
    6. Sort by score descending and assign ranks
    7. Return List[RetrievalResult]

Design decisions:
    - Over-fetch: search for top_k * 3 candidates, then apply scope_filter,
      then truncate to top_k.  This ensures that filtering does not reduce
      the final result count below top_k when some candidates are excluded.
    - Scope filter: optional.  When None, results are returned without
      filtering.  When a set of scope_flag values is provided, only chunks
      whose scope_flag is in that set are returned.
    - The retriever loads the FAISS index and metadata once at construction
      time and caches them for all subsequent queries.
    - The BGEEncoder is also loaded once and reused.

Integrity invariants:
    - normalize_arabic() is called on the query before every encode call.
      The normalized query string is never persisted or logged.
    - FAISS index position N ↔ metadata_list[N] ↔ RetrievalResult.
    - Raw chunk text from metadata_list is returned as-is (never normalized).
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Sequence

from src.config.constants import FAISS_STORE_DIR
from src.embeddings.bge_encoder import BGEEncoder
from src.embeddings.faiss_store import FAISSStore
from src.preprocessing.arabic_normalizer import normalize_arabic
from src.retrieval.result_types import RetrievalResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default paths (aligned with embedding_pipeline.py)
# ---------------------------------------------------------------------------

_FAISS_INDEX_PATH = FAISS_STORE_DIR / "index.faiss"
_METADATA_PATH = FAISS_STORE_DIR / "metadata.pkl"

# ---------------------------------------------------------------------------
# Retriever
# ---------------------------------------------------------------------------


class Retriever:
    """
    Dense retriever over the ALSHAYEB LAW FAISS index.

    Usage::

        retriever = Retriever()
        results = retriever.retrieve("أحكام القانون المدني", top_k=10)

    Args:
        faiss_path       : Path to the FAISS index file.
                           Default: outputs/faiss/index.faiss.
        metadata_path    : Path to the metadata pickle file.
                           Default: outputs/faiss/metadata.pkl.
        encoder          : BGEEncoder instance, or None to create a default one.
        default_top_k    : Default number of results to return. Default 10.
        overfetch_factor : Multiplier for over-fetching before scope filtering.
                           Default 3 (searches 3 × top_k candidates).
    """

    def __init__(
        self,
        faiss_path: Path | str | None = None,
        metadata_path: Path | str | None = None,
        encoder: BGEEncoder | None = None,
        *,
        default_top_k: int = 10,
        overfetch_factor: int = 3,
    ) -> None:
        self._default_top_k = default_top_k
        self._overfetch_factor = overfetch_factor

        # Resolve paths
        self._faiss_path = Path(faiss_path) if faiss_path else _FAISS_INDEX_PATH
        self._metadata_path = (
            Path(metadata_path) if metadata_path else _METADATA_PATH
        )

        # Load FAISS index (raises FileNotFoundError if missing)
        logger.info("Loading FAISS index from %s", self._faiss_path)
        self._store = FAISSStore.load(self._faiss_path)
        logger.info(
            "FAISS index loaded: ntotal=%d, dim=%d",
            self._store.ntotal,
            self._store.d,
        )

        # Load metadata
        logger.info("Loading metadata from %s", self._metadata_path)
        if not self._metadata_path.exists():
            raise FileNotFoundError(
                f"Metadata file not found at '{self._metadata_path}'. "
                "Run the embedding pipeline first."
            )
        with self._metadata_path.open("rb") as fh:
            self._metadata: list[dict] = pickle.load(fh)
        logger.info("Metadata loaded: %d records", len(self._metadata))

        # Validate alignment
        if len(self._metadata) != self._store.ntotal:
            raise RuntimeError(
                f"Metadata count ({len(self._metadata)}) does not match "
                f"FAISS vector count ({self._store.ntotal}). "
                "Re-run the embedding pipeline."
            )

        # Initialise or reuse encoder
        self._encoder = encoder or BGEEncoder(show_progress_bar=False)
        logger.info("Retriever ready (default_top_k=%d, overfetch=%d)", default_top_k, overfetch_factor)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def total_vectors(self) -> int:
        """Number of vectors in the FAISS index."""
        return self._store.ntotal

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        scope_filter: set[str] | None = None,
    ) -> list[RetrievalResult]:
        """
        Retrieve the top-k most relevant chunks for a query.

        ADR-015: The query is normalized with normalize_arabic() before
        encoding.  The normalized form is never persisted or logged.

        ADR-013: When scope_filter is provided, only chunks whose scope_flag
        matches one of the values in the set are returned.  Over-fetching
        (searching k × 3 candidates) ensures that the final top-k is not
        reduced by filtering.

        Args:
            query        : Raw Arabic query string.
            top_k        : Number of results to return.  Uses default_top_k
                           from constructor if None.
            scope_filter : Optional set of scope_flag values to filter by.
                           Example: {"statute", "treaty"}.

        Returns:
            List of RetrievalResult objects sorted by score descending
            (most relevant first).  Empty list if no results match.

        Raises:
            ValueError: If query is empty or whitespace-only.
        """
        # ── Validate inputs ──────────────────────────────────────────────
        if not query or not query.strip():
            raise ValueError("Query must not be empty.")

        effective_top_k = top_k if top_k is not None else self._default_top_k

        # ── Step 1: Normalize query (ADR-015 — in-memory only) ──────────
        normalized_query = normalize_arabic(query)

        # ── Step 2: Encode normalized query ─────────────────────────────
        query_vector = self._encoder.encode_query(normalized_query)
        # normalized_query goes out of scope here — never persisted

        # ── Step 3: FAISS search with over-fetch ────────────────────────
        search_k = min(
            effective_top_k * self._overfetch_factor,
            self._store.ntotal,
        )
        distances, indices = self._store.search(query_vector, search_k)

        # ── Step 4: Map indices to metadata ─────────────────────────────
        candidates: list[tuple[float, dict]] = []
        for pos in range(search_k):
            idx = int(indices[0][pos])
            score = float(distances[0][pos])

            # Skip invalid indices (-1 = not found)
            if idx < 0 or idx >= len(self._metadata):
                continue

            meta = self._metadata[idx]
            candidates.append((score, meta))

        # ── Step 5: Apply scope_flag filter (ADR-013) ───────────────────
        if scope_filter is not None and scope_filter:
            filtered: list[tuple[float, dict]] = []
            for score, meta in candidates:
                if meta.get("scope_flag", "") in scope_filter:
                    filtered.append((score, meta))
            candidates = filtered

        # ── Step 6: Sort by score descending, truncate to top_k ─────────
        candidates.sort(key=lambda pair: pair[0], reverse=True)
        candidates = candidates[:effective_top_k]

        # ── Step 7: Build RetrievalResult list with ranks ───────────────
        results: list[RetrievalResult] = []
        for rank, (score, meta) in enumerate(candidates, start=1):
            results.append(
                RetrievalResult(
                    chunk_id=meta.get("chunk_id", ""),
                    score=score,
                    rank=rank,
                    text=meta.get("text", ""),
                    title=meta.get("title", ""),
                    law_number=meta.get("law_number"),
                    law_year=meta.get("law_year"),
                    law_slug=meta.get("law_slug", ""),
                    scope_flag=meta.get("scope_flag", ""),
                    section=meta.get("section", ""),
                    article_number=meta.get("article_number"),
                    seq=meta.get("seq", 0),
                    source_id=meta.get("source_id", ""),
                    node_id=meta.get("node_id", ""),
                    type_metadata=meta.get("type_metadata", {}),
                )
            )

        logger.info(
            "Query returned %d results (top_k=%d, scope_filter=%s)",
            len(results),
            effective_top_k,
            scope_filter,
        )
        return results

