"""
Base parser interface for ALSHAYEB LAW.

Every document-type parser must implement BaseParser.
The ingestion orchestrator depends only on this interface — it never
imports StatuteParser, PDFBookParser, or any concrete parser directly.

Extension pattern:
    1. Subclass BaseParser.
    2. Implement parse() to yield ParsedDocument records.
    3. Register the subclass in ParserRegistry.
    4. The orchestrator picks it up automatically.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator


@dataclass
class ParsedDocument:
    """
    Intermediate representation produced by a parser.

    A parser converts a raw source file (JSON, PDF, XML …) into a flat
    sequence of ParsedDocument records.  The orchestrator then converts
    each ParsedDocument into the canonical Source / Node / Chunk triple.

    Fields
    ------
    source_type     : "statute" | "book" | "case_law" | "treaty" | "uncertain"
    title           : human-readable document title
    law_number      : extracted law number, or None
    law_year        : extracted law year, or None
    law_slug        : URL-safe unique identifier (collision-free)
    scope_flag      : same vocabulary as source_type, set by the parser
    token_count     : whole-document token estimate
    sections        : ordered list of (section_name, [(article_number|None, text)])
                      section_name is "promulgation" | "main" for statutes,
                      "chapter_N" | "section_N" for books, etc.
    type_metadata   : open dict for source-specific fields (no schema migration needed)
    """

    source_type: str
    title: str
    law_number: str | None
    law_year: str | None
    law_slug: str
    scope_flag: str
    token_count: int
    sections: list[tuple[str, list[tuple[int | None, str]]]]
    parser_name: str = ""          # set by the parser; used in chunk type_metadata
    type_metadata: dict[str, Any] = field(default_factory=dict)


class BaseParser(ABC):
    """
    Abstract base class for all document-type parsers.

    Subclasses must implement parse().  They must NOT write to the
    canonical store — that is the orchestrator's responsibility.
    """

    @property
    @abstractmethod
    def source_type(self) -> str:
        """Return the source_type string this parser handles."""

    @abstractmethod
    def parse(self, source_path: Path) -> Iterator[ParsedDocument]:
        """
        Parse a source file and yield ParsedDocument records.

        Args:
            source_path: Path to the raw source file (JSON, PDF, …).

        Yields:
            One ParsedDocument per logical document in the source file.
            A single JSON file may contain hundreds of laws → hundreds of records.
            A single PDF book yields one record.
        """
