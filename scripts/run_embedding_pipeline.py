"""
CLI entry point for the ALSHAYEB LAW Embedding Pipeline.

Usage:
    py -3 scripts/run_embedding_pipeline.py [options]

Options:
    --batch-size INT    Encoding batch size (default: 32).
                        Reduce to 8 or 16 if the process runs out of memory.
    --device STR        Force a specific device: "cpu" or "cuda".
                        Default: auto-select (CUDA if available, else CPU).
    --no-resume         Start from scratch, ignoring any existing checkpoints.
    --no-progress       Suppress the tqdm progress bar during encoding.
    --help              Show this message and exit.

Output files (written to outputs/faiss/):
    index.faiss              — FAISS binary index (8,340 vectors × 1024 dims)
    metadata.pkl             — Python list of 8,340 chunk dicts
    embedding_manifest.json  — Audit manifest with checksums and provenance

The embedding pipeline reads from outputs/canonical/chunks.jsonl (read-only)
and never modifies any file under outputs/canonical/.

Checkpointing:
    If the process is interrupted, re-run with the same command.
    The pipeline resumes from the last completed batch automatically.
    To force a full re-run (discarding checkpoints), pass --no-resume.

Estimated run time: 15–45 minutes on CPU with BAAI/bge-m3.

Execute from the project root:
    py -3 scripts/run_embedding_pipeline.py

The script inserts the project root into sys.path so that `import src.*`
resolves correctly regardless of the working directory.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# ── Path fix ──────────────────────────────────────────────────────────────────
# Ensure project root is on sys.path so that `import src.*` works when this
# script is executed directly (e.g. py -3 scripts/run_embedding_pipeline.py).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ── Logging configuration ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("run_embedding_pipeline")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "ALSHAYEB LAW — Embedding Pipeline\n"
            "Encodes canonical chunks with BAAI/bge-m3 and writes a FAISS index."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--batch-size",
        type=int,
        default=32,
        metavar="INT",
        help="Encoding batch size (default: 32). Reduce if OOM.",
    )
    p.add_argument(
        "--device",
        type=str,
        default=None,
        metavar="STR",
        help="Force device: 'cpu' or 'cuda'. Default: auto-select.",
    )
    p.add_argument(
        "--no-resume",
        action="store_true",
        help="Ignore existing checkpoints and start from scratch.",
    )
    p.add_argument(
        "--no-progress",
        action="store_true",
        help="Suppress tqdm progress bar during encoding.",
    )
    return p


def main() -> None:
    args = _build_parser().parse_args()

    logger.info("Starting ALSHAYEB LAW Embedding Pipeline")
    logger.info("  batch-size  : %d", args.batch_size)
    logger.info("  device      : %s", args.device or "auto")
    logger.info("  resume      : %s", not args.no_resume)
    logger.info("  show-progress: %s", not args.no_progress)

    # Import here (after sys.path fix) so the script is self-contained
    from src.embeddings.embedding_pipeline import EmbeddingPipeline

    pipeline = EmbeddingPipeline(
        model_name="BAAI/bge-m3",
        batch_size=args.batch_size,
        device=args.device,
        show_progress=not args.no_progress,
        resume=not args.no_resume,
    )

    try:
        pipeline.run()
        logger.info("Pipeline completed successfully.")
        logger.info("Output files:")
        logger.info("  outputs/faiss/index.faiss")
        logger.info("  outputs/faiss/metadata.pkl")
        logger.info("  outputs/faiss/embedding_manifest.json")
        sys.exit(0)
    except KeyboardInterrupt:
        logger.warning(
            "Pipeline interrupted by user. "
            "Progress has been checkpointed. Re-run to resume."
        )
        sys.exit(1)
    except Exception as exc:
        logger.error("Pipeline failed: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
