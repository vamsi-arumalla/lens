import time

from tests.conftest import API_KEY, make_jpeg

HEADERS = {"X-API-Key": API_KEY}


def _ingest(client, text="keys on the counter"):
    return client.post(
        "/ingest",
        files=[("frames", ("f.jpg", make_jpeg(), "image/jpeg"))],
        data={"text": text},
        headers=HEADERS,
    )


def test_ingest_stores_a_moment(memory_client, fake_store):
    resp = _ingest(memory_client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["caption"] == "a red mug on a table"
    row = fake_store.rows[body["id"]]
    assert row["transcript"] == "keys on the counter"
    assert len(row["image_emb"]) == 512
    assert len(row["text_emb"]) == 384


def test_ingest_503_when_memory_disabled(client):
    resp = _ingest(client)
    assert resp.status_code == 503


def test_search_returns_ranked_moments(memory_client):
    _ingest(memory_client, "whiteboard with notes")
    resp = memory_client.post(
        "/memory/search", json={"query": "whiteboard"}, headers=HEADERS
    )
    assert resp.status_code == 200
    moments = resp.json()["moments"]
    assert len(moments) == 1
    assert moments[0]["transcript"] == "whiteboard with notes"
    assert moments[0]["thumb_url"].endswith("/thumb.jpg")
    assert moments[0]["score"] is not None


def test_thumb_and_frame_are_served(memory_client):
    moment_id = _ingest(memory_client).json()["id"]
    for kind in ("thumb", "frame"):
        resp = memory_client.get(f"/memory/{moment_id}/{kind}.jpg", headers=HEADERS)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/jpeg"
        assert resp.content[:2] == b"\xff\xd8"  # JPEG magic


def test_delete_moment_and_delete_all(memory_client, fake_store):
    ids = [_ingest(memory_client).json()["id"] for _ in range(2)]
    assert memory_client.delete(f"/memory/{ids[0]}", headers=HEADERS).status_code == 204
    assert ids[0] not in fake_store.rows
    resp = memory_client.delete("/memory", headers=HEADERS)
    assert resp.json() == {"deleted": 1}
    assert fake_store.rows == {}


def test_ask_gets_memory_tool_and_auto_ingests(memory_client, fake_vlm, fake_store):
    resp = memory_client.post(
        "/ask",
        files=[("frames", ("f.jpg", make_jpeg(), "image/jpeg"))],
        data={"text": "what is this?"},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    # The VLM was handed a live search_memory callable
    assert fake_vlm.memory_search is not None
    # The ask itself becomes a moment (background task; poll briefly)
    for _ in range(40):
        if fake_store.rows:
            break
        time.sleep(0.05)
    (row,) = fake_store.rows.values()
    assert row["question"] == "what is this?"
    assert row["answer"] == "It is a red mug."


def test_ask_still_works_without_memory(client, fake_vlm):
    resp = client.post(
        "/ask",
        files=[("frames", ("f.jpg", make_jpeg(), "image/jpeg"))],
        data={"text": "what is this?"},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    assert resp.content == b"[It is a red mug.]"
    assert fake_vlm.memory_search is None
