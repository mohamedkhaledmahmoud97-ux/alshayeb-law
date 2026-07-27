"""
Embedding pipeline for ALSHAYEB LAW.

Transforms the canonical chunk corpus into a FAISS vector index, a
metadata store, and an audit manifest.

Pipeline stages:
    1. Load all chunks from canonical store (read-only; never writes).
    2. Batch-normalize chunk text with normalize_arabic() in memory (ADR-015).
    3. Encode normalized text with BAAI/bge-m3.
    4. Add L2-normalized vectors to FAISS IndexFlatIP.
    5. Append chunk dicts (original text) to in-memory metadata list.
    6. Save checkpoint after each batch for resumable execution.
    7. After all batches: persist index.faiss, metadata.pkl, manifest.

Checkpointing (Phase4_Design_Document.md §6.5):
    outputs/faiss/checkpoints/
    ├── checkpoint.json    — {"last_completed_batch": N, "total_batches": M}
    ├── vectors_0.npy      — numpy array for batch 0
    ├── vectors_1.npy      — numpy array for batch 1
    └── ...

    On resume, the pipeline reads checkpoint.json, skips completed batches,
    and continues from last_completed_batch + 1.  On successful completion
    the checkpoint directory is removed.

ADR-015 compliance:
    - normalize_arabic() is called inside _embed_batch() immediately before
      passing text to the encoder.
    - normalized_texts is a local variable; it is never returned, logged,
      or persisted.
    - metadata.pkl stores chunk["text"] (original Arabic text), NOT the
      normalized form.
    - The canonical store (outputs/canonical/) is opened read-only.

ADR-013 compliance:
    - The scope_flag field is preserved in every metadata dict entry.
    - Retrieval-time scope filtering operates on this field.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import logging
import pickle
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from src.config.constants import CANONICAL_STORE_DIR, OUTPUTS_DIR
from src.data.canonical_store import read_chunks
from src.data.models import Chunk
from src.embeddings.bge_encoder import BGEEncoder
from src.embeddings.faiss_store import FAISSStore
from src.preprocessing.arabic_normalizer import normalize_arabic

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Output paths (Phase4_Design_Document.md §6.4 and §6.5)
# ---------------------------------------------------------------------------

FAISS_STORE_DIR = OUTPUTS_DIR / "faiss"
FAISS_INDEX_PATH = FAISS_STORE_DIR / "index.faiss"
METADATA_PATH = FAISS_STORE_DIR / "metadata.pkl"
MANIFEST_PATH = FAISS_STORE_DIR / "embedding_manifest.json"
CHECKPOINT_DIR = FAISS_STORE_DIR / "checkpoints"
CHECKPOINT_JSON = CHECKPOINT_DIR / "checkpoint.json"

# ---------------------------------------------------------------------------
# Embedding pipeline
# ---------------------------------------------------------------------------


class EmbeddingPipeline:
    """
    End-to-end pipeline: canonical corpus → FAISS index + metadata + manifest.

    Usage::

        pipeline = EmbeddingPipeline()
        pipeline.run()

    Args:
        model_name       : HuggingFace model ID. Default BAAI/bge-m3. (ADR-011)
        batch_size       : Chunks per encoding batch. Default 32.
        device           : "cuda" | "cpu" | None (auto). Default None.
        show_progress    : Show tqdm progress bar during encoding. Default True.
        resume           : If True, resume from last completed checkpoint.
                           If False, start from scratch (overwrites existing).
                           Default True.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        batch_size: int = 32,
        device: str | None = None,
        *,
        show_progress: bool = True,
        resume: bool = True,
    ) -> None:
        self._model_name = model_name
        self._batch_size = batch_size
        self._device = device
        self._show_progress = show_progress
        self._resume = resume

    # ------------------------------------------------------------------
    # ADR-015: Arabic normalization (in-memory, never persisted)
    # ------------------------------------------------------------------

    def _embed_batch(
        self,
        batch: list[dict[str, Any]],
        encoder: BGEEncoder,
    ) -> np.ndarray:
        """
        Normalize chunk texts and encode them into vectors.

        ADR-015: normalize_arabic() is called here, immediately before
        passing text to the encoder.  normalized_texts is a local variable
        scoped to this method — it is never stored, returned as part of
        metadata, or written to disk.

        Args:
            batch   : List of chunk dicts (original text, never modified).
            encoder : Initialized BGEEncoder instance.

        Returns:
            float32 numpy array of shape (len(batch), 1024), L2-normalized.
        """
        # ADR-015: normalize immediately before encode — in memory only
        normalized_texts = [normalize_arabic(chunk["text"]) for chunk in batch]
        vectors = encoder.encode_documents(normalized_texts)
        # normalized_texts goes out of scope here and is never persisted
        return vectors

    # ------------------------------------------------------------------
    # Checkpointing helpers
    # ------------------------------------------------------------------

    def _read_checkpoint(self) -> int:
        """Return last completed batch index, or -1 if no checkpoint exists."""
        if not CHECKPOINT_JSON.exists():
            return -1
        try:
            with CHECKPOINT_JSON.open("r", encoding="utf-8") as fh:
                state = json.load(fh)
            last = int(state.get("last_completed_batch", -1))
            logger.info("Checkpoint found: last_completed_batch=%d", last)
            return last
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning("Could not read checkpoint.json (%s). Starting fresh.", exc)
            return -1

    def _save_checkpoint(
        self,
        batch_index: int,
        total_batches: int,
        vectors: np.ndarray,
    ) -> None:
        """Persist batch vectors and update checkpoint.json."""
        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        np.save(CHECKPOINT_DIR / f"vectors_{batch_index}.npy", vectors)
        state = {"last_completed_batch": batch_index, "total_batches": total_batches}
        with CHECKPOINT_JSON.open("w", encoding="utf-8") as fh:
            json.dump(state, fh)
        logger.debug("Checkpoint saved: batch %d / %d", batch_index, total_batches - 1)

    def _clear_checkpoints(self) -> None:
        """Remove checkpoint directory after successful completion."""
        if CHECKPOINT_DIR.exists():
            import shutil
            shutil.rmtree(CHECKPOINT_DIR)
            logger.info("Checkpoint directory removed after successful run.")

    # ------------------------------------------------------------------
    # Manifest helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _file_sha256(path: Path) -> str:
        """Compute SHA-256 hex digest of a file."""
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for block in iter(lambda: fh.read(65536), b""):
                h.update(block)
        return h.hexdigest()

    def _write_manifest(
        self,
        total_vectors: int,
        batch_size: int,
        device: str,
    ) -> None:
        """Write embedding_manifest.json (Phase4_Design_Document.md §5.3)."""
        manifest = {
            "model_name": self._model_name,
            "embedding_dimension": 1024,
            "total_chunks": total_vectors,
            "total_vectors": total_vectors,
            "index_type": "IndexFlatIP",
            "normalization": "L2",
            "adr_015_applied": True,
            "normalizer": "src.preprocessing.arabic_normalizer.normalize_arabic",
            "corpus_source": str(CANONICAL_STORE_DIR / "chunks.jsonl"),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "index_checksum_sha256": self._file_sha256(FAISS_INDEX_PATH),
            "metadata_checksum_sha256": self._file_sha256(METADATA_PATH),
            "batch_size": batch_size,
            "device": device,
        }
        FAISS_STORE_DIR.mkdir(parents=True, exist_ok=True)
        with MANIFEST_PATH.open("w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2, ensure_ascii=False)
        logger.info("Manifest written to %s", MANIFEST_PATH)

    # ------------------------------------------------------------------
    # Main run method
    # ------------------------------------------------------------------

    def run(self) -> None:
        """
        Execute the full embedding pipeline.

        Steps:
            1. Load all chunks from canonical store (read-only).
            2. Batch the chunks.
            3. If resuming, reload completed batch vectors from checkpoints.
            4. For each pending batch: normalize → encode → checkpoint.
            5. Assemble full vector matrix from checkpoints + new batches.
            6. Build FAISSStore and add all vectors.
            7. Write index.faiss, metadata.pkl, embedding_manifest.json.
            8. Validate vector count vs chunk count.
            9. Clear checkpoint directory.

        Raises:
            RuntimeError: If the vector count does not match the chunk count
                          after all batches are complete.
        """
        t_start = time.perf_counter()
        logger.info("=== ALSHAYEB LAW — Embedding Pipeline ===")
        logger.info("Model      : %s", self._model_name)
        logger.info("Batch size : %d", self._batch_size)
        logger.info("Resume     : %s", self._resume)

        # Step 1: Load chunks
        logger.info("Loading chunks from canonical store...")
        all_chunks: list[dict[str, Any]] = [
            dataclasses.asdict(chunk) for chunk in read_chunks()
        ]
        total_chunks = len(all_chunks)
        logger.info("Loaded %d chunks.", total_chunks)

        if total_chunks == 0:
            raise RuntimeError(
                "No chunks found in the canonical store. "
                "Run the ingestion pipeline first."
            )

        # Step 2: Partition into batches
        batches: list[list[dict[str, Any]]] = [
            all_chunks[i : i + self._batch_size]
            for i in range(0, total_chunks, self._batch_size)
        ]
        total_batches = len(batches)
        logger.info("Total batches: %d (batch_size=%d)", total_batches, self._batch_size)

        # Step 3: Determine resume point
        if self._resume:
            last_completed = self._read_checkpoint()
        else:
            last_completed = -1
            # Clear any stale checkpoints from a prior interrupted run
            self._clear_checkpoints()

        # Step 4: Initialize encoder (deferred until after chunk loading)
        logger.info("Initializing BGE-M3 encoder...")
        encoder = BGEEncoder(
            model_name=self._model_name,
            batch_size=self._batch_size,
            device=self._device,
            show_progress_bar=self._show_progress,
        )
        effective_device = (
            str(encoder._model.device)
            if hasattr(encoder._model, "device")
            else (self._device or "cpu")
        )
        logger.info("Encoder ready on device: %s", effective_device)

        # Step 5: Process each batch
        for batch_idx, batch in enumerate(batches):
            if batch_idx <= last_completed:
                logger.info(
                    "Skipping batch %d / %d (already checkpointed).",
                    batch_idx,
                    total_batches - 1,
                )
                continue

            logger.info(
                "Encoding batch %d / %d (%d chunks)...",
                batch_idx,
                total_batches - 1,
                len(batch),
            )

            # ADR-015: normalize → encode (normalized text stays in _embed_batch scope)
            vectors = self._embed_batch(batch, encoder)
            self._save_checkpoint(batch_idx, total_batches, vectors)

        logger.info("All %d batches encoded and checkpointed.", total_batches)

        # Step 6: Assemble full vector matrix from checkpoint files
        logger.info("Assembling full vector matrix from checkpoints...")
        vector_parts: list[np.ndarray] = []
        for batch_idx in range(total_batches):
            npy_path = CHECKPOINT_DIR / f"vectors_{batch_idx}.npy"
            vector_parts.append(np.load(npy_path))

        all_vectors = np.vstack(vector_parts).astype(np.float32)
        logger.info(
            "Vector matrix shape: %s (expected %d × 1024)",
            all_vectors.shape,
            total_chunks,
        )

        # Step 7: Build FAISS index
        logger.info("Building FAISS IndexFlatIP...")
        store = FAISSStore.build_new(dim=encoder.embedding_dim)
        store.add(all_vectors)
        logger.info("FAISS index built: ntotal=%d", store.ntotal)

        # Step 8: Persist index
        FAISS_STORE_DIR.mkdir(parents=True, exist_ok=True)
        store.save(FAISS_INDEX_PATH)

        # Step 9: Persist metadata (original chunk dicts — NOT normalized texts)
        logger.info("Writing metadata.pkl...")
        with METADATA_PATH.open("wb") as fh:
            pickle.dump(all_chunks, fh, protocol=pickle.HIGHEST_PROTOCOL)
        logger.info("Metadata written: %d records", len(all_chunks))

        # Step 10: Write manifest
        self._write_manifest(
            total_vectors=store.ntotal,
            batch_size=self._batch_size,
            device=effective_device,
        )

        # Step 11: Validate alignment
        if store.ntotal != total_chunks:
            raise RuntimeError(
                f"Vector count mismatch: FAISS has {store.ntotal} vectors "
                f"but canonical store has {total_chunks} chunks. "
                "Re-run the embedding pipeline without --resume."
            )
        logger.info(
            "Validation PASS: %d vectors == %d chunks.", store.ntotal, total_chunks
        )

        # Step 12: Clear checkpoints
        self._clear_checkpoints()

        elapsed = time.perf_counter() - t_start
        logger.info(
            "=== Embedding pipeline complete in %.1fs (%.0f chunks/min) ===",
            elapsed,
            total_chunks / elapsed * 60,
        )
