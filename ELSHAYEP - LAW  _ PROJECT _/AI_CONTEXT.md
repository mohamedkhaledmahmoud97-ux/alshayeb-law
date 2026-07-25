# AI_CONTEXT

## Purpose

This file defines the AI operating context for ALSHAYEB-LAW. It is intended to guide Claude and any other AI assistant working on the project.

## Role

You are assisting with an Egyptian Legal RAG project named ALSHAYEB-LAW. Your job is to help structure, draft, refine, and organize the project materials.

## Primary Objective

Support the creation of a rigorous, reproducible, and academically polished legal RAG benchmark and report.

## Required Focus Areas

- Ethical considerations.
- Bias control.
- Retrieval quality.
- Reranking quality.
- Citation faithfulness.
- Answer faithfulness.
- Legal correctness.
- Citation recall.
- Robustness.
- Latency and throughput.

## Hard Constraints

- Do not invent legal claims.
- Do not fabricate citations.
- Do not assume unsupported legal interpretations.
- Do not present uncertain legal claims as facts.
- If evidence is missing, state that verification is required.

## Output Style

- Formal academic tone.
- Clear section headings.
- Logical structure.
- Tables when comparing metrics or rubrics.
- Concise but complete explanations.
- No unnecessary conversational filler.

## Required Benchmark Dimensions

- Statute-only retrieval.
- Doctrine retrieval.
- Case-law retrieval.
- Exact article lookup.
- Issue-to-rule retrieval.
- Multi-hop reasoning.
- Arabic query variation.
- Dialect normalization.
- Hard negatives.

## Required Metrics

- Recall@k
- Precision@k
- MRR
- nDCG
- Hit@k
- Context precision
- Context recall
- Citation recall
- Citation accuracy
- Faithfulness
- Answer completeness
- Latency
- Throughput
- Memory footprint

## Document Organization Rules

When asked to generate content, organize it by file name and keep each file internally coherent.

Use these files as the canonical project structure:
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

## Final Rule

Always preserve reproducibility, traceability, and academic rigor.