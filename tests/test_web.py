"""Tests for FastAPI generation and download endpoints (Task 3.1)."""

from pathlib import Path

import pytest

# Skip the entire module if fastapi is not installed
pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from src.web.app import app, get_deck_generator, get_generation_provider  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_provider(words: list[str]) -> str:
    return "\n".join(f"# {w}" for w in words)


def _fake_deck_generator(md_file: str, apkg_file: str, deck_name: str) -> bool:
    Path(apkg_file).touch()
    return True


def _make_client_with_fakes() -> TestClient:
    app.dependency_overrides[get_generation_provider] = lambda: _fake_provider
    app.dependency_overrides[get_deck_generator] = lambda: _fake_deck_generator
    client = TestClient(app, raise_server_exceptions=True)
    return client


# ---------------------------------------------------------------------------
# POST /generate
# ---------------------------------------------------------------------------


def test_post_generate_returns_ok_and_apkg_files():
    client = _make_client_with_fakes()
    try:
        response = client.post(
            "/generate",
            json={"words": "你好\n谢谢", "deck_name": "Test Deck"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert isinstance(body["apkg_files"], list)
    assert len(body["apkg_files"]) >= 1


def test_post_generate_processed_words_match_input():
    client = _make_client_with_fakes()
    try:
        response = client.post(
            "/generate",
            json={"words": "你好\n谢谢\n学习", "deck_name": "Test"},
        )
    finally:
        app.dependency_overrides.clear()

    body = response.json()
    assert sorted(body["processed_words"]) == sorted(["你好", "谢谢", "学习"])


def test_post_generate_empty_words_returns_error():
    client = _make_client_with_fakes()
    try:
        response = client.post("/generate", json={"words": "", "deck_name": "Test"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code in (400, 422)


def test_post_generate_provider_failure_returns_error_json():
    def _failing_provider(words: list[str]) -> str:
        raise RuntimeError("provider unavailable")

    app.dependency_overrides[get_generation_provider] = lambda: _failing_provider
    app.dependency_overrides[get_deck_generator] = lambda: _fake_deck_generator
    client = TestClient(app, raise_server_exceptions=False)
    try:
        response = client.post(
            "/generate",
            json={"words": "你好", "deck_name": "Test"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code in (500, 422)
    body = response.json()
    assert "ok" not in body or body["ok"] is False


# ---------------------------------------------------------------------------
# GET /download/{filename}
# ---------------------------------------------------------------------------


def test_get_download_serves_existing_file(tmp_path, monkeypatch):
    apkg_file = tmp_path / "output_1.apkg"
    apkg_file.write_bytes(b"fake apkg content")

    from src.web import app as web_module

    monkeypatch.setattr(web_module, "ANKI_ROOT", str(tmp_path))

    client = TestClient(app)
    response = client.get("/download/output_1.apkg")

    assert response.status_code == 200
    assert response.content == b"fake apkg content"


def test_get_download_path_traversal_returns_404():
    client = TestClient(app)
    response = client.get("/download/../etc/passwd")

    assert response.status_code == 404


def test_get_download_dotdot_in_name_returns_404():
    client = TestClient(app)
    response = client.get("/download/..%2Fetc%2Fpasswd")

    assert response.status_code == 404


def test_get_download_nonexistent_file_returns_404():
    client = TestClient(app)
    response = client.get("/download/does_not_exist.apkg")

    assert response.status_code == 404
