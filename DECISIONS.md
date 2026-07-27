# Architecture Decisions — ALSHAYEB LAW

Version 1.0

---

# Overview

This document records the major architectural and project decisions made during the development of ALSHAYEB LAW.

The purpose of this document is to preserve the reasoning behind important decisions, improve traceability, and make future maintenance easier.

Every significant technical decision should be documented here before implementation.

---

# Decision Status

| Status | Meaning |
|----------|---------|
| ✅ Accepted | Official project decision |
| 🟡 Proposed | Under discussion |
| 🔄 Superseded | Replaced by another decision |
| ❌ Rejected | Evaluated but not adopted |

---

# ADR-001 — Use Markdown for Core Documentation

**Status**

✅ Accepted

**Decision**

All core project documentation shall be written in Markdown.

**Reason**

Markdown is lightweight, version-friendly, easy to review, and integrates naturally with GitHub.

**Alternatives Considered**

- Microsoft Word
- Google Docs
- PDF-only documentation

**Impact**

- Easier collaboration
- Better version control
- Simple export to PDF or DOCX

---

# ADR-002 — Documentation-First Development

**Status**

✅ Accepted

**Decision**

Documentation shall be completed before implementing core system components.

**Reason**

A clear specification reduces ambiguity and improves implementation quality.

**Impact**

- Better planning
- Lower implementation risk
- Easier AI-assisted development

---

# ADR-003 — Separate Report and Appendix Files

**Status**

✅ Accepted

**Decision**

The evaluation report and appendix materials shall be maintained in separate documents.

**Reason**

Improves readability and simplifies future revisions.

**Impact**

Cleaner documentation and easier academic submission.

---

# ADR-004 — Maintain a Dedicated AI Context

**Status**

✅ Accepted

**Decision**

AI operating instructions shall be stored in AI_CONTEXT.md.

**Reason**

Ensures consistent behavior across AI assistants such as Claude, ChatGPT, Cursor, and GitHub Copilot.

**Impact**

Improves reproducibility and consistency.

---

# ADR-005 — Separate Benchmarks from Documentation

**Status**

✅ Accepted

**Decision**

Benchmark datasets and evaluation assets shall be stored independently from project documentation.

**Reason**

Prevents documentation from becoming cluttered and simplifies dataset versioning.

**Impact**

Cleaner repository organization.

---

# ADR-006 — Isolate Generated Outputs

**Status**

✅ Accepted

**Decision**

Generated reports, logs, figures, and evaluation artifacts shall be stored in the outputs directory.

**Reason**

Keeps generated files separate from source materials.

**Impact**

Improves maintainability and repository cleanliness.

---

# ADR-007 — Use GitHub as the Source of Truth

**Status**

✅ Accepted

**Decision**

GitHub shall be the official source for project documentation, history, and collaboration.

**Reason**

Git provides complete version history, traceability, and collaborative workflows.

**Impact**

Improves transparency and project governance.

---

# ADR-008 — Use Python as the Primary Language

**Status**

✅ Accepted

**Decision**

Python shall be the primary implementation language.

**Reason**

Python provides a mature ecosystem for AI, NLP, machine learning, and Retrieval-Augmented Generation.

**Alternatives Considered**

- Java
- C#
- JavaScript

**Impact**

Simplifies integration with modern AI frameworks.

---

# ADR-009 — Use FastAPI for Backend Development

**Status**

✅ Accepted

**Decision**

FastAPI shall be used for REST API development.

**Reason**

FastAPI offers high performance, automatic API documentation, and excellent Python integration.

**Impact**

Provides scalable and maintainable APIs.

---

# ADR-010 — Use FAISS as the Initial Vector Database

**Status**

✅ Accepted

**Decision**

FAISS will be used during the first implementation phase.

**Reason**

FAISS is lightweight, well-supported, and ideal for research prototypes.

**Future Alternatives**

- Qdrant
- Milvus
- Weaviate

---

# ADR-011 — Use BGE-M3 as the Default Embedding Model

**Status**

✅ Accepted

**Decision**

BGE-M3 will serve as the default embedding model.

**Reason**

It provides strong multilingual retrieval performance, including Arabic.

**Impact**

Improves retrieval quality for Egyptian legal documents.

---

# ADR-012 — Never Generate Unsupported Legal Claims

**Status**

✅ Accepted

**Decision**

The system must never fabricate legal articles, citations, court decisions, or legal interpretations.

**Reason**

Legal AI systems require evidence-based responses.

**Impact**

Improves trustworthiness and academic integrity.

---

# ADR-013 — Use `scope_flag` (Not `source_type`) for Document Category Filtering

**Status**

✅ Accepted

**Decision**

At retrieval time, document category filtering (statute-only, treaty-only, case-law-only) must be applied on the `scope_flag` field, not on `source_type`.

**Reason**

The dataset `Egyptian_legal_laws.json` is a mixed corpus. It contains 9 court judgments and 16 treaties stored alongside statutes. All 481 records are parsed by `StatuteParser`, so every record carries `source_type="statute"` regardless of its actual legal category. The `scope_flag` field is set by the scope classifier and correctly identifies the document category (`statute`, `case_law`, `treaty`, `uncertain`).

Filtering on `source_type` would include all 25 non-statute records in statute-only queries. Filtering on `scope_flag` correctly excludes them.

**Impact**

- All retrieval filters must use `scope_flag`, not `source_type`.
- `source_type` identifies which parser produced the record; `scope_flag` identifies the legal category of the document.
- This distinction must be documented in the retrieval layer when it is implemented.

---

# ADR-014 — Denormalize Source Metadata onto Every Chunk

**Status**

✅ Accepted

**Decision**

Every `Chunk` record carries a full copy of its parent source’s metadata fields (`title`, `law_number`, `law_year`, `law_slug`, `scope_flag`, `source_type`, `source_id`), even though these fields are already present on the parent `Source` record.

**Reason**

In a vector database, each retrieved chunk must be self-describing. When a chunk is returned by a similarity search, the system must be able to construct a complete legal citation (`law_name`, `article_number`, `section`) without performing a secondary lookup against the canonical store. Requiring a join at retrieval time would add latency and complexity.

**Alternatives Considered**

- Store only `chunk_id` and `node_id` in the vector index, and look up metadata separately. Rejected: adds a mandatory secondary read on every retrieval call.

**Impact**

- Storage overhead is acceptable at the current corpus size (8,340 chunks).
- If source metadata changes (e.g. a law title is corrected), all child chunks must be re-ingested to stay consistent.
- This is a deliberate and documented trade-off between storage and retrieval simplicity.

---

# ADR-015 — Apply Arabic Normalization at Embedding Time Only (Dual-Representation Architecture)

**Status**

✅ Accepted

**Decision**

Arabic normalization shall be applied exclusively to the text passed to the embedding model. The canonical corpus (`outputs/canonical/chunks.jsonl`) shall never be modified. The original chunk text is preserved unchanged for storage, retrieval display, and legal citation construction. The embedding pipeline maintains a derived normalized representation in memory during embedding generation only — it is never persisted as a separate file.

**Reason**

Two simpler alternatives were evaluated and rejected:

- **Option A — Normalize at ingestion time**: Modifies the canonical corpus. Stored chunk text would differ from the original legal source text. Legal citations displayed to users would show normalized characters (e.g. bare alef `ا` instead of `أ`, dotless yeh `ي` instead of `ى`), which is incorrect for a legal system where exact wording carries legal weight. Chunk hashes would change on every re-normalization, breaking reproducibility.

- **Option B — Normalize at query time only**: Applies normalization to the user query before embedding but leaves stored chunk text un-normalized. Retrieval recall improves only if the embedding model fails to bridge the spelling gap internally. BGE-M3 has strong multilingual subword tokenization that partially handles Arabic spelling variants, but character-level normalization before encoding is still measurably beneficial for exact-match recall on legal terminology.

**ADR-015 (this decision) — Dual-representation architecture**: The embedding pipeline applies `normalize_arabic()` to each chunk’s text immediately before passing it to the encoder. The normalized text is used only for vector generation and is discarded after encoding. The original text stored in `chunks.jsonl` is never touched. The same normalization is applied to user queries at retrieval time, ensuring that query and document vectors are produced from the same normalized surface form.

**Consequences**

- The canonical corpus remains immutable. No re-ingestion is required.
- Chunk IDs, chunk hashes, and all citation fields remain stable.
- Retrieval recall benefits from normalization without corrupting the legal text.
- The embedding pipeline must import and apply `normalize_arabic()` from `src/preprocessing/arabic_normalizer.py` before every encode call.
- The query preprocessing layer must apply the same normalization before embedding user queries.
- `arabic_normalizer.py` is now a required dependency of the embedding pipeline, not an optional preprocessing utility.

**Alternatives Rejected**

| Option | Reason for rejection |
|---|---|
| A — Normalize stored text | Corrupts legal citations; breaks chunk hash stability |
| B — Query-time only | Leaves document-side encoding un-normalized; asymmetric representation |

---

# Future Decisions

Future ADRs may include:

- Hybrid Retrieval
- Knowledge Graph Integration
- Legal Ontology
- Authentication Strategy
- Cloud Infrastructure
- Deployment Architecture
- Monitoring and Logging
- Multi-Agent Architecture

---

# Maintenance Rules

To maintain this document:

- Record every major architectural decision.
- Explain the reasoning behind each decision.
- Document alternatives when appropriate.
- Never delete historical decisions.
- Mark outdated decisions as "Superseded" instead of removing them.
