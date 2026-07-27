"""
CLI entry point for FAISS index validation — ALSHAYEB LAW.

Performs all post-build validation checks on the FAISS index, metadata store,
and embedding manifest. Must PASS before Phase 4 can be declared complete.

Usage:
    py -3 scripts/validate_faiss.py

Options:
    --smoke-queries INT    Number of smoke test queries to run (default: 5).
    --verbose, -v          Print detailed per-check information.
    --quiet, -q            Suppress progress output; print only the summary.
    --exit-on-fail         Exit with code 1 on first failure (default: run all).
    --help                 Show this message and exit.

Exit codes:
    0 — All checks PASS
    1 — One or more checks FAILED

Execute from the project root:
    py -3 scripts/validate_faiss.py

The script inserts the project root into sys.path so that `import src.*`
resolves correctly regardless of the working directory.

Output:
    - Machine-readable JSON report written to outputs/faiss/validation_report.json
    - Human-readable summary printed to stdout
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Path fix ──────────────────────────────────────────────────────────────────
# Ensure project root is on sys.path so that `import src.*` works when this
# script is executed directly (e.g. py -3 scripts/validate_faiss.py).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ── Logging configuration ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.WARNING,  # suppress INFO from imported modules; we handle output
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("validate_faiss")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "ALSHAYEB LAW — FAISS Index Validation\n"
            "Validates the FAISS index, metadata store, and embedding manifest "
            "after the embedding pipeline has completed."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--smoke-queries",
        type=int,
        default=5,
        metavar="INT",
        help="Number of smoke test queries (default: 5).",
    )
    p.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed per-check information.",
    )
    p.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress progress output; print only the summary.",
    )
    p.add_argument(
        "--exit-on-fail",
        action="store_true",
        help="Exit with code 1 on first failure (default: run all checks).",
    )
    return p


def _to_serializable(obj):
    """Convert non-serializable types to JSON-safe values."""
    if isinstance(obj, dict):
        return {k: _to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_serializable(v) for v in obj]
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.ndarray,)):
        return obj.tolist()
    return obj


def main() -> None:
    args = _build_parser().parse_args()

    if not args.quiet:
        print("=" * 70)
        print("  ALSHAYEB LAW — FAISS Index Validation")
        print("=" * 70)
        print(f"  Smoke test queries : {args.smoke_queries}")
        print(f"  Verbose           : {args.verbose}")
        print(f"  Exit on fail      : {args.exit_on_fail}")
        print()

    # Import here (after sys.path fix) so the script is self-contained
    from src.embeddings.faiss_validator import FAISSValidator

    validator = FAISSValidator()
    report = validator.validate_all()

    # ── Print human-readable summary ──────────────────────────────────────

    if args.quiet:
        # Just print the summary line
        status = "PASS" if report.all_passed() else "FAIL"
        print(f"FAISS_VALIDATION {status} | {report.passed_count} passed, {report.failed_count} failed")
    else:
        print(report.summary())

        if args.verbose and report.failures:
            print()
            print("  DETAILED FAILURE INFO:")
            for f in report.failures:
                print(f"    ── [{f.name}] ──")
                print(f"    Message: {f.message}")
                if f.detail:
                    print(f"    Detail : {json.dumps(_to_serializable(f.detail), indent=6, ensure_ascii=False)}")
                print()

    # ── Write machine-readable JSON report ────────────────────────────────

    report_data = {
        "validation_timestamp": datetime.now(timezone.utc).isoformat(),
        "overall_status": "PASS" if report.all_passed() else "FAIL",
        "total_checks": len(report.checks),
        "passed": report.passed_count,
        "failed": report.failed_count,
        "checks": [
            {
                "name": c.name,
                "passed": c.passed,
                "message": c.message,
                "detail": _to_serializable(c.detail),
            }
            for c in report.checks
        ],
    }

    report_path = _PROJECT_ROOT / "outputs" / "faiss" / "validation_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as fh:
        json.dump(report_data, fh, indent=2, ensure_ascii=False)

    if not args.quiet:
        print(f"  Machine-readable report saved to: {report_path}")

    # ── Exit with appropriate code ────────────────────────────────────────

    if report.all_passed():
        if not args.quiet:
            print()
            print(f"  {'=' * 66}")
            print(f"    ✅  ALL VALIDATION CHECKS PASSED")
            print(f"    Phase 4 Step 4 complete. Proceed to Step 5 (Retrieval Engine).")
            print(f"  {'=' * 66}")
            print()
        sys.exit(0)
    else:
        if not args.quiet:
            print()
            print(f"  {'=' * 66}")
            print(f"    ❌  VALIDATION FAILED — {report.failed_count} check(s) did not pass")
            print(f"    Do not proceed to Phase 4 Step 5 until all checks pass.")
            print(f"    See details above and in {report_path}")
            print(f"  {'=' * 66}")
            print()
        sys.exit(1)


if __name__ == "__main__":
    # Import numpy here for serialization helper
    import numpy as np  # noqa: F811 — needed by _to_serializable
    main()

