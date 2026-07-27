"""
PDF Book Parser stub for ALSHAYEB LAW.

Handles legal commentary books (e.g. Al-Sanhuri's شرح القانون المدني).

STATUS: STUB — not implemented.

Per ARCHITECTURE.md §3, this parser must NOT be implemented until a real
PDF source has been acquired and its internal structure inspected.
The book hierarchy (Book → Volume → Chapter → Section → Page → Chunk)
and citation ID scheme are provisional until that inspection happens.

When implementing:
    - Use pdfplumber or pymupdf for text extraction.
    - Detect volume/chapter/section boundaries from headings or TOC.
    - Assign citation IDs: book:{book_slug}:{volume}:{chapter}:p{page}:seq{n}
    - Register with: registry.register(PDFBookParser())
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from src.data.base_parser import BaseParser, ParsedDocument


class PDFBookParser(BaseParser):
    """Parser for Arabic legal commentary books in PDF format. STUB."""

    @property
    def source_type(self) -> str:
        return "book"

    def parse(self, source_path: Path) -> Iterator[ParsedDocument]:
        raise NotImplementedError(
            "PDFBookParser is not yet implemented. "
            "Per ARCHITECTURE.md §3, implement only after acquiring and "
            "inspecting a real PDF source from datasets/doctrine/."
        )
