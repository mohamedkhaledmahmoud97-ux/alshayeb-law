"""
Statute parser for ALSHAYEB LAW.

Implements BaseParser for Egyptian statutory laws stored in the canonical
JSON dataset (Egyptian_legal_laws.json).

Pipeline (per record):
    1. Clean scraper artifacts (targeted deletion, never truncation).
    2. Extract law_number / law_year from title.
    3. Build a collision-free slug.
    4. Scope-classify (statute | case_law | treaty | uncertain).
    5. Segment into promulgation vs. main sections.
    6. Two-pass article boundary detection within each section.
    7. Yield a ParsedDocument.

The orchestrator handles chunking and canonical-store writes.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Iterator

from src.data.base_parser import BaseParser, ParsedDocument

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scraper artifact removal
# Targeted deletion — never truncate — to avoid silent data loss in the
# ~21 laws that have real article content after the CONTENT END marker.
# ---------------------------------------------------------------------------

_SCRAPER_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"يمكنك مشاركة المقالة من خلال تلك الايقونات\s*CONTENT END\s*\d*",
        re.UNICODE,
    ),
    re.compile(r"CONTENT END\s*\d*", re.UNICODE),
]

# ---------------------------------------------------------------------------
# Law number / year extraction
# Handles both "قانون رقم N لسنة YYYY" and "القانون رقم N لسنة YYYY"
# ---------------------------------------------------------------------------

_LAW_NUM_YEAR_RE = re.compile(
    r"(?:القانون|قانون)\s+رقم\s+(\d+)\s+لسنة\s+(\d{4})",
    re.UNICODE,
)

# ---------------------------------------------------------------------------
# Scope classification
#
# BUG FIXED (Phase 3.5 QA):
# Removed 'حكم' and 'جلسة' — both appear in ordinary statute text and
# caused 173 false-positive case_law classifications.
# Retained only precise multi-word phrases exclusive to court judgments.
# ---------------------------------------------------------------------------

_CASE_LAW_SIGNALS = re.compile(
    r"(محكمة النقض|طعن رقم|الطاعن|المطعون ضده)",
    re.UNICODE,
)
_TREATY_SIGNALS = re.compile(
    r"(اتفاقية|معاهدة|بروتوكول|ميثاق|الأمم المتحدة|الدول الأطراف)",
    re.UNICODE,
)

# ---------------------------------------------------------------------------
# Article boundary detection
#
# BUG FIXED (Phase 3.6 Corpus Validation):
# The original regex only matched:
#   - مادة (N)       — parenthesised number
#   - مادة N-        — number followed by dash/en-dash
#   - (المادة الأولى) — ordinal in parens
#   - مادة (الأولى)  — ordinal in parens variant
#
# Corpus diagnostic showed the dominant format is:
#   مادة N <space> <text>   e.g. "مادة 1 في تطبيق أحكام هذا القانون..."
#   مادة N\n               e.g. "مادة 10\n"
#   مادة N ملغاة           e.g. "مادة 23 ملغاة"
#
# This caused 466/481 laws to produce 0 article boundaries.
#
# Fix: add مادة\s+\d+ as the final (catch-all) alternative so any article
# header starting with مادة followed by a number is matched, regardless
# of what follows. More specific patterns remain first for priority.
# ---------------------------------------------------------------------------

_ARTICLE_BOUNDARY_RE = re.compile(
    r"(?:^|\n)\s*"
    r"(?:"
    r"\(المادة\s+[\w\u0600-\u06FF]+\)"    # (المادة الأولى)
    r"|مادة\s*\(\s*\d+\s*\)"               # مادة (1)
    r"|مادة\s+\d+\s*[-–]"                  # مادة 1-  or  مادة 1–
    r"|مادة\s*\(\s*[\u0600-\u06FF]+\s*\)"  # مادة (الأولى)
    r"|مادة\s+\d+"                          # مادة 1  (dominant corpus format)
    r")",
    re.UNICODE | re.MULTILINE,
)

# Numeric article boundary only — used for section splitting.
# Updated to include the bare مادة N format.
_NUMERIC_ARTICLE_RE = re.compile(
    r"(?:^|\n)\s*(?:مادة\s*\(\s*\d+\s*\)|مادة\s+\d+\s*[-–]|مادة\s+\d+)",
    re.UNICODE | re.MULTILINE,
)


class StatuteParser(BaseParser):
    """Parser for Egyptian statutory laws (JSON format)."""

    @property
    def source_type(self) -> str:
        return "statute"

    def parse(self, source_path: Path) -> Iterator[ParsedDocument]:
        """
        Parse Egyptian_legal_laws.json and yield one ParsedDocument per law.

        Deduplication is performed here (by law_name) so the orchestrator
        receives only unique records.  Slug collisions (same law_number+year
        under two different title formats) are resolved by appending a
        counter suffix: law-18-2019, law-18-2019-2, law-18-2019-3, …
        """
        raw_records = self._load(source_path)
        unique_records = self._deduplicate(raw_records)

        # Slug collision tracker: base_slug → count of times seen so far
        slug_counts: dict[str, int] = defaultdict(int)

        for record in unique_records:
            title: str = record["law_name"].strip()
            raw_text: str = record.get("text", "")
            token_count: int = record.get("tokens", max(1, len(raw_text) // 4))

            clean_text = self._clean(raw_text)
            law_number, law_year = self._extract_law_meta(title)
            base_slug = self._base_slug(title, law_number, law_year)

            # Collision-free slug
            slug_counts[base_slug] += 1
            count = slug_counts[base_slug]
            law_slug = base_slug if count == 1 else f"{base_slug}-{count}"

            scope_flag = self._classify_scope(title, clean_text)
            sections = self._split_sections(clean_text)

            yield ParsedDocument(
                source_type="statute",
                title=title,
                law_number=law_number,
                law_year=law_year,
                law_slug=law_slug,
                scope_flag=scope_flag,
                token_count=token_count,
                sections=sections,
                parser_name="StatuteParser",
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load(path: Path) -> list[dict]:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        logger.info("StatuteParser: loaded %d raw records from %s", len(data), path)
        return data

    @staticmethod
    def _deduplicate(records: list[dict]) -> list[dict]:
        seen: set[str] = set()
        unique: list[dict] = []
        for r in records:
            key = r["law_name"].strip()
            if key not in seen:
                seen.add(key)
                unique.append(r)
        removed = len(records) - len(unique)
        if removed:
            logger.info("StatuteParser: deduplication removed %d records", removed)
        return unique

    @staticmethod
    def _clean(text: str) -> str:
        for pattern in _SCRAPER_PATTERNS:
            text = pattern.sub("", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def _extract_law_meta(title: str) -> tuple[str | None, str | None]:
        m = _LAW_NUM_YEAR_RE.search(title)
        return (m.group(1), m.group(2)) if m else (None, None)

    @staticmethod
    def _base_slug(title: str, law_number: str | None, law_year: str | None) -> str:
        if law_number and law_year:
            return f"law-{law_number}-{law_year}"
        h = abs(hash(unicodedata.normalize("NFC", title))) % 10_000_000
        return f"law-{h}"

    @staticmethod
    def _classify_scope(title: str, text: str) -> str:
        sample = title + " " + text[:2000]
        if _CASE_LAW_SIGNALS.search(sample):
            return "case_law"
        if _TREATY_SIGNALS.search(sample):
            return "treaty"
        if re.search(r"قانون", title, re.UNICODE):
            return "statute"
        return "uncertain"

    @staticmethod
    def _split_sections(
        text: str,
    ) -> list[tuple[str, list[tuple[int | None, str]]]]:
        """
        Split law text into (section_name, articles) pairs.

        Returns a list (not dict) to preserve order:
            [("promulgation", [...articles...]), ("main", [...articles...])]

        Empty sections are omitted.
        """
        m = _NUMERIC_ARTICLE_RE.search(text)
        if not m:
            articles = StatuteParser._extract_articles(text)
            return [("promulgation", articles)] if articles else []

        split_pos = m.start()
        promulgation_text = text[:split_pos].strip()
        main_text = text[split_pos:].strip()

        result: list[tuple[str, list[tuple[int | None, str]]]] = []
        if promulgation_text:
            arts = StatuteParser._extract_articles(promulgation_text)
            if arts:
                result.append(("promulgation", arts))
        if main_text:
            arts = StatuteParser._extract_articles(main_text)
            if arts:
                result.append(("main", arts))
        return result

    @staticmethod
    def _extract_articles(
        section_text: str,
    ) -> list[tuple[int | None, str]]:
        """
        Two-pass article boundary detection.

        Pass 1: collect all boundary positions and article numbers.
        Pass 2: slice text between consecutive boundaries.
        """
        if not section_text.strip():
            return []

        boundaries: list[tuple[int, int | None]] = []
        for m in _ARTICLE_BOUNDARY_RE.finditer(section_text):
            num_match = re.search(r"\d+", m.group())
            art_num = int(num_match.group()) if num_match else None
            boundaries.append((m.start(), art_num))

        if not boundaries:
            return [(None, section_text.strip())]

        articles: list[tuple[int | None, str]] = []

        preamble = section_text[: boundaries[0][0]].strip()
        if preamble:
            articles.append((None, preamble))

        for i, (pos, art_num) in enumerate(boundaries):
            end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(section_text)
            art_text = section_text[pos:end].strip()
            if art_text:
                articles.append((art_num, art_text))

        return articles
