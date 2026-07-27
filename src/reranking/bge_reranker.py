"""
BGE Cross-Encoder reranker wrapper for ALSHAYEB LAW.

Wraps BAAI/bge-reranker-v2-m3 for consistent, deterministic query-document
relevance scoring used by the reranking pipeline.

Design decisions (Phase 5):
    - Model: BAAI/bge-reranker-v2-m3 (BGE family — consistent with BGE-M3 encoder)
    - Cross-encoder architecture: joint query-document scoring (more accurate
      than bi-encoder cosine similarity for relevance ranking)
    - Device auto-selected: CUDA if available, otherwise CPU
