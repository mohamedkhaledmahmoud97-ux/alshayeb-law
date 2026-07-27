# Data Profiling Statistical Analysis Report

**Project:** ALSHAYEB LAW — Egyptian Legal RAG System  
**Phase:** 4 — Embedding Pipeline & Retrieval Engine (Step 2)  
**Version:** 1.0  
**Date:** July 2026  
**Status:** Completed  
**Source Data:** `outputs/canonical/` (canonical corpus)

---

## 1. Executive Summary

This report presents a comprehensive data profiling and statistical analysis of the ALSHAYEB LAW canonical corpus. The corpus is the foundation for the Phase 4 Embedding Pipeline and Retrieval Engine. 

All statistics in this report are programmatically derived from the actual, validated canonical corpus files:
- **Sources (`sources.jsonl`):** 481 records
- **Nodes (`nodes.jsonl`):** 1,455 records
- **Chunks (`chunks.jsonl`):** 8,340 records

The analysis confirms that the corpus conforms to all architectural parameters (e.g., maximum chunk size of 512 tokens / 2,048 characters), preserves complete referential integrity, and contains no duplicate identifiers. It highlights the critical importance of `scope_flag` filtering (ADR-013) due to the presence of mixed legal document types within a single parser scope.

---

## 2. Source-Level Analysis (`sources.jsonl`)

The top-level dataset consists of **481 legal source documents**.

### 2.1 Parser and Source Type Distribution
All 481 source records are parsed using the `StatuteParser`, yielding:
- `source_type = "statute"`: 481 records (100.0%)

### 2.2 Legal Scope Category Distribution (`scope_flag`)
The scope classifier detects and assigns a `scope_flag` to identify the actual legal category of each document. The distribution is as follows:

| Legal Category (`scope_flag`) | Count | Percentage |
|--------------------------------|-------|------------|
| **Statute** (`statute`)        | 455   | 94.59%     |
| **Treaty** (`treaty`)          | 16    | 3.33%      |
| **Case Law** (`case_law`)      | 9     | 1.87%      |
| **Uncertain** (`uncertain`)    | 1     | 0.21%      |
| **Total**                      | **481** | **100.00%**|

> [!IMPORTANT]
> **Retrieval Filter Validation (ADR-013):**
> Because 100% of the sources carry `source_type="statute"` but represent different legal categories (e.g., 16 treaties, 9 case law judgments), retrieval-time filtering must be performed strictly using the `scope_flag` field rather than `source_type`.

---

## 3. Node-Level Analysis (`nodes.jsonl`)

Nodes represent structural units within a source document, corresponding to parsed articles or section preambles.

### 3.1 Node Statistics
- **Total Nodes:** 1,455
- **Node Type:** 100% are of type `article` (preambles and segmented articles are both represented as article-type nodes).

### 3.2 Nodes Per Source Distribution

| Metric | Value |
|--------|-------|
| Minimum nodes per source | 1 |
| Maximum nodes per source | 552 |
| Mean nodes per source | 3.02 |
| Median nodes per source | 1.0 |

*Note: Many laws in the corpus are short amending acts containing only 1 to 5 article nodes (often representing the amendment articles plus a promulgation article).*

---

## 4. Chunk-Level Analysis (`chunks.jsonl`)

Chunks are the individual text fragments to be embedded using the `BAAI/bge-m3` model and indexed in FAISS. There are **8,340 chunks** in the canonical store.

### 4.1 Legal Scope Distribution of Chunks
Because longer documents yield more chunks, the distribution of chunk-level `scope_flag` differs slightly from the source-level distribution:

| Legal Category (`scope_flag`) | Chunk Count | Percentage |
|--------------------------------|-------------|------------|
| **Statute** (`statute`)        | 7,667       | 91.93%     |
| **Treaty** (`treaty`)          | 387         | 4.64%      |
| **Case Law** (`case_law`)      | 270         | 3.24%      |
| **Uncertain** (`uncertain`)    | 16          | 0.19%      |
| **Total Chunks**               | **8,340**   | **100.00%**|

### 4.2 Chunks Per Node and Chunks Per Source

| Metric | Chunks Per Node | Chunks Per Source |
|--------|-----------------|-------------------|
| Minimum | 1               | 1                 |
| Maximum | 223             | 552               |
| Mean | 5.73            | 17.34             |
| Median | 1.0             | 8.0               |

---

## 5. Text and Length Statistics (Chunks)

The embedding pipeline relies on a strict size constraint. The maximum token length for the BGE-M3 model is 8,192 tokens, but the project has chosen a standard chunk size of **512 tokens** (modeled as **2,048 characters** using a conservative conversion factor of 4 characters per token).

### 5.1 Character Length and Token Count Statistics

| Statistical Metric | Character Length (Raw Text) | Token Count |
|---------------------|-----------------------------|-------------|
| **Minimum**         | 28 characters               | 7 tokens    |
| **Maximum**         | 2,048 characters            | 512 tokens  |
| **Mean**            | 1,461.09 characters         | 364.90 tokens |
| **Median**          | 1,719.00 characters         | 429.00 tokens |
| **Standard Deviation** | 601.43 characters        | 150.36 tokens |

### 5.2 Token Count Distribution Buckets

```
Token Count Bucket    Chunk Count    Percentage
───────────────────────────────────────────────
0 - 64  tokens        595            7.13%
65 - 128 tokens        574            6.88%
129 - 256 tokens        749            8.98%
257 - 384 tokens       1,265           15.17%
385 - 512 tokens       5,157           61.83%
513+    tokens         0               0.00%
```

> [!TIP]
> **Observation on Chunk Sizing:**
> - Over **61.8% of chunks** are packed closely to the maximum token limit of 512 tokens (between 385 and 512). This indicates highly dense context window usage, maximizing the context passed to downstream models.
> - **0.0% of chunks exceed the 512-token limit**, confirming that the sub-chunking fallback logic implemented in Phase 3.6 succeeded.

---

## 6. Schema and Integrity Analysis

### 6.1 Chunk Fields
Every JSON object in `chunks.jsonl` contains the following **15 fields**:
1. `article_number` (int | null)
2. `chunk_id` (str) — deterministic citation ID
3. `law_number` (str | null)
4. `law_slug` (str)
5. `law_year` (str | null)
6. `node_id` (str)
7. `scope_flag` (str)
8. `section` (str)
9. `seq` (int)
10. `source_id` (str)
11. `source_type` (str)
12. `text` (str)
13. `title` (str)
14. `token_count` (int)
15. `type_metadata` (dict)

### 6.2 Extended Type Metadata (`type_metadata`)
Under ADR-014 and Phase 3.6, every chunk contains the following metadata properties within the `type_metadata` dictionary:
- `chunk_hash` (str) — SHA-256 prefix for integrity tracking
- `created_at` (str) — ISO-8601 UTC timestamp of ingestion
- `document_type` (str) — legal parser source type classification
- `embedding_ready` (bool) — boolean flag verifying chunk status
- `language` (str) — language code (always `"ar"`)
- `parser_name` (str) — name of parser (always `"StatuteParser"`)
- `parser_version` (str) — parser version string

### 6.3 Integrity Audit Results
- **Unique Chunk IDs:** 8,340 / 8,340 (100.0% unique, zero collisions).
- **Null or Empty Text Check:** 0 chunks contain null or blank text.
- **Referential Integrity:** 100% of chunks successfully link back to valid node and source records.

---

## 7. Conclusions for Phase 4 Embedding Generation

1. **Size Bound Compliance:** No chunk exceeds the 512-token boundary. The embedding pipeline is safe from hard model-side truncation bugs.
2. **Deterministic Processing:** The 100% uniqueness of chunk IDs ensures that the index-to-metadata position mapping in `metadata.pkl` will be fully aligned and reproducible.
3. **Arabic Normalization:** Since character lengths range from 28 to 2,048, the `normalize_arabic` step (ADR-015) will operate on a highly stable set of texts. The total corpus size of ~12.18M characters (8,340 chunks × ~1,461 mean length) is small enough to embed in ~15 to 45 minutes on a standard CPU.
4. **Scope-Filtered Retrieval:** The retriever must be built to support boolean filtering on `scope_flag` during candidate search. This will guarantee that a user querying for `statute` documents will never be returned `treaty` or `case_law` chunks, even though all were processed by `StatuteParser`.
