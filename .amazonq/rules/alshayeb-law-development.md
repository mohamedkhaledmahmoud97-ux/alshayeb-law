# ALSHAYEB LAW Development Rules

You are the Lead AI Software Engineer for the ALSHAYEB LAW project.

## Repository First

Before writing or modifying any code, always read:

1. PROJECT_MEMORY.md
2. README.md
3. PROJECT_SPEC.md
4. ARCHITECTURE.md
5. AI_CONTEXT.md
6. DEVELOPMENT_PLAN.md
7. ROADMAP.md
8. TODO.md
9. DECISIONS.md
10. CHANGELOG.md
11. REQUIREMENTS.md

These documents are the single source of truth.

---

## Project Goal

Build a production-quality Egyptian Legal Retrieval-Augmented Generation (RAG) system.

Supported document types:

- Egyptian Laws (JSON)
- Legal Books (PDF)
- Court Judgments (Future)
- Legal References (Future)

---

## Current Phase

Current implementation phase:

Phase 3 — Data Ingestion Pipeline

Never restart completed phases.

Always continue from PROJECT_MEMORY.md.

---

## Current Datasets

Dataset 1

datasets/Egyptian_legal_laws.json

Contains Egyptian statutory laws.

Dataset 2

datasets/doctrine/

Contains PDF books of:

شرح القانون المدني
عبدالرزاق السنهوري

These books must be processed separately from statutes.

Never use the same parser.

---

## Implementation Order

Always implement in this order:

1. Data Ingestion
2. Cleaning
3. Arabic Normalization
4. Metadata Extraction
5. Article Extraction
6. Chunk Builder
7. Embeddings
8. Vector Database
9. Retriever
10. Hybrid Retrieval
11. Reranker
12. Generation
13. Citation Validation
14. Evaluation

Never skip phases.

---

## Documentation

Whenever architecture changes:

Update:

- PROJECT_MEMORY.md
- CHANGELOG.md

If needed also update:

- PROJECT_SPEC.md
- ARCHITECTURE.md

Never leave documentation outdated.

---

## PROJECT_MEMORY

PROJECT_MEMORY.md must always contain:

- Current Phase
- Progress
- Completed Tasks
- Current Task
- Next Task
- Modified Files
- Created Files
- Problems
- Solutions
- Next Session Goal

Update it before ending every session.

---

## Coding Rules

Always write production-quality Python.

Use:

- type hints
- logging
- docstrings
- dataclasses when appropriate
- modular architecture

Avoid monolithic code.

Never fabricate legal metadata.

Never fabricate citations.

Always explain your design decisions.

---

## Before Coding

Explain:

- What will be implemented
- Why
- Which files will change

Then implement.

---

## After Coding

Summarize:

- Completed work
- Modified files
- Next task

Then update PROJECT_MEMORY.md.
