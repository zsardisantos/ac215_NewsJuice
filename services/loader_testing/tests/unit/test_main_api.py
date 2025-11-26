# services/loader_faster/tests/unit/test_main_api.py

import pytest


@pytest.fixture(autouse=True)
def mock_db_url(monkeypatch):
    # Needed so importing loader (from main) doesn't crash
    monkeypatch.setenv("DATABASE_URL", "postgresql://fake")


def test_health_endpoint():
    from api import main as main_mod
    from fastapi.testclient import TestClient

    client = TestClient(main_mod.app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_process_endpoint_queues_background(monkeypatch):
    from api import main as main_mod
    from fastapi.testclient import TestClient

    # We don't actually want to run the real chunk_embed_load
    def fake_chunk_embed_load(method: str):
        return {"status": "success", "processed": 0, "total_found": 0}

    monkeypatch.setattr(main_mod, "chunk_embed_load", fake_chunk_embed_load)

    client = TestClient(main_mod.app)
    resp = client.post("/process")
    assert resp.status_code == 200
    assert resp.json() == {"status": "started"}


def test_process_sync_endpoint_uses_chunk_embed_load(monkeypatch):
    from api import main as main_mod
    from fastapi.testclient import TestClient

    fake_result = {"status": "success", "processed": 3, "total_found": 5}

    def fake_chunk_embed_load(method: str = "recursive-split"):
        return fake_result

    monkeypatch.setattr(main_mod, "chunk_embed_load", fake_chunk_embed_load)

    client = TestClient(main_mod.app)
    resp = client.post("/process-sync")
    assert resp.status_code == 200
    assert resp.json() == fake_result
