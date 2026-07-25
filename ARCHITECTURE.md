# System Architecture — ALSHAYEB LAW

## Overview

ALSHAYEB LAW is a modular Egyptian Legal Retrieval-Augmented Generation (RAG) system designed for legal research, academic evaluation, and production-oriented development.

The project combines modern information retrieval techniques with Large Language Models (LLMs) to generate legally grounded answers supported by verifiable Egyptian legal sources.

The architecture emphasizes:

- Modularity
- Scalability
- Reproducibility
- Traceability
- Academic rigor
- Maintainability

Every major component is designed to be independently replaceable without affecting the rest of the system.

---

# Architecture Goals

The architecture is designed to:

- Minimize hallucinations.
- Maximize retrieval quality.
- Improve citation accuracy.
- Support reproducible benchmarking.
- Produce evidence-based legal answers.
- Scale from research prototype to production system.

---

# High-Level System Architecture

```
                        User
                          │
                          ▼
                  FastAPI REST API
                          │
                          ▼
                 Query Preprocessing
                          │
                          ▼
           Arabic Query Normalization
                          │
                          ▼
                  Embedding Model
                     (BGE-M3)
                          │
                          ▼
               Vector Database (FAISS)
                          │
                          ▼
                 Initial Retrieval
                          │
                          ▼
            Cross-Encoder Reranker
                          │
                          ▼
               Context Construction
                          │
                          ▼
                Large Language Model
        (GPT / Claude / Qwen / DeepSeek)
                          │
                          ▼
               Citation Validation
                          │
                          ▼
                   Final Response
```

---

# Data Flow

The system processes every legal query using the following pipeline:

1. Receive the user's legal question.
2. Preprocess the Arabic query.
3. Normalize legal terminology.
4. Generate semantic embeddings.
5. Search the vector database.
6. Retrieve candidate legal documents.
7. Rerank retrieved results.
8. Build the evidence context.
9. Generate an answer using the selected LLM.
10. Validate legal citations.
11. Return the final evidence-based response.

---

# Core Components

The system consists of the following modules:

## API Layer

Responsible for receiving requests and exposing REST endpoints.

Technology:

- FastAPI

---

## Query Processing

Responsible for:

- Cleaning user queries
- Tokenization
- Arabic preprocessing
- Input validation

---

## Arabic Query Normalization

Responsible for:

- Normalizing Arabic characters
- Removing spelling variations
- Handling dialect differences
- Legal terminology normalization

---

## Embedding Pipeline

Responsible for transforming legal documents and queries into dense vector representations.

Default Model:

- BAAI/BGE-M3

---

## Vector Store

Stores document embeddings for semantic retrieval.

Initial implementation:

- FAISS

Future options:

- Qdrant
- Milvus
- Weaviate

---

## Retrieval Engine

Responsible for retrieving the most relevant legal documents.

Future improvements include:

- Dense Retrieval
- BM25
- Hybrid Retrieval

---

## Reranking Module

Improves retrieval quality using a Cross-Encoder model.

Recommended model:

- BGE Reranker

---

## Prompt Builder

Constructs structured prompts using retrieved legal evidence before sending them to the LLM.

---

## LLM Generation

Generates final legal answers.

The architecture intentionally supports interchangeable providers.

Supported models include:

- GPT
- Claude
- Qwen
- DeepSeek

---

## Citation Validation

Verifies:

- legal references
- article numbers
- supporting evidence
- citation consistency

The system should never generate unsupported citations.

---

## Evaluation Framework

Measures system quality using benchmark datasets and evaluation metrics.

---

# Technology Stack

## Backend

- Python
- FastAPI

## RAG Framework

- LangChain

## Embedding Model

- BGE-M3

## Vector Database

- FAISS

## Reranker

- BGE Cross Encoder

## Database

- PostgreSQL

## Frontend

- React (Planned)

## Testing

- Pytest

## CI/CD

- GitHub Actions

## Deployment

- Docker

---

# Repository Architecture

The repository follows a documentation-first and benchmark-driven organization.

## Root Files

- README.md
- PROJECT_SPEC.md
- AI_CONTEXT.md
- DEVELOPMENT_PLAN.md
- ARCHITECTURE.md
- REQUIREMENTS.md
- ROADMAP.md
- TODO.md
- DECISIONS.md
- CHANGELOG.md
- CONTRIBUTING.md
- LICENSE
- SECURITY.md
- CODE_OF_CONDUCT.md

---

## Directory Structure

### docs/

Contains:

- Evaluation reports
- Working drafts
- Methodology
- Research notes
- Deployment guides
- Appendix material

---

### prompts/

Contains:

- Claude instructions
- ChatGPT instructions
- System prompts
- Prompt templates

---

### benchmarks/

Contains:

- Query sets
- Gold labels
- Relevance grading
- Hard negatives
- Benchmark definitions
- Evaluation results

---

### datasets/

Contains:

- Raw legal documents
- Processed datasets
- Metadata
- Embeddings
- Annotations
- Versioned datasets

---

### src/

Contains:

- Retrieval pipeline
- Embedding pipeline
- Reranking
- Evaluation
- Citation validation
- Utilities
- API implementation

---

### tests/

Contains:

- Unit tests
- Integration tests
- Evaluation tests
- Validation tests

---

### config/

Contains:

- Configuration files
- Environment settings
- Model configuration
- System parameters

---

### references/

Contains:

- Research papers
- Legal references
- Bibliography
- External resources

---

### outputs/

Contains:

- Reports
- Tables
- Figures
- Evaluation logs
- Generated artifacts

---

### .github/

Contains:

- GitHub Actions
- Issue templates
- Pull request templates
- Repository automation

---

# Design Principles

The architecture follows these principles:

- Documentation First
- Evidence First
- Citation Before Generation
- Modular Design
- Separation of Concerns
- Reproducibility
- Explainability
- Scalability
- Maintainability
- Traceability

---

# Future Architecture Extensions

The architecture is designed for future expansion.

Possible additions include:

- Hybrid Search (BM25 + Dense Retrieval)
- Knowledge Graph Integration
- Legal Ontology
- Agentic Workflows
- Multi-Agent Collaboration
- Continuous Evaluation Pipeline
- Human Feedback Loop
- Online Learning
- Monitoring Dashboard

---

# Current Development Status

## Completed

- Repository initialization
- Core documentation
- Repository organization
- Project specification
- AI operating context

## In Progress

- Benchmark design
- Documentation refinement
- Architecture planning

## Planned

- Dataset collection
- Data preprocessing
- Embedding generation
- Retrieval implementation
- Evaluation framework
- API development
- User interface
- Production deployment

---

# Final Architecture Principles

Every component in ALSHAYEB LAW should prioritize:

- Truthfulness over fluency.
- Evidence over assumptions.
- Traceable citations over unsupported claims.
- Reproducibility over convenience.
- Modular design over monolithic implementation.
- Academic quality together with production readiness.

The architecture should remain flexible enough to support future research while being robust enough for real-world legal AI applications.
