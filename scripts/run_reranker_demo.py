"""
CLI demo entry point for the ALSHAYEB LAW Reranker.

Demonstrates the cross-encoder reranker using test queries and dummy
candidates.  Meant for manual verification that the reranker loads,
scores, and ranks correctly.

Usage:
    py -3 scripts/run_reranker_demo.py [options]

Options:
    --device STR        Force a specific device: "cpu" or "cuda".
                        Default: auto-select (CUDA if available, else CPU).
    --alpha FLOAT       Weight for combining scores (default: 0.7).
    --help              Show this message and exit.

Execute from the project root:
    py -3 scripts/run_reranker_demo.py

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
# script is executed directly (e.g. py -3 scripts/run_reranker_demo.py).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ── Logging configuration ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("run_reranker_demo")


# ── Test data ─────────────────────────────────────────────────────────────────

_DEMO_QUERY = "ما هي شروط عقد الإيجار في القانون المدني المصري؟"

_DEMO_CANDIDATES = [
    {
        "chunk_id": "statute:law-131-1948:main:art558:seq1",
        "text": "الإيجار عقد يلتزم المؤجر بمقتضاه أن يمكن المستأجر من الانتفاع بالشيء المؤجر مدة معينة لقاء أجر معلوم. وتنطبق على عقد الإيجار القواعد العامة المقررة للالتزامات والعقود.",
        "title": "القانون المدني المصري – القانون رقم 131 لسنة 1948",
        "law_number": "131",
        "law_year": "1948",
        "law_slug": "law-131-1948",
        "scope_flag": "statute",
        "section": "main",
        "article_number": 558,
        "seq": 1,
        "source_id": "statute:law-131-1948",
        "node_id": "statute:law-131-1948:main:art558",
        "_retrieval_score": 0.85,
    },
    {
        "chunk_id": "statute:law-131-1948:main:art559:seq1",
        "text": "يجب أن يكون الأجر معيناً تعييناً نافياً للجهالة الفاحشة، وإلا كان العقد باطلاً. ويجوز أن يكون الأجر نقداً أو عيناً أو منفعة.",
        "title": "القانون المدني المصري – القانون رقم 131 لسنة 1948",
        "law_number": "131",
        "law_year": "1948",
        "law_slug": "law-131-1948",
        "scope_flag": "statute",
        "section": "main",
        "article_number": 559,
        "seq": 1,
        "source_id": "statute:law-131-1948",
        "node_id": "statute:law-131-1948:main:art559",
        "_retrieval_score": 0.82,
    },
    {
        "chunk_id": "statute:law-131-1948:main:art560:seq1",
        "text": "يلتزم المؤجر بأن يسلم العين المؤجرة للمستأجر في الحالة التي تمكنه من الانتفاع بها انتفاعاً طبيعياً، وبأن يقوم بجميع الترميمات الضرورية لصيانة العين أثناء المدة، وبأن يضمن عدم تعرض الغير للانتفاع.",
        "title": "القانون المدني المصري – القانون رقم 131 لسنة 1948",
        "law_number": "131",
        "law_year": "1948",
        "law_slug": "law-131-1948",
        "scope_flag": "statute",
        "section": "main",
        "article_number": 560,
        "seq": 1,
        "source_id": "statute:law-131-1948",
        "node_id": "statute:law-131-1948:main:art560",
        "_retrieval_score": 0.78,
    },
    {
        "chunk_id": "statute:law-131-1948:main:art100:seq1",
        "text": "الأهلية للتعاقد تعتبر مناط التمييز، وكل شخص بلغ سن الرشد المحدد في القانون يكون أهلاً لإجراء التصرفات القانونية ما لم يقرر القانون غير ذلك.",
        "title": "القانون المدني المصري – القانون رقم 131 لسنة 1948",
        "law_number": "131",
        "law_year": "1948",
        "law_slug": "law-131-1948",
        "scope_flag": "statute",
        "section": "main",
        "article_number": 100,
        "seq": 1,
        "source_id": "statute:law-131-1948",
        "node_id": "statute:law-131-1948:main:art100",
        "_retrieval_score": 0.65,
    },
    {
        "chunk_id": "statute:law-174-2025:main:art1:seq1",
        "text": "تسري أحكام هذا القانون على الإجراءات الجنائية أمام المحاكم الجنائية. ويعمل به بعد ثلاثين يوماً من تاريخ نشره في الجريدة الرسمية.",
        "title": "قانون الاجراءات الجنائية – قانون رقم 174 لسنة 2025",
        "law_number": "174",
        "law_year": "2025",
        "law_slug": "law-174-2025",
        "scope_flag": "statute",
        "section": "main",
        "article_number": 1,
        "seq": 1,
        "source_id": "statute:law-174-2025",
        "node_id": "statute:law-174-2025:main:art1",
        "_retrieval_score": 0.72,
    },
]


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "ALSHAYEB LAW — Reranker Demo\n"
            "Demonstrates cross-encoder reranking with test query and candidates."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--device",
        type=str,
        default=None,
        metavar="STR",
        help="Force device: 'cpu' or 'cuda'. Default: auto-select.",
    )
    p.add_argument(
        "--alpha",
        type=float,
        default=0.7,
        metavar="FLOAT",
        help="Weight for combining original and reranker scores (default: 0.7).",
    )
    return p


def main() -> None:
    args = _build_parser().parse_args()

    logger.info("Starting ALSHAYEB LAW Reranker Demo")
    logger.info("  device : %s", args.device or "auto")
    logger.info("  alpha  : %.2f", args.alpha)

    # ── Import here (after sys.path fix) so the script is self-contained ──
    from src.reranking.reranker import Reranker

    reranker = Reranker(
        device=args.device,
        alpha=args.alpha,
    )

    logger.info("Reranker model: %s", reranker.model_name)

    # ── Run reranking ─────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print("  RERANKER DEMO")
    print("=" * 70)
    print(f"  Query: {_DEMO_QUERY}")
    print(f"  Candidates: {len(_DEMO_CANDIDATES)}")
    print(f"  Alpha: {args.alpha}")
    print()

    results = reranker.rerank(
        query=_DEMO_QUERY,
        candidates=_DEMO_CANDIDATES,
        top_k=5,
    )

    # ── Display results ───────────────────────────────────────────────────
    print(f"  {'Rank':<5s} {'Article':<25s} {'Original':<10s} {'Reranker':<10s} {'Combined':<10s} {'Title':<40s}")
    print(f"  {'-'*5} {'-'*25} {'-'*10} {'-'*10} {'-'*10} {'-'*40}")
    for r in results:
        article_str = f"art.{r.article_number}" if r.article_number else "preamble"
        title_short = r.title[:38] + ".." if len(r.title) > 38 else r.title
        print(
            f"  {r.rank:<5d} {article_str:<25s} "
            f"{r.original_score:<10.4f} {r.reranker_score:<10.4f} "
            f"{r.combined_score:<10.4f} {title_short:<40s}"
        )

    print()
    print("  Reranker demo completed successfully.")
    print()


if __name__ == "__main__":
    main()
