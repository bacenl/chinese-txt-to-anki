"""FastAPI application exposing /generate and /download endpoints."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Callable

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse

from ..pipeline import DeckGenerator, GenerationOptions, generate_cards
from ..processing import generate_anki_deck
from .schemas import GenerateRequest

ANKI_ROOT: str = os.getenv("ANKI_ROOT", "io/output_apkg")

app = FastAPI(title="Chinese Anki Generator")


def get_generation_provider() -> Callable[[list[str]], str]:
    """Default provider dependency — override in tests via app.dependency_overrides."""
    from ..providers import get_provider

    return get_provider("deepseek")


def get_deck_generator() -> DeckGenerator:
    """Default deck generator dependency — override in tests via app.dependency_overrides."""
    return generate_anki_deck


@app.post("/generate")
def generate(
    body: GenerateRequest,
    provider: Callable[[list[str]], str] = Depends(get_generation_provider),
    deck_gen: DeckGenerator = Depends(get_deck_generator),
) -> dict[str, Any]:
    words = [w.strip() for w in body.words.split("\n") if w.strip()]

    md_dir = Path(tempfile.mkdtemp())
    anki_dir = Path(tempfile.mkdtemp())
    history_path = md_dir / "history.txt"

    input_file = md_dir / "words.txt"
    input_file.write_text("\n".join(words), encoding="utf-8")

    try:
        result = generate_cards(
            GenerationOptions(
                input_path=input_file,
                markdown_root=md_dir / "md",
                anki_root=anki_dir,
                deck_name=body.deck_name,
                ignore_history=True,
                history_path=history_path,
            ),
            provider=provider,
            deck_generator=deck_gen,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return result.to_dict()


@app.get("/download/{filename}")
def download(filename: str) -> FileResponse:
    # Use only the basename to prevent directory traversal
    safe_name = Path(filename).name
    anki_root = Path(ANKI_ROOT).resolve()
    safe_path = (anki_root / safe_name).resolve()

    if (
        ".." in filename
        or not safe_path.exists()
        or not safe_path.is_file()
        or not safe_path.is_relative_to(anki_root)
    ):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(safe_path)
