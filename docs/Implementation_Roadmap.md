You are a delivery-focused AI architect and software program manager.

Create a weekly implementation roadmap for building “ALSHAYEB LAW”, an Egyptian Legal RAG platform.

The roadmap must be organized as sprints and include:

1. Sprint number and duration.
2. Sprint objectives.
3. Tasks.
4. Deliverables.
5. Dependencies.
6. Risks.
7. Acceptance criteria.
8. Estimated complexity.
9. Success metrics.

Mandatory roadmap phases:

- Sprint 1: Data audit and schema design.
- Sprint 2: Ingestion and normalization.
- Sprint 3: Chunking and indexing.
- Sprint 4: Hybrid retrieval baseline.
- Sprint 5: Reranker integration.
- Sprint 6: Citation validation layer.
- Sprint 7: LLM prompting and response schema.
- Sprint 8: Evaluation framework.
- Sprint 9: Performance tuning.
- Sprint 10: Deployment and monitoring.

Roadmap constraints:

- Prioritize the legal laws corpus first.
- Defer unstructured doctrines and judgments to later sprints.
- Include an MVP definition.
- Include a post-MVP expansion path.
- Include testing and evaluation in every major phase.
- Include rollback and quality-control checkpoints.

Writing style:

- Concise but operational.
- Use a table for sprint planning.
- Make dependencies explicit.
- Avoid generic project-management language.
- Focus on what must be built, in what order, and why.

Below is a **10-sprint weekly roadmap** for building **ALSHAYEB LAW** as an Egyptian Legal RAG platform. It prioritizes the statutory laws corpus first, keeps doctrines and judgments for later expansion, and includes testing, rollback, and quality-control checkpoints in every major phase. The roadmap is designed around the core RAG principle that retrieval quality must be measured and improved independently from generation, using metrics such as Recall@k, MRR, nDCG, and faithfulness.[^1][^2][^3][^4][^5]

## Sprint roadmap

| Sprint | Duration | Objectives | Key tasks | Deliverables | Dependencies | Risks | Acceptance criteria | Complexity | Success metrics |
| :-- | --: | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| 1. Data audit and schema design | Week 1 | Define the canonical legal data model for laws only | Audit the 481-law JSON corpus, normalize fields, design IDs for law/article/version, define metadata schema, define provenance and audit fields, create test fixtures | Canonical schema, data dictionary, entity-relationship draft, sample records, validation rules | None | Missing/ inconsistent article fields, duplicate law versions, malformed JSON | 100% of sample laws map to schema; no unresolved mandatory fields in validation set | Medium | Schema coverage; parse success rate; duplicate detection rate |
| 2. Ingestion and normalization | Week 2 | Convert laws corpus into structured, versioned legal records | Build ingestion parser, Arabic normalization, version hashing, source classification, validation pipeline, raw-to-canonical ETL, rollback-ready snapshots | Ingestion notebook/service, normalized dataset, versioned law registry, raw snapshot archive | Sprint 1 schema | Over-normalization may damage legal text; accidental text corruption | Laws can be ingested and reproduced deterministically from raw inputs | Medium | Ingestion throughput; checksum stability; text fidelity audit pass |
| 3. Chunking and indexing | Week 3 | Produce retrieval-ready article chunks and build initial indexes | Article-level chunking, sub-article handling for long articles, metadata enrichment, dense embeddings, BM25 index, Qdrant collection with payload filters | Chunked corpus, BM25 index, vector index, payload schema, indexing logs | Sprint 2 normalized corpus | Bad chunk boundaries, lost citations, index drift | Every article has a stable chunk ID and retrieval payload; indexing is reproducible | High | Chunk integrity; index build success; retrieval-ready coverage |
| 4. Hybrid retrieval baseline | Week 4 | Build a first retrieval engine for legal article search | Query understanding, Arabic legal normalization, entity extraction, hybrid BM25 + dense retrieval, metadata filter application, score fusion, top-k candidate output | Retrieval API v1, query router, baseline hybrid retriever, retrieval logs | Sprint 3 indexes | Poor lexical-dense balance; irrelevant top-k results | Exact article queries return correct statutes in top-k; filters work by law/article/source/date | High | Recall@k, MRR, precision@k on test set |
| 5. Reranker integration | Week 5 | Improve precision of top results before generation | Integrate cross-encoder reranker, set candidate pool sizes, deduplicate results, reranker thresholds, confidence scoring, fallback logic | Reranker service, ranked evidence bundle, confidence scores, ablation log | Sprint 4 retrieval baseline | Latency increase, reranker overfitting, top-k instability | Reranker improves MRR/nDCG over baseline and does not reduce recall materially | High | MRR gain, nDCG gain, reranker latency |
| 6. Citation validation layer | Week 6 | Enforce evidence-grounded responses and block unsupported claims | Build claim-to-evidence matcher, citation verification rules, evidence span alignment, refusal fallback, validation audit trail, response rejection path | Citation validator, claim-support matrix, refusal protocol, validation report | Sprint 5 ranked evidence bundles | False positives in validation, overly aggressive refusals | No unsupported citation passes; every accepted claim is linked to source evidence | High | Citation accuracy, unsupported-claim rejection rate, refusal precision |
| 7. LLM prompting and response schema | Week 7 | Constrain the model to formatting only | Create system prompt, output schema, context assembly template, legal answer template, source formatting rules, confidence display, post-generation sanity checks | Prompt pack, response schema, formatter chain, test prompts, safety rules | Sprint 6 validation layer | Model paraphrases unsupported content; schema drift | The model outputs only the defined schema and cannot invent citations in tests | Medium | Schema compliance rate, hallucination rate, formatting success |
| 8. Evaluation framework | Week 8 | Measure retrieval, reranking, citation fidelity, and answer faithfulness | Build gold test set, define query classes, run Recall@k/MRR/nDCG, faithfulness checks, citation accuracy tests, hard negative analysis, significance testing | Benchmark suite, evaluation dashboard, baseline report, error taxonomy | Sprint 4–7 pipeline | Incomplete labels, biased test queries, metric mismatch | End-to-end evaluation runs reproducibly and reports retrieval + generation quality separately | High | Recall@k, MRR, nDCG, faithfulness, citation accuracy |
| 9. Performance tuning | Week 9 | Reduce latency and improve robustness before release | Optimize payload indexes, caching, batch embedding, reranker depth, top-k sizes, query routing, retry/fallback rules, load tests, rollback tests | Performance report, tuned parameters, cache policies, rollback plan, stress-test results | Sprint 8 evaluation data | Optimization may reduce quality; caching may stale results | Tuned system meets latency target without degrading legal retrieval quality | Medium | p95 latency, throughput, cache hit rate, quality regression |
| 10. Deployment and monitoring | Week 10 | Release MVP with observability and controlled rollout | Containerization, CI/CD, environment config, monitoring dashboards, alerting, audit logs, access controls, canary release, runbooks | Deployed MVP, dashboards, alerts, operational docs, incident runbook | Sprint 9 tuned system | Deployment bugs, monitoring gaps, ACL errors | MVP runs in production-like environment with traceable queries and rollback support | High | Uptime, error rate, audit completeness, rollback success |

## MVP definition

The **MVP** should end at Sprint 10 and support the following legal capabilities:

- statute-only question answering,
- exact article retrieval,
- evidence-grounded summaries,
- citation-validated responses,
- audit logging and traceability,
- basic Arabic legal normalization,
- hybrid retrieval with reranking.

At MVP stage, **do not** include unstructured doctrine and judgments in production retrieval unless they are tightly curated and separately indexed. That expansion should happen only after the statutory pipeline proves stable and measurable.

## Post-MVP expansion path

After the statutory MVP is validated, the next phases should add:

1. **Court of Cassation judgments** with judgment-level and paragraph-level indexing.
2. **Administrative court decisions** with issue, reasoning, and holding segmentation.
3. **Legal doctrine and commentaries** with hierarchical chunking and author metadata.
4. **Knowledge graph linking** between articles, precedents, doctrines, and legal topics.
5. **Human review workflows** for curated evidence bundles and difficult legal domains.

This sequencing is important because statutes are structurally simpler and easier to validate, while judgments and doctrine introduce more ambiguity and require richer metadata and chunking logic.

## Rollback and QC checkpoints

Every sprint should end with a rollback checkpoint:

- preserve the previous stable schema or index snapshot,
- keep versioned embeddings and index snapshots,
- maintain a reproducible build manifest,
- require evaluation sign-off before promoting to the next sprint.

Quality control should be explicit:

- **Sprint 1–2:** schema and normalization review.
- **Sprint 3–4:** retrieval correctness and metadata filter tests.
- **Sprint 5–6:** ranking and citation-validation tests.
- **Sprint 7–8:** prompt safety and benchmark validation.
- **Sprint 9–10:** performance and deployment rehearsal.


## Dependency logic

The roadmap is intentionally sequential because later layers depend on earlier correctness:

- schema must exist before ingestion,
- ingestion must be stable before chunking,
- chunking and indexing must exist before retrieval,
- retrieval must be stable before reranking,
- reranking must be stable before citation validation,
- citation validation must exist before prompt finalization,
- evaluation must cover the full chain before deployment.

This ordering reflects current RAG practice, where retrieval quality, reranking, and grounding are evaluated as separate but connected stages.[^2][^3][^4][^6][^5][^1]

## Risk profile

The most important risks are:

- corrupted legal text during normalization,
- incorrect article segmentation,
- poor retrieval on Arabic variants,
- reranker latency growth,
- false citation approvals,
- model-generated unsupported claims,
- version drift across legal updates.

The main mitigation is conservative engineering: preserve provenance, use article-level canonical IDs, keep the LLM constrained, and refuse answers when evidence is insufficient.

## Success criteria for release

The project should be considered ready for MVP deployment if:

- statute retrieval reaches strong top-k quality on the internal benchmark,
- reranking improves precision without unacceptable latency,
- citation validation blocks unsupported claims reliably,
- the prompt layer produces schema-compliant outputs,
- the monitoring stack captures all query traces,
- the rollback path has been tested successfully.

If you want, I can convert this roadmap into a **Gantt-style sprint plan** or a **Notion/Jira-ready implementation board** with tasks and subtasks.
<span style="display:none">[^10][^11][^12][^13][^14][^15][^16][^17][^18][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: https://arxiv.org/pdf/2502.17163.pdf

[^2]: https://arxiv.org/pdf/2405.07437.pdf

[^3]: http://arxiv.org/pdf/2408.08067.pdf

[^4]: https://arxiv.org/pdf/2309.15217.pdf

[^5]: https://arxiv.org/abs/2604.01733

[^6]: https://langcopilot.com/posts/2025-09-17-rag-evaluation-101-from-recall-k-to-answer-faithfulness

[^7]: http://arxiv.org/pdf/2409.03759.pdf

[^8]: https://arxiv.org/pdf/2407.11005.pdf

[^9]: https://arxiv.org/pdf/2404.13781.pdf

[^10]: http://arxiv.org/pdf/2405.13622.pdf

[^11]: https://ui.adsabs.harvard.edu/abs/2024arXiv240203216C/abstract

[^12]: https://arxiv.org/html/2402.03216v3

[^13]: https://www.semanticscholar.org/paper/BGE-M3-Embedding:-Multi-Lingual,-Multi-Granularity-Chen-Xiao/4d5735c186ddb2430ac9689ccf61fdcbbfc23abc

[^14]: https://qdrant.tech/documentation/manage-data/payload/

[^15]: https://deepwiki.com/qdrant/qdrant-client/5.1-payload-filtering

[^16]: https://arxiv.org/html/2604.01733v1

[^17]: https://www.devshelfhub.com/cheatsheets/qdrant/

[^18]: https://deepwiki.com/qdrant/qdrant/4-payload-indexing-and-filtering

