"""
Court Judgment Parser stub for ALSHAYEB LAW.

Handles Egyptian court judgment documents.

STATUS: STUB — not implemented.

Court judgments are a future dataset (see PROJECT_MEMORY.md).
This stub exists to confirm the extension point works and to document
the intended citation ID scheme:
    judgment:{court_slug}:{year}:case{n}:seq{n}

When implementing:
    - Determine source format (PDF, XML, JSON) from the actual dataset.
    - Extract: court name, case number, judgment date, parties, ruling text.
    - Assign citation IDs using the scheme above.
    - Register with: registry.register(CourtJudgmentParser())
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from src.data.base_parser import BaseParser, ParsedDocument


class CourtJudgmentParser(BaseParser):
    """Parser for Egyptian court judgment documents. STUB."""

    @property
    def source_type(self) -> str:
        return "case_law"

    def parse(self, source_path: Path) -> Iterator[ParsedDocument]:
        raise NotImplementedError(
            "CourtJudgmentParser is not yet implemented. "
            "Implement after the court judgment dataset is acquired."
        )
