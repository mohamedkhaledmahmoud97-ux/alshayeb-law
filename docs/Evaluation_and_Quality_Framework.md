You are a research scientist specializing in retrieval evaluation and RAG benchmarking.

Design a complete Evaluation \& Benchmarking framework for “ALSHAYEB LAW”, an Egyptian Legal RAG system.

The framework must evaluate:

1. Retrieval quality.
2. Reranking quality.
3. Citation faithfulness.
4. Answer faithfulness.
5. Legal correctness.
6. Latency and throughput.
7. Robustness across query types.

Mandatory metrics:

- Recall@k
- Precision@k
- MRR
- nDCG
- Hit@k
- Context precision
- Context recall
- Faithfulness
- Citation accuracy
- Answer completeness
- Latency
- Memory footprint

Benchmark design requirements:

- Separate statute-only queries from doctrine queries and case-law queries.
- Include exact article lookup tasks.
- Include legal issue-to-rule retrieval tasks.
- Include multi-hop legal reasoning tasks.
- Include Arabic legal wording variation and dialect normalization tests.
- Include hard negative examples.
- Include ablation studies for chunking, embeddings, reranking, and prompts.
- Include statistical significance testing.

Methodological requirements:

- Define gold labels.
- Define relevance grading.
- Define query sets.
- Define retrieval candidate evaluation.
- Define generation evaluation.
- Define error analysis categories.
- Define success thresholds for deployment readiness.

Output style:

- Academic and implementation-oriented.
- Include a benchmark table.
- Explain why each metric matters in a legal RAG context.
- Make the evaluation reproducible and auditable.

Below is a complete, implementation-oriented **Evaluation \& Benchmarking framework** for **ALSHAYEB LAW**, designed for an Egyptian legal RAG system where legal correctness, traceability, and source faithfulness matter more than conversational fluency.

## 1. Evaluation objectives

The framework should measure the system at four distinct layers: retrieval, reranking, generation, and citation validation. In a legal setting, these layers must be evaluated separately because a system can retrieve the right article but generate an unsupported explanation, or generate a fluent answer with incorrect attribution. The benchmark should therefore treat the pipeline as a sequence of measurable components rather than a single end-to-end chatbot score.

## 2. Benchmark design

The benchmark should be partitioned into source-specific and task-specific subsets so that performance can be measured fairly across different legal materials. This is important because statutes, doctrine, and case law have different structure, ambiguity, and retrieval difficulty.

### Benchmark table

| Benchmark slice | Purpose | Example task type | Main metrics |
| :-- | :-- | :-- | :-- |
| Statute-only | Exact legal article retrieval | Find the article governing a specific rule | Recall@k, MRR, Hit@k |
| Doctrine | Retrieve doctrinal explanation | Find commentary explaining a rule | Recall@k, nDCG, context precision |
| Case law | Retrieve holding / reasoning | Find a ruling applying a rule | Recall@k, Precision@k, faithfulness |
| Exact lookup | Pinpoint article or case | Identify the exact article number | Hit@k, MRR, citation accuracy |
| Rule-to-application | Map issue to rule | Retrieve the governing rule and application | nDCG, context recall, answer completeness |
| Multi-hop reasoning | Combine statute + case + doctrine | Answer a compound legal question | Recall@k, faithfulness, answer completeness |
| Arabic variation | Handle paraphrase and dialect | Same query in formal and colloquial Arabic | Recall@k, MRR, robustness |
| Hard negatives | Resist near-miss sources | Similar article, wrong legal topic | Precision@k, nDCG, citation accuracy |

## 3. Gold labels

Gold labels should be created at the level of retrieval relevance and answer support. For retrieval, each query should have one or more gold source IDs and relevance grades. For generation, each query should have a reference answer outline and evidence spans that support the answer. For citation validation, each gold answer should specify which claims require which sources.

### Gold-label fields

- `query_id`
- `query_text`
- `query_type`
- `source_class`
- `gold_source_ids`
- `gold_span_ids`
- `relevance_grade`
- `reference_answer`
- `required_citations`
- `hard_negative_ids`

Gold labels should be versioned so that benchmark results remain reproducible across corpus updates.

## 4. Relevance grading

Use graded relevance rather than binary relevance because legal sources can be partially relevant. A simple four-level scale is sufficient.

- **3 = highly relevant:** directly answers the legal issue or contains the exact rule.
- **2 = relevant:** useful support or closely related application.
- **1 = marginally relevant:** background or partial context.
- **0 = not relevant:** irrelevant or misleading.

This grading is especially useful for nDCG, because ranked legal retrieval should reward placing the most legally useful source at the top, not just any related source.

## 5. Retrieval evaluation

Retrieval should be evaluated independently of generation. This is necessary because the LLM may compensate for retrieval mistakes in superficial ways, which can hide retrieval failure. The retrieval benchmark should use Recall@k, Precision@k, MRR, nDCG, and Hit@k.

### Why each metric matters

- **Recall@k:** measures whether the correct legal source appears somewhere in the retrieved set.
- **Precision@k:** measures how much of the top-k retrieval is actually useful.
- **MRR:** measures how early the first correct source appears.
- **nDCG:** measures ranking quality with graded relevance.
- **Hit@k:** measures whether the system finds at least one correct source in the top-k.

For statutory article search, MRR and Hit@k are especially important. For doctrine and case law, nDCG and Precision@k become more important because several partially relevant passages may exist.

## 6. Reranking evaluation

Reranking should be benchmarked on the same query set as retrieval, but evaluated separately. The candidate list from the retriever should be fixed, and the reranker should be measured by how much it improves ranking of gold evidence. A strong reranker should raise MRR and nDCG without lowering Recall@k.

### Reranking metrics

- pre-rerank vs post-rerank Recall@k,
- MRR improvement,
- nDCG improvement,
- top-1 accuracy,
- latency cost per query.

The reranker is successful if it consistently moves exact legal sources closer to the top while preserving the correct source set.

## 7. Generation evaluation

Generation must be evaluated for faithfulness, answer completeness, and legal correctness. A legal answer that is fluent but unsupported is a failure. A legal answer that is partially correct but omits a crucial exception may also be a failure.

### Generation metrics

- **Faithfulness:** whether the answer is supported by the retrieved context.
- **Answer completeness:** whether the answer addresses all required legal points.
- **Legal correctness:** whether the answer follows the governing legal rule.
- **Citation accuracy:** whether cited sources are real, present, and correctly matched.

Faithfulness is especially important because a legal system must not introduce unsupported doctrine, invented article numbers, or speculative reasoning.

## 8. Citation evaluation

Citation faithfulness should be measured separately from answer correctness. A response may be factually close to correct but still cite the wrong source, which is unacceptable in law. The benchmark should therefore include citation-level labels that mark each sentence or claim as supported, partially supported, or unsupported.

### Citation metrics

- **Citation accuracy:** proportion of citations that exist and match the retrieved evidence.
- **Citation faithfulness:** proportion of claims whose citations truly support the claim.
- **Unsupported-claim rate:** proportion of answer claims with no source support.
- **Version correctness:** whether the cited source is the correct legal version.

A legal RAG system should not be considered ready for deployment unless citation accuracy is consistently high and unsupported-claim rate is very low.

## 9. Robustness testing

Robustness should be tested across query paraphrases, Arabic wording variation, dialectal phrasing, and ambiguous legal formulations. The same legal question should be expressed in multiple ways and the system should return the same governing sources.

### Robustness slices

- formal Modern Standard Arabic,
- colloquial Egyptian Arabic,
- mixed Arabic-English legal terms,
- abbreviated article references,
- synonym-rich paraphrases,
- long multi-constraint questions.

Robustness matters because legal users do not always ask questions in textbook Arabic. The benchmark should therefore include query normalization tests and semantic equivalence groups.

## 10. Hard negatives

Hard negatives are essential for legal retrieval benchmarking because legal documents often look similar while supporting different rules. The benchmark should include articles from the same law, adjacent articles, or similar rulings that are intentionally incorrect for the query.

### Hard negative examples

- same law, wrong article;
- same topic, different legal effect;
- same court, different holding;
- same doctrinal author, different legal rule.

These examples test whether the system can discriminate between similar legal texts rather than merely finding something that looks related.

## 11. Ablation studies

Ablation studies are required to understand which component improves which metric. At minimum, the benchmark should compare:

- chunking strategies,
- embedding models,
- retriever types,
- reranker presence/absence,
- prompt variants,
- citation validation enabled vs disabled.


### Ablation questions

- Does article-based chunking outperform semantic chunking for statutory retrieval?
- Does hybrid retrieval outperform dense-only retrieval?
- Does reranking improve MRR without hurting Recall@k?
- Does strict citation validation reduce hallucinations?

Ablation results should be reported per query type, not only as a global average, because improvements may differ across statutes, doctrine, and case law.

## 12. Statistical significance testing

All main comparisons should include statistical significance testing. Use paired tests on per-query scores so that system A and system B are compared on the same queries. For metrics like Recall@k and MRR, paired bootstrap testing is a practical choice. For continuous measures such as faithfulness or latency, paired bootstrap or Wilcoxon signed-rank tests are appropriate.

### Reporting rules

- report mean and confidence interval,
- report p-values for primary comparisons,
- avoid claiming improvement unless it is statistically supported,
- include effect size where possible.

This prevents overinterpreting small benchmark fluctuations as real progress.

## 13. Error analysis categories

The benchmark should not stop at aggregate scores. It should include a structured error taxonomy so that failures can be traced to specific pipeline stages.

### Error categories

- **Retrieval miss:** correct source not retrieved.
- **Ranking error:** correct source retrieved but not ranked highly enough.
- **Chunking error:** legal unit split incorrectly or context truncated.
- **Normalization error:** Arabic normalization caused retrieval mismatch.
- **Citation error:** source cited incorrectly or fabricated.
- **Faithfulness error:** answer contradicts retrieved evidence.
- **Completeness error:** answer omits a crucial rule or exception.
- **Version error:** wrong legal version used.

This taxonomy helps decide whether a failure is caused by ingestion, retrieval, reranking, prompting, or validation.

## 14. Success thresholds

Before deployment, the system should meet minimum thresholds defined per task class. Exact thresholds depend on the corpus and gold set size, but the framework should require:

- high Recall@k on statute-only queries,
- strong MRR on exact lookup tasks,
- strong citation accuracy on grounded answers,
- low unsupported-claim rate,
- acceptable p95 latency,
- low memory overhead,
- stable performance across paraphrase variants.

A practical deployment rule is: if the system cannot retrieve the correct statute reliably, it should not be allowed to generate a legal answer from memory.

## 15. Reproducibility and auditability

The benchmark must be fully reproducible. That means locking the corpus version, embedding version, chunking strategy, reranker version, prompt version, and evaluation script version. Every experiment should save:

- query set version,
- index snapshot ID,
- model checkpoint/version,
- retrieval outputs,
- reranker outputs,
- generation outputs,
- evaluation reports.

This is essential in a legal system because benchmark drift can create false confidence. If the corpus changes, the benchmark should be rerun and the new results must be comparable to the old ones only through versioned provenance.

## 16. Recommended evaluation workflow

A good evaluation workflow is:

1. Build the gold query set by task type.
2. Label retrieval relevance grades.
3. Prepare hard negatives and paraphrase variants.
4. Run retrieval-only evaluation.
5. Run reranking evaluation.
6. Run generation evaluation with fixed context.
7. Run citation validation evaluation.
8. Perform error analysis.
9. Run ablations.
10. Report significance tests and deployment readiness.

This workflow ensures that the team sees whether a problem belongs to retrieval, ranking, generation, or citation control.

## 17. Deployment readiness checklist

The system is ready for production only if:

- statute retrieval is reliable on exact lookup tasks,
- hybrid retrieval beats or matches baselines,
- reranking improves ranking quality,
- citation accuracy is high,
- unsupported claims are rare or blocked,
- faithfulness is stable across Arabic variants,
- latency is within target for real use,
- benchmark runs are reproducible and auditable.

That combination is the correct standard for a legal RAG platform, because legal users need source fidelity, not only fluent answers.

If you want, I can convert this into a **formal evaluation protocol document** with sections, tables, and a scoring rubric suitable for inclusion in your project report.

