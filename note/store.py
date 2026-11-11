"""In-memory note store with dummy data. Ids are 1..N, so newest = highest id."""

from __future__ import annotations

import os
import random
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from index import SearchIndex

SNIPPET_LEN = 140

_WORDS = """
meeting agenda project roadmap budget invoice client proposal deadline sprint
backlog release deploy staging production database migration schema index query
cache latency throughput monitoring alert incident postmortem review feedback
design prototype wireframe mockup typography accessibility onboarding tutorial
documentation readme changelog testing integration regression benchmark profile
refactor cleanup dependency upgrade security audit permission encryption token
authentication session payment subscription pricing discount marketing campaign
newsletter analytics dashboard metric funnel retention growth hiring interview
candidate resume salary vacation holiday travel flight hotel itinerary passport
grocery recipe dinner breakfast coffee workout running yoga meditation sleep
reading book chapter summary podcast lecture course exercise homework research
paper experiment dataset model training evaluation inference pipeline warehouse
kubernetes docker container cluster network firewall gateway proxy balancer
frontend backend mobile desktop browser server client endpoint payload schema
idea brainstorm sketch outline draft revision publish archive reminder todo
birthday gift party family friend neighbor weekend morning evening tonight
""".split()


def _make_rare_words(count: int) -> list[str]:
    """Pronounceable pseudo-words, so the vocabulary is realistically large.

    Real notes contain names, ids and jargon, not just ~160 common words. A
    tiny vocabulary hides the cost of storing and searching words.
    """
    rng = random.Random(123)
    consonants, vowels = "bcdfghjklmnprstvwz", "aeiou"
    out: set[str] = set()
    while len(out) < count:
        syllables = rng.randint(2, 4)
        word = "".join(rng.choice(consonants) + rng.choice(vowels) for _ in range(syllables))
        out.add(word + rng.choice(["", "n", "r", "s", "x"]))
    return sorted(out)


_RARE_WORDS = _make_rare_words(30_000)
_RARE_SHARE = 0.25  # fraction of words drawn from the rare vocabulary

_TITLE_STARTS = [
    "Notes on", "Ideas for", "Plan for", "Todo:", "Follow up on", "Summary of",
    "Questions about", "Draft:", "Checklist for", "Thoughts on",
]


def _pick_words(rng: random.Random, k: int) -> list[str]:
    return [
        rng.choice(_RARE_WORDS) if rng.random() < _RARE_SHARE else rng.choice(_WORDS)
        for _ in range(k)
    ]


@dataclass(slots=True)
class Note:
    id: int
    title: str
    body: str
    created_at: datetime
    updated_at: datetime | None = None


def _make_note(note_id: int, title: str, body: str, created_at: datetime) -> Note:
    # No lowercase copies are stored (that would double the text memory); the
    # few notes on a page are lowercased on demand in make_snippet/matched_in.
    return Note(note_id, title, body, created_at)


class NoteStore:
    def __init__(self) -> None:
        # Index 0 unused, ids start at 1. Deleted notes leave a None tombstone so
        # ids stay stable and `get` stays O(1).
        self._notes: list[Note | None] = [None]
        self._count = 0
        self._lock = threading.Lock()
        self.index = SearchIndex()

    def __len__(self) -> int:
        return self._count

    def get(self, note_id: int) -> Note | None:
        if 1 <= note_id < len(self._notes):
            return self._notes[note_id]
        return None

    def create(self, title: str, body: str) -> Note:
        with self._lock:
            note = _make_note(
                len(self._notes), title, body, datetime.now(timezone.utc)
            )
            self._notes.append(note)
            self._count += 1
            self.index.add(note.id, note.title, note.body)
        return note

    def update(self, note_id: int, title: str, body: str) -> Note | None:
        with self._lock:
            note = self.get(note_id)
            if note is None:
                return None
            old = (note.title, note.body)
            note.title, note.body = title, body
            note.updated_at = datetime.now(timezone.utc)
            self.index.update(note_id, old, (title, body))
            return note

    def delete(self, note_id: int) -> bool:
        with self._lock:
            note = self.get(note_id)
            if note is None:
                return False
            self._notes[note_id] = None
            self._count -= 1
            self.index.remove(note_id, note.title, note.body)
            return True

    def seed(self, count: int, rng_seed: int = 42) -> None:
        rng = random.Random(rng_seed)
        now = datetime.now(timezone.utc)
        batch: list[tuple[int, str, str]] = []
        with self._lock:
            for i in range(count):
                title = f"{rng.choice(_TITLE_STARTS)} " + " ".join(
                    _pick_words(rng, rng.randint(2, 4))
                )
                body = " ".join(_pick_words(rng, rng.randint(15, 60)))
                # Older notes get older timestamps; id order == time order.
                created = now - timedelta(minutes=(count - i) * 7)
                note = _make_note(len(self._notes), title, body, created)
                self._notes.append(note)
                self._count += 1
                batch.append((note.id, title, body))
            self.index.bulk_add(batch)


def _lower(text: str) -> str:
    """Lowercase for matching; positions must line up with the original text."""
    lowered = text.lower()
    return lowered if len(lowered) == len(text) else text


def make_snippet(note: Note, terms: list[str]) -> str:
    """Body excerpt centred on the earliest match (or the body start)."""
    body, body_lc = note.body, _lower(note.body)
    pos = -1
    for t in terms:
        p = body_lc.find(t)
        if p != -1 and (pos == -1 or p < pos):
            pos = p
    if pos == -1:
        pos = 0
        start = 0
    else:
        start = max(pos - SNIPPET_LEN // 3, 0)
        # Start on a word boundary so we do not cut a word in half.
        if start > 0:
            space = body.find(" ", start)
            if space != -1 and space < pos:
                start = space + 1
    end = min(start + SNIPPET_LEN, len(body))
    text = body[start:end].strip()
    return ("…" if start > 0 else "") + text + ("…" if end < len(body) else "")


def matched_in(note: Note, terms: list[str]) -> list[str]:
    where = []
    title_lc, body_lc = _lower(note.title), _lower(note.body)
    if any(t in title_lc for t in terms):
        where.append("title")
    if any(t in body_lc for t in terms):
        where.append("body")
    return where


def build_store() -> NoteStore:
    store = NoteStore()
    store.seed(int(os.environ.get("NOTES_SEED_COUNT", "20000")))
    return store
