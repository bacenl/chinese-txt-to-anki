"""Tests for the AnkiConnect helper module (Task 3.3)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.anki_connect import AnkiConnectClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client() -> AnkiConnectClient:
    return AnkiConnectClient(base_url="http://127.0.0.1:8765")


def _anki_response(result, error=None):
    return {"result": result, "error": error}


# ---------------------------------------------------------------------------
# deck_exists
# ---------------------------------------------------------------------------


def test_deck_exists_returns_true_when_deck_present():
    with patch("src.anki_connect.requests.post") as mock_post:
        mock_post.return_value.json.return_value = _anki_response(["Default", "My Deck"])
        client = _make_client()
        assert client.deck_exists("My Deck") is True


def test_deck_exists_returns_false_when_deck_absent():
    with patch("src.anki_connect.requests.post") as mock_post:
        mock_post.return_value.json.return_value = _anki_response(["Default"])
        client = _make_client()
        assert client.deck_exists("Missing Deck") is False


# ---------------------------------------------------------------------------
# import_apkg
# ---------------------------------------------------------------------------


def test_import_apkg_sends_correct_action_and_path(tmp_path):
    apkg_file = tmp_path / "cards.apkg"
    apkg_file.touch()

    with patch("src.anki_connect.requests.post") as mock_post:
        mock_post.return_value.json.return_value = _anki_response(1)
        client = _make_client()
        result = client.import_apkg(str(apkg_file))

    call_payload = mock_post.call_args[1]["json"]
    assert call_payload["action"] == "importPackage"
    assert str(apkg_file) in str(call_payload["params"])
    assert result == {"result": 1, "error": None}


def test_import_apkg_raises_on_anki_error(tmp_path):
    apkg_file = tmp_path / "cards.apkg"
    apkg_file.touch()

    with patch("src.anki_connect.requests.post") as mock_post:
        mock_post.return_value.json.return_value = _anki_response(
            None, error="collection not loaded"
        )
        client = _make_client()
        with pytest.raises(RuntimeError, match="collection not loaded"):
            client.import_apkg(str(apkg_file))


# ---------------------------------------------------------------------------
# add_note
# ---------------------------------------------------------------------------


def test_add_note_returns_note_id():
    with patch("src.anki_connect.requests.post") as mock_post:
        mock_post.return_value.json.return_value = _anki_response(1234567890)
        client = _make_client()
        note_id = client.add_note(deck="Chinese", front="你好", back="hello")

    assert note_id == 1234567890


def test_add_note_sends_deck_and_fields():
    with patch("src.anki_connect.requests.post") as mock_post:
        mock_post.return_value.json.return_value = _anki_response(42)
        client = _make_client()
        client.add_note(deck="My Deck", front="学习", back="to study")

    payload = mock_post.call_args[1]["json"]
    assert payload["action"] == "addNote"
    note_params = payload["params"]["note"]
    assert note_params["deckName"] == "My Deck"
    assert note_params["fields"]["Front"] == "学习"
    assert note_params["fields"]["Back"] == "to study"


# ---------------------------------------------------------------------------
# Connection errors
# ---------------------------------------------------------------------------


def test_anki_connect_unreachable_raises_connection_error():
    import requests as req_lib

    with patch("src.anki_connect.requests.post", side_effect=req_lib.ConnectionError):
        client = _make_client()
        with pytest.raises(Exception):
            client.deck_exists("Any Deck")


# ---------------------------------------------------------------------------
# Real AnkiConnect integration (skipped unless ANKI_CONNECT_REAL_TEST=1)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not __import__("os").getenv("ANKI_CONNECT_REAL_TEST"),
    reason="ANKI_CONNECT_REAL_TEST not set",
)
def test_real_anki_connect_deck_exists():
    client = AnkiConnectClient()
    result = client.deck_exists("Default")
    assert result is True
