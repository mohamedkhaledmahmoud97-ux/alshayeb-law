"""
Phase 3.6 — Diagnostic: Article boundary miss investigation + sub-chunk failures
"""
import sys
import json
import re
from pathlib import Path
from collections import Counter

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

sys.stdout.reconfigure(encoding="utf-8")

DATASET = _PROJECT_ROOT / "datasets" / "Egyptian_legal_laws.json"
raw_data = json.load(open(DATASET, encoding="utf-8"))

_SCRAPER_PATTERNS = [
    re.compile(r"يمكنك مشاركة المقالة من خلال تلك الايقونات\s*CONTENT END\s*\d*", re.UNICODE),
    re.compile(r"CONTENT END\s*\d*", re.UNICODE),
]

def clean_text(text):
    for p in _SCRAPER_PATTERNS:
        text = p.sub("", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()

# Current regex (same as parser)
_CURRENT_RE = re.compile(
    r"(?:^|\n)\s*"
    r"(?:"
    r"\(المادة\s+[\w\u0600-\u06FF]+\)"
    r"|مادة\s*\(\s*\d+\s*\)"
    r"|مادة\s+\d+\s*[-\u2013]"
    r"|مادة\s*\(\s*[\u0600-\u06FF]+\s*\)"
    r")",
    re.UNICODE | re.MULTILINE,
)

# ── Investigate what article formats exist in zero-boundary laws ──────────────
print("=" * 70)
print("DIAGNOSTIC 1 — What article formats appear in zero-boundary laws?")
print("=" * 70)

# Broader patterns to detect any مادة occurrence
_ANY_MADA = re.compile(r"مادة", re.UNICODE)
_MADA_CONTEXT = re.compile(r"مادة.{0,60}", re.UNICODE)

zero_boundary_laws = []
for r in raw_data:
    txt = clean_text(r["text"])
    if not _CURRENT_RE.search(txt):
        zero_boundary_laws.append((r["law_name"], txt))

print(f"Zero-boundary laws: {len(zero_boundary_laws)}")
print()

# Sample 10 zero-boundary laws that DO contain مادة
has_mada = [(name, txt) for name, txt in zero_boundary_laws if _ANY_MADA.search(txt)]
no_mada  = [(name, txt) for name, txt in zero_boundary_laws if not _ANY_MADA.search(txt)]

print(f"Zero-boundary laws that contain 'مادة': {len(has_mada)}")
print(f"Zero-boundary laws with NO 'مادة' at all: {len(no_mada)}")
print()

print("Sample article formats from zero-boundary laws (first 20 مادة occurrences):")
seen_formats = []
for name, txt in has_mada[:30]:
    for m in _MADA_CONTEXT.finditer(txt):
        ctx = m.group().strip()[:80]
        seen_formats.append(ctx)
        if len(seen_formats) >= 20:
            break
    if len(seen_formats) >= 20:
        break

for f in seen_formats:
    print(f"  {f!r}")
print()

# ── Collect all unique مادة patterns across the entire corpus ─────────────────
print("=" * 70)
print("DIAGNOSTIC 2 — All مادة patterns in corpus (frequency)")
print("=" * 70)

# Extract the first ~30 chars after مادة to see all formats
_MADA_FULL = re.compile(r"مادة.{0,40}", re.UNICODE)
pattern_counter = Counter()
for r in raw_data:
    txt = clean_text(r["text"])
    for m in _MADA_FULL.finditer(txt):
        snippet = m.group().strip()[:50]
        pattern_counter[snippet] += 1

print("Top 40 مادة patterns by frequency:")
for pat, cnt in pattern_counter.most_common(40):
    print(f"  {cnt:5d}  {pat!r}")
print()

# ── Identify the missing pattern ──────────────────────────────────────────────
print("=" * 70)
print("DIAGNOSTIC 3 — Patterns NOT matched by current regex")
print("=" * 70)

unmatched = Counter()
for r in raw_data:
    txt = clean_text(r["text"])
    for m in _MADA_FULL.finditer(txt):
        snippet = m.group().strip()
        # Check if this مادة occurrence is at a line start (as the regex requires)
        pos = m.start()
        # Get char before this position
        before = txt[max(0, pos-3):pos]
        at_line_start = (pos == 0 or "\n" in before)
        if at_line_start and not _CURRENT_RE.search("\n" + snippet):
            unmatched[snippet[:60]] += 1

print("Top 30 unmatched مادة patterns (at line start, not caught by current regex):")
for pat, cnt in unmatched.most_common(30):
    print(f"  {cnt:5d}  {pat!r}")
print()

# ── Sub-chunk failure investigation ──────────────────────────────────────────
print("=" * 70)
print("DIAGNOSTIC 4 — Sub-chunk failure root cause")
print("=" * 70)

import importlib
import src.data.statute_parser as _sp
import src.data.statute_ingestion as _si
importlib.reload(_sp)
importlib.reload(_si)
from src.data.statute_ingestion import run_statute_ingestion
from collections import defaultdict

sources, nodes, chunks = run_statute_ingestion()
node_to_chunks = defaultdict(list)
for c in chunks:
    node_to_chunks[c.node_id].append(c)

MAX_CHUNK_CHARS = 512 * 4

over_limit_nodes = [n for n in nodes if len(n.text) > MAX_CHUNK_CHARS]
sub_chunk_failures = []
for n in over_limit_nodes:
    child_chunks = node_to_chunks[n.node_id]
    still_over = [c for c in child_chunks if len(c.text) > MAX_CHUNK_CHARS]
    if still_over:
        sub_chunk_failures.append((n, still_over))

print(f"Sub-chunk failures: {len(sub_chunk_failures)}")
for n, bad in sub_chunk_failures:
    print(f"\n  node_id  : {n.node_id}")
    print(f"  node_len : {len(n.text)} chars")
    print(f"  bad chunks: {len(bad)}")
    for bc in bad:
        print(f"    chunk_id={bc.chunk_id} len={len(bc.text)}")
        # Show what the paragraph structure looks like
        paras = [p.strip() for p in re.split(r"\n\n+", n.text) if p.strip()]
        long_paras = [p for p in paras if len(p) > MAX_CHUNK_CHARS]
        print(f"    paragraphs in node: {len(paras)}, paragraphs > limit: {len(long_paras)}")
        if long_paras:
            print(f"    longest para: {len(long_paras[0])} chars, preview: {long_paras[0][:200]!r}")
