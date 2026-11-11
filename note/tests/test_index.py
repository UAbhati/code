import random

import pytest

from index import SearchIndex, query_terms, tokenize
from store import NoteStore, make_snippet, matched_in


def reference(store: NoteStore, q: str) -> set[int]:
    """Brute force: a note matches if every term is a substring of some word."""
    terms = query_terms(q)
    out = set()
    for n in store._notes[1:]:
        if n is None:
            continue
        words = set(tokenize(n.title)) | set(tokenize(n.body))
        if terms and all(any(t in w for w in words) for t in terms):
            out.add(n.id)
    return out


def all_ids(store: NoteStore, q: str) -> list[int]:
    total, ids, _ = store.index.search(q, limit=100_000, offset=0)
    assert total == len(ids)
    return ids


@pytest.fixture()
def store():
    s = NoteStore()
    s.seed(1500, rng_seed=7)
    return s


QUERIES = ["m", "me", "meet", "eeti", "kube clust", "ing", "on", "zzzz", "Notes on", "a b c"]


@pytest.mark.parametrize("q", QUERIES)
def test_matches_brute_force(store, q):
    assert set(all_ids(store, q)) == reference(store, q)


def test_matches_start_middle_and_end_of_word():
    s = NoteStore()
    s.create("meeting notes", "")
    for q in ("meet", "eeti", "ting", "g"):
        assert len(all_ids(s, q)) == 1, q
    assert all_ids(s, "xyz") == []


def test_all_terms_must_match():
    s = NoteStore()
    a = s.create("alpha beta", "")
    s.create("alpha gamma", "")
    assert all_ids(s, "alpha beta") == [a.id]
    assert all_ids(s, "beta alpha") == [a.id]


def test_case_insensitive():
    s = NoteStore()
    s.create("Quarterly BUDGET", "")
    assert len(all_ids(s, "budget")) == len(all_ids(s, "BuDgEt")) == 1


def test_title_matches_rank_before_body_matches():
    s = NoteStore()
    title = s.create("zebra facts", "")
    body_only = s.create("something else", "mention of zebra here")  # newer
    assert all_ids(s, "zebra") == [title.id, body_only.id]


def test_exact_prefix_title_beats_middle_title():
    s = NoteStore()
    prefix = s.create("zebra", "")
    middle = s.create("subzebra", "")  # newer, but only a middle match
    assert all_ids(s, "zebra") == [prefix.id, middle.id]


def test_newest_first_within_tier():
    s = NoteStore()
    ids = [s.create(f"zebra {i}", "").id for i in range(5)]
    assert all_ids(s, "zebra") == ids[::-1]


def test_empty_query_lists_newest_first_with_pagination(store):
    total, ids, terms = store.index.search("", limit=5, offset=0)
    assert (total, ids, terms) == (1500, [1500, 1499, 1498, 1497, 1496], [])
    _, page2, _ = store.index.search("", limit=5, offset=5)
    assert page2 == [1495, 1494, 1493, 1492, 1491]
    _, tail, _ = store.index.search("", limit=5, offset=1498)
    assert tail == [2, 1]
    _, beyond, _ = store.index.search("", limit=5, offset=5000)
    assert beyond == []


@pytest.mark.parametrize("q", ["m", "meet", "ing"])
def test_pagination_is_consistent(store, q):
    everything = all_ids(store, q)
    paged: list[int] = []
    offset = 0
    while True:
        total, ids, _ = store.index.search(q, limit=37, offset=offset)
        assert total == len(everything)
        if not ids:
            break
        paged += ids
        offset += 37
    assert paged == everything


def test_create_is_searchable_immediately(store):
    n = store.create("Zebrafish plan", "xylophone")
    assert all_ids(store, "ebraf")[0] == n.id
    assert all_ids(store, "xylo") == [n.id]
    assert store.index.search("", 1, 0)[1] == [n.id]


def test_update_reindexes(store):
    n = store.create("Zebrafish plan", "xylophone")
    all_ids(store, "xylo")  # warm the cache so we know it is invalidated
    store.update(n.id, "Walrus plan", "harmonica")
    assert all_ids(store, "xylo") == []
    assert all_ids(store, "zebra") == []
    assert all_ids(store, "harmon") == [n.id]
    assert all_ids(store, "walr") == [n.id]
    assert store.get(n.id).updated_at is not None
    assert store.get(n.id).title == "Walrus plan"


def test_delete_removes_everywhere(store):
    n = store.create("Zebrafish plan", "xylophone")
    all_ids(store, "xylo")
    before = len(store)
    assert store.delete(n.id) is True
    assert len(store) == before - 1
    assert all_ids(store, "xylo") == []
    assert store.get(n.id) is None
    assert n.id not in store.index.search("", 10_000, 0)[1]
    assert store.delete(n.id) is False
    assert store.update(n.id, "x", "y") is None


def test_random_mutations_match_brute_force(store):
    rng = random.Random(1)
    live = [n.id for n in store._notes[1:] if n]
    for step in range(150):
        op = rng.choice(["create", "update", "delete"])
        if op == "create":
            live.append(store.create(f"fresh {rng.choice(['alpha', 'beta'])} {step}", "body gamma").id)
        elif op == "update" and live:
            store.update(rng.choice(live), f"edited delta {step}", "new epsilon")
        elif op == "delete" and live:
            store.delete(live.pop(rng.randrange(len(live))))
    for q in QUERIES + ["alpha", "delta", "epsilon", "gamma", "fresh beta"]:
        assert set(all_ids(store, q)) == reference(store, q), q
    assert len(store) == len(live)
    assert sorted(store.index.search("", 10_000, 0)[1]) == sorted(live)


def test_cache_does_not_serve_stale_results():
    s = NoteStore()
    assert all_ids(s, "zebra") == []
    n = s.create("zebra", "")
    assert all_ids(s, "zebra") == [n.id]
    s.delete(n.id)
    assert all_ids(s, "zebra") == []


def test_snippet_centres_on_match_and_matched_in():
    s = NoteStore()
    body = " ".join(f"word{i}" for i in range(80)) + " needle " + " ".join(f"tail{i}" for i in range(80))
    n = s.create("A title", body)
    snip = make_snippet(n, ["needle"])
    assert "needle" in snip and snip.startswith("…") and snip.endswith("…")
    assert make_snippet(n, []).startswith("word0")
    assert matched_in(n, ["needle"]) == ["body"]
    assert matched_in(n, ["title"]) == ["title"]
    assert matched_in(n, ["a"]) == ["title", "body"]  # "a" is in both


def test_tokenizer_and_term_order():
    assert tokenize("Hello, World_42!") == ["hello", "world", "42"]
    assert query_terms("b bb b") == ["bb", "b"]
