"""
Canonical data model for ALSHAYEB LAW.

Every legal source is represented as a three-level hierarchy:
    Source  — the original document (a law, a book, a judgment)
    Node    — a structural unit within a source (section, article, chapter)
    Chunk   — the text unit that is embedded and stored in the vector database

All three levels share a stable core metadata schema.
Source-specific fields live in `type_metadata` to avoid schema migration.

Phase 3.6 — extended type_metadata fields stamped on every Chunk:
    document_type   : source_type string ("statute", "book", …)
    parser_name     : name of the parser class that produced this chunk
    parser_version  : parser version string
    language        : ISO 639-1 language code ("ar")
    chunk_hash      : first 16 hex chars of SHA-256 of chunk text
    embedding_ready : True when the chunk is ready for embedding
    created_at      : UTC ISO-8601 timestamp of ingestion
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Source:
    """Top-level legal document."""

    source_id: str          # e.g. "statute:law-174-2025"
    source_type: str        # "statute" | "book" | "case_law" | "treaty" | "uncertain"
    title: str              # law_name as-is from the dataset
    law_number: str | None  # extracted, e.g. "174"
    law_year: str | None    # extracted, e.g. "2025"
    law_slug: str           # URL-safe slug derived from title
    scope_flag: str         # "statute" | "case_law" | "treaty" | "uncertain"
    token_count: int
    type_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Node:
    """Structural unit within a Source (section or article)."""

    node_id: str            # e.g. "statute:law-174-2025:main:art5"
    source_id: str
    node_type: str          # "section" | "article"
    section: str            # "promulgation" | "main"
    article_number: int | None
    text: str
    type_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    """Text unit that is embedded and stored in the vector database."""

    chunk_id: str           # deterministic citation ID
    node_id: str
    source_id: str
    source_type: str
    title: str
    law_number: str | None
    law_year: str | None
    law_slug: str
    scope_flag: str
    section: str
    article_number: int | None
    seq: int                # sequence within article (1-based; 1 for unsplit articles)
    text: str
    token_count: int
    type_metadata: dict[str, Any] = field(default_factory=dict)
    # type_metadata keys (Phase 3.6): document_type, parser_name, parser_version,
    # language, chunk_hash, embedding_ready, created_at
