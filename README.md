# ALSHAYEB LAW

**ALSHAYEB LAW** is an Egyptian Legal Retrieval-Augmented Generation (RAG) project focused on building, evaluating, and documenting a legally grounded AI assistant for Egyptian legal research.  
The project is designed as an academic and implementation-oriented benchmark for measuring retrieval quality, reranking quality, citation faithfulness, answer faithfulness, legal correctness, robustness, latency, throughput, and memory footprint.

---

## Project Overview

This repository contains the files, documentation, evaluation materials, and working drafts for an Egyptian legal RAG system named **ALSHAYEB LAW**.

The project is intended to support:

- legal article lookup,
- statute-only retrieval,
- doctrine retrieval,
- case-law retrieval,
- issue-to-rule retrieval,
- multi-hop legal reasoning,
- Arabic query normalization,
- citation validation,
- faithfulness evaluation,
- error analysis,
- and reproducible benchmark reporting.

The project is structured to work as a formal academic submission as well as a practical development workspace for Claude-assisted drafting and analysis.

---

## Goals

The main goals of this project are:

1. Build a structured evaluation framework for Egyptian legal RAG.
2. Define benchmark tasks and query sets.
3. Specify gold labels and relevance grading.
4. Measure retrieval, reranking, and generation quality.
5. Evaluate citation recall and citation accuracy.
6. Analyze robustness across Arabic query variations.
7. Document error analysis methods and deployment readiness criteria.
8. Produce a polished academic report that can be submitted as a formal project deliverable.

---

## Why This Project Exists

Legal AI systems must do more than answer questions fluently.  
They must retrieve the correct legal source, cite it accurately, and avoid unsupported or misleading claims.

This project exists to create a reproducible benchmark and report framework for an Egyptian legal RAG system that is:

- grounded in evidence,
- auditable,
- academically structured,
- and suitable for high-stakes legal use.

---

## Tools Used

This project is organized around the following tools and workflows:

### 1. Claude Project
Used for:
- generating report sections,
- refining academic wording,
- organizing instructions,
- drafting benchmark descriptions,
- producing structured tables and appendices,
- and keeping a persistent project context.

### 2. GitHub Repository
Used for:
- version control,
- file organization,
- documentation,
- maintaining source history,
- and managing project artifacts.

### 3. Markdown
Used for:
- writing working drafts,
- keeping version-friendly documentation,
- storing structured content,
- and making the project easy to update.

### 4. Word / PDF Export
Used for:
- final academic submission,
- polished formatting,
- and delivery to supervisors or reviewers.

### 5. Evaluation Frameworks and Metrics
The project uses standard RAG evaluation concepts such as:
- Recall@k,
- Precision@k,
- MRR,
- nDCG,
- Hit@k,
- Context Precision,
- Context Recall,
- Faithfulness,
- Citation Accuracy,
- Answer Completeness,
- Latency,
- Throughput,
- Memory Footprint.

---

## Evaluation Focus

The project evaluates the system across the following dimensions:

- Retrieval quality.
- Reranking quality.
- Citation faithfulness.
- Answer faithfulness.
- Legal correctness.
- Latency and throughput.
- Robustness across query types.
- Ethical and bias considerations.
- Citation recall.

The benchmark is intentionally divided into:
- statute-only queries,
- doctrine queries,
- case-law queries,
- exact article lookup tasks,
- legal issue-to-rule retrieval tasks,
- multi-hop legal reasoning tasks,
- Arabic wording variation tests,
- dialect normalization tests,
- hard negatives.

---

## Repository Structure

```text
alshayeb-law/
├── README.md
├── .gitignore
├── docs/
│   ├── ALSHAYEB_LAW_Evaluation_Report.md
│   ├── ALSHAYEB_LAW_Appendix_Pack.md
│   └── ALSHAYEB_LAW_Working_Draft.md
├── prompts/
│   ├── claude_project_instructions.md
│   └── system_prompt.md
├── benchmarks/
│   ├── query_sets/
│   ├── gold_labels/
│   ├── relevance_grading/
│   └── hard_negatives/
├── rubrics/
│   ├── retrieval_rubric.md
│   ├── generation_rubric.md
│   ├── citation_rubric.md
│   └── error_analysis_taxonomy.md
├── notes/
│   ├── methodology.md
│   ├── ethical_bias_considerations.md
│   └── deployment_readiness.md
├── references/
│   └── bibliography.md
└── outputs/
    ├── tables/
    ├── figures/
    └── evaluation_logs/
```

---

## Main Files

### `docs/ALSHAYEB_LAW_Evaluation_Report.md`
The main academic report, including:
- abstract,
- introduction,
- evaluation methodology,
- benchmark design,
- ethical and bias considerations,
- citation recall chapter,
- error analysis methodologies,
- statistical testing,
- scoring rubric,
- deployment readiness criteria.

### `docs/ALSHAYEB_LAW_Appendix_Pack.md`
Supporting appendix material, including:
- benchmark tables,
- gold label fields,
- relevance grading,
- rubrics,
- summary table,
- error taxonomy.

### `docs/ALSHAYEB_LAW_Working_Draft.md`
Editable working draft for continuous revision and Claude-assisted drafting.

### `prompts/claude_project_instructions.md`
Project-level instructions used in Claude to ensure consistent style, structure, and domain constraints.

---

## Suggested Workflow

1. Write or update the working draft in Markdown.
2. Store benchmark queries, labels, and rubrics in the repository.
3. Use Claude Project instructions to generate or refine sections.
4. Review outputs manually for structure and correctness.
5. Convert the final report to Word or PDF for submission.
6. Keep the GitHub repository updated with version history.

---

## Ethical and Quality Principles

This project follows the principle that a legal RAG system must be:

- faithful to the evidence,
- transparent in citations,
- careful about uncertainty,
- reproducible across runs,
- and robust to query variation.

The system should never invent legal claims, article numbers, or case references.

---

## Deployment and Reporting Readiness

The project is considered ready for submission when:

- the report is fully structured,
- benchmark slices are defined,
- gold labels are documented,
- rubrics are complete,
- error analysis categories are included,
- citations are traceable,
- and the repository is organized clearly.

---

## Contributing

If you are collaborating on this project, please:

- keep file names consistent,
- update documentation when content changes,
- use clear Markdown formatting,
- preserve version history,
- and avoid adding unsupported legal claims.

---

## License

Add a license when the repository is ready for sharing publicly.  
For private academic work, this section can remain pending until final publication.

---

## Contact

Project owner: **ALSHAYEB LAW**  
Purpose: **Egyptian legal RAG evaluation and academic benchmarking**  
Status: **Active development**

---

## Notes

This repository is intended to serve as both:

- a technical research workspace,
- and a formal academic submission package.

The final report should be kept in the `docs/` folder, while working materials, benchmark files, and prompts should remain organized by function.
