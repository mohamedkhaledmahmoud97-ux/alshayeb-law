# PROJECT_MEMORY

> **Purpose:** This file serves as the persistent memory of the ALSHAYEB LAW project. It records the project's current state, implementation progress, AI sessions, technical decisions, completed work, pending tasks, and recovery instructions so that any AI assistant or developer can resume work without losing context.

---

# Project Status

**Project Name:** ALSHAYEB LAW

**Current Phase:** Phase 4 — Embedding Pipeline & Retrieval Engine (Step 1 Complete — Step 2 In Progress)

**Overall Progress:** 60%

**Status:** Active Development

**Last Updated:** 2026-07-28 (Session 11)

---

# Project Goal

Develop a high-accuracy Retrieval-Augmented Generation (RAG) system for Egyptian legal research that provides evidence-based answers with accurate legal citations.

Primary objectives include:

- Egyptian legal retrieval
- Citation validation
- Faithful answer generation
- Academic benchmarking
- Reproducible evaluation

---

# Current Repository State

## Completed

- Repository created and documented (Sessions 1–2)
- Full dataset analysis of `Egyptian_legal_laws.json` (Session 3)
- Multi-source ingestion architecture designed (Session 4)
- Statute Ingestion Pipeline implemented (Session 5)
- Generic Ingestion Framework implemented; 89 duplicate IDs fixed (Session 6)
- Phase 3.5 QA completed; scope classifier bug fixed (Session 7)
- Phase 3.6 Corpus Validation completed; article boundary fix, sub-chunk fix, extended metadata (Session 8)
- Pre-Phase 4 Engineering Audit completed; all critical and high findings resolved (Session 9)
- ADR-015 adopted; Phase 3.7 complete; Phase 4 cleared to begin (Session 10)

## Phase 3 — Ingestion Pipeline: COMPLETE

Files created:

- `src/data/models.py` — Source, Node, Chunk dataclasses
- `src/preprocessing/arabic_normalizer.py` — Arabic character normalization
- `src/data/base_parser.py` — BaseParser ABC + ParsedDocument
- `src/data/parser_registry.py` — ParserRegistry singleton
- `src/data/statute_parser.py` — StatuteParser (fully implemented)
- `src/data/pdf_book_parser.py` — PDFBookParser (stub)
- `src/data/court_judgment_parser.py` — CourtJudgmentParser (stub)
- `src/data/ingestion_orchestrator.py` — generic orchestrator
- `src/data/statute_ingestion.py` — backward-compatible entry point
- `src/data/canonical_store.py` — JSONL writer/reader
- `src/config/constants.py` — updated with CANONICAL_STORE_DIR, STATUTE_DATASET

## Phase 3.5 — QA & Validation: COMPLETE

QA report: `docs/INGESTION_QA_REPORT.md`

Bugs fixed this phase:

- Scope classifier false positives: `حكم` and `جلسة` removed from `_CASE_LAW_SIGNALS` in `src/data/statute_parser.py`. 173 false-positive `case_law` classifications corrected.

Final verified statistics:

- 481 sources, 1,442 nodes, 8,085 chunks
- 0 duplicate chunk IDs, 0 duplicate source IDs, 0 duplicate node IDs
- All 10 integrity checks: PASS
- Scope: 455 statute / 16 treaty / 9 case_law / 1 uncertain

## Phase 3.6 — Corpus Validation: COMPLETE

Bugs fixed this phase:

- Article boundary extraction: added `مادة\s+\d+` as catch-all alternative in `_ARTICLE_BOUNDARY_RE`. 466/481 laws were producing 0 boundaries with the old regex.
- Sub-chunk fallback: three-level strategy (paragraph → sentence → hard word-split) added to `ingestion_orchestrator.py`.
- Extended chunk metadata: `document_type`, `parser_name`, `parser_version`, `language`, `chunk_hash`, `embedding_ready`, `created_at` stamped on every chunk.
- Validation script: removed stale local regex copy; now imports `_ARTICLE_BOUNDARY_RE` from `statute_parser`.

Final verified statistics:

- 481 sources, 1,455 nodes, 8,340 chunks
- 0 duplicate chunk IDs, 0 sub-chunk failures, max chunk = 2,048 chars
- OVERALL VALIDATION: PASS

## Phase 3.7 — Engineering Audit and ADR-015: COMPLETE

All 15 engineering audit findings resolved or formally deferred.
ADR-015 adopted: dual-representation Arabic normalization.
Phase 4 cleared to begin.

## Phase 4 — Embedding Pipeline & Retrieval Engine: IN PROGRESS

### Step 1 — Architecture: COMPLETE

File created: `docs/Phase4_Design_Document.md`

Key architectural decisions documented:
- FAISS index type: `IndexFlatIP` with L2-normalized vectors (cosine similarity)
- Embedding dimension: 1024 (BGE-M3 output)
- ADR-015 integration: `normalize_arabic()` called on chunk text before every encode call; normalized text never persisted
- Metadata alignment: FAISS position N ↔ metadata_list[N] (ordered list in metadata.pkl)
- Checkpoint strategy: per-batch numpy arrays + checkpoint.json for resumable execution
- Manifest: `embedding_manifest.json` with model name, dimension, checksums, timestamp
- Retrieval: `IndexFlatIP` exact search, scope_flag filter (ADR-013), Top-K with over-fetch
- Scalability path: IndexFlatIP → IndexIVFFlat → IndexIVFPQ as corpus grows

### Step 2 — Data Profiling: IN PROGRESS
### Step 3 — Embedding Pipeline: PENDING
### Step 4 — FAISS Validation: PENDING
### Step 5 — Retrieval Engine: PENDING

## Pending

- Phase 4 — Embedding Pipeline (CLEARED — begin implementation)
- Embedding pipeline must apply `normalize_arabic()` to chunk text before encoding (ADR-015)
- Embedding pipeline must apply `normalize_arabic()` to user queries before encoding (ADR-015)
- Vector database generation (FAISS index)
- Retrieval pipeline
- LLM integration
- Evaluation framework
- User interface

---

# Current Dataset

Current primary dataset:

- `datasets/Egyptian_legal_laws.json` — 481 records, all unique by title, ~2.49M tokens.
- Real schema (verified): `law_name` (str), `text` (str), `tokens` (int). No `law_number` or `article_number` in source — derived at ingestion.
- Two redundant copies exist (`egyptian-legal-laws-training-data.json`, `egyptian-legal-laws-training-data-preview.json`) — do not use in ingestion code.

Future datasets:

- Egyptian Civil Law Commentary (Al-Sanhuri) — PDF, not yet acquired
- Egyptian Court Judgments — format TBD
- Additional legal references

---

# Current Working Task

Phase 4 — Step 2: Data Profiling Statistical Analysis Report.

Read actual corpus files:
- `outputs/canonical/sources.jsonl` (481 records)
- `outputs/canonical/nodes.jsonl` (1,455 records)
- `outputs/canonical/chunks.jsonl` (8,340 records)

Produce: `reports/Data_Profiling_Statistical_Analysis_Report.md`

All statistics must be derived from the actual corpus. No fabricated metrics.

Architecture specification (from Step 1):
- Model: BAAI/bge-m3 (1024-dim)
- Index: FAISS IndexFlatIP with L2 normalization
- Input: `outputs/canonical/chunks.jsonl` (8,340 chunks)
- Output: `outputs/faiss/` (index.faiss + metadata.pkl + embedding_manifest.json)
- Metadata: all 14 chunk fields preserved in metadata.pkl
- ADR-015: normalize_arabic() applied before every encode call; never persisted
- Scope filter: scope_flag field (ADR-013)

Do not implement PDFBookParser or CourtJudgmentParser until the respective datasets are acquired and inspected.

---

# AI Session Log

## Session 1

Completed: Repository initialization, documentation planning, project specification.
Status: Completed

---

## Session 2

Completed: Repository structure, Python project structure, initial configuration.
Status: Completed

---

## Session 3

Completed: Full technical dataset analysis of `Egyptian_legal_laws.json`. Identified 11 risks. Produced chunking strategy and metadata recommendations.
Status: Completed

---

## Session 4

Completed: Multi-source `Source → Node → Chunk` architecture designed. Statute and Book ingestion pipelines designed. Unified metadata schema designed. `ARCHITECTURE.md`, `docs/PROJECT_SPEC.md`, `datasets/schema.md`, `CHANGELOG.md` updated.
Status: Completed

---

## Session 5

Completed: Statute Ingestion Pipeline implemented. `models.py`, `arabic_normalizer.py`, `statute_ingestion.py`, `canonical_store.py` created. `constants.py` updated. `src/__init__.py` syntax error fixed. Pipeline verified: 481 sources, 1442 nodes, 8085 chunks.
Status: Completed

---

## Session 6

Completed: Architecture review. 89 duplicate chunk IDs found and fixed (slug collision + artX preamble collision). Monolithic pipeline refactored into generic framework: BaseParser, ParserRegistry, StatuteParser, PDFBookParser stub, CourtJudgmentParser stub, ingestion_orchestrator. Uniqueness guard added. Verified: 0 duplicate IDs.
Status: Completed

---

## Session 11

Completed: Phase 4 Step 1 — Architecture Design Document.

**File created:**
- `docs/Phase4_Design_Document.md` — Complete Phase 4 architecture covering: objectives, system architecture diagram, component responsibilities (EmbeddingPipeline, FAISSStore, BGEEncoder, Retriever, RetrievalResult), embedding lifecycle, retrieval lifecycle, data/metadata flow, FAISS architecture (IndexFlatIP rationale, L2 normalization, checkpoint layout, manifest structure), BGE-M3 model selection rationale, ADR-015 integration specification, scalability path, performance targets, failure handling, future extensibility (hybrid retrieval, incremental indexing, model replacement, vector DB migration), file layout, implementation checklist.

**Key architectural decisions recorded in design document:**
- FAISS index type: IndexFlatIP (exact cosine similarity via inner product on L2-normalized vectors)
- Embedding dimension: 1024
- Checkpoint strategy: per-batch numpy arrays + checkpoint.json
- Metadata alignment: FAISS integer position = metadata_list index
- ADR-015 integration: normalize_arabic() called in _embed_batch() and retrieve(); normalized text never persisted
- Over-fetch strategy: search k*3 candidates, apply scope_flag filter, return top_k

**Files modified:**
- `PROJECT_MEMORY.md` — this update
- `CHANGELOG.md` — Version 0.9.0 added

Status: Completed

---

## Session 10

Completed: Phase 3.7 — ADR-015 Adoption and Engineering Audit Completion.

**ADR-015 — Dual-Representation Arabic Normalization:**

A third normalization architecture was adopted instead of Option A (normalize stored text) or Option B (query-time only). The decision:

- The canonical corpus (`outputs/canonical/chunks.jsonl`) is preserved exactly as published. No re-ingestion required.
- `normalize_arabic()` is applied to each chunk’s text immediately before passing it to the BGE-M3 encoder during Phase 4 embedding generation.
- The same normalization is applied to user queries before embedding at retrieval time.
- The normalized text is never persisted — it exists only in memory during encoding.
- Chunk IDs, chunk hashes, citation fields, and all stored text remain stable.

This resolves audit finding F-01 (High) without modifying the canonical store.

**Files modified this session:**

- `DECISIONS.md` — added ADR-015 with full rationale, consequences, and rejection table
- `CHANGELOG.md` — added Version 0.8.0 with full audit resolution table
- `docs/INGESTION_QA_REPORT.md` — updated §8 remaining risks
- `PROJECT_MEMORY.md` — this update

**Engineering Audit status after this session:**

All 15 findings are either resolved or formally deferred. No finding remains open or unaddressed.

Status: Completed

---

## Session 9

Completed: Pre-Phase 4 Engineering Audit — all critical and high findings resolved.

**Audit findings resolved:**

- **F-01 (High) — `arabic_normalizer.py` not wired into ingestion pipeline**: Recorded as a known architectural gap. The normalizer exists and is correct. Wiring it into the ingestion pipeline requires a deliberate decision about whether to normalize stored chunk text or normalize only at query time. This decision is deferred to Phase 4 and documented in PROJECT_MEMORY Known Issues.
- **F-02 (Medium) — `canonical_store.write_*` always overwrites**: Fixed. All three write functions now accept `append=True`. Default remains `False` (overwrite) to preserve existing behaviour for single-source ingestion.
- **F-03 (Medium) — `INGESTION_QA_REPORT.md` stale statistics**: Fixed. Report updated to Phase 3.6 final figures (1,455 nodes / 8,340 chunks / max chunk 2,048 chars).
- **F-05 (Low) — `utcnow()` deprecated in orchestrator**: Fixed. Replaced with `datetime.now(timezone.utc).isoformat()`.
- **F-06 (Low) — `parser_name` derived incorrectly in orchestrator**: Fixed. Added `parser_name` field to `ParsedDocument`. `StatuteParser` sets it explicitly. Orchestrator reads it directly.
- **F-07 (Medium) — `scope_flag` vs `source_type` undocumented**: Fixed. ADR-013 added to `DECISIONS.md`.
- **F-09 (Low) — `read_nodes()` and `read_sources()` missing**: Fixed. Both functions implemented in `canonical_store.py`.
- **F-12 (Medium) — Resource leak in `corpus_validation.py`**: Fixed. `open()` replaced with `with` statement.
- **F-14 (Info) — Chunk denormalization undocumented**: Fixed. ADR-014 added to `DECISIONS.md`.

**Files modified this session:**

- `src/data/base_parser.py` — added `parser_name` field to `ParsedDocument`
- `src/data/statute_parser.py` — set `parser_name="StatuteParser"` in yielded `ParsedDocument`
- `src/data/ingestion_orchestrator.py` — fixed `utcnow()`, fixed `parser_name` derivation
- `src/data/canonical_store.py` — added `append` mode, added `read_sources()` and `read_nodes()`
- `scripts/corpus_validation.py` — fixed resource leak
- `docs/INGESTION_QA_REPORT.md` — updated to Phase 3.6 final statistics
- `DECISIONS.md` — added ADR-013 and ADR-014
- `CHANGELOG.md` — added Version 0.7.0
- `PROJECT_MEMORY.md` — this update

**Findings deferred (not blocking Phase 4):**

- F-01: `arabic_normalizer.py` not wired into ingestion — deferred pending Phase 4 normalisation strategy decision (see Known Issues below)
- F-04: `camel-tools` CI installation risk — deferred; does not affect ingestion correctness
- F-08: `ParserRegistry` singleton side-effect import — deferred; functional, low risk at current scale
- F-10: `diagnostic.py` stale script — deferred; does not affect production code
- F-11: CI matrix Python version mismatch — deferred; no runtime failure
- F-13: `PROJECT_VERSION` stale in `constants.py` — deferred; constant is unused
- F-15: `python-publish.yml` generic template — deferred; no harm

Status: Completed

---

## Session 8

Completed: Phase 3.6 — Corpus Validation & Bug Fixes.

- **Article boundary extraction fix** (`src/data/statute_parser.py`): The original `_ARTICLE_BOUNDARY_RE` only matched `مادة (N)`, `مادة N-`, and ordinal variants. The dominant corpus format `مادة N <text>` was not matched, causing 466/481 laws to produce 0 article boundaries. Fixed by adding `مادة\s+\d+` as the final catch-all alternative. Result: 1,455 nodes produced (up from 1,442).
- **Three-level sub-chunk fallback** (`src/data/ingestion_orchestrator.py`): Some laws are stored as a single unbroken paragraph with no double-newlines. The original sub-chunker only split on paragraph breaks then sentence endings (`[.؟!]`), leaving oversized chunks. Fixed with three-level fallback: paragraph → sentence (expanded to `[.؟!،;]`) → hard word-split. Result: 0 sub-chunk failures, max chunk = 2,048 chars exactly.
- **Extended chunk metadata** (`src/data/ingestion_orchestrator.py`): Every chunk's `type_metadata` now contains: `document_type`, `parser_name`, `parser_version`, `language`, `chunk_hash` (SHA-256 first 16 hex), `embedding_ready`, `created_at`.
- **Corpus validation script** (`scripts/corpus_validation.py`): Removed stale local `_ARTICLE_BOUNDARY_RE` copy. Script now imports `_ARTICLE_BOUNDARY_RE` directly from `src.data.statute_parser` — the validation script can never diverge from the ingestion pipeline again.
- **Validation result**: OVERALL VALIDATION: PASS. All sections clean.
- **Phase 4 approved**: Embedding Pipeline (BAAI/bge-m3, FAISS) approved for implementation.

Final verified statistics:

- 481 sources, 1,455 nodes, 8,340 chunks
- 0 duplicate chunk IDs, 0 sub-chunk failures, max chunk = 2,048 chars

Status: Completed

---

## Session 7

Completed: Phase 3.5 QA & Validation.

- All required files verified present in repository.
- Pipeline re-run on canonical dataset.
- Full statistics collected (481 sources, 1442 nodes, 8085 chunks).
- 10 integrity checks: all PASS.
- Random sample audit (n=20, seed=42): all correct.
- Scope classifier bug identified and fixed:
  - Root cause: `حكم` (appeared in 179/481 laws as common statute vocabulary) and `جلسة` (8/481 laws) were triggering false `case_law` classifications.
  - Fix: removed both signals; retained only `محكمة النقض`, `طعن رقم`, `الطاعن`, `المطعون ضده`.
  - Result: 173 false positives corrected. Scope now: 455 statute / 16 treaty / 9 case_law / 1 uncertain.
- QA report written to `docs/INGESTION_QA_REPORT.md`.
- Phase 4 approved.

Status: Completed

---

## Current Decisions

### Decision 1
Use Markdown for all documentation. Reason: Version control and AI readability.

### Decision 2
Use GitHub as the project's single source of truth.

### Decision 3
Use JSON as the primary legal source for the first RAG implementation.

### Decision 4
Treat `datasets/Egyptian_legal_laws.json` as the single canonical dataset file.

### Decision 5
Adopt a unified `Source → Node → Chunk` data model with stable core schema + open `type_metadata`.

### Decision 6
Adopt a generic ingestion framework (BaseParser / ParserRegistry / Orchestrator) so the orchestrator depends only on the BaseParser interface.

### Decision 7
Scope classifier must use only precise multi-word phrases exclusive to court judgment text. Single common Arabic words (`حكم`, `جلسة`) must never be used as scope signals because they appear in all statute text.

### Decision 8
The `scope_flag` field (not `source_type`) is the correct field for filtering chunks by legal document category at retrieval time. `source_type` identifies the parser that produced the record; `scope_flag` identifies the legal category of the document. See ADR-013.

### Decision 9
Chunk denormalization (copying source metadata onto every chunk) is a deliberate design decision to make each chunk self-describing at retrieval time without requiring a secondary lookup. See ADR-014.

### Decision 10
Arabic normalization uses a dual-representation architecture (ADR-015). The canonical corpus is never modified. `normalize_arabic()` is applied only to the text passed to the embedding encoder — at document embedding time and at query embedding time. The normalized text is never persisted. This preserves legal citation fidelity while ensuring symmetric normalization between query and document vectors.

---

# Known Issues

- ~~89 duplicate chunk IDs~~ — Resolved in Session 6.
- ~~173 false-positive `case_law` scope classifications~~ — Resolved in Session 7.
- ~~`schema.md` does not match the real dataset schema~~ — Resolved in Session 4.
- ~~Article numbers are not unique within a document~~ — Resolved in Session 4.
- ~~Scraper boilerplate not removed~~ — Resolved in Session 5.
- ~~Longest chunk was 15,368 chars~~ — Resolved in Phase 3.6 (max chunk now 2,048 chars).
- ~~`arabic_normalizer.py` is implemented but not wired into the ingestion pipeline~~ — Resolved in Phase 3.7 via ADR-015. Normalization is applied at embedding time only; the canonical corpus is never modified.
- Vector database not yet generated.
- PDFBookParser not yet implemented (stub only — awaiting PDF source inspection).
- CourtJudgmentParser not yet implemented (stub only — awaiting dataset acquisition).

---

# Resume Instructions

Before continuing development:

1. Read README.md
2. Read PROJECT_SPEC.md
3. Read AI_CONTEXT.md
4. Read PROJECT_MEMORY.md

Then continue from the current working task. Do not recreate completed files. Preserve all architectural decisions.

---

# Next Immediate Tasks

Priority order:

1. ~~Build JSON Loader~~ ✅
2. ~~Normalize Arabic text~~ ✅
3. ~~Create metadata extractor~~ ✅
4. ~~Build chunking module~~ ✅
5. ~~QA & Validation~~ ✅
6. Generate embeddings (BAAI/BGE-M3 on chunks.jsonl) ← NEXT
7. Build FAISS index
8. Implement retriever
9. Connect the LLM
10. Evaluate retrieval quality

---

# Recovery Instructions

If an AI session ends unexpectedly:

- Read this file first.
- Continue from the latest completed task.
- Avoid repeating finished work.
- Preserve all repository structure.
- Record all new progress before stopping.

---

# Notes

This document must always reflect the latest implementation state of the project.

Every development session should update this file before completion.
