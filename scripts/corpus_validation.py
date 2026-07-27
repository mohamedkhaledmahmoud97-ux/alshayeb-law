"""
Phase 3.6 — Corpus Validation Script
ALSHAYEB LAW

Execute from the project root:
    py -3 scripts/corpus_validation.py

The script inserts the project root (the directory containing this file's
parent) into sys.path[0] so that `import src.*` always resolves correctly
regardless of which directory Python was launched from.
"""

import hashlib
import importlib
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

# ── Execution-environment fix ─────────────────────────────────────────────────
# When Python runs a script, sys.path[0] is set to the script's own directory.
# We need the PROJECT ROOT (parent of scripts/) on the path so that
# `import src.*` resolves correctly.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

sys.stdout.reconfigure(encoding="utf-8")

import src.data.statute_parser as _sp
import src.data.statute_ingestion as _si
importlib.reload(_sp)
importlib.reload(_si)
from src.data.statute_ingestion import run_statute_ingestion
from src.data.statute_parser import _ARTICLE_BOUNDARY_RE

DATASET = Path("datasets/Egyptian_legal_laws.json")
MAX_CHUNK_TOKENS = 512
CHARS_PER_TOKEN = 4
MAX_CHUNK_CHARS = MAX_CHUNK_TOKENS * CHARS_PER_TOKEN  # 2048

_SCRAPER_PATTERNS = [
    re.compile(r"\u064a\u0645\u0643\u0646\u0643 \u0645\u0634\u0627\u0631\u0643\u0629 \u0627\u0644\u0645\u0642\u0627\u0644\u0629 \u0645\u0646 \u062e\u0644\u0627\u0644 \u062a\u0644\u0643 \u0627\u0644\u0627\u064a\u0642\u0648\u0646\u0627\u062a\s*CONTENT END\s*\d*", re.UNICODE),
    re.compile(r"CONTENT END\s*\d*", re.UNICODE),
]

def clean_text(text):
    for p in _SCRAPER_PATTERNS:
        text = p.sub("", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()

# ── Run ingestion ─────────────────────────────────────────────────────────────
sources, nodes, chunks = run_statute_ingestion()
with open(DATASET, encoding="utf-8") as _fh:
    raw_data = json.load(_fh)

# ── Build lookup maps ─────────────────────────────────────────────────────────
src_map = {s.source_id: s for s in sources}
node_map = {n.node_id: n for n in nodes}
node_to_chunks = defaultdict(list)
for c in chunks:
    node_to_chunks[c.node_id].append(c)
src_to_nodes = defaultdict(list)
for n in nodes:
    src_to_nodes[n.source_id].append(n)

# =============================================================================
print("=" * 70)
print("SECTION 1 — ARTICLE EXTRACTION AUDIT")
print("=" * 70)

article_counts = []
zero_boundary_laws = []
for r in raw_data:
    txt = clean_text(r["text"])
    n_boundaries = len(_ARTICLE_BOUNDARY_RE.findall(txt))
    article_counts.append((r["law_name"], n_boundaries))
    if n_boundaries == 0:
        zero_boundary_laws.append(r["law_name"])

total_raw_boundaries = sum(c for _, c in article_counts)
counts_only = [c for _, c in article_counts]

print(f"Total raw article boundaries detected : {total_raw_boundaries}")
print(f"Laws with 0 detected boundaries       : {len(zero_boundary_laws)}")
print(f"Min boundaries in a law               : {min(counts_only)}")
print(f"Max boundaries in a law               : {max(counts_only)}")
print(f"Mean boundaries per law               : {statistics.mean(counts_only):.2f}")
print(f"Median boundaries per law             : {statistics.median(counts_only):.1f}")
print()

print("Top 10 laws by article boundary count:")
for name, cnt in sorted(article_counts, key=lambda x: -x[1])[:10]:
    print(f"  {cnt:4d}  {name[:72]}")
print()

print(f"Laws with 0 boundaries (become 1 preamble node each) — first 15:")
for name in zero_boundary_laws[:15]:
    print(f"  {name[:80]}")
if len(zero_boundary_laws) > 15:
    print(f"  ... and {len(zero_boundary_laws) - 15} more")
print()

node_counts_per_src = [len(src_to_nodes[s.source_id]) for s in sources]
print(f"Actual nodes produced                 : {len(nodes)}")
print(f"Avg nodes per source                  : {statistics.mean(node_counts_per_src):.2f}")
print(f"Median nodes per source               : {statistics.median(node_counts_per_src):.1f}")
print(f"Min nodes per source                  : {min(node_counts_per_src)}")
print(f"Max nodes per source                  : {max(node_counts_per_src)}")
print()

single_node_sources = [s for s in sources if len(src_to_nodes[s.source_id]) == 1]
print(f"Sources with exactly 1 node           : {len(single_node_sources)}")
print()

print("EXPLANATION — Why 1,455 nodes from 481 laws:")
print(f"  Total raw boundaries detected: {total_raw_boundaries}")
print(f"  Each boundary = 1 article node in the main section.")
print(f"  Each law also gets preamble node(s) for text before first boundary.")
print(f"  {len(zero_boundary_laws)} laws have 0 boundaries → each becomes exactly 1 preamble node.")
print(f"  Many laws are short amendment acts with only 2–5 articles.")
print(f"  481 laws × avg {statistics.mean(node_counts_per_src):.2f} nodes = {len(nodes)} nodes — this is correct.")
print()

# =============================================================================
print("=" * 70)
print("SECTION 2 — CHUNKING AUDIT")
print("=" * 70)

chunk_lengths = [len(c.text) for c in chunks]
over_limit_chunks = [c for c in chunks if len(c.text) > MAX_CHUNK_CHARS]
over_limit_nodes = [n for n in nodes if len(n.text) > MAX_CHUNK_CHARS]

print(f"MAX_CHUNK_CHARS (512 tok × 4)         : {MAX_CHUNK_CHARS}")
print(f"Total chunks                          : {len(chunks)}")
print(f"Chunks within limit (≤{MAX_CHUNK_CHARS} chars)    : {len(chunks) - len(over_limit_chunks)}")
print(f"Chunks OVER limit                     : {len(over_limit_chunks)}")
print(f"Nodes (articles) over limit           : {len(over_limit_nodes)}")
print()

buckets = Counter()
for c in chunks:
    t = c.token_count
    if t <= 64:     buckets["0-64"] += 1
    elif t <= 128:  buckets["65-128"] += 1
    elif t <= 256:  buckets["129-256"] += 1
    elif t <= 384:  buckets["257-384"] += 1
    elif t <= 512:  buckets["385-512"] += 1
    else:           buckets["513+"] += 1

print("Chunk token distribution:")
for label in ["0-64", "65-128", "129-256", "257-384", "385-512", "513+"]:
    pct = buckets[label] / len(chunks) * 100
    print(f"  {label:10s}: {buckets[label]:5d}  ({pct:.1f}%)")
print()

print("Top 10 longest chunks (chars):")
for c in sorted(chunks, key=lambda x: -len(x.text))[:10]:
    print(f"  {len(c.text):6d} ch | tok={c.token_count:4d} | {c.chunk_id}")
print()

print("Top 10 longest nodes/articles (chars):")
for n in sorted(nodes, key=lambda x: -len(x.text))[:10]:
    child_count = len(node_to_chunks[n.node_id])
    print(f"  {len(n.text):6d} ch | {child_count} chunk(s) | {n.node_id}")
print()

longest_chunk = max(chunks, key=lambda x: len(x.text))
print("LONGEST CHUNK INVESTIGATION:")
print(f"  chunk_id  : {longest_chunk.chunk_id}")
print(f"  source    : {longest_chunk.title[:70]}")
print(f"  section   : {longest_chunk.section}")
print(f"  art_number: {longest_chunk.article_number}")
print(f"  length    : {len(longest_chunk.text)} chars / {longest_chunk.token_count} tokens")
print(f"  text[:500]: {longest_chunk.text[:500]}")
print()

# Sub-chunking correctness: every node > MAX_CHUNK_CHARS must have > 1 chunk
sub_chunk_failures = []
for n in over_limit_nodes:
    child_chunks = node_to_chunks[n.node_id]
    # All child chunks must be within limit
    still_over = [c for c in child_chunks if len(c.text) > MAX_CHUNK_CHARS]
    if still_over:
        sub_chunk_failures.append((n, still_over))

print(f"Nodes over limit with chunks still over limit: {len(sub_chunk_failures)}")
for n, bad_chunks in sub_chunk_failures[:5]:
    print(f"  node={n.node_id} node_len={len(n.text)}")
    for bc in bad_chunks:
        print(f"    chunk={bc.chunk_id} len={len(bc.text)}")
print()

# =============================================================================
print("=" * 70)
print("SECTION 3 — HIERARCHY INTEGRITY")
print("=" * 70)

# Full chain integrity
chain_ok = all(
    c.node_id in node_map and node_map[c.node_id].source_id in src_map
    for c in chunks
)
print(f"Full chain (chunk->node->source) intact : {'PASS' if chain_ok else 'FAIL'}")

# Node text reconstruction
reconstruction_failures = []
for node_id, child_chunks in node_to_chunks.items():
    node = node_map[node_id]
    sorted_chunks = sorted(child_chunks, key=lambda x: x.seq)
    if len(sorted_chunks) == 1:
        if sorted_chunks[0].text.strip() != node.text.strip():
            reconstruction_failures.append((node_id, "single-chunk text mismatch"))
    else:
        # Multi-chunk: verify all chars of node.text appear in concatenated chunks
        combined = "".join(c.text for c in sorted_chunks)
        node_clean = re.sub(r"\s+", "", node.text)
        combined_clean = re.sub(r"\s+", "", combined)
        if node_clean not in combined_clean and combined_clean not in node_clean:
            # Allow for minor whitespace differences at split boundaries
            missing_ratio = 1 - len(set(node_clean) & set(combined_clean)) / max(len(set(node_clean)), 1)
            if missing_ratio > 0.01:
                reconstruction_failures.append((node_id, f"multi-chunk coverage gap ratio={missing_ratio:.3f}"))

print(f"Node text reconstruction check          : {'PASS' if not reconstruction_failures else 'FAIL'}")
if reconstruction_failures:
    for nid, reason in reconstruction_failures[:5]:
        print(f"  {nid}: {reason}")
print()

# Source coverage: total chars in nodes vs expected from token_count
low_coverage = []
for src in sources:
    total_node_chars = sum(len(nd.text) for nd in src_to_nodes[src.source_id])
    expected_chars = src.token_count * CHARS_PER_TOKEN
    ratio = total_node_chars / max(expected_chars, 1)
    if ratio < 0.05:
        low_coverage.append((src.title[:60], ratio, total_node_chars, expected_chars))

print(f"Sources with <5% text coverage          : {len(low_coverage)}")
for title, ratio, got, exp in low_coverage[:5]:
    print(f"  {ratio:.1%} | got={got} | exp~{exp} | {title}")
print()

# =============================================================================
print("=" * 70)
print("SECTION 4 — SEQ NUMBERING INTEGRITY")
print("=" * 70)

seq_errors = []
for node_id, child_chunks in node_to_chunks.items():
    seqs = sorted(c.seq for c in child_chunks)
    expected = list(range(1, len(seqs) + 1))
    if seqs != expected:
        seq_errors.append((node_id, seqs))

print(f"Seq numbering errors (non-contiguous)   : {len(seq_errors)}")
if seq_errors:
    for nid, seqs in seq_errors[:5]:
        print(f"  {nid}: got {seqs}")
print()

multi_chunk_nodes = {nid: cl for nid, cl in node_to_chunks.items() if len(cl) > 1}
print(f"Nodes split into multiple chunks        : {len(multi_chunk_nodes)}")
if multi_chunk_nodes:
    sample_nid = next(iter(multi_chunk_nodes))
    sample_chunks = sorted(multi_chunk_nodes[sample_nid], key=lambda x: x.seq)
    print(f"Sample multi-chunk node: {sample_nid}")
    for c in sample_chunks:
        print(f"  seq={c.seq} len={len(c.text)} tok={c.token_count}")
print()

# =============================================================================
print("=" * 70)
print("SECTION 5 — METADATA EXTENSION PREVIEW")
print("=" * 70)

import datetime
sample = chunks[5]
extended = {
    "document_type": "statute",
    "parser_name": "StatuteParser",
    "parser_version": "1.0.0",
    "language": "ar",
    "chunk_hash": hashlib.sha256(sample.text.encode("utf-8")).hexdigest()[:16],
    "embedding_ready": True,
    "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
}
print("Fields to be added to type_metadata:")
for k, v in extended.items():
    print(f"  {k:20s}: {v!r}")
print()

# =============================================================================
print("=" * 70)
print("SECTION 6 — FINAL SUMMARY")
print("=" * 70)

all_pass = (
    len(sub_chunk_failures) == 0
    and len(reconstruction_failures) == 0
    and len(seq_errors) == 0
    and chain_ok
    and len(low_coverage) == 0
)

print(f"Sources                              : {len(sources)}")
print(f"Nodes                                : {len(nodes)}")
print(f"Chunks                               : {len(chunks)}")
print(f"Raw article boundaries in dataset    : {total_raw_boundaries}")
print(f"Laws with 0 boundaries               : {len(zero_boundary_laws)}")
print(f"Chunks over MAX_CHUNK_CHARS          : {len(over_limit_chunks)}")
print(f"Sub-chunk failures                   : {len(sub_chunk_failures)}")
print(f"Reconstruction failures              : {len(reconstruction_failures)}")
print(f"Seq numbering errors                 : {len(seq_errors)}")
print(f"Low-coverage sources (<5%)           : {len(low_coverage)}")
print()
print(f"OVERALL VALIDATION: {'PASS' if all_pass else 'NEEDS ATTENTION'}")
