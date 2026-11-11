"""Search benchmark: indexed search vs. a naive scan, plus JSON encoding cost.

Usage: .venv/bin/python bench.py [note_count ...]   (default: 20000 100000)
"""

from __future__ import annotations

import json
import statistics
import sys
import time

import orjson

from index import query_terms
from store import NoteStore, make_snippet, matched_in

QUERIES = [
    "m", "me", "meet", "eeti", "kube clust", "pipeline regress", "ing",
    "Notes on", "dependency upgrade security", "zzzz",
]
LIMIT = 30


def naive_search(texts: list[tuple[str, str]], q: str) -> int:
    """Plain substring scan over every note (what we would do without an index).

    `texts` holds pre-lowercased (title, body) pairs, so the baseline is not
    penalised for lowercasing on every query.
    """
    terms = query_terms(q)
    n = 0
    for title_lc, body_lc in texts:
        if all(t in title_lc or t in body_lc for t in terms):
            n += 1
    return n


def timed(fn, repeat: int) -> list[float]:
    out = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        fn()
        out.append((time.perf_counter() - t0) * 1000)
    return out


def pct(values: list[float], p: float) -> float:
    s = sorted(values)
    return s[min(int(len(s) * p), len(s) - 1)]


def run(count: int) -> None:
    store = NoteStore()
    t0 = time.perf_counter()
    store.seed(count)
    build = time.perf_counter() - t0
    idx = store.index
    texts = [(n.title.lower(), n.body.lower()) for n in store._notes[1:] if n]
    print(f"\n=== {count:,} notes | build+index {build:.2f}s | vocab {len(idx._words):,} words ===")
    print(f"{'query':<30}{'matches':>9}{'cold ms':>10}{'warm ms':>10}{'page ms':>10}{'naive ms':>10}{'speedup':>9}")

    cold_all, warm_all = [], []
    for q in QUERIES:
        def cold():
            idx._cache.clear()
            idx.search(q, LIMIT, 0)

        def warm():
            idx.search(q, LIMIT, 0)

        def page():  # what the endpoint does: search + build items for one page
            idx._cache.clear()
            _, ids, terms = idx.search(q, LIMIT, 0)
            for i in ids:
                n = store.get(i)
                make_snippet(n, terms)
                matched_in(n, terms)

        total = idx.search(q, LIMIT, 0)[0]
        c = timed(cold, 30)
        w = timed(warm, 30)
        p = timed(page, 30)
        nv = timed(lambda: naive_search(texts, q), 3)
        cold_all += c
        warm_all += w
        print(f"{q:<30}{total:>9,}{statistics.median(c):>10.2f}{statistics.median(w):>10.3f}"
              f"{statistics.median(p):>10.2f}{statistics.median(nv):>10.1f}"
              f"{statistics.median(nv) / max(statistics.median(c), 1e-6):>8.0f}x")

    print(f"cold (uncached) p50 {pct(cold_all, .5):.2f} ms | p95 {pct(cold_all, .95):.2f} ms | "
          f"warm p95 {pct(warm_all, .95):.3f} ms")

    # JSON encoding of one full page: orjson vs stdlib.
    _, ids, terms = idx.search("", LIMIT, 0)
    items = [{"id": n.id, "title": n.title, "snippet": make_snippet(n, terms),
              "matched_in": [], "created_at": n.created_at.isoformat(), "updated_at": None}
             for n in map(store.get, ids)]
    payload = {"total": count, "items": items, "terms": [], "took_ms": 0.1}
    o = timed(lambda: orjson.dumps(payload), 500)
    j = timed(lambda: json.dumps(payload), 500)
    print(f"encode {LIMIT} items: orjson {statistics.median(o) * 1000:.0f} us | "
          f"json {statistics.median(j) * 1000:.0f} us")


def memory(count: int) -> None:
    """Memory held by the store + index (tracemalloc, so the build is slower)."""
    import gc
    import tracemalloc

    tracemalloc.start()
    store = NoteStore()
    store.seed(count)
    gc.collect()
    total = tracemalloc.get_traced_memory()[0]
    tracemalloc.stop()
    text = sum(len(n.title) + len(n.body) for n in store._notes[1:] if n)
    print(f"\n=== memory at {count:,} notes: {total / 1e6:.0f} MB total "
          f"({total / count:.0f} bytes/note) | raw text {text / 1e6:.0f} MB chars | "
          f"vocab {len(store.index._words):,} ===")


if __name__ == "__main__":
    args = sys.argv[1:]
    mem_only = "--mem" in args
    counts = [int(a) for a in args if a.isdigit()] or [20_000, 100_000]
    for c in counts:
        memory(c) if mem_only else run(c)
