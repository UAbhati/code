# Decisions log

Running record of choices made while building the notes app. Newest entries go at the bottom of each section.

## Scope and stack
- **Python + FastAPI, no database.** Notes live in memory and are seeded with dummy data (default 20,000, override with `NOTES_SEED_COUNT`). Data is lost on restart by design.
- **Frontend: one static HTML file with vanilla JS**, served by FastAPI. No build step, to fit the 30-minute budget.
- **Search runs on the server** (`GET /api/notes?q=`), so it stays fast regardless of how many notes the browser would otherwise have to hold.

## Search
- **Inverted index (word -> note ids)**, separate for title and body. Gives sub-millisecond lookups and lets us tell title matches from body matches.
- **Trigram index over the vocabulary (unique words), not over note text.** Needed to match the middle of words (`eeti` finds `meeting`). The vocabulary is tiny compared to the note text, so memory and build time stay low.
- **Terms of 1-2 characters** have no trigrams, so we scan the vocabulary directly. Still cheap because the vocabulary is small.
- **Multiple terms are AND-ed.** Each term can match anywhere in a word. A query like `team meet` is not treated as a literal phrase (known limitation).
- **Ranking uses set-based tiers, not per-note scoring:** (1) every term is an exact or prefix hit in the title, (2) every term hits the title somewhere, (3) everything else. Inside a tier, newest first (higher id). Only the top `offset + limit` ids are extracted per tier with `heapq.nlargest`.
- **Tokenizer:** lowercase, `[a-z0-9]+`. Non-ASCII letters are not indexed yet (known limitation).
- **LRU cache (256 entries)** on the normalized query, storing the tier sets. Cleared on every create. Terms are sorted for the key, so `a b` and `b a` share an entry.
- **Skipped for now:** reusing the previous query's results to narrow the next one (`mee` to `meet`). The cache and the small vocabulary already give sub-millisecond results; revisit if the benchmark says otherwise.

## Concurrency
- FastAPI runs plain `def` handlers in a threadpool, so reads and the `POST` write can overlap. The index uses one `RLock` around adds and searches. Searches are very short, so the lock is not a bottleneck. The note store has its own lock for id assignment.

## API
- `GET /api/notes?q=&limit=30&offset=0` returns `{ total, items, terms, took_ms }`. `limit` max is 100. Each item has `id`, `title`, `snippet`, `matched_in` (`title`/`body`), `created_at`.
- `terms` is returned so the frontend can highlight with exactly the terms the server matched.
- Snippets and `matched_in` are computed only for the returned page, not for every match.
- `POST /api/notes` takes `{ title, body }`. A blank title returns 422. The new note is searchable immediately.
- Responses are encoded with `orjson` directly (`Response(orjson.dumps(...))`) rather than FastAPI's response model path, to avoid per-item validation overhead. GZip is enabled for responses over 1 KB.

## Ids and ordering
- Ids are sequential from 1, and the note list is indexed by id. Newest note = highest id, so "newest first" needs no sorting. Seeded timestamps are generated in id order to stay consistent.
- **Deleted notes leave a `None` tombstone** in the list, so ids are never reused and lookups stay O(1). The index keeps a sorted list of live ids (`bisect` for deletes) for the empty-query listing, which is newest first and skips deleted notes.
- **Edit keeps the note's id and `created_at`**, so its position in the list does not change. `updated_at` is set and the UI shows "(edited)".

## Edit and delete
- `GET /api/notes/{id}` returns the full note (the list only has snippets, so the edit form needs this). `PUT /api/notes/{id}` updates it. `DELETE /api/notes/{id}` returns 204. Unknown ids return 404, and a blank title returns 422.
- **Index updates:** removing or editing a note removes its id from the postings of its old words, then (for edit) adds it for the new words. Edit does both under one lock, so a search never sees a half-updated note. Empty posting entries are deleted.
- **Words are never removed from the vocabulary or trigram index**, even if no note uses them anymore. A stale word just resolves to empty postings, and the vocabulary stays small, so this is cheaper than reference counting.
- The query cache is cleared on every create, edit and delete.
- A search can return an id that is deleted a moment later, before the page is built. The handler skips missing notes instead of failing, so `total` can be off by one for that single response.

## Frontend (`static/index.html`)
- **Debounce 100 ms plus `AbortController` and a request counter**, so a slow older response can never overwrite a newer one.
- **Previous results stay visible (dimmed) while a new search loads**, to avoid flicker.
- **Highlighting is done on raw text, escaping each piece separately.** Escaping first and then highlighting would let a term like `amp` or `lt` match inside an HTML entity such as `&amp;`.
- **Badges** ("Title match", "Body match") come from the server's `matched_in`. Highlights use the server's `terms`.
- **Infinite scroll** with `IntersectionObserver` (30 per page, 600px look-ahead), so the DOM only grows as the user scrolls. Cards use `content-visibility: auto` to skip rendering work for off-screen cards.
- **After creating a note** the list is simply reloaded with the current query, so the server stays the single source of truth for ordering and matching.
- Light and dark themes follow the OS setting.
- **Edit** reuses the top form: fetch the full note, fill the form, switch the button to "Update note" and show Cancel. After saving, the list reloads, because an edit can change whether and why the note matches.
- **Delete** asks for confirmation, then removes the card in place (scroll position stays) and decrements the count instead of reloading.

## Benchmark and performance tuning (`bench.py`)
- `bench.py` compares indexed search with a naive scan, reports cold (uncached) and warm (cached) latency, the time to build one page (search plus snippets), and `orjson` against the stdlib encoder. Run it with `.venv/bin/python bench.py [note_count ...]`.
- **First benchmark found a weak spot:** very broad queries (`m` matches 99.7% of 100k notes) took about 17 ms uncached, because we built huge sets and then picked the top 30 with `heapq.nlargest`.
- **Fixes:** (1) `set.union(*sets)` so the merge runs in C; (2) dropped redundant intersections with `matched` (title hits are always a subset of all hits); (3) the lowest ranking tier (`rest`) is built lazily, only when better tiers cannot fill the page; (4) for dense tiers, walk live ids newest-first until `k` members are found instead of scanning the whole tier. Results are unchanged: the brute-force tests still pass.
- **Still open:** broad queries at 100k notes are 5-12 ms uncached (`m`, `ing`, `Notes on`), above the 5 ms goal. The dummy data has only about 160 distinct words, so every word appears in a large share of notes and postings are far bigger than in real notes. Selective queries (`meet`, `eeti`, `kube clust`) are 0.7-2.5 ms at 100k. Cached repeats take under 0.1 ms. Accepted for now since typing is debounced and the cost only hits very short or very common terms.
- **orjson:** encoding a 30-item page takes about 2 us with orjson against about 24 us with stdlib `json`. Both are negligible next to search, so the gain is small. Kept because it also handles `datetime` natively and costs nothing.

## Testing
- `pytest` tests in `tests/`: the index is compared against a brute-force reference for many queries, ranking, pagination consistency, cache invalidation, and a random mix of create/update/delete. API tests cover CRUD, validation, limits, and serving the page.

## Note modal
- Clicking a card (or pressing Enter on a focused card) opens a native `<dialog>` with the full note. `<dialog>` gives focus trapping, Escape to close and a backdrop for free. A click on the backdrop or Close also closes it. Cards are focusable (`tabindex="0"`).
- The modal fetches the full note with `GET /api/notes/{id}` (the list only carries snippets). A request counter drops a slow response if another note was opened in the meantime.
- It uses the same `terms` and `highlight()` as the list, so the title and body show the same highlights, and the first highlighted match in the body is scrolled into view.
- The Edit and Delete buttons on a card do not open the modal. Edit and Delete inside the modal reuse the same `startEdit` and `deleteNote` functions as the card buttons, so behaviour matches.
- A click does not open the modal if the user has text selected inside the list, so selecting a snippet to copy it does not pop the modal open. Only selections inside the list count; a selection elsewhere on the page (for example in the form) must not block it.
- Body text uses `white-space: pre-wrap` so line breaks in a note are kept.
