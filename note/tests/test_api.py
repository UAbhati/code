import os

import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture(scope="module")
def client():
    os.environ["NOTES_SEED_COUNT"] = "500"
    with TestClient(main.app) as c:
        yield c


def test_health(client):
    assert client.get("/api/health").json() == {"ok": True, "notes": 500}


def test_list_shape_and_limits(client):
    r = client.get("/api/notes", params={"limit": 5}).json()
    assert r["total"] == 500 and len(r["items"]) == 5 and r["terms"] == []
    assert set(r["items"][0]) == {"id", "title", "snippet", "matched_in", "created_at", "updated_at"}
    assert client.get("/api/notes", params={"limit": 101}).status_code == 422
    assert client.get("/api/notes", params={"limit": 0}).status_code == 422
    assert client.get("/api/notes", params={"offset": -1}).status_code == 422
    assert client.get("/api/notes", params={"q": "x" * 201}).status_code == 422


def test_search_returns_terms_and_match_info(client):
    r = client.get("/api/notes", params={"q": "EETI", "limit": 3}).json()
    assert r["terms"] == ["eeti"] and r["total"] > 0 and r["took_ms"] >= 0
    for item in r["items"]:
        assert item["matched_in"]


def test_crud_roundtrip(client):
    r = client.post("/api/notes", json={"title": "  Zebrafish plan  ", "body": " xylophone "})
    assert r.status_code == 201
    nid = r.json()["id"]
    assert client.get("/api/notes", params={"q": "ebraf"}).json()["items"][0]["id"] == nid

    full = client.get(f"/api/notes/{nid}").json()
    assert full["title"] == "Zebrafish plan" and full["body"] == "xylophone"

    r = client.put(f"/api/notes/{nid}", json={"title": "Walrus plan", "body": "harmonica"})
    assert r.status_code == 200 and r.json()["updated_at"] is not None
    assert client.get("/api/notes", params={"q": "zebra"}).json()["total"] == 0
    assert client.get("/api/notes", params={"q": "harmon"}).json()["items"][0]["id"] == nid

    assert client.delete(f"/api/notes/{nid}").status_code == 204
    assert client.get("/api/notes", params={"q": "harmon"}).json()["total"] == 0
    assert client.get(f"/api/notes/{nid}").status_code == 404
    assert client.delete(f"/api/notes/{nid}").status_code == 404
    assert client.put(f"/api/notes/{nid}", json={"title": "x"}).status_code == 404


def test_validation(client):
    assert client.post("/api/notes", json={"title": "   "}).status_code == 422
    assert client.post("/api/notes", json={"title": ""}).status_code == 422
    assert client.post("/api/notes", json={}).status_code == 422
    assert client.put("/api/notes/1", json={"title": "  "}).status_code == 422
    assert client.get("/api/notes/999999").status_code == 404


def test_html_in_notes_is_returned_as_plain_text(client):
    r = client.post("/api/notes", json={"title": "<script>alert(1)</script>", "body": "&amp; <b>"})
    assert client.get(f"/api/notes/{r.json()['id']}").json()["title"] == "<script>alert(1)</script>"


def test_frontend_is_served(client):
    r = client.get("/")
    assert r.status_code == 200 and "<title>Notes</title>" in r.text
