"""
Ingestion orchestrator for ALSHAYEB LAW.

Converts ParsedDocument records (produced by any BaseParser subclass) into
canonical Source / Node / Chunk triples and writes them to the canonical store.

The orchestrator knows nothing about statutes, PDFs, or judgments.
It depends only on BaseParser and the canonical data model.

Entry point:
    run_ingestion(source_type, source_path, registry)

Chunking strategy:
    - One Chunk per article by default.
    - Sub-chunk articles exceeding MAX_CHUNK_TOKENS using a three-level
      fallback: paragraph breaks → sentence breaks → hard word-split.
    - Citation ID format: {source_type}:{law_slug}:{section}:{art_part}:seq{n}
"""

from __future__ import annotations

import datetime
import hashlib
import logging
import re
from datetime import timezone
from pathlib import Path

from src.data.base_parser import BaseParser, ParsedDocument
from src.data.canonical_store import write_chunks, write_nodes, write_sources
from src.data.models import Chunk, Node, Source
from src.data.parser_registry import ParserRegistry

logger = logging.getLogger(__name__)

MAX_CHUNK_TOKENS = 512
_CHARS_PER_TOKEN = 4
PARSER_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Extended type_metadata builder (Phase 3.6)
# ---------------------------------------------------------------------------

def _build_type_metadata(source_type: str, parser_name: str, text: str) -> dict:
    """Build the extended type_metadata dict stamped on every Chunk."""
    return {
        "document_type": source_type,
        "parser_name": parser_name,
        "parser_version": PARSER_VERSION,
        "language": "ar",
        "chunk_hash": hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
        "embedding_ready": True,
        "created_at": datetime.datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Chunking helpers (source-type agnostic)
# ---------------------------------------------------------------------------

def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // _CHARS_PER_TOKEN)


def _sub_chunk(text: str) -> list[str]:
    """
    Split text into sub-chunks at paragraph/sentence/character boundaries.

    Three-level fallback strategy:
    1. Split on double newlines (paragraph breaks).
    2. For paragraphs still over limit: split on Arabic/Latin sentence endings.
    3. For text still over limit (no usable boundaries): hard word-split to
       guarantee every chunk fits within MAX_CHUNK_CHARS.

    This ensures no chunk ever exceeds MAX_CHUNK_CHARS, even for laws stored
    as a single unbroken paragraph (e.g. old military codes without newlines).
    """
    max_chars = MAX_CHUNK_TOKENS * _CHARS_PER_TOKEN
    if len(text) <= max_chars:
        return [text]

    def _split_on_sentences(para: str) -> list[str]:
        """Split a paragraph on sentence boundaries; hard word-split if needed."""
        sentences = re.split(r"(?<=[.؟!،;])\s+", para)
        result: list[str] = []
        current = ""
        for sent in sentences:
            if len(current) + len(sent) + 1 <= max_chars:
                current = (current + " " + sent).strip() if current else sent
            else:
                if current:
                    result.append(current)
                if len(sent) > max_chars:
                    # Hard word-split as last resort
                    words = sent.split()
                    current = ""
                    for word in words:
                        if len(current) + len(word) + 1 <= max_chars:
                            current = (current + " " + word).strip() if current else word
                        else:
                            if current:
                                result.append(current)
                            current = word
                else:
                    current = sent
        if current:
            result.append(current)
        return result if result else [para]

    paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_chars:
            current = (current + "\n\n" + para).strip() if current else para
        else:
            if current:
                chunks.append(current)
            if len(para) > max_chars:
                chunks.extend(_split_on_sentences(para))
                current = ""
            else:
                current = para

    if current:
        chunks.append(current)

    return chunks if chunks else [text]


def _citation_id(
    source_type: str,
    law_slug: str,
    section: str,
    art_num: int | str | None,
    seq: int,
) -> str:
    if art_num is None:
        art_part = "artX"
    elif isinstance(art_num, int):
        art_part = f"art{art_num}"
    else:
        art_part = f"art{art_num}"  # already a string like "X1", "X2"
    return f"{source_type}:{law_slug}:{section}:{art_part}:seq{seq}"


# ---------------------------------------------------------------------------
# Document → Source / Node / Chunk conversion
# ---------------------------------------------------------------------------

def _convert(doc: ParsedDocument) -> tuple[Source, list[Node], list[Chunk]]:
    source_id = f"{doc.source_type}:{doc.law_slug}"
    # Use the parser_name declared by the parser itself (set on ParsedDocument).
    # Never derive it from source_type — that assumption breaks for parsers whose
    # class name does not follow the {source_type.capitalize()}Parser convention.
    parser_name = doc.parser_name or f"{doc.source_type.capitalize()}Parser"

    source = Source(
        source_id=source_id,
        source_type=doc.source_type,
        title=doc.title,
        law_number=doc.law_number,
        law_year=doc.law_year,
        law_slug=doc.law_slug,
        scope_flag=doc.scope_flag,
        token_count=doc.token_count,
        type_metadata=doc.type_metadata,
    )

    nodes: list[Node] = []
    chunks: list[Chunk] = []

    for section_name, articles in doc.sections:
        preamble_counter = 0  # counts unnamed (artX) nodes per section
        for art_num, art_text in articles:
            if art_num is None:
                preamble_counter += 1
            node_id = _citation_id(
                doc.source_type, doc.law_slug, section_name,
                art_num if art_num is not None else f"X{preamble_counter}", 0
            ).replace(":seq0", "")
            node = Node(
                node_id=node_id,
                source_id=source_id,
                node_type="article",
                section=section_name,
                article_number=art_num,
                text=art_text,
                type_metadata=doc.type_metadata,
            )
            nodes.append(node)

            for seq, sub_text in enumerate(_sub_chunk(art_text), start=1):
                chunk_id = _citation_id(
                    doc.source_type, doc.law_slug, section_name,
                    art_num if art_num is not None else f"X{preamble_counter}", seq
                )
                chunks.append(
                    Chunk(
                        chunk_id=chunk_id,
                        node_id=node_id,
                        source_id=source_id,
                        source_type=doc.source_type,
                        title=doc.title,
                        law_number=doc.law_number,
                        law_year=doc.law_year,
                        law_slug=doc.law_slug,
                        scope_flag=doc.scope_flag,
                        section=section_name,
                        article_number=art_num,
                        seq=seq,
                        text=sub_text,
                        token_count=_estimate_tokens(sub_text),
                        type_metadata=_build_type_metadata(
                            doc.source_type, parser_name, sub_text
                        ),
                    )
                )

    return source, nodes, chunks


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_ingestion(
    source_type: str,
    source_path: Path,
    registry: ParserRegistry,
) -> tuple[list[Source], list[Node], list[Chunk]]:
    """
    Run the ingestion pipeline for a single source file.

    Looks up the correct parser from the registry, parses the file,
    converts each ParsedDocument to Source/Node/Chunk, writes the
    canonical store, and returns all three record lists.

    Args:
        source_type : e.g. "statute", "book", "case_law"
        source_path : path to the raw source file
        registry    : ParserRegistry with the relevant parser registered

    Returns:
        (sources, nodes, chunks)
    """
    parser: BaseParser = registry.get(source_type)

    all_sources: list[Source] = []
    all_nodes: list[Node] = []
    all_chunks: list[Chunk] = []

    for doc in parser.parse(source_path):
        source, nodes, chunks = _convert(doc)
        all_sources.append(source)
        all_nodes.extend(nodes)
        all_chunks.extend(chunks)

    # Uniqueness guard — fail loudly rather than silently produce bad data
    chunk_ids = [c.chunk_id for c in all_chunks]
    if len(chunk_ids) != len(set(chunk_ids)):
        from collections import Counter
        dupes = [k for k, v in Counter(chunk_ids).items() if v > 1]
        raise RuntimeError(
            f"Duplicate chunk IDs detected ({len(dupes)} groups). "
            f"First 5: {dupes[:5]}"
        )

    write_sources(all_sources)
    write_nodes(all_nodes)
    write_chunks(all_chunks)

    logger.info(
        "Ingestion complete [%s]: %d sources, %d nodes, %d chunks",
        source_type,
        len(all_sources),
        len(all_nodes),
        len(all_chunks),
    )
    return all_sources, all_nodes, all_chunks
