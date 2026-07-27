# Changelog

All notable changes to ALSHAYEB LAW will be documented in this file.

The project follows the principles of semantic versioning where applicable.

---

# Version 0.9.2 — Phase 4 Step 4: FAISS Validation

**Status**

Released

**Date**

July 2026

## Added

- **`src/embeddings/faiss_validator.py`**: Comprehensive FAISS index validator with 9 independent checks:
  - Index load integrity — verifies FAISS file exists and loads correctly
  - Vector count — verifies ntotal == 8,340 (expected chunk count)
  - Embedding dimension — verifies d == 1024 (BGE-M3 output)
  - Metadata alignment — verifies len(metadata_list) == FAISS ntotal
  - Orphan metadata check — verifies every metadata entry has valid chunk_id
  - Manifest consistency — verifies checksums, counts, dimensions match actual files
  - Index search integrity — verifies search returns correct shape and valid indices
  - Metadata field presence — verifies all 14 expected chunk fields present in every entry
  - Retrieval smoke test — runs 5 Arabic legal queries and validates results

- **`scripts/validate_faiss.py`**: CLI entry point with `--verbose`, `--quiet`, `--exit-on-fail` options. Writes machine-readable JSON report to `outputs/faiss/validation_report.json`.

- **`outputs/faiss/validation_report.json`**: Machine-readable validation report produced by `scripts/validate_faiss.py`.

## Validation Result

All 9 checks PASS. Phase 4 Step 4 complete. Step 5 — Retrieval Engine cleared to begin.

## Approval Gate

Phase 4 Step 4 complete. Step 5 — Retrieval Engine cleared to begin.

---

# Version 0.9.1 — Phase 4 Step 2: Data Profiling Statistical Analysis Report

**Status**

Released

**Date**

July 2026

## Added

- **`reports/Data_Profiling_Statistical_Analysis_Report.md`**: Programmatically derived data profiling report of the ALSHAYEB LAW canonical corpus (sources, nodes, chunks). Key additions include:
  - Exact counts: 481 sources, 1,455 nodes, 8,340 chunks.
  - Length statistics (character & token) confirming 0.0% of chunks exceed the 512-token limit.
  - Core metadata schema verification: 15 chunk fields and 7 type_metadata keys validated.
  - Chunk-level scope flag distribution (`scope_flag`): 7,667 statute, 387 treaty, 270 case law, 16 uncertain.
  - ID uniqueness and referential integrity audit (100% PASS).

## Approval Gate

Phase 4 Step 2 complete. Step 3 — Embedding Pipeline cleared to begin.

---

# Version 0.9.0 — Phase 4 Step 1: Architecture Design Document

**Status**

Released

**Date**

July 2026

## Added

- **`docs/Phase4_Design_Document.md`**: Complete Phase 4 architecture specification covering:
  - Objectives and success criteria (7 primary objectives)
  - System architecture diagram (Canonical Corpus → Embedding Pipeline → FAISS Store → Retrieval Engine)
  - Component responsibilities: `EmbeddingPipeline`, `FAISSStore`, `BGEEncoder`, `Retriever`, `RetrievalResult`
  - Embedding lifecycle (document) and retrieval lifecycle (query)
  - Data and metadata flow: all 14 chunk fields preserved in `metadata.pkl`
  - FAISS architecture: `IndexFlatIP` with L2-normalized vectors (cosine similarity); rationale for rejecting IVF and HNSW at current corpus scale
  - BGE-M3 model selection rationale: multilingual coverage, 8192-token context, Arabic benchmark performance, local inference
  - ADR-015 integration: exact code patterns for `_embed_batch()` and `retrieve()`; symmetry guarantee; canonical corpus immutability enforcement
  - Scalability path: IndexFlatIP → IndexIVFFlat → IndexIVFPQ as corpus grows
  - Performance targets: embedding throughput, query latency, FAISS search latency, memory footprint
  - Failure handling: OOM, model load failure, corrupt chunk, disk full, interrupted run, index not found, metadata mismatch
  - Future extensibility: hybrid retrieval, incremental indexing, model replacement, vector DB migration
  - Complete file and directory layout for Phase 4
  - Implementation checklist for Steps 1–5

## Approval Gate

Phase 4 Step 1 complete. Step 2 — Data Profiling Statistical Analysis Report cleared to begin.

---

# Version 0.8.0 — Phase 3.7 ADR-015 and Engineering Audit Completion

**Status**

Released

**Date**

July 2026

## Architecture Decision

- **ADR-015 — Dual-Representation Arabic Normalization** (`DECISIONS.md`): Adopted a third normalization architecture that preserves the canonical corpus exactly as published. Arabic normalization (`normalize_arabic()`) is applied only to the text passed to the embedding encoder — both at document embedding time and at query embedding time. The normalized text is never persisted. The original chunk text in `outputs/canonical/chunks.jsonl` is never modified. This resolves audit finding F-01 without touching the canonical store.

## Documentation

- **`DECISIONS.md`**: Added ADR-015 with full rationale, consequences, and rejection table for Options A and B.
- **`docs/INGESTION_QA_REPORT.md`**: Updated §8 remaining risks — arabic_normalizer open item resolved via ADR-015.
- **`PROJECT_MEMORY.md`**: Session 10 entry added. F-01 resolved. Decision 10 recorded. Phase 3.7 marked complete.

## Engineering Audit Status

All findings from the Pre-Phase 4 Engineering Audit are now resolved or formally deferred:

| Finding | Severity | Resolution |
|---|---|---|
| F-01 — `arabic_normalizer.py` not wired into pipeline | High | ✅ Resolved — ADR-015 adopted |
| F-02 — `canonical_store.write_*` always overwrites | Medium | ✅ Fixed in v0.7.0 |
| F-03 — `INGESTION_QA_REPORT.md` stale statistics | Medium | ✅ Fixed in v0.7.0 |
| F-05 — `utcnow()` deprecated | Low | ✅ Fixed in v0.7.0 |
| F-06 — `parser_name` derived incorrectly | Low | ✅ Fixed in v0.7.0 |
| F-07 — `scope_flag` vs `source_type` undocumented | Medium | ✅ Fixed in v0.7.0 (ADR-013) |
| F-09 — `read_nodes()` / `read_sources()` missing | Low | ✅ Fixed in v0.7.0 |
| F-12 — Resource leak in `corpus_validation.py` | Medium | ✅ Fixed in v0.7.0 |
| F-14 — Chunk denormalization undocumented | Info | ✅ Fixed in v0.7.0 (ADR-014) |
| F-04 — `camel-tools` CI risk | Medium | ⏳ Deferred — does not affect ingestion |
| F-08 — `ParserRegistry` singleton side-effect | Low | ⏳ Deferred — functional at current scale |
| F-10 — `diagnostic.py` stale script | Low | ⏳ Deferred — does not affect production |
| F-11 — CI matrix Python version mismatch | Low | ⏳ Deferred — no runtime failure |
| F-13 — `PROJECT_VERSION` stale | Info | ⏳ Deferred — constant is unused |
| F-15 — `python-publish.yml` generic template | Info | ⏳ Deferred — no harm |

## Approval Gate

Phase 3.7 complete. Phase 4 — Embedding Pipeline cleared to begin.

---

# Version 0.7.0 — Pre-Phase 4 Engineering Audit Fixes

**Status**

Released

**Date**

July 2026

## Fixed

- **Deprecated `utcnow()` in orchestrator** (`src/data/ingestion_orchestrator.py`): Replaced `datetime.datetime.utcnow().isoformat() + "Z"` with `datetime.datetime.now(timezone.utc).isoformat()`. Eliminates DeprecationWarning on Python 3.12+ and produces a standards-compliant ISO 8601 UTC timestamp.
- **Fragile `parser_name` derivation in orchestrator** (`src/data/ingestion_orchestrator.py`): The orchestrator previously derived `parser_name` as `f"{source_type.capitalize()}Parser"`, which would produce incorrect metadata for any parser whose class name does not follow that convention. The orchestrator now reads `parser_name` directly from `ParsedDocument.parser_name`.
- **Resource leak in `corpus_validation.py`** (`scripts/corpus_validation.py`): Replaced `json.load(open(...))` with a `with` statement to ensure the file handle is closed after reading.

## Added

- **`parser_name` field on `ParsedDocument`** (`src/data/base_parser.py`): Each parser now declares its own name on the intermediate representation it yields. `StatuteParser` sets `parser_name="StatuteParser"`. Future parsers must set this field explicitly.
- **Append mode for canonical store writes** (`src/data/canonical_store.py`): All three `write_*` functions now accept an `append: bool = False` keyword argument. Pass `append=True` when running multiple ingestion passes (e.g. statutes then books) to prevent the second pass from overwriting the first.
- **`read_sources()` and `read_nodes()`** (`src/data/canonical_store.py`): The read API now covers all three record types. Previously only `read_chunks()` was implemented.

## Documentation

- **`docs/INGESTION_QA_REPORT.md`**: Updated to reflect Phase 3.6 final statistics (1,455 nodes / 8,340 chunks / max chunk 2,048 chars). Previous Phase 3.5 figures (1,442 nodes / 8,085 chunks / 15,368 max chunk) are preserved as historical notes.
- **`DECISIONS.md`**: Added ADR-013 (`scope_flag` vs `source_type` for retrieval filtering) and ADR-014 (chunk denormalization rationale).

---

# Version 0.6.0 — Phase 3.6 Corpus Validation

**Status**

Released

**Date**

July 2026

## Fixed

- **Article boundary extraction** (`src/data/statute_parser.py`): The original `_ARTICLE_BOUNDARY_RE` missed the dominant corpus format `مادة N <text>`, causing 466/481 laws to produce 0 article boundaries. Added `مادة\s+\d+` as the final catch-all alternative. Nodes increased from 1,442 to 1,455.
- **Oversized chunk splitting** (`src/data/ingestion_orchestrator.py`): Single-paragraph laws produced chunks exceeding MAX_CHUNK_CHARS. Replaced two-level splitter with three-level fallback: paragraph → sentence (`[.؟!،;]`) → hard word-split. Result: 0 sub-chunk failures, max chunk = 2,048 chars.
- **Corpus validation script** (`scripts/corpus_validation.py`): Removed stale local `_ARTICLE_BOUNDARY_RE` copy. Script now imports the pattern directly from `src.data.statute_parser`, eliminating the risk of future divergence.

## Added

- **Extended chunk metadata** (`src/data/ingestion_orchestrator.py`): Every chunk's `type_metadata` now contains `document_type`, `parser_name`, `parser_version`, `language`, `chunk_hash` (SHA-256 first 16 hex), `embedding_ready`, `created_at`.

## Verified Output (post-fix)

| Metric | Value |
|---|---|
| Sources | 481 |
| Nodes | 1,455 |
| Chunks | 8,340 |
| Duplicate chunk IDs | 0 |
| Sub-chunk failures | 0 |
| Max chunk (chars) | 2,048 |
| Overall validation | PASS |

## Approval Gate

Phase 4 — Embedding Pipeline approved.

---

# Version 0.5.0 — Phase 3.5 QA & Validation

**Status**

Released

**Date**

July 2026

## Added

- `docs/INGESTION_QA_REPORT.md` — Full Phase 3.5 QA report including pipeline statistics, integrity check results, scope classifier investigation, fixes applied, remaining risks, and Phase 4 approval gate.

## Fixed

- **Scope classifier false positives** (`src/data/statute_parser.py`):
  - Root cause: `حكم` appeared in 179/481 laws (37%) as common statute vocabulary (`أحكام هذا القانون`, `يلغى كل حكم يخالف`, etc.). `جلسة` appeared in 8/481 laws in procedural statute text. Both were incorrectly used as case-law signals.
  - Fix: removed `حكم` and `جلسة` from `_CASE_LAW_SIGNALS`. Retained only precise multi-word phrases exclusive to court judgment text: `محكمة النقض`, `طعن رقم`, `الطاعن`, `المطعون ضده`.
  - Result: 173 false-positive `case_law` classifications corrected.

## Verified Output (post-fix)

| Metric | Value |
|---|---|
| Sources | 481 |
| Nodes | 1,442 |
| Chunks | 8,085 |
| Duplicate chunk IDs | 0 |
| Duplicate source IDs | 0 |
| Duplicate node IDs | 0 |
| Integrity checks passed | 10 / 10 |
| scope: statute | 455 |
| scope: treaty | 16 |
| scope: case_law | 9 |
| scope: uncertain | 1 |

## Approval Gate

Phase 4 — Embedding Pipeline approved. See `docs/INGESTION_QA_REPORT.md` §9.

---

# Version 0.4.0 — Generic Ingestion Framework

**Status**

Released

**Date**

July 2026

## Added

- `src/data/base_parser.py` — BaseParser abstract base class and ParsedDocument dataclass. Defines the extension interface for all document-type parsers. The orchestrator depends only on this interface.
- `src/data/parser_registry.py` — ParserRegistry singleton. Maps source_type strings to BaseParser instances. Decouples the orchestrator from all concrete parsers.
- `src/data/statute_parser.py` — StatuteParser(BaseParser). All statute-specific logic extracted from the old monolithic statute_ingestion.py. Includes collision-free slug generation (per-slug counter) and two-pass article boundary detection.
- `src/data/pdf_book_parser.py` — PDFBookParser(BaseParser) stub. Raises NotImplementedError until a real PDF source is acquired and inspected per ARCHITECTURE.md §3.
- `src/data/court_judgment_parser.py` — CourtJudgmentParser(BaseParser) stub. Raises NotImplementedError until the court judgment dataset is acquired.
- `src/data/ingestion_orchestrator.py` — Generic ingestion orchestrator. Depends only on BaseParser. Handles chunking, citation ID assignment, and canonical-store writes for all document types. Includes a uniqueness guard that raises RuntimeError on duplicate chunk IDs.

## Changed

- `src/data/statute_ingestion.py` — Replaced with a thin backward-compatible entry point that registers StatuteParser and delegates to run_ingestion().

## Fixed

- 89 duplicate chunk IDs caused by two independent bugs:
  1. Slug collisions: same law_number+year appearing under two title formats both yielded the same base slug. Fixed by appending a per-slug counter on collision (law-18-2019, law-18-2019-2, …).
  2. artX preamble collision: multiple preamble chunks within the same section all received `artX`. Fixed by using a per-section preamble counter (artX1, artX2, …).

## Verified Output

- 481 sources, 1442 nodes, 8085 chunks, 0 duplicate chunk IDs, 0 slug collisions.

---

# Version 0.3.0 — Statute Ingestion Pipeline

**Status**

Released

**Date**

July 2026

## Added

- `src/data/models.py` — Source, Node, Chunk dataclasses implementing the unified `Source → Node → Chunk` canonical data model designed in `ARCHITECTURE.md` §2.
- `src/preprocessing/arabic_normalizer.py` — character-level Arabic normalization: alef variants, teh marbuta, yeh variants, tatweel removal, diacritics removal, whitespace normalization.
- `src/data/statute_ingestion.py` — full Statute Ingestion Pipeline:
  - Load from canonical JSON dataset only.
  - Deduplicate by law_name.
  - Targeted scraper-artifact removal (never truncation).
  - law_number / law_year extraction from title.
  - Scope classification: statute / case_law / treaty / uncertain.
  - Promulgation vs. main section segmentation.
  - Two-pass article boundary detection.
  - Article-level chunking with sub-chunking for long articles.
  - Deterministic citation IDs: `statute:{law_slug}:{section}:art{n}:seq{n}`.
- `src/data/canonical_store.py` — JSONL writer/reader for Source, Node, Chunk records under `outputs/canonical/`.

## Changed

- `src/config/constants.py` — added CANONICAL_STORE_DIR and STATUTE_DATASET path constants.

## Fixed

- `src/__init__.py` — fixed pre-existing syntax error in `__author__` string (nested double quotes).

## Verified Output

- 481 sources, 1442 nodes, 8085 chunks written to `outputs/canonical/`.
- Scope distribution: 287 statute, 182 case_law, 11 treaty, 1 uncertain.

---

# Version 0.1.0 — Repository Foundation

**Status**

Current Development

**Date**

July 2026

## Added

- Initialized the GitHub repository.
- Added the project license.
- Added the .gitignore file.
- Created the initial repository structure.
- Created the documentation directories.
- Created the datasets directory.
- Created the benchmarks directory.
- Created the source directory.

---

## Documentation

Added the following project documents:

- README.md
- PROJECT_SPEC.md
- AI_CONTEXT.md
- ARCHITECTURE.md
- REQUIREMENTS.md
- DEVELOPMENT_PLAN.md
- ROADMAP.md
- TODO.md
- DECISIONS.md

---

## Repository Improvements

- Organized repository structure.
- Defined documentation standards.
- Added architecture decision records (ADR).
- Established development workflow.
- Defined software requirements.
- Defined implementation roadmap.
- Created engineering backlog.

---

## Planned for Version 0.2.0

- Complete governance documents.
- Add CONTRIBUTING.md.
- Add SECURITY.md.
- Add CODE_OF_CONDUCT.md.
- Prepare benchmark datasets.
- Build dataset structure.
- Begin implementation of the RAG pipeline.

---

# Versioning Policy

The project follows semantic versioning.

Format:

MAJOR.MINOR.PATCH

Example:

- 1.0.0
- 1.1.0
- 1.2.3

Definitions:

- MAJOR: Breaking architectural or system changes.
- MINOR: New functionality and significant improvements.
- PATCH: Documentation updates, bug fixes, and minor corrections.

---

# Maintenance Rules

Whenever a significant change is introduced:

- Add a new version section.
- Record the release date.
- Summarize major additions.
- Summarize improvements.
- Document breaking changes if any.
- Never rewrite historical entries.

---

# Future Releases

## Version 0.2.0

- Governance documents
- Benchmark preparation
- Dataset organization

## Version 0.3.0

- Embedding pipeline
- Vector database
- Retrieval engine

## Version 0.4.0

- Reranker
- Citation validation
- Evaluation framework

## Version 1.0.0

First stable public release of ALSHAYEB LAW.
