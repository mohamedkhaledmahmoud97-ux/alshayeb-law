"""
Reranker orchestration for ALSHAYEB LAW.

Accepts a query and a list of candidate RetrievalResult objects (from Phase 4
Retrieval Engine), re-ranks them using the BGE cross-encoder, and returns a
re-ordered list with updated scores.

Design:
    - The reranker operates on the output of the Retrieval Engine.
    - It does NOT re-retrieve or modify the FAISS index.
    - It is a post-processing step that improves ranking precision.
    - The original retrieval scores are preserved in each result's
      `type_metadata` for ablation analysis.

Integration with broader pipeline:
    Retriever → Reranker → Context Builder (Phase 6) → LLM (Phase 6)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Sequence

from src.reranking.bge_reranker import BGEReranker

logger = logging.getLogger(__name__)


@dataclass
class RerankerResult:
    """
    Re-ranked result with both original and reranked scores.

    Fields
    ------
    chunk_id         : Deterministic chunk citation ID.
    text             : Original chunk text (not normalized).
    title            : Law or document title.
    law_number       : Extracted law number, or None.
    law_year         : Extracted law year, or None.
    law_slug         : URL-safe document identifier.
    scope_flag       : Legal category (statute / treaty / case_law / uncertain).
    section          : Section name (promulgation / main).
    article_number   : Article number, or None.
    seq              : Sub-chunk sequence number.
    source_id        : Parent source identifier.
    node_id          : Parent node identifier.
    original_score   : Score from the retrieval engine (cosine similarity).
    reranker_score   : Score from the cross-encoder reranker.
    combined_score   : Weighted combination of original_score and reranker_score.
    rank             : Final rank after reranking (1-based).
    type_metadata    : Open dict for additional metadata.
    """

    chunk_id: str
    text: str
    title: str
    law_number: str | None
    law_year: str | None
    law_slug: str
    scope_flag: str
    section: str
    article_number: int | None
    seq: int
    source_id: str
    node_id: str
    original_score: float
    reranker_score: float = 0.0
    combined_score: float = 0.0
    rank: int = 0
    type_metadata: dict[str, Any] = field(default_factory=dict)


class Reranker:
    """
    Orchestrates cross-encoder reranking over retrieved results.

    Usage::

        reranker = Reranker()
        results = reranker.rerank(query, retrieval_results, top_k=10)

    Args:
        model_name    : HuggingFace model ID. Default BAAI/bge-reranker-v2-m3.
        batch_size    : Scoring batch size. Default 32.
        device        : "cuda" | "cpu" | None (auto). Default None.
        show_progress : Show tqdm progress bar during scoring. Default True.
        alpha         : Weight for combining original_score and reranker_score.
                        combined = alpha * reranker_score + (1 - alpha) * original_score.
                        Default 0.7 (favour reranker).
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        batch_size: int = 32,
        device: str | None = None,
        *,
        show_progress: bool = True,
        alpha: float = 0.7,
    ) -> None:
        self._alpha = alpha
        self._reranker_model = BGEReranker(
            model_name=model_name,
            batch_size=batch_size,
            device=device,
            show_progress_bar=show_progress,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def model_name(self) -> str:
        """HuggingFace model identifier of the underlying cross-encoder."""
        return self._reranker_model.model_name

    def rerank(
        self,
        query: str,
        candidates: Sequence[dict[str, Any]] | None = None,
        *,
        texts: Sequence[str] | None = None,
        metadatas: Sequence[dict[str, Any]] | None = None,
        top_k: int = 10,
    ) -> list[RerankerResult]:
        """
        Re-rank candidate documents by relevance to the query.

        Accepts candidates in one of two formats:
        1. A list of dicts (chunk metadata dicts from FAISS metadata.pkl).
        2. Separate lists of texts and metadatas (for flexible integration).

        Args:
            query      : The user query string.
            candidates : List of chunk metadata dicts. Each dict must contain
                         'text', 'chunk_id', 'title', etc.
                         Mutually exclusive with texts+metadatas.
            texts      : List of candidate document texts.
                         Mutually exclusive with candidates.
            metadatas  : List of metadata dicts corresponding to each text.
                         Required if texts is provided.
            top_k      : Number of top results to return after reranking.
                         Default 10.

        Returns:
            List of RerankerResult instances, sorted by combined_score
            descending (most relevant first).

        Raises:
            ValueError: If neither candidates nor texts are provided, or if
                        texts and metadatas have mismatched lengths.
        """
        # ── Resolve input format ──────────────────────────────────────────
        if candidates is not None:
            # Input is list of metadata dicts (from FAISS metadata.pkl)
            cand_texts = [c["text"] for c in candidates]
            cand_metadatas = candidates
        elif texts is not None and metadatas is not None:
            if len(texts) != len(metadatas):
                raise ValueError(
                    f"texts ({len(texts)}) and metadatas ({len(metadatas)}) "
                    "must have the same length."
                )
            cand_texts = list(texts)
            cand_metadatas = list(metadatas)
        else:
            raise ValueError(
                "Either candidates or (texts + metadatas) must be provided."
            )

        if not cand_texts:
            return []

        # ── Score with cross-encoder ──────────────────────────────────────
        scores = self._reranker_model.score(query, cand_texts)

        # ── Build RerankerResult list with combined scores ────────────────
        results: list[RerankerResult] = []
        for i in range(len(cand_texts)):
            meta = cand_metadatas[i]
            original_score = float(meta.get("_retrieval_score", meta.get("score", 0.0)))
            reranker_score = float(scores[i])
            combined = self._alpha * reranker_score + (1 - self._alpha) * original_score

            results.append(
                RerankerResult(
                    chunk_id=meta.get("chunk_id", ""),
                    text=cand_texts[i],
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
                    original_score=original_score,
                    reranker_score=reranker_score,
                    combined_score=combined,
                    rank=0,  # set below after sorting
                )
            )

        # ── Sort by combined_score descending and assign ranks ────────────
        results.sort(key=lambda r: r.combined_score, reverse=True)

        # Apply top_k
        results = results[:top_k]

        for idx, r in enumerate(results, start=1):
            r.rank = idx

        logger.info(
            "Reranked %d candidates → returned %d results (alpha=%.2f)",
            len(cand_texts),
            len(results),
            self._alpha,
        )
        return results
