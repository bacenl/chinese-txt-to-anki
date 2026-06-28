"""Pydantic schemas for the web API."""

from __future__ import annotations

from pydantic import BaseModel, field_validator


class GenerateRequest(BaseModel):
    words: str
    deck_name: str = "Chinese Vocabulary"

    @field_validator("words")
    @classmethod
    def words_not_empty(cls, v: str) -> str:
        if not any(w.strip() for w in v.split("\n")):
            raise ValueError("words must not be empty")
        return v
