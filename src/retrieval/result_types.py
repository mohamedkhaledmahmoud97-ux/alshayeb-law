"""
Retrieval result types for ALSHAYEB LAW.

Defines the RetrievalResult dataclass returned by the Retriever
to downstream components (Reranker, Context Builder, LLM).

Every result carries full chunk metadata and a retrieval score,
preserving all fields needed for citation construction, display,
and downstream reranking.

Design (Phase4_Design_Document.md §3.5):
    - All 14 chunk fields are preserved for citation fidelity.
    - `score` is the cosine similarity from FAISS inner-product search.
    - `rank` is assigned after scope filtering and sorting.
    - `type_metadata` carries extended metadata for future extensibility.

Metadata alignment (Phase4_Design_Document.md §5.2):
    FAISS position N ↔ metadata_list[N] ↔ RetrievalResult
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RetrievalResult:
    """
    A single retrieved chunk with its search score and full metadata.

    Fields
    ------
    chunk_id       : Deterministic chunk citation ID.
    score          : Cosine similarity score from FAISS inner-product search.
    rank           : Rank after filtering and sorting (1-based; 0 = unranked).
    text           : Original chunk text (not normalized — ADR-015).
    title          : Law or document title.
    law_number     : Extracted law number, or None.
    law_year       : Extracted law year, or None.
    law_slug       : URL-safe document identifier.
    scope_flag     : Legal category (statute / treaty / case_law / uncertain).
    section        : Section name (promulgation / main).
    article_number : Article number, or None.
    seq            : Sub-chunk sequence number (1-based; 1 for unsplit).
    source_id      : Parent source identifier.
    node_id        : Parent node identifier.
    type_metadata  : Open dict for extended metadata (Phase 3.6 fields).
    """

    chunk_id: str
    score: float
    rank: int
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
    type_metadata: dict[str, Any] = field(default_factory=dict)

