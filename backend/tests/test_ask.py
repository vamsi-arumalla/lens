from tests.conftest import API_KEY, make_jpeg


def _files(n_frames: int = 1, with_audio: bool = False):
    files = [("frames", ("f.jpg", make_jpeg(), "image/jpeg")) for _ in range(n_frames)]
    if with_audio:
        files.append(("audio", ("q.webm", b"fake-audio", "audio/webm")))
    return files


def test_ask_requires_api_key(client):
    resp = client.post("/ask", files=_files(), data={"text": "what is this?"})
    assert resp.status_code == 401


def test_ask_streams_spoken_answer(client, fake_vlm):
    resp = client.post(
        "/ask",
        files=_files(),
        data={"text": "what is this?"},
        headers={"X-API-Key": API_KEY},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("audio/mpeg")
    # FakeTTS wraps each spoken chunk in brackets
    assert resp.content == b"[It is a red mug.]"
    assert fake_vlm.calls == [("what is this?", 1)]
    assert "vlm_first_token_ms" in resp.headers["X-Stage-Timings"]


def test_ask_uses_stt_when_audio_present(client, fake_vlm):
    resp = client.post(
        "/ask", files=_files(with_audio=True), headers={"X-API-Key": API_KEY}
    )
    assert resp.status_code == 200
    assert fake_vlm.calls == [("what is this", 1)]
    assert "stt_ms" in resp.headers["X-Stage-Timings"]


def test_ask_without_question_is_422(client):
    resp = client.post("/ask", files=_files(), headers={"X-API-Key": API_KEY})
    assert resp.status_code == 422


def test_ask_rejects_more_than_three_frames(client):
    resp = client.post(
        "/ask",
        files=_files(n_frames=4),
        data={"text": "hi"},
        headers={"X-API-Key": API_KEY},
    )
    assert resp.status_code == 422


def test_vlm_failure_returns_spoken_fallback_not_500(failing_vlm_client):
    resp = failing_vlm_client.post(
        "/ask",
        files=_files(),
        data={"text": "what is this?"},
        headers={"X-API-Key": API_KEY},
    )
    assert resp.status_code == 200
    assert resp.content == b"[Sorry, I couldn't process that.]"
    assert resp.headers["X-Lens-Error"] == "vlm_failed"
