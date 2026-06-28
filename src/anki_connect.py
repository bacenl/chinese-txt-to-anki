"""Local AnkiConnect client for pushing .apkg files into a running Anki instance.

This module is intended to run on the user's local machine only.
The generation server does NOT call AnkiConnect.
"""

from __future__ import annotations

import requests


class AnkiConnectClient:
    """HTTP client for the AnkiConnect add-on (default: http://127.0.0.1:8765)."""

    def __init__(self, base_url: str = "http://127.0.0.1:8765") -> None:
        self._base_url = base_url

    def _request(self, payload: dict) -> dict:
        response = requests.post(self._base_url, json={**payload, "version": 6})
        result = response.json()
        if result.get("error"):
            raise RuntimeError(result["error"])
        return result

    def deck_exists(self, deck_name: str) -> bool:
        result = self._request({"action": "deckNames"})
        return deck_name in (result.get("result") or [])

    def import_apkg(self, apkg_path: str) -> dict:
        return self._request({"action": "importPackage", "params": {"path": apkg_path}})

    def add_note(self, deck: str, front: str, back: str) -> int:
        result = self._request(
            {
                "action": "addNote",
                "params": {
                    "note": {
                        "deckName": deck,
                        "modelName": "Basic",
                        "fields": {"Front": front, "Back": back},
                        "options": {"allowDuplicate": False},
                    }
                },
            }
        )
        return int(result["result"])
