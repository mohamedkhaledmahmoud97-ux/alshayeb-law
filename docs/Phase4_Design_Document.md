# Phase 4 Design Document — Embedding Pipeline & Retrieval Engine

**Project:** ALSHAYEB LAW — Egyptian Legal RAG System
**Phase:** 4 — Embedding Pipeline, FAISS Index, and Retrieval Engine
**Version:** 1.0
**Date:** July 2026
**Status:** Approved for Implementation
**Governing Decision:** ADR-015 (Dual-Representation Arabic Normalization)

---

## Table of Contents

1. [Objectives](#1-objectives)
2. [System Architecture Overview](#2-system-architecture-overview)
3. [Component Responsibilities](#3-component-responsibilities)
4. [Embedding & Retrieval Lifecycle](#4-embedding--retrieval-lifecycle)
5. [Data & Metadata Flow](#5-data--metadata-flow)
6. [FAISS Architecture](#6-faiss-architecture)
7. [Model Selection Rationale](#7-model-selection-rationale)
8. [ADR-015 Integration](#8-adr-015-integration)
9. [Scalability](#9-scalability)
10. [Performance Targets](#10-performance-targets)
11. [Failure Handling](#11-failure-handling)
12. [Future Extensibility](#12-future-extensibility)
13. [File & Directory Layout](#13-file--directory-layout)
14. [Implementation Checklist](#14-implementation-checklist)

---

## 1. Objectives

Phase 4 transforms the validated canonical corpus into a searchable vector index and implements the retrieval engine that will serve all downstream RAG components.

### Primary Objectives

| # | Objective | Success Criterion |
|---|---|---|
| P4-O1 | Embed all 8,340 canonical chunks using BAAI/bge-m3 | 8,340 vectors written to FAISS index |
| P4-O2 | Apply ADR-015 normalization before every encode call | `normalize_arabic()` called on every chunk text and every query |
| P4-O3 | Preserve full chunk metadata alongside every vector | All 14 chunk fields recoverable from metadata store |
| P4-O4 | Produce a deterministic, reproducible FAISS index | Same input → same index on every run |
| P4-O5 | Implement resumable embedding with checkpointing | Pipeline can restart from last completed batch |
| P4-O6 | Validate the index before declaring Phase 4 complete | Vector count, dimension, orphan check, smoke test all PASS |
| P4-O7 | Implement a retrieval engine with scope filtering | Top-K retrieval with `scope_flag` filter operational |

### Out of Scope for Phase 4

- Cross-encoder reranking (Phase 5)
- LLM generation (Phase 6)
- BM25 / hybrid retrieval (Phase 5)
- PDFBookParser implementation (awaiting dataset inspection)
- API layer (Phase 7)

---

## 2. System Architecture Overview

Phase 4 introduces two new subsystems: the **Embedding Pipeline** and the **Retrieval Engine**. Both sit between the canonical corpus (Phase 3 output) and the future generation layer (Phase 6).

```
┌─────────────────────────────────────────────────────────────────┐
│                     CANONICAL CORPUS (Phase 3)                  │
│              outputs/canonical/chunks.jsonl  (8,340 chunks)     │
│                    ← IMMUTABLE — ADR-015 ←                      │
└─────────────────────────────┬───────────────────────────────────┘
                              │  read (never write)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   EMBEDDING PIPELINE (Phase 4)                  │
│                                                                 │
│  1. Load chunks from canonical store                            │
│  2. normalize_arabic(chunk.text)  ← ADR-015                     │
│  3. Batch encode with BAAI/bge-m3                               │
│  4. Write vectors to FAISS index                                │
│  5. Write metadata to metadata.pkl                              │
│  6. Write manifest to embedding_manifest.json                   │
└─────────────────────────────┬───────────────────────────────────┘
                              │  produces
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FAISS INDEX STORE                           │
│                                                                 │
│  outputs/faiss/index.faiss          ← dense vectors            │
│  outputs/faiss/metadata.pkl         ← chunk metadata list       │
│  outputs/faiss/embedding_manifest.json  ← audit manifest       │
└─────────────────────────────┬───────────────────────────────────┘
                              │  read at query time
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   RETRIEVAL ENGINE (Phase 4)                    │
│                                                                 │
│  1. normalize_arabic(query)  ← ADR-015                          │
│  2. Encode query with BAAI/bge-m3                               │
│  3. FAISS similarity search (Top-K)                             │
│  4. Apply scope_flag filter (ADR-013)                           │
│  5. Reconstruct full chunk metadata                             │
│  6. Return ranked RetrievalResult list                          │
└─────────────────────────────┬───────────────────────────────────┘
                              │  feeds
                              ▼
                  ┌───────────────────────┐
                  │  Reranker (Phase 5)   │
                  │  LLM Layer (Phase 6)  │
                  └───────────────────────┘
```

---

## 3. Component Responsibilities

### 3.1 `src/embeddings/embedding_pipeline.py`

**Responsibility:** Transform canonical chunks into dense vectors and persist the FAISS index.

| Responsibility | Detail |
|---|---|
| Load chunks | Read from `outputs/canonical/chunks.jsonl` via `canonical_store.read_chunks()` |
| Normalize text | Call `normalize_arabic(chunk.text)` before every encode call (ADR-015) |
| Batch encode | Send normalized text batches to BGE-M3 encoder |
| Checkpoint | Save progress after each batch; resume from last completed batch |
| Write FAISS index | `faiss.IndexFlatIP` (inner product on L2-normalized vectors = cosine similarity) |
| Write metadata | Ordered list of chunk dicts, index position = FAISS vector position |
| Write manifest | JSON file recording model name, dimension, chunk count, checksums, timestamp |
| Validate output | Verify vector count matches chunk count before declaring success |

### 3.2 `src/embeddings/faiss_store.py`

**Responsibility:** Encapsulate all FAISS read/write operations.

| Responsibility | Detail |
|---|---|
| Save index | `faiss.write_index(index, path)` |
| Load index | `faiss.read_index(path)` with integrity check |
| Add vectors | Accept numpy float32 array; L2-normalize before adding |
| Search | `index.search(query_vector, k)` returning distances and indices |
| Dimension property | Expose `d` for validation |
| Vector count property | Expose `ntotal` for validation |

### 3.3 `src/embeddings/bge_encoder.py`

**Responsibility:** Wrap BAAI/bge-m3 for consistent encode calls.

| Responsibility | Detail |
|---|---|
| Load model | Load from HuggingFace Hub or local cache |
| Encode documents | Accept list of strings; return float32 numpy array |
| Encode query | Single string; return float32 numpy array (shape: `[1, d]`) |
| L2 normalization | Normalize all output vectors before returning |
| Device selection | Auto-select CUDA if available, else CPU |
| Batch size | Configurable; default 32 |

### 3.4 `src/retrieval/retriever.py`

**Responsibility:** Accept a user query and return ranked, metadata-enriched results.

| Responsibility | Detail |
|---|---|
| Query normalization | Call `normalize_arabic(query)` before encoding (ADR-015) |
| Query encoding | Use `BGEEncoder.encode_query()` |
| Similarity search | Call `FAISSStore.search(query_vector, k * 3)` (over-fetch for post-filter) |
| Scope filtering | Filter results by `scope_flag` (ADR-013) |
| Metadata reconstruction | Map FAISS index positions to full chunk metadata |
| Return type | List of `RetrievalResult` dataclass instances |
| Top-K | Configurable; default 10 |

### 3.5 `src/retrieval/result_types.py`

**Responsibility:** Define the `RetrievalResult` dataclass returned by the retriever.

Fields: `chunk_id`, `score`, `rank`, `text`, `title`, `law_number`, `law_year`, `law_slug`, `scope_flag`, `section`, `article_number`, `seq`, `source_id`, `node_id`.

### 3.6 `scripts/validate_faiss.py`

**Responsibility:** Post-build validation of the FAISS index.

Checks: vector count, embedding dimension, missing embeddings, orphan metadata, index integrity, load test, retrieval smoke test.

### 3.7 `scripts/run_embedding_pipeline.py`

**Responsibility:** Entry point for running the full embedding pipeline from the command line.

---

## 4. Embedding & Retrieval Lifecycle

### 4.1 Document Embedding Lifecycle

```
chunks.jsonl
    │
    ▼  canonical_store.read_chunks()
List[Chunk]
    │
    ▼  [for each batch]
    │
    ├─► normalize_arabic(chunk.text)  ← ADR-015 (in-memory only)
    │
    ▼  BGEEncoder.encode_documents(normalized_texts)
numpy float32 [batch_size, 1024]
    │
    ▼  L2 normalize
    │
    ▼  FAISSStore.add(vectors)
    │
    ▼  metadata_list.append(chunk_dict)
    │
    ▼  [checkpoint saved after each batch]
    │
    ▼  [after all batches]
FAISSStore.save()  →  outputs/faiss/index.faiss
pickle.dump(metadata_list)  →  outputs/faiss/metadata.pkl
json.dump(manifest)  →  outputs/faiss/embedding_manifest.json
```

### 4.2 Query Retrieval Lifecycle

```
User query (raw Arabic string)
    │
    ▼  normalize_arabic(query)  ← ADR-015 (in-memory only)
Normalized query string
    │
    ▼  BGEEncoder.encode_query(normalized_query)
numpy float32 [1, 1024]
    │
    ▼  L2 normalize
    │
    ▼  FAISSStore.search(query_vector, k=top_k * 3)
(distances, indices) arrays
    │
    ▼  [for each index]
    │
    ├─► metadata_list[index]  →  chunk_dict
    │
    ├─► scope_flag filter (ADR-013)
    │
    ▼  [sort by score, take top_k]
List[RetrievalResult]
    │
    ▼  → Reranker (Phase 5) / LLM (Phase 6)
```

---

## 5. Data & Metadata Flow

### 5.1 Chunk Fields Preserved in Metadata Store

Every entry in `metadata.pkl` is a dict containing all 14 chunk fields:

| Field | Type | Source | Purpose at Retrieval |
|---|---|---|---|
| `chunk_id` | str | Canonical corpus | Citation ID |
| `node_id` | str | Canonical corpus | Parent node reference |
| `source_id` | str | Canonical corpus | Parent source reference |
| `source_type` | str | Canonical corpus | Parser identification |
| `title` | str | Canonical corpus | Display: law name |
| `law_number` | str\|None | Canonical corpus | Citation construction |
| `law_year` | str\|None | Canonical corpus | Citation construction |
| `law_slug` | str | Canonical corpus | URL-safe identifier |
| `scope_flag` | str | Canonical corpus | **Retrieval filter (ADR-013)** |
| `section` | str | Canonical corpus | Citation: promulgation/main |
| `article_number` | int\|None | Canonical corpus | Citation: article number |
| `seq` | int | Canonical corpus | Citation: sub-chunk sequence |
| `text` | str | Canonical corpus | Display: original legal text |
| `token_count` | int | Canonical corpus | Context window management |
| `type_metadata` | dict | Canonical corpus | Extended metadata |

### 5.2 FAISS Index ↔ Metadata Alignment

The FAISS index and the metadata list are aligned by integer position:

```
FAISS index position 0  ←→  metadata_list[0]  (chunk_id: "statute:...")
FAISS index position 1  ←→  metadata_list[1]  (chunk_id: "statute:...")
...
FAISS index position 8339  ←→  metadata_list[8339]
```

This alignment is established during embedding and validated during the FAISS validation step.

### 5.3 Manifest Structure

`embedding_manifest.json` records:

```json
{
  "model_name": "BAAI/bge-m3",
  "embedding_dimension": 1024,
  "total_chunks": 8340,
  "total_vectors": 8340,
  "index_type": "IndexFlatIP",
  "normalization": "L2",
  "adr_015_applied": true,
  "normalizer": "src.preprocessing.arabic_normalizer.normalize_arabic",
  "corpus_source": "outputs/canonical/chunks.jsonl",
  "created_at": "<UTC ISO-8601 timestamp>",
  "index_checksum_sha256": "<sha256 of index.faiss>",
  "metadata_checksum_sha256": "<sha256 of metadata.pkl>",
  "batch_size": 32,
  "device": "cpu|cuda"
}
```

---

## 6. FAISS Architecture

### 6.1 Index Type Selection

| Index Type | Description | Selected? |
|---|---|---|
| `IndexFlatL2` | Exact L2 distance search | No — cosine similarity preferred |
| `IndexFlatIP` | Exact inner product (= cosine on L2-normalized vectors) | **Yes** |
| `IndexIVFFlat` | Approximate search with inverted file | No — corpus too small to benefit |
| `IndexHNSW` | Graph-based approximate search | No — adds complexity without benefit at 8,340 vectors |

**Decision:** `IndexFlatIP` with L2-normalized vectors.

Rationale:
- 8,340 vectors is a small corpus. Exact search is fast (< 5ms on CPU).
- Approximate methods (IVF, HNSW) require training and introduce recall loss that is not justified at this scale.
- Inner product on L2-normalized vectors is mathematically equivalent to cosine similarity, which is the standard for dense retrieval.
- `IndexFlatIP` is deterministic and requires no training step.

### 6.2 Vector Dimension

BGE-M3 produces 1024-dimensional dense vectors. The FAISS index is initialized with `d=1024`.

### 6.3 L2 Normalization

All vectors (document and query) are L2-normalized before being added to or searched against the index. This ensures that inner product scores are in the range `[-1, 1]` and are directly interpretable as cosine similarity scores.

Normalization formula: `v_normalized = v / ||v||_2`

### 6.4 Index File Layout

```
outputs/faiss/
├── index.faiss              ← FAISS binary index (8,340 vectors × 1024 dims)
├── metadata.pkl             ← Python list of 8,340 chunk dicts (pickle)
└── embedding_manifest.json  ← Audit manifest with checksums and provenance
```

### 6.5 Checkpoint Layout

During embedding, a checkpoint directory tracks progress:

```
outputs/faiss/checkpoints/
├── checkpoint.json          ← {"last_completed_batch": N, "total_batches": M}
├── vectors_0.npy            ← numpy array for batch 0
├── vectors_1.npy            ← numpy array for batch 1
└── ...
```

On resume, the pipeline reads `checkpoint.json`, skips completed batches, and continues from `last_completed_batch + 1`. After successful completion, the checkpoint directory is removed.

---

## 7. Model Selection Rationale

### 7.1 BAAI/bge-m3

**Selected model:** `BAAI/bge-m3`

| Property | Value |
|---|---|
| Architecture | XLM-RoBERTa-based encoder |
| Embedding dimension | 1024 |
| Max input tokens | 8192 |
| Languages | 100+ (strong Arabic support) |
| Retrieval paradigm | Dense (also supports sparse and multi-vector) |
| License | MIT |
| HuggingFace Hub | `BAAI/bge-m3` |

**Why BGE-M3 for Arabic legal text:**

1. **Multilingual coverage:** BGE-M3 was trained on 100+ languages including Arabic. It handles Modern Standard Arabic (MSA) and Egyptian Arabic variants.
2. **Long context:** 8192-token context window. Our max chunk is 2,048 characters (~512 tokens), well within the model's capacity.
3. **Legal domain:** Dense retrieval models trained on large multilingual corpora generalize well to legal text without domain-specific fine-tuning.
4. **Subword tokenization:** BGE-M3's tokenizer handles Arabic morphological variation at the subword level. ADR-015 normalization further reduces surface-form variation before tokenization.
5. **Established benchmark performance:** BGE-M3 achieves state-of-the-art results on MIRACL (Arabic) and other multilingual retrieval benchmarks.
6. **No API cost:** Local inference. No external API dependency. Reproducible.

### 7.2 Alternatives Considered

| Model | Reason Not Selected |
|---|---|
| `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` | 768-dim, weaker Arabic performance than BGE-M3 |
| `intfloat/multilingual-e5-large` | Strong alternative; BGE-M3 preferred for Arabic legal domain |
| `OpenAI text-embedding-3-large` | API cost, external dependency, not reproducible offline |
| `CAMeL-Lab/bert-base-arabic-camelbert-msa` | Arabic-only, no multilingual generalization, smaller context |

---

## 8. ADR-015 Integration

ADR-015 mandates a dual-representation architecture. This section specifies exactly how it is implemented in Phase 4.

### 8.1 Document Embedding (Offline)

```python
# In EmbeddingPipeline._embed_batch()
from src.preprocessing.arabic_normalizer import normalize_arabic

normalized_texts = [normalize_arabic(chunk["text"]) for chunk in batch]
vectors = encoder.encode_documents(normalized_texts)
# normalized_texts is discarded after this line — never persisted
```

**Invariants:**
- `chunk["text"]` is read from `chunks.jsonl` and is never modified.
- `normalized_texts` exists only within the scope of `_embed_batch()`.
- The FAISS index stores only the float32 vector — not the normalized text.
- `metadata.pkl` stores `chunk["text"]` (original) — not the normalized form.

### 8.2 Query Embedding (Online)

```python
# In Retriever.retrieve()
from src.preprocessing.arabic_normalizer import normalize_arabic

normalized_query = normalize_arabic(query)
query_vector = encoder.encode_query(normalized_query)
# normalized_query is discarded after encoding
```

**Invariants:**
- The original query string is preserved for display and logging.
- Only the normalized form is passed to the encoder.
- The normalized form is never stored in any log or response.

### 8.3 Symmetry Guarantee

Both document vectors and query vectors are produced from text that has passed through the same `normalize_arabic()` function with the same default parameters (`remove_diacritics=True`). This guarantees that the cosine similarity between a query vector and a document vector is computed in the same normalized embedding space.

### 8.4 Canonical Corpus Immutability

The embedding pipeline opens `chunks.jsonl` in read-only mode. No write operation is performed on any file under `outputs/canonical/`. This is enforced by the pipeline design: `canonical_store.read_chunks()` returns a generator; the pipeline never calls any `write_*` function.

---

## 9. Scalability

### 9.1 Current Scale

| Metric | Value |
|---|---|
| Chunks to embed | 8,340 |
| Embedding dimension | 1024 |
| Index size (float32) | 8,340 × 1024 × 4 bytes ≈ 34 MB |
| Metadata size (estimated) | ~15 MB (pickle) |
| Total FAISS store | ~50 MB |

At this scale, `IndexFlatIP` with CPU inference is entirely adequate. Full embedding of 8,340 chunks at batch size 32 requires ~261 batches. On CPU with BGE-M3, estimated time is 15–45 minutes depending on hardware.

### 9.2 Scaling Path

| Corpus Size | Recommended Action |
|---|---|
| < 100K chunks | `IndexFlatIP` — no change needed |
| 100K–1M chunks | Migrate to `IndexIVFFlat` with `nlist=1024` |
| > 1M chunks | Migrate to `IndexIVFPQ` or Qdrant/Milvus |

The `FAISSStore` class is designed with a `save()` / `load()` interface that is index-type agnostic. Migrating to a different index type requires only changing the index constructor inside `FAISSStore` — the retriever and pipeline code remain unchanged.

### 9.3 Multi-Source Scaling

When PDFBookParser and CourtJudgmentParser are implemented, their chunks will be appended to the canonical store using `append=True` (ADR-014 / canonical_store design). The embedding pipeline will need to support incremental indexing — embedding only new chunks and merging them into the existing FAISS index. This is deferred to Phase 4.5 (incremental indexing).

---

## 10. Performance Targets

| Metric | Target | Measurement Method |
|---|---|---|
| Embedding throughput | ≥ 100 chunks/min on CPU | Timed pipeline run |
| Query latency (retrieval only) | < 50ms on CPU | `time.perf_counter()` around `retrieve()` |
| FAISS search latency | < 5ms for Top-10 on 8,340 vectors | Isolated `index.search()` timing |
| Index load time | < 2s | Timed `faiss.read_index()` |
| Memory footprint (index in RAM) | < 100 MB | `psutil.Process().memory_info().rss` |
| Recall@10 (smoke test) | ≥ 0.8 on 5 known queries | Manual validation |

---

## 11. Failure Handling

### 11.1 Embedding Pipeline Failures

| Failure Mode | Detection | Recovery |
|---|---|---|
| OOM during batch encoding | `torch.cuda.OutOfMemoryError` | Reduce batch size; retry batch |
| Model load failure | `OSError` from HuggingFace | Log error; raise with clear message |
| Corrupt chunk in JSONL | `json.JSONDecodeError` | Log chunk ID; skip; continue |
| Disk full during write | `OSError` on `faiss.write_index` | Log; raise; do not write partial index |
| Interrupted run | Process kill | Resume from checkpoint on next run |

### 11.2 Retrieval Failures

| Failure Mode | Detection | Recovery |
|---|---|---|
| Index not found | `FileNotFoundError` | Raise `IndexNotBuiltError` with instructions |
| Metadata/index count mismatch | Count check on load | Raise `IndexCorruptError` |
| Empty query | `len(query.strip()) == 0` | Raise `ValueError` |
| Zero results after scope filter | `len(results) == 0` | Return empty list; do not raise |

### 11.3 Validation Failures

If `scripts/validate_faiss.py` reports any FAIL, the Phase 4 embedding step must be re-run before proceeding to Phase 5. The validation script exits with code 1 on any failure.

---

## 12. Future Extensibility

### 12.1 Hybrid Retrieval (Phase 5)

The retrieval engine is designed to be hybrid-search ready. The `Retriever` class will accept a `retrieval_mode` parameter:

- `"dense"` — current Phase 4 implementation
- `"sparse"` — BM25 over original chunk text (Phase 5)
- `"hybrid"` — weighted combination of dense and sparse scores (Phase 5)

The `RetrievalResult` dataclass includes a `score` field that is mode-agnostic. The reranker (Phase 5) operates on `List[RetrievalResult]` regardless of retrieval mode.

### 12.2 Incremental Indexing

When new document types are added (PDFBookParser, CourtJudgmentParser), the embedding pipeline will support `--incremental` mode:

1. Load existing `index.faiss` and `metadata.pkl`.
2. Identify chunks in `chunks.jsonl` not yet in `metadata.pkl` (by `chunk_id`).
3. Embed only new chunks.
4. Append vectors to the FAISS index.
5. Append metadata entries.
6. Update the manifest.

### 12.3 Model Replacement

The `BGEEncoder` class wraps the model behind a `encode_documents()` / `encode_query()` interface. Replacing BGE-M3 with a different model requires only:

1. Implementing a new encoder class with the same interface.
2. Updating `embedding_manifest.json` model name.
3. Re-running the embedding pipeline (full re-embed required on model change).

### 12.4 Vector Database Migration

`FAISSStore` exposes `save()` / `load()` / `search()` / `add()`. Migrating to Qdrant or Milvus requires implementing a `QdrantStore` or `MilvusStore` class with the same interface and updating the dependency injection in `EmbeddingPipeline` and `Retriever`.

---

## 13. File & Directory Layout

### New Files Created in Phase 4

```
src/embeddings/
├── __init__.py
├── bge_encoder.py           ← BGE-M3 wrapper
├── embedding_pipeline.py    ← Main pipeline: load → normalize → encode → store
└── faiss_store.py           ← FAISS index encapsulation

src/retrieval/
├── __init__.py
├── result_types.py          ← RetrievalResult dataclass
└── retriever.py             ← Query → normalize → encode → search → filter → rank

scripts/
├── run_embedding_pipeline.py  ← CLI entry point for embedding
└── validate_faiss.py          ← Post-build FAISS validation

outputs/faiss/
├── index.faiss              ← FAISS binary index (generated)
├── metadata.pkl             ← Chunk metadata list (generated)
└── embedding_manifest.json  ← Audit manifest (generated)

reports/
└── Data_Profiling_Statistical_Analysis_Report.md  ← Step 2 output
```

### Existing Files Modified in Phase 4

```
src/config/constants.py      ← Add FAISS_STORE_DIR constant
PROJECT_MEMORY.md            ← Updated after each step
CHANGELOG.md                 ← Updated after each step
DECISIONS.md                 ← Updated if new ADRs are needed
```

---

## 14. Implementation Checklist

### Step 1 — Architecture (this document) ✅
- [x] Phase 4 Design Document created

### Step 2 — Data Profiling
- [ ] `reports/Data_Profiling_Statistical_Analysis_Report.md` created from actual corpus

### Step 3 — Embedding Pipeline
- [ ] `src/embeddings/bge_encoder.py` implemented
- [ ] `src/embeddings/faiss_store.py` implemented
- [ ] `src/embeddings/embedding_pipeline.py` implemented
- [ ] `scripts/run_embedding_pipeline.py` implemented
- [ ] `outputs/faiss/index.faiss` generated
- [ ] `outputs/faiss/metadata.pkl` generated
- [ ] `outputs/faiss/embedding_manifest.json` generated

### Step 4 — FAISS Validation
- [ ] `scripts/validate_faiss.py` implemented
- [ ] All validation checks PASS

### Step 5 — Retrieval Engine
- [ ] `src/retrieval/result_types.py` implemented
- [ ] `src/retrieval/retriever.py` implemented
- [ ] Smoke test queries return correct results

---

*Document owner: ALSHAYEB LAW Engineering*
*Governing decisions: ADR-010, ADR-011, ADR-013, ADR-014, ADR-015*
*Next step: Step 2 — Data Profiling Statistical Analysis Report*
