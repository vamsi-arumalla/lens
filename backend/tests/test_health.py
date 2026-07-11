def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["versions"]["python"].startswith("3.12")
    assert "X-Stage-Timings" in resp.headers


def test_health_needs_no_api_key(client):
    assert client.get("/health").status_code == 200
