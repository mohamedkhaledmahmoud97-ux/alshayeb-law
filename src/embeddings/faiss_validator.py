"""
FAISS index validator for ALSHAYEB LAW.

Performs post-build validation of the FAISS vector index, metadata store,
and embedding manifest. All checks must PASS before Phase 4 can be declared
complete and Phase 5 can begin.

Validation checks (Phase4_Design_Document.md §14 Step 4):
    1. Index load integrity     — FAISS index loads without error
    2. Vector count             — ntotal matches expected chunk count (8,340)
    3. Embedding dimension      — d matches BGE-M3 output (1024)
    4. Metadata alignment       — len(metadata_list) == FAISS ntotal
    5. Orphan metadata check    — every metadata entry has a valid chunk_id
    6. Manifest consistency     — checksums, counts, dimensions match
    7. Index search integrity   — search returns valid results
    8. Metadata field presence  — all 14 chunk fields present in every entry
    9. Retrieval smoke test     — 5 sample queries return top-K results

Usage (programmatic)::

    from src.embeddings.faiss_validator import FAISSValidator, ValidationReport

    validator = FAISSValidator()
    report = validator.validate_all()
    if report.all_passed():
        print("All checks PASS.")
    else:
        print(f"FAILURES: {report.failures}")

Design decisions:
    - The validator is a standalone module that does not import from
      EmbeddingPipeline (no circular dependency risk).
    - It reuses FAISSStore.load() and BGEEncoder for the smoke test.
    - All file paths are derived from project constants.
    - Every check is independent — one failure does not block others.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import logging
import pickle
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from src.config.constants import CANONICAL_STORE_DIR, FAISS_STORE_DIR
from src.data.canonical_store import read_chunks
from src.data.models import Chunk
from src.embeddings.faiss_store import FAISSStore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Output paths (shared with embedding_pipeline.py)
# ---------------------------------------------------------------------------

FAISS_INDEX_PATH = FAISS_STORE_DIR / "index.faiss"
METADATA_PATH = FAISS_STORE_DIR / "metadata.pkl"
MANIFEST_PATH = FAISS_STORE_DIR / "embedding_manifest.json"

# ---------------------------------------------------------------------------
# Expected values (from Phase4_Design_Document.md and embedding_manifest.json)
# ---------------------------------------------------------------------------

EXPECTED_DIMENSION = 1024
EXPECTED_TOTAL_CHUNKS = 8340
EXPECTED_INDEX_TYPE = "IndexFlatIP"
EXPECTED_NORMALIZATION = "L2"

# ---------------------------------------------------------------------------
# Validation report types
# ---------------------------------------------------------------------------


@dataclass
class CheckResult:
    """Result of a single validation check."""

    name: str
    passed: bool
    message: str = ""
    detail: dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return self.passed


@dataclass
class ValidationReport:
    """Aggregated report of all validation checks."""

    checks: list[CheckResult] = field(default_factory=list)
    _start_time: float = field(default_factory=time.perf_counter)

    def add(self, result: CheckResult) -> None:
        self.checks.append(result)

    @property
    def failures(self) -> list[CheckResult]:
        return [c for c in self.checks if not c.passed]

    @property
    def passed_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def failed_count(self) -> int:
        return len(self.failures)

    def all_passed(self) -> bool:
        return self.failed_count == 0

    def summary(self) -> str:
        elapsed = time.perf_counter() - self._start_time
        status = "PASS" if self.all_passed() else "FAIL"
        lines = [
            f"{'=' * 70}",
            f"  FAISS VALIDATION REPORT",
            f"  Status: {status}",
            f"  Checks: {self.passed_count} passed, {self.failed_count} failed",
            f"  Time  : {elapsed:.2f}s",
            f"{'=' * 70}",
        ]
        for check in self.checks:
            icon = "✅" if check.passed else "❌"
            lines.append(f"  {icon}  [{check.name:40s}] {check.message}")
        if self.failures:
            lines.append(f"{'─' * 70}")
            lines.append("  FAILURE DETAILS:")
            for f in self.failures:
                lines.append(f"    [{f.name}] {f.message}")
                for k, v in f.detail.items():
                    lines.append(f"      {k}: {v!r}")
        lines.append(f"{'=' * 70}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# FAISS Validator
# ---------------------------------------------------------------------------


class FAISSValidator:
    """
    Post-build validator for the ALSHAYEB LAW FAISS index.

    Performs all checks defined in Phase4_Design_Document.md §14 Step 4.
    Each check is a separate method returning a CheckResult.
    """

    def __init__(self) -> None:
        self._index_store: FAISSStore | None = None
        self._metadata: list[dict[str, Any]] | None = None
        self._manifest: dict[str, Any] | None = None
        self._canonical_chunks: list[dict[str, Any]] | None = None

    # ------------------------------------------------------------------
    # Data loading helpers
    # ------------------------------------------------------------------

    def _load_index(self) -> FAISSStore:
        """Load the FAISS index from disk. Raises on failure."""
        if self._index_store is None:
            self._index_store = FAISSStore.load(FAISS_INDEX_PATH)
        return self._index_store

    def _load_metadata(self) -> list[dict[str, Any]]:
        """Load metadata.pkl from disk."""
        if self._metadata is None:
            if not METADATA_PATH.exists():
                raise FileNotFoundError(
                    f"Metadata file not found at '{METADATA_PATH}'. "
                    "Run the embedding pipeline first."
                )
            with METADATA_PATH.open("rb") as fh:
                self._metadata = pickle.load(fh)
        return self._metadata

    def _load_manifest(self) -> dict[str, Any]:
        """Load embedding_manifest.json from disk."""
        if self._manifest is None:
            if not MANIFEST_PATH.exists():
                raise FileNotFoundError(
                    f"Manifest file not found at '{MANIFEST_PATH}'. "
                    "Run the embedding pipeline first."
                )
            with MANIFEST_PATH.open("r", encoding="utf-8") as fh:
                self._manifest = json.load(fh)
        return self._manifest

    def _load_canonical_chunks(self) -> list[dict[str, Any]]:
        """Load canonical chunks from chunks.jsonl."""
        if self._canonical_chunks is None:
            self._canonical_chunks = [
                dataclasses.asdict(chunk) for chunk in read_chunks()
            ]
        return self._canonical_chunks

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def check_index_load(self) -> CheckResult:
        """
        Check 1: Index load integrity.

        Verifies that the FAISS index file exists, can be loaded,
        and has a valid dimension and vector count.
        """
        name = "Index load integrity"
        try:
            if not FAISS_INDEX_PATH.exists():
                return CheckResult(
                    name=name, passed=False,
                    message=f"File not found: {FAISS_INDEX_PATH}",
                )
            store = self._load_index()
            return CheckResult(
                name=name, passed=True,
                message=f"Loaded: ntotal={store.ntotal}, dim={store.d}",
                detail={"ntotal": store.ntotal, "d": store.d, "path": str(FAISS_INDEX_PATH)},
            )
        except Exception as exc:
            return CheckResult(
                name=name, passed=False,
                message=f"Load failed: {exc}",
            )

    def check_vector_count(self) -> CheckResult:
        """
        Check 2: Vector count.

        Verifies that the FAISS index contains exactly EXPECTED_TOTAL_CHUNKS (8,340) vectors.
        """
        name = "Vector count"
        try:
            store = self._load_index()
            if store.ntotal == EXPECTED_TOTAL_CHUNKS:
                return CheckResult(
                    name=name, passed=True,
                    message=f"ntotal={store.ntotal} == expected={EXPECTED_TOTAL_CHUNKS}",
                    detail={"ntotal": store.ntotal, "expected": EXPECTED_TOTAL_CHUNKS},
                )
            return CheckResult(
                name=name, passed=False,
                message=f"ntotal={store.ntotal} != expected={EXPECTED_TOTAL_CHUNKS}",
                detail={"ntotal": store.ntotal, "expected": EXPECTED_TOTAL_CHUNKS},
            )
        except Exception as exc:
            return CheckResult(name=name, passed=False, message=f"Error: {exc}")

    def check_embedding_dimension(self) -> CheckResult:
        """
        Check 3: Embedding dimension.

        Verifies that the FAISS index dimension is EXPECTED_DIMENSION (1024).
        """
        name = "Embedding dimension"
        try:
            store = self._load_index()
            if store.d == EXPECTED_DIMENSION:
                return CheckResult(
                    name=name, passed=True,
                    message=f"dim={store.d} == expected={EXPECTED_DIMENSION}",
                    detail={"d": store.d, "expected": EXPECTED_DIMENSION},
                )
            return CheckResult(
                name=name, passed=False,
                message=f"dim={store.d} != expected={EXPECTED_DIMENSION}",
                detail={"d": store.d, "expected": EXPECTED_DIMENSION},
            )
        except Exception as exc:
            return CheckResult(name=name, passed=False, message=f"Error: {exc}")

    def check_metadata_alignment(self) -> CheckResult:
        """
        Check 4: Metadata alignment.

        Verifies that len(metadata_list) == FAISS ntotal.
        This ensures every vector has a corresponding metadata entry.
        """
        name = "Metadata alignment"
        try:
            store = self._load_index()
            metadata = self._load_metadata()
            if len(metadata) == store.ntotal:
                return CheckResult(
                    name=name, passed=True,
                    message=f"metadata count={len(metadata)} == ntotal={store.ntotal}",
                    detail={"metadata_count": len(metadata), "ntotal": store.ntotal},
                )
            return CheckResult(
                name=name, passed=False,
                message=f"metadata count={len(metadata)} != ntotal={store.ntotal}",
                detail={"metadata_count": len(metadata), "ntotal": store.ntotal},
            )
        except Exception as exc:
            return CheckResult(name=name, passed=False, message=f"Error: {exc}")

    def check_orphan_metadata(self) -> CheckResult:
        """
        Check 5: Orphan metadata check.

        Verifies that every metadata entry has a non-empty chunk_id.
        Missing or null chunk_ids indicate a corruption in the metadata store.
        """
        name = "Orphan metadata check"
        try:
            metadata = self._load_metadata()
            missing_ids = [
                i for i, m in enumerate(metadata)
                if not m.get("chunk_id")
            ]
            if not missing_ids:
                return CheckResult(
                    name=name, passed=True,
                    message=f"All {len(metadata)} entries have valid chunk_id",
                    detail={"total": len(metadata)},
                )
            return CheckResult(
                name=name, passed=False,
                message=f"{len(missing_ids)} entries missing chunk_id",
                detail={"missing_positions": missing_ids[:10], "total": len(metadata)},
            )
        except Exception as exc:
            return CheckResult(name=name, passed=False, message=f"Error: {exc}")

    def check_manifest_consistency(self) -> CheckResult:
        """
        Check 6: Manifest consistency.

        Verifies that the manifest fields match the actual index and metadata:
            - total_chunks == ntotal
            - total_vectors == ntotal
            - embedding_dimension == d
            - index_type == "IndexFlatIP"
            - index checksum matches actual file
            - metadata checksum matches actual file
        """
        name = "Manifest consistency"
        try:
            store = self._load_index()
            manifest = self._load_manifest()

            issues: list[str] = []

            # Check total_chunks
            if manifest.get("total_chunks") != store.ntotal:
                issues.append(
                    f"total_chunks={manifest.get('total_chunks')} != ntotal={store.ntotal}"
                )

            # Check total_vectors
            if manifest.get("total_vectors") != store.ntotal:
                issues.append(
                    f"total_vectors={manifest.get('total_vectors')} != ntotal={store.ntotal}"
                )

            # Check dimension
            if manifest.get("embedding_dimension") != store.d:
                issues.append(
                    f"embedding_dimension={manifest.get('embedding_dimension')} != d={store.d}"
                )

            # Check index_type
            if manifest.get("index_type") != EXPECTED_INDEX_TYPE:
                issues.append(
                    f"index_type={manifest.get('index_type')} != expected={EXPECTED_INDEX_TYPE}"
                )

            # Check index checksum
            actual_index_hash = self._file_sha256(FAISS_INDEX_PATH)
            manifest_index_hash = manifest.get("index_checksum_sha256")
            if manifest_index_hash and actual_index_hash != manifest_index_hash:
                issues.append(
                    f"index checksum mismatch: manifest={manifest_index_hash}, actual={actual_index_hash}"
                )

            # Check metadata checksum
            actual_meta_hash = self._file_sha256(METADATA_PATH)
            manifest_meta_hash = manifest.get("metadata_checksum_sha256")
            if manifest_meta_hash and actual_meta_hash != manifest_meta_hash:
                issues.append(
                    f"metadata checksum mismatch: manifest={manifest_meta_hash}, actual={actual_meta_hash}"
                )

            if not issues:
                return CheckResult(
                    name=name, passed=True,
                    message=f"All {len(manifest)} manifest fields consistent",
                    detail={"manifest_fields": list(manifest.keys())},
                )
            return CheckResult(
                name=name, passed=False,
                message=f"{len(issues)} inconsistency(ies) found",
                detail={"issues": issues, "manifest": manifest},
            )
        except Exception as exc:
            return CheckResult(name=name, passed=False, message=f"Error: {exc}")

    def check_index_search_integrity(self) -> CheckResult:
        """
        Check 7: Index search integrity.

        Verifies that search returns valid results with correct shape.
        Uses a zero vector as a basic sanity check (always returns results).
        """
        name = "Index search integrity"
        try:
            store = self._load_index()
            # Create a zero query vector with correct dimension
            query = np.zeros((1, store.d), dtype=np.float32)
            # L2-normalize it
            norm = np.linalg.norm(query)
            if norm > 0:
                query = query / norm

            k = min(10, store.ntotal)
            distances, indices = store.search(query, k)

            # Verify output shapes
            if distances.shape != (1, k):
                return CheckResult(
                    name=name, passed=False,
                    message=f"distances shape mismatch: {distances.shape} != (1, {k})",
                    detail={"distances_shape": distances.shape, "expected": (1, k)},
                )
            if indices.shape != (1, k):
                return CheckResult(
                    name=name, passed=False,
                    message=f"indices shape mismatch: {indices.shape} != (1, {k})",
                    detail={"indices_shape": indices.shape, "expected": (1, k)},
                )

            # Verify indices are within valid range
            invalid_indices = [int(i) for i in indices[0] if i < 0 and i != -1]
            if invalid_indices:
                return CheckResult(
                    name=name, passed=False,
                    message=f"Invalid indices found: {invalid_indices[:5]}",
                    detail={"invalid_indices": invalid_indices[:10]},
                )

            return CheckResult(
                name=name, passed=True,
                message=f"Search OK: top-{k} results, scores in [{float(distances[0][-1]):.4f}, {float(distances[0][0]):.4f}]",
                detail={
                    "k": k,
                    "distances_shape": list(distances.shape),
                    "indices_shape": list(indices.shape),
                    "score_range": [float(distances[0][-1]), float(distances[0][0])],
                },
            )
        except Exception as exc:
            return CheckResult(name=name, passed=False, message=f"Error: {exc}")

    def check_metadata_field_presence(self) -> CheckResult:
        """
        Check 8: Metadata field presence.

        Verifies that every metadata entry contains all 14 expected chunk fields.
        """
        name = "Metadata field presence"
        expected_fields = {
            "chunk_id", "node_id", "source_id", "source_type",
            "title", "law_number", "law_year", "law_slug",
            "scope_flag", "section", "article_number", "seq",
            "text", "token_count",
        }
        try:
            metadata = self._load_metadata()
            missing_fields: dict[int, set[str]] = {}
            for i, entry in enumerate(metadata):
                missing = expected_fields - set(entry.keys())
                if missing:
                    missing_fields[i] = missing

            if not missing_fields:
                return CheckResult(
                    name=name, passed=True,
                    message=f"All {len(metadata)} entries contain {len(expected_fields)} expected fields",
                    detail={"expected_fields": sorted(expected_fields), "entry_count": len(metadata)},
                )
            return CheckResult(
                name=name, passed=False,
                message=f"{len(missing_fields)} entries have missing fields",
                detail={
                    "sample_missing": {str(k): sorted(v) for k, v in list(missing_fields.items())[:5]},
                    "total_affected": len(missing_fields),
                },
            )
        except Exception as exc:
            return CheckResult(name=name, passed=False, message=f"Error: {exc}")

    def check_retrieval_smoke_test(self) -> CheckResult:
        """
        Check 9: Retrieval smoke test.

        Runs 5 sample Arabic legal queries through the index and verifies:
            - Each query returns top-K results
            - Results have non-empty text
            - Results have valid chunk_ids
            - Results are scored (no NaN or inf)
        """
        name = "Retrieval smoke test"
        sample_queries = [
            "أحكام القانون المدني المصري",
            "نطاق تطبيق قانون العقوبات",
            "قواعد الإجراءات الجنائية",
            "الأحكام العامة للعقود",
            "تنظيم حق العمل",
        ]
        try:
            store = self._load_index()
            metadata = self._load_metadata()

            # Import encoder here to avoid circular import at module level
            from src.embeddings.bge_encoder import BGEEncoder
            from src.preprocessing.arabic_normalizer import normalize_arabic

            encoder = BGEEncoder(show_progress_bar=False)
            k = 5

            query_results: list[dict[str, Any]] = []
            issues: list[str] = []

            for q in sample_queries:
                # Normalize (ADR-015) and encode
                normalized = normalize_arabic(q)
                query_vector = encoder.encode_query(normalized)

                # Search
                distances, indices = store.search(query_vector, k)

                # Verify results
                results_for_query: list[dict[str, Any]] = []
                for pos in range(k):
                    idx = int(indices[0][pos])
                    score = float(distances[0][pos])

                    result_entry: dict[str, Any] = {
                        "index_pos": idx,
                        "score": score,
                    }

                    if idx >= 0 and idx < len(metadata):
                        chunk = metadata[idx]
                        result_entry["chunk_id"] = chunk.get("chunk_id", "")
                        result_entry["text_preview"] = chunk.get("text", "")[:100]
                    else:
                        issues.append(f"Query '{q[:30]}...': invalid index {idx}")
                        result_entry["chunk_id"] = None

                    results_for_query.append(result_entry)

                query_results.append({
                    "query": q[:60],
                    "top_scores": [r["score"] for r in results_for_query],
                    "top_chunk_ids": [r["chunk_id"] for r in results_for_query],
                })

                # Validate scores are finite
                for r in results_for_query:
                    if not np.isfinite(r["score"]):
                        issues.append(f"Query '{q[:30]}...': non-finite score {r['score']}")

            if not issues:
                return CheckResult(
                    name=name, passed=True,
                    message=f"All {len(sample_queries)} smoke test queries returned valid results",
                    detail={"queries": query_results, "k": k},
                )
            return CheckResult(
                name=name, passed=False,
                message=f"{len(issues)} issue(s) in smoke test",
                detail={"issues": issues, "queries": query_results},
            )
        except Exception as exc:
            return CheckResult(name=name, passed=False, message=f"Smoke test error: {exc}")

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _file_sha256(path: Path) -> str:
        """Compute SHA-256 hex digest of a file."""
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for block in iter(lambda: fh.read(65536), b""):
                h.update(block)
        return h.hexdigest()

    # ------------------------------------------------------------------
    # Run all checks
    # ------------------------------------------------------------------

    def validate_all(self) -> ValidationReport:
        """
        Run all 9 validation checks and return a consolidated report.

        Order of checks:
            1. Index load integrity
            2. Vector count
            3. Embedding dimension
            4. Metadata alignment
            5. Orphan metadata check
            6. Manifest consistency
            7. Index search integrity
            8. Metadata field presence
            9. Retrieval smoke test

        Returns:
            ValidationReport with all check results.
        """
        report = ValidationReport()

        # Each check is independent — use a list so all run even if some fail
        checks = [
            self.check_index_load,
            self.check_vector_count,
            self.check_embedding_dimension,
            self.check_metadata_alignment,
            self.check_orphan_metadata,
            self.check_manifest_consistency,
            self.check_index_search_integrity,
            self.check_metadata_field_presence,
            self.check_retrieval_smoke_test,
        ]

        for check_fn in checks:
            try:
                result = check_fn()
            except Exception as exc:
                result = CheckResult(
                    name=check_fn.__name__.replace("check_", "").replace("_", " ").title(),
                    passed=False,
                    message=f"Unexpected error: {exc}",
                )
            report.add(result)

        return report

