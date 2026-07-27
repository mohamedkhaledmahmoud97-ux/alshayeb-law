"""
Canonical store for ALSHAYEB LAW.

Writes and reads Source / Node / Chunk records as newline-delimited JSON (JSONL).
One file per record type, stored under outputs/canonical/.

Write behaviour
---------------
By default every write call overwrites the file (append=False).  Pass
append=True when running multiple ingestion passes (e.g. statutes then books)
so that records from earlier passes are preserved.

Read behaviour
--------------
All three read_* functions yield dataclass instances one at a time so that
large stores can be iterated without loading everything into memory.
"""

from __future__ import annotations

import dataclasses
import json
import logging
from pathlib import Path
from typing import Iterator

from src.data.models import Chunk, Node, Source

logger = logging.getLogger(__name__)

_CANONICAL_DIR = Path(__file__).resolve().parents[2] / "outputs" / "canonical"


def _ensure_dir() -> None:
    _CANONICAL_DIR.mkdir(parents=True, exist_ok=True)


def write_sources(sources: list[Source], *, append: bool = False) -> Path:
    _ensure_dir()
    path = _CANONICAL_DIR / "sources.jsonl"
    mode = "a" if append else "w"
    with path.open(mode, encoding="utf-8") as fh:
        for s in sources:
            fh.write(json.dumps(dataclasses.asdict(s), ensure_ascii=False) + "\n")
    logger.info("Wrote %d sources → %s (append=%s)", len(sources), path, append)
    return path


def write_nodes(nodes: list[Node], *, append: bool = False) -> Path:
    _ensure_dir()
    path = _CANONICAL_DIR / "nodes.jsonl"
    mode = "a" if append else "w"
    with path.open(mode, encoding="utf-8") as fh:
        for n in nodes:
            fh.write(json.dumps(dataclasses.asdict(n), ensure_ascii=False) + "\n")
    logger.info("Wrote %d nodes → %s (append=%s)", len(nodes), path, append)
    return path


def write_chunks(chunks: list[Chunk], *, append: bool = False) -> Path:
    _ensure_dir()
    path = _CANONICAL_DIR / "chunks.jsonl"
    mode = "a" if append else "w"
    with path.open(mode, encoding="utf-8") as fh:
        for c in chunks:
            fh.write(json.dumps(dataclasses.asdict(c), ensure_ascii=False) + "\n")
    logger.info("Wrote %d chunks → %s (append=%s)", len(chunks), path, append)
    return path


def read_sources() -> Iterator[Source]:
    path = _CANONICAL_DIR / "sources.jsonl"
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            yield Source(**json.loads(line))


def read_nodes() -> Iterator[Node]:
    path = _CANONICAL_DIR / "nodes.jsonl"
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            yield Node(**json.loads(line))


def read_chunks() -> Iterator[Chunk]:
    path = _CANONICAL_DIR / "chunks.jsonl"
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            yield Chunk(**json.loads(line))
