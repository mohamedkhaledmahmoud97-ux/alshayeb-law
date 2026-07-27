"""
Statute ingestion entry point — ALSHAYEB LAW.

Backward-compatible entry point.  All logic now lives in:
    src/data/statute_parser.py       (StatuteParser)
    src/data/ingestion_orchestrator.py (run_ingestion)

This module registers StatuteParser and calls run_ingestion so that
existing callers of run_statute_ingestion() continue to work unchanged.
"""

from __future__ import annotations

from pathlib import Path

from src.config.constants import STATUTE_DATASET
from src.data.ingestion_orchestrator import run_ingestion
from src.data.models import Chunk, Node, Source
from src.data.parser_registry import registry
from src.data.statute_parser import StatuteParser

# Register the statute parser (idempotent — safe to call multiple times)
registry.register(StatuteParser())


def run_statute_ingestion(
    dataset_path: Path = STATUTE_DATASET,
) -> tuple[list[Source], list[Node], list[Chunk]]:
    """
    Run the Statute Ingestion Pipeline.

    Delegates to run_ingestion() via the generic framework.
    Returns (sources, nodes, chunks).
    """
    return run_ingestion("statute", dataset_path, registry)
