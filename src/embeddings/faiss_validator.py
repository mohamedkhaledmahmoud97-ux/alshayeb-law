"""
FAISS validation module for ALSHAYEB LAW.

Post-build validation of the FAISS index, per Phase4_Design_Document.md §3.6:
    "Responsibility: Post-build validation of the FAISS index.
     Checks: vector count, embedding dimension, missing embeddings,
     orphan metadata, index integrity, load test, retrieval smoke test."

This module is read-only with respect to every artifact it inspects:
    outputs/canonical/chunks.jsonl   (source of truth for what SHOULD be embedded)
    outputs/faiss/index.faiss        (FAISS binary index)
    outputs/faiss/metadata.pkl       (chunk metadata list, position-aligned with the index)
    outputs/faiss/embedding_manifest.json  (audit manifest with checksums)

It never re-runs the embedding pipeline and never modifies any of these files.

ADR-015 note: this module does not call normalize_arabic() directly. The
optional query-encoding smoke test delegates to BGEEncoder.encode_query(),
which — per ADR-015 and bge_encoder.py's own docstring — expects the CALLER
to normalize text first. The self-retrieval smoke test (the default,
dependency-light check) does not encode new text at all, so normalization
is not applicable to it.

Per Phase4_Design_Document.md §11.3: if any check FAILs, Phase 4 embedding
must be re-run before Phase 5 begins. scripts/validate_faiss.py enforces
this by exiting with code 1 on any FAIL.
"""

from __future__ import annotations

import json
import logging
import pickle
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np

from src.config.constants import CANONICAL_STORE_DIR, FAISS_STORE_DIR

logger = logging.getLogger(__name__)

_EXPECTED_DIM = 1024
_EXPECTED_INDEX_TYPE = "IndexFlatIP"
_NORM_TOLERANCE = 1e-3  # L2-normalized vectors should have norm 1.0 +/- this

FAISS_INDEX_PATH = FAISS_STORE_DIR / "index.faiss"
METADATA_PATH = FAISS_STORE_DIR / "metadata.pkl"
MANIFEST_PATH = FAISS_STORE_DIR / "embedding_manifest.json"
CANONICAL_CHUNKS_PATH = CANONICAL_STORE_DIR / "chunks.jsonl"


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class CheckResult:
    """Outcome of a single validation check."""

    name: str
    passed: bool
    details: dict[str, Any] = field(default_factory=dict)
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": "PASS" if self.passed else "FAIL",
            "message": self.message,
            "details": self.details,
        }


@dataclass
class ValidationReport:
    """Aggregate result of a full validation run."""

    checks: list[CheckResult] = field(default_factory=list)
    started_at: str = ""
    elapsed_seconds: float = 0.0

    @property
    def overall_pass(self) -> bool:
        return all(c.passed for c in self.checks)

    def add(self, result: CheckResult) -> None:
        self.checks.append(result)
        logger.info(
            "[%s] %s%s",
            "PASS" if result.passed else "FAIL",
            result.name,
            f" — {result.message}" if result.message else "",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_status": "PASS" if self.overall_pass else "FAIL",
            "started_at": self.started_at,
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "checks": [c.to_dict() for c in self.checks],
        }

    def summary_lines(self) -> list[str]:
        lines = [f"[{c.to_dict()['status']}] {c.name}" for c in self.checks]
        lines.append(
            f"OVERALL VALIDATION: {'PASS' if self.overall_pass else 'FAIL'}"
        )
        return lines


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class FAISSValidator:
    """
    Runs the full Phase 4 Step 4 validation suite against the artifacts
    produced by EmbeddingPipeline (src/embeddings/embedding_pipeline.py).

    Usage::

        validator = FAISSValidator()
        report = validator.run_all()
        if not report.overall_pass:
            sys.exit(1)

    Every artifact is opened read-only. This class never writes to
    outputs/faiss/ or outputs/canonical/.
    """

    def __init__(
        self,
        index_path: Path = FAISS_INDEX_PATH,
        metadata_path: Path = METADATA_PATH,
        manifest_path: Path = MANIFEST_PATH,
        canonical_chunks_path: Path = CANONICAL_CHUNKS_PATH,
    ) -> None:
        self._index_path = index_path
        self._metadata_path = metadata_path
        self._manifest_path = manifest_path
        self._canonical_chunks_path = canonical_chunks_path

        # Populated by _load_artifacts(), consumed by later checks.
        self._index = None
        self._metadata: list[dict[str, Any]] | None = None
        self._manifest: dict[str, Any] | None = None
        self._canonical_chunk_ids: list[str] | None = None

    # ------------------------------------------------------------------
    # Artifact loading (shared by multiple checks; failures are captured
    # as FAILed CheckResults rather than raised, so run_all() can still
    # report on every artifact that DID load successfully).
    # ------------------------------------------------------------------

    def _load_artifacts(self) -> CheckResult:
        """
        Load the FAISS index, metadata.pkl, manifest, and canonical chunk
        ID list. This is also the "load test" required by
        Phase4_Design_Document.md §3.6 — it exercises the same FAISSStore.load()
        path the retriever will use in Phase 5.
        """
        details: dict[str, Any] = {}
        try:
            from src.embeddings.faiss_store import FAISSStore

            store = FAISSStore.load(self._index_path)
            self._index = store
            details["index_ntotal"] = store.ntotal
            details["index_dim"] = store.d
        except Exception as exc:  # noqa: BLE001 - report, don't crash the suite
            return CheckResult(
                name="load_test",
                passed=False,
                message=f"Failed to load FAISS index via FAISSStore.load(): {exc}",
                details=details,
            )

        try:
            with self._metadata_path.open("rb") as fh:
                self._metadata = pickle.load(fh)
            details["metadata_count"] = len(self._metadata)
        except Exception as exc:  # noqa: BLE001
            return CheckResult(
                name="load_test",
                passed=False,
                message=f"Failed to load metadata.pkl: {exc}",
                details=details,
            )

        try:
            with self._manifest_path.open("r", encoding="utf-8") as fh:
                self._manifest = json.load(fh)
        except Exception as exc:  # noqa: BLE001
            return CheckResult(
                name="load_test",
                passed=False,
                message=f"Failed to load embedding_manifest.json: {exc}",
                details=details,
            )

        try:
            ids: list[str] = []
            with self._canonical_chunks_path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    ids.append(json.loads(line)["chunk_id"])
            self._canonical_chunk_ids = ids
            details["canonical_chunk_count"] = len(ids)
        except Exception as exc:  # noqa: BLE001
            return CheckResult(
                name="load_test",
                passed=False,
                message=f"Failed to read canonical chunks.jsonl: {exc}",
                details=details,
            )

        return CheckResult(
            name="load_test",
            passed=True,
            message="Index, metadata, manifest, and canonical chunk IDs all loaded successfully.",
            details=details,
        )

    # ------------------------------------------------------------------
    # Individual checks (each assumes _load_artifacts() has succeeded;
    # run_all() short-circuits if it did not)
    # ------------------------------------------------------------------

    def check_index_integrity(self) -> CheckResult:
        """
        Verify the loaded index is well-formed: correct FAISS index class,
        is_trained, non-zero vector count, and no NaN/Inf in a sample of
        reconstructed vectors.
        """
        assert self._index is not None
        raw_index = self._index._index  # underlying faiss.Index (read-only access)
        index_type = type(raw_index).__name__

        problems: list[str] = []
        if index_type != _EXPECTED_INDEX_TYPE:
            problems.append(
                f"expected index type {_EXPECTED_INDEX_TYPE!r}, got {index_type!r}"
            )
        if not getattr(raw_index, "is_trained", True):
            problems.append("index reports is_trained=False")
        if self._index.ntotal == 0:
            problems.append("index contains 0 vectors")

        nan_inf_positions: list[int] = []
        if self._index.ntotal > 0:
            sample_positions = self._sample_positions(self._index.ntotal, n=50)
            for pos in sample_positions:
                vec = raw_index.reconstruct(pos)
                if not np.all(np.isfinite(vec)):
                    nan_inf_positions.append(pos)
        if nan_inf_positions:
            problems.append(
                f"NaN/Inf found in reconstructed vectors at positions {nan_inf_positions}"
            )

        return CheckResult(
            name="index_integrity",
            passed=not problems,
            message="; ".join(problems) if problems else "Index is well-formed.",
            details={
                "index_type": index_type,
                "is_trained": getattr(raw_index, "is_trained", True),
                "ntotal": self._index.ntotal,
                "sampled_positions_checked": len(sample_positions) if self._index.ntotal else 0,
            },
        )

    def check_vector_count(self) -> CheckResult:
        """
        Cross-check vector/record counts across all four sources of truth:
        FAISS index, metadata.pkl, embedding_manifest.json, and the
        canonical chunks.jsonl the pipeline was supposed to embed.
        """
        assert self._index is not None
        assert self._metadata is not None
        assert self._manifest is not None
        assert self._canonical_chunk_ids is not None

        counts = {
            "faiss_ntotal": self._index.ntotal,
            "metadata_count": len(self._metadata),
            "manifest_total_vectors": self._manifest.get("total_vectors"),
            "manifest_total_chunks": self._manifest.get("total_chunks"),
            "canonical_chunk_count": len(self._canonical_chunk_ids),
        }
        distinct_values = {v for v in counts.values() if v is not None}
        passed = len(distinct_values) == 1

        return CheckResult(
            name="vector_count",
            passed=passed,
            message=(
                "All counts match."
                if passed
                else f"Count mismatch across sources: {counts}"
            ),
            details=counts,
        )

    def check_embedding_dimensions(self) -> CheckResult:
        """
        Verify the index dimension matches the BGE-M3 output dimension
        (1024, per ADR-011 / Phase4_Design_Document.md §6.1) and that a
        sample of stored vectors are L2-normalized (required for
        IndexFlatIP inner-product search to behave as cosine similarity).
        """
        assert self._index is not None
        raw_index = self._index._index

        dim_ok = self._index.d == _EXPECTED_DIM
        manifest_dim = (self._manifest or {}).get("embedding_dimension")
        manifest_dim_ok = manifest_dim == _EXPECTED_DIM

        norm_problems: list[dict[str, Any]] = []
        sample_positions: list[int] = []
        if self._index.ntotal > 0:
            sample_positions = self._sample_positions(self._index.ntotal, n=50)
            for pos in sample_positions:
                vec = raw_index.reconstruct(pos)
                norm = float(np.linalg.norm(vec))
                if abs(norm - 1.0) > _NORM_TOLERANCE:
                    norm_problems.append({"position": pos, "norm": norm})

        passed = dim_ok and manifest_dim_ok and not norm_problems
        messages = []
        if not dim_ok:
            messages.append(f"index.d={self._index.d} != expected {_EXPECTED_DIM}")
        if not manifest_dim_ok:
            messages.append(
                f"manifest embedding_dimension={manifest_dim} != expected {_EXPECTED_DIM}"
            )
        if norm_problems:
            messages.append(
                f"{len(norm_problems)}/{len(sample_positions)} sampled vectors "
                f"not L2-normalized (tolerance {_NORM_TOLERANCE})"
            )

        return CheckResult(
            name="embedding_dimensions",
            passed=passed,
            message="; ".join(messages) if messages else "Dimension and L2 normalization verified.",
            details={
                "index_dim": self._index.d,
                "manifest_dim": manifest_dim,
                "sampled_vectors_checked": len(sample_positions),
                "norm_problems": norm_problems,
            },
        )

    def check_metadata_alignment(self) -> CheckResult:
        """
        Verify metadata.pkl is correctly position-aligned with the FAISS
        index (position N in the index must correspond to metadata[N]),
        and check for missing embeddings (canonical chunks with no
        corresponding metadata entry) and orphan metadata (metadata
        entries with no corresponding canonical chunk) — both explicitly
        required by Phase4_Design_Document.md §3.6.
        """
        assert self._metadata is not None
        assert self._canonical_chunk_ids is not None

        metadata_ids = [m.get("chunk_id") for m in self._metadata]

        # Duplicate chunk_id check within metadata itself.
        seen: set[str] = set()
        duplicates: list[str] = []
        for cid in metadata_ids:
            if cid in seen:
                duplicates.append(cid)
            seen.add(cid)

        # Order/alignment check: metadata order must exactly match the
        # canonical chunks.jsonl order, since EmbeddingPipeline.run()
        # embeds chunks in the order read_chunks() yields them and
        # appends to metadata_list in lock-step with FAISSStore.add().
        order_matches = metadata_ids == self._canonical_chunk_ids

        canonical_set = set(self._canonical_chunk_ids)
        metadata_set = set(metadata_ids)
        missing_embeddings = sorted(canonical_set - metadata_set)  # in canon, not embedded
        orphan_metadata = sorted(metadata_set - canonical_set)     # embedded, not in canon

        required_keys = {
            "chunk_id", "node_id", "source_id", "source_type", "title",
            "law_number", "law_year", "law_slug", "scope_flag", "section",
            "article_number", "seq", "text", "token_count", "type_metadata",
        }
        schema_problems: list[dict[str, Any]] = []
        for pos in self._sample_positions(len(self._metadata), n=25):
            record = self._metadata[pos]
            missing_keys = required_keys - set(record.keys())
            if missing_keys:
                schema_problems.append({"position": pos, "missing_keys": sorted(missing_keys)})

        passed = (
            not duplicates
            and order_matches
            and not missing_embeddings
            and not orphan_metadata
            and not schema_problems
        )

        messages = []
        if duplicates:
            messages.append(f"{len(duplicates)} duplicate chunk_id(s) in metadata")
        if not order_matches:
            messages.append(
                "metadata order does not match canonical chunks.jsonl order "
                "(FAISS position <-> metadata alignment cannot be trusted)"
            )
        if missing_embeddings:
            messages.append(f"{len(missing_embeddings)} canonical chunk(s) missing an embedding")
        if orphan_metadata:
            messages.append(f"{len(orphan_metadata)} orphan metadata record(s) with no canonical chunk")
        if schema_problems:
            messages.append(f"{len(schema_problems)} sampled metadata record(s) missing required keys")

        return CheckResult(
            name="metadata_alignment",
            passed=passed,
            message="; ".join(messages) if messages else "Metadata is fully aligned with the FAISS index and canonical store.",
            details={
                "duplicate_chunk_ids": duplicates[:20],
                "order_matches": order_matches,
                "missing_embeddings_count": len(missing_embeddings),
                "missing_embeddings_sample": missing_embeddings[:20],
                "orphan_metadata_count": len(orphan_metadata),
                "orphan_metadata_sample": orphan_metadata[:20],
                "schema_problems": schema_problems,
            },
        )

    def check_manifest_consistency(self) -> CheckResult:
        """
        Recompute SHA-256 checksums of index.faiss and metadata.pkl and
        compare against the values recorded in embedding_manifest.json at
        write time (embedding_pipeline.py._write_manifest). A mismatch
        means the files were modified, corrupted, or regenerated after
        the manifest was written.
        """
        assert self._manifest is not None

        index_hash = self._file_sha256(self._index_path)
        metadata_hash = self._file_sha256(self._metadata_path)

        expected_index_hash = self._manifest.get("index_checksum_sha256")
        expected_metadata_hash = self._manifest.get("metadata_checksum_sha256")

        index_ok = index_hash == expected_index_hash
        metadata_ok = metadata_hash == expected_metadata_hash

        required_manifest_keys = {
            "model_name", "embedding_dimension", "total_chunks", "total_vectors",
            "index_type", "normalization", "adr_015_applied", "normalizer",
            "corpus_source", "created_at", "index_checksum_sha256",
            "metadata_checksum_sha256", "batch_size", "device",
        }
        missing_manifest_keys = sorted(required_manifest_keys - set(self._manifest.keys()))

        passed = index_ok and metadata_ok and not missing_manifest_keys
        messages = []
        if not index_ok:
            messages.append("index.faiss checksum does not match manifest")
        if not metadata_ok:
            messages.append("metadata.pkl checksum does not match manifest")
        if missing_manifest_keys:
            messages.append(f"manifest missing keys: {missing_manifest_keys}")

        return CheckResult(
            name="manifest_consistency",
            passed=passed,
            message="; ".join(messages) if messages else "Manifest checksums and required fields verified.",
            details={
                "index_checksum_match": index_ok,
                "metadata_checksum_match": metadata_ok,
                "computed_index_sha256": index_hash,
                "computed_metadata_sha256": metadata_hash,
                "manifest_model_name": self._manifest.get("model_name"),
                "manifest_adr_015_applied": self._manifest.get("adr_015_applied"),
            },
        )

    def check_retrieval_smoke_test(
        self,
        n_samples: int = 10,
        seed: int = 42,
        known_queries: list[tuple[str, str]] | None = None,
    ) -> CheckResult:
        """
        Retrieval smoke test.

        Two modes:

        1. Self-retrieval mode (always run, no external model required):
           For `n_samples` vectors already stored in the index, search the
           index using that same stored vector as the query. The chunk at
           position 0 of the result must be the chunk itself, with a
           similarity score of ~1.0. This verifies the index is actually
           searchable end-to-end (not just loadable) and that scores behave
           as expected for IndexFlatIP cosine similarity, without requiring
           network access to download the BGE-M3 model.

        2. Known-query mode (optional, requires BGEEncoder / a downloaded
           BAAI/bge-m3 model): if `known_queries` is provided as a list of
           (query_text, expected_chunk_id_substring) pairs, each query is
           encoded with BGEEncoder.encode_query() and searched against the
           index; the check verifies the expected chunk appears in the
           Top-10 results. This is the fuller check described in
           Phase4_Design_Document.md §10 ("Recall@10 on 5 known queries"),
           which that document itself marks as "Manual validation" — it
           depends on a curated query set that does not yet exist
           (benchmarks/query_sets is not yet populated) and on the encoder
           model being available in the runtime environment.
        """
        assert self._index is not None
        assert self._metadata is not None

        details: dict[str, Any] = {}
        problems: list[str] = []

        # --- Mode 1: self-retrieval (always executed) ---
        raw_index = self._index._index
        rng = np.random.default_rng(seed)
        n = min(n_samples, self._index.ntotal)
        positions = (
            rng.choice(self._index.ntotal, size=n, replace=False)
            if self._index.ntotal > 0
            else np.array([], dtype=int)
        )

        self_retrieval_failures: list[dict[str, Any]] = []
        for pos in positions.tolist():
            query_vec = raw_index.reconstruct(int(pos)).reshape(1, -1).astype(np.float32)
            distances, indices = self._index.search(query_vec, k=3)
            top_index = int(indices[0][0])
            top_score = float(distances[0][0])
            expected_chunk_id = self._metadata[pos]["chunk_id"]
            actual_chunk_id = self._metadata[top_index]["chunk_id"]
            if top_index != pos or abs(top_score - 1.0) > 1e-3:
                self_retrieval_failures.append(
                    {
                        "queried_position": pos,
                        "expected_top_position": pos,
                        "actual_top_position": top_index,
                        "expected_chunk_id": expected_chunk_id,
                        "actual_chunk_id": actual_chunk_id,
                        "top_score": top_score,
                    }
                )

        details["self_retrieval_samples"] = n
        details["self_retrieval_failures"] = self_retrieval_failures
        if self_retrieval_failures:
            problems.append(
                f"{len(self_retrieval_failures)}/{n} self-retrieval samples "
                "did not return themselves as the top-1 result"
            )

        # --- Mode 2: known-query recall (optional, only if provided) ---
        if known_queries:
            try:
                from src.embeddings.bge_encoder import BGEEncoder

                encoder = BGEEncoder(show_progress_bar=False)
                hits = 0
                per_query: list[dict[str, Any]] = []
                for query_text, expected_substring in known_queries:
                    qvec = encoder.encode_query(query_text)
                    distances, indices = self._index.search(qvec, k=10)
                    top_chunk_ids = [
                        self._metadata[int(i)]["chunk_id"] for i in indices[0] if i >= 0
                    ]
                    hit = any(expected_substring in cid for cid in top_chunk_ids)
                    hits += int(hit)
                    per_query.append(
                        {
                            "query": query_text,
                            "expected_substring": expected_substring,
                            "hit": hit,
                            "top_chunk_ids": top_chunk_ids,
                        }
                    )
                recall_at_10 = hits / len(known_queries)
                details["known_query_recall_at_10"] = recall_at_10
                details["known_query_results"] = per_query
                if recall_at_10 < 0.8:
                    problems.append(
                        f"known-query Recall@10 = {recall_at_10:.2f}, below the 0.8 target "
                        "(Phase4_Design_Document.md §10)"
                    )
            except ImportError as exc:
                details["known_query_skipped_reason"] = str(exc)
                logger.warning(
                    "Known-query smoke test skipped (encoder unavailable): %s", exc
                )
        else:
            details["known_query_skipped_reason"] = (
                "No known_queries provided. Phase4_Design_Document.md §10 describes this "
                "as a manual validation step requiring a curated 5-query set with expected "
                "results; benchmarks/query_sets is not yet populated (Phase 6+)."
            )

        return CheckResult(
            name="retrieval_smoke_test",
            passed=not problems,
            message="; ".join(problems) if problems else "Self-retrieval smoke test passed for all samples.",
            details=details,
        )

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------

    def run_all(
        self,
        known_queries: list[tuple[str, str]] | None = None,
    ) -> ValidationReport:
        """
        Run every validation check in sequence and return an aggregate
        ValidationReport. If artifact loading itself fails, only the
        load_test result is returned (the remaining checks cannot run
        meaningfully without loaded artifacts).
        """
        from datetime import datetime, timezone

        t_start = time.perf_counter()
        report = ValidationReport(started_at=datetime.now(timezone.utc).isoformat())

        load_result = self._load_artifacts()
        report.add(load_result)

        if not load_result.passed:
            report.elapsed_seconds = time.perf_counter() - t_start
            return report

        checks: list[Callable[[], CheckResult]] = [
            self.check_index_integrity,
            self.check_vector_count,
            self.check_embedding_dimensions,
            self.check_metadata_alignment,
            self.check_manifest_consistency,
            lambda: self.check_retrieval_smoke_test(known_queries=known_queries),
        ]
        for check_fn in checks:
            report.add(check_fn())

        report.elapsed_seconds = time.perf_counter() - t_start
        return report

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _sample_positions(total: int, n: int, seed: int = 7) -> list[int]:
        """Deterministic reproducible sample of index positions to inspect."""
        if total == 0:
            return []
        rng = np.random.default_rng(seed)
        size = min(n, total)
        return sorted(int(i) for i in rng.choice(total, size=size, replace=False))

    @staticmethod
    def _file_sha256(path: Path) -> str:
        import hashlib

        h = hashlib.sha256()
        with path.open("rb") as fh:
            for block in iter(lambda: fh.read(65536), b""):
                h.update(block)
        return h.hexdigest()
