"""In-memory search index for notes.

Design (see DECISIONS.md):
  * Inverted index: word -> sorted array of note ids, kept separately for title
    and body. Ids are stored as `uint32` numpy arrays (4 bytes per entry; a
    Python `set` of ints costs about 50-90).
  * Word index: every 1-, 2- and 3-character substring of every unique word ->
    sorted array of word ids. A query term is resolved to all words containing
    it (start, middle or end) without scanning the vocabulary.
  * Searching works on boolean masks indexed by note id: one mask per term,
    AND-ed together. Cost is roughly constant in the number of matches, which
    keeps very broad queries fast.
  * Ranking uses mask tiers (title hits first); only the newest `offset + limit`
    ids are extracted.
"""

from __future__ import annotations

import re
import threading
from bisect import bisect_left
from collections import OrderedDict
from dataclasses import dataclass

import numpy as np

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_MAX_GRAM = 3
_CACHE_SIZE = 128


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def query_terms(q: str) -> list[str]:
    """Unique query terms, longest first (most selective first)."""
    seen: dict[str, None] = {}
    for t in tokenize(q):
        seen.setdefault(t, None)
    return sorted(seen, key=len, reverse=True)


def _grams(word: str) -> set[str]:
    """All substrings of length 1..3 (what the word index is keyed by)."""
    return {
        word[i : i + n]
        for n in range(1, _MAX_GRAM + 1)
        for i in range(len(word) - n + 1)
    }


class _Postings:
    """Sorted `uint32` ids with amortised O(1) append (ids usually increase)."""

    __slots__ = ("a", "n")

    def __init__(self, ids: list[int] | None = None) -> None:
        if ids:
            self.a = np.array(ids, dtype=np.uint32)
            self.n = len(ids)
        else:
            self.a = np.empty(4, dtype=np.uint32)
            self.n = 0

    def view(self) -> np.ndarray:
        return self.a[: self.n]

    def _ensure_room(self) -> None:
        if self.n == len(self.a):
            grown = np.empty(max(8, self.n + (self.n >> 1)), dtype=np.uint32)
            grown[: self.n] = self.a
            self.a = grown

    def add(self, i: int) -> None:
        n = self.n
        if n == 0 or i > self.a[n - 1]:  # common case: newest id
            self._ensure_room()
            self.a[n] = i
            self.n = n + 1
            return
        pos = int(np.searchsorted(self.a[:n], i))
        if pos < n and self.a[pos] == i:
            return
        self._ensure_room()
        a = self.a
        a[pos + 1 : n + 1] = a[pos:n].copy()
        a[pos] = i
        self.n = n + 1

    def discard(self, i: int) -> bool:
        """Remove `i`; returns True if the list is now empty."""
        n = self.n
        pos = int(np.searchsorted(self.a[:n], i))
        if pos < n and self.a[pos] == i:
            a = self.a
            a[pos : n - 1] = a[pos + 1 : n].copy()
            self.n = n - 1
        return self.n == 0


@dataclass(slots=True)
class _Tiers:
    """Matching note ids as bit-packed masks (cheap to cache), best tier first."""

    size: int  # mask length (max note id + 1 when computed)
    total: int
    strong: np.ndarray | None  # every term is an exact/prefix hit in the title
    n_strong: int
    title: np.ndarray | None  # every term hits the title somewhere (minus strong)
    n_title: int
    matched: np.ndarray | None  # all matches; `rest` = matched minus the above


_EMPTY = _Tiers(0, 0, None, 0, None, 0, None)


class SearchIndex:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._words: list[str] = []
        self._word_id: dict[str, int] = {}
        self._gram_words: dict[str, _Postings] = {}
        self._title_post: dict[int, _Postings] = {}
        self._body_post: dict[int, _Postings] = {}
        # Ascending ids of live notes (ids are only ever appended in increasing
        # order). Used for the empty-query listing and deletes via bisect.
        self._ids: list[int] = []
        self._max_id = 0
        self._cache: OrderedDict[str, _Tiers] = OrderedDict()

    # ------------------------------------------------------------------ build
    def _intern(self, word: str) -> int:
        wid = self._word_id.get(word)
        if wid is not None:
            return wid
        wid = len(self._words)
        self._words.append(word)
        self._word_id[word] = wid
        for g in _grams(word):
            p = self._gram_words.get(g)
            if p is None:
                p = self._gram_words[g] = _Postings()
            p.add(wid)
        return wid

    def _index_text(self, note_id: int, title: str, body: str) -> None:
        for post, text in ((self._title_post, title), (self._body_post, body)):
            for word in set(tokenize(text)):
                wid = self._intern(word)
                p = post.get(wid)
                if p is None:
                    p = post[wid] = _Postings()
                p.add(note_id)

    def _unindex_text(self, note_id: int, title: str, body: str) -> None:
        # Words stay in the vocabulary (cheap); only postings are cleaned up.
        for post, text in ((self._title_post, title), (self._body_post, body)):
            for word in set(tokenize(text)):
                wid = self._word_id.get(word)
                p = post.get(wid) if wid is not None else None
                if p is not None and p.discard(note_id):
                    del post[wid]

    def add(self, note_id: int, title: str, body: str) -> None:
        with self._lock:
            self._index_text(note_id, title, body)
            self._ids.append(note_id)
            self._max_id = max(self._max_id, note_id)
            self._cache.clear()

    def bulk_add(self, notes: list[tuple[int, str, str]]) -> None:
        """Add many notes (ascending ids) building exact-size arrays in one go."""
        with self._lock:
            lists = ({}, {})  # title, body: word id -> ids
            for note_id, title, body in notes:
                for acc, text in zip(lists, (title, body)):
                    for word in set(tokenize(text)):
                        acc.setdefault(self._intern(word), []).append(note_id)
                self._ids.append(note_id)
                self._max_id = max(self._max_id, note_id)
            for post, acc in zip((self._title_post, self._body_post), lists):
                for wid, ids in acc.items():
                    p = post.get(wid)
                    if p is None:
                        post[wid] = _Postings(ids)
                    else:
                        for i in ids:
                            p.add(i)
            self._cache.clear()

    def update(
        self, note_id: int, old: tuple[str, str], new: tuple[str, str]
    ) -> None:
        """Re-index a note atomically so readers never see it half-updated."""
        with self._lock:
            self._unindex_text(note_id, *old)
            self._index_text(note_id, *new)
            self._cache.clear()

    def remove(self, note_id: int, title: str, body: str) -> None:
        with self._lock:
            self._unindex_text(note_id, title, body)
            i = bisect_left(self._ids, note_id)
            if i < len(self._ids) and self._ids[i] == note_id:
                del self._ids[i]
            self._cache.clear()

    # ----------------------------------------------------------------- search
    def _resolve(self, term: str) -> tuple[list[int], list[int]]:
        """Word ids containing `term`: (strong = exact/prefix, all)."""
        words = self._words
        if len(term) < _MAX_GRAM:
            p = self._gram_words.get(term)  # keyed by the term itself
            if p is None:
                return [], []
            allowed = p.view().tolist()
        else:
            posts = [self._gram_words.get(term[i : i + _MAX_GRAM]) for i in range(len(term) - 2)]
            if any(p is None for p in posts):
                return [], []
            posts.sort(key=lambda p: p.n)  # type: ignore[union-attr]
            cand = posts[0].view()  # type: ignore[union-attr]
            for p in posts[1:]:
                cand = np.intersect1d(cand, p.view(), assume_unique=True)  # type: ignore[union-attr]
                if not cand.size:
                    return [], []
            # Trigrams only narrow the candidates; confirm the real substring.
            allowed = [w for w in cand.tolist() if term in words[w]]
        strong = [w for w in allowed if words[w].startswith(term)]
        return strong, allowed

    @staticmethod
    def _mask(post: dict[int, _Postings], word_ids: list[int], size: int) -> np.ndarray:
        m = np.zeros(size, dtype=bool)
        views = [post[w].view() for w in word_ids if w in post]
        if views:
            m[views[0] if len(views) == 1 else np.concatenate(views)] = True
        return m

    def _compute(self, terms: list[str]) -> _Tiers:
        size = self._max_id + 1
        matched = title_any = title_strong = None
        for term in terms:
            strong, allowed = self._resolve(term)
            if not allowed:
                return _EMPTY
            t_any = self._mask(self._title_post, allowed, size)
            hit = t_any | self._mask(self._body_post, allowed, size)
            t_strong = self._mask(self._title_post, strong, size)
            if matched is None:
                matched, title_any, title_strong = hit, t_any, t_strong
            else:
                matched &= hit
                title_any &= t_any
                title_strong &= t_strong
            if not matched.any():
                return _EMPTY
        assert matched is not None and title_any is not None and title_strong is not None
        # title_strong is a subset of title_any, which is a subset of matched.
        title_only = title_any & ~title_strong
        n_strong, n_title = int(title_strong.sum()), int(title_only.sum())
        return _Tiers(
            size=size,
            total=int(matched.sum()),
            strong=np.packbits(title_strong) if n_strong else None,
            n_strong=n_strong,
            title=np.packbits(title_only) if n_title else None,
            n_title=n_title,
            matched=np.packbits(matched),
        )

    @staticmethod
    def _unpack(bits: np.ndarray, size: int) -> np.ndarray:
        return np.unpackbits(bits, count=size).view(bool)

    def _page_ids(self, tiers: _Tiers, need: int) -> list[int]:
        """The newest `need` ids in rank order: strong title, title, the rest."""
        size = tiers.size
        out: list[int] = []
        for kind in range(3):
            remaining = need - len(out)
            if remaining <= 0:
                break
            if kind == 0:
                if not tiers.n_strong:
                    continue
                mask = self._unpack(tiers.strong, size)  # type: ignore[arg-type]
            elif kind == 1:
                if not tiers.n_title:
                    continue
                mask = self._unpack(tiers.title, size)  # type: ignore[arg-type]
            else:
                if tiers.total == tiers.n_strong + tiers.n_title:
                    continue
                mask = self._unpack(tiers.matched, size)  # type: ignore[arg-type]
                if tiers.n_strong:
                    mask &= ~self._unpack(tiers.strong, size)  # type: ignore[arg-type]
                if tiers.n_title:
                    mask &= ~self._unpack(tiers.title, size)  # type: ignore[arg-type]
            ids = np.flatnonzero(mask)
            out.extend(ids[::-1][:remaining].tolist())
        return out

    def search(self, q: str, limit: int, offset: int) -> tuple[int, list[int], list[str]]:
        """Return (total, ordered note ids for the page, terms)."""
        terms = query_terms(q)
        with self._lock:
            if not terms:
                total = len(self._ids)
                hi = max(total - offset, 0)
                lo = max(hi - limit, 0)
                return total, self._ids[lo:hi][::-1], []

            key = " ".join(sorted(terms))
            tiers = self._cache.get(key)
            if tiers is None:
                tiers = self._compute(terms)
                self._cache[key] = tiers
                if len(self._cache) > _CACHE_SIZE:
                    self._cache.popitem(last=False)
            else:
                self._cache.move_to_end(key)

            need = offset + limit
            return tiers.total, self._page_ids(tiers, need)[offset:need], terms
