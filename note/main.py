from __future__ import annotations

import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import orjson
from fastapi import FastAPI, Query, Response
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from store import Note, NoteStore, build_store, make_snippet, matched_in

STATIC_DIR = Path(__file__).parent / "static"
MAX_LIMIT = 100


class NoteIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(default="", max_length=10_000)


def _json(payload: dict, status: int = 200) -> Response:
    # orjson is considerably faster than the stdlib encoder for large pages.
    return Response(
        orjson.dumps(payload), status_code=status, media_type="application/json"
    )


def _item(n: Note, terms: list[str]) -> dict:
    return {
        "id": n.id,
        "title": n.title,
        "snippet": make_snippet(n, terms),
        "matched_in": matched_in(n, terms),
        "created_at": n.created_at,
        "updated_at": n.updated_at,
    }


def _not_found() -> Response:
    return _json({"detail": "Note not found"}, status=404)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.store = build_store()
    yield


app = FastAPI(title="Notes", lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=1024)


# Plain `def` handlers run in FastAPI's threadpool; the index is lock-protected.
@app.get("/api/notes")
def list_notes(
    q: Annotated[str, Query(max_length=200)] = "",
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = 30,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Response:
    store: NoteStore = app.state.store
    t0 = time.perf_counter()
    total, ids, terms = store.index.search(q, limit, offset)
    # A note may be deleted between the search and this lookup; skip it.
    items = [_item(n, terms) for i in ids if (n := store.get(i)) is not None]
    took_ms = (time.perf_counter() - t0) * 1000
    return _json(
        {"total": total, "items": items, "terms": terms, "took_ms": round(took_ms, 2)}
    )


@app.post("/api/notes", status_code=201)
def create_note(payload: NoteIn) -> Response:
    store: NoteStore = app.state.store
    title = payload.title.strip()
    if not title:
        return _json({"detail": "Title must not be blank"}, status=422)
    note = store.create(title, payload.body.strip())
    return _json(_item(note, []), status=201)


@app.get("/api/notes/{note_id}")
def get_note(note_id: int) -> Response:
    note = app.state.store.get(note_id)
    if note is None:
        return _not_found()
    # Full body (the list endpoint only returns snippets) for the edit form.
    return _json({**_item(note, []), "body": note.body})


@app.put("/api/notes/{note_id}")
def update_note(note_id: int, payload: NoteIn) -> Response:
    title = payload.title.strip()
    if not title:
        return _json({"detail": "Title must not be blank"}, status=422)
    note = app.state.store.update(note_id, title, payload.body.strip())
    if note is None:
        return _not_found()
    return _json({**_item(note, []), "body": note.body})


@app.delete("/api/notes/{note_id}")
def delete_note(note_id: int) -> Response:
    if not app.state.store.delete(note_id):
        return _not_found()
    return Response(status_code=204)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "notes": len(app.state.store)}


@app.get("/", include_in_schema=False)
def home() -> Response:
    page = STATIC_DIR / "index.html"
    if page.exists():
        return FileResponse(page)
    return _json({"message": "Frontend not built yet. See /docs for the API."})


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
