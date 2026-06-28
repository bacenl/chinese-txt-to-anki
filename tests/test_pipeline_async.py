"""Tests for the async generation pipeline (Task 2.1)."""

import asyncio
from pathlib import Path

from src.pipeline import GenerationOptions
from src.pipeline_async import generate_cards_async


def _fake_deck_generator(md_file: str, apkg_file: str, deck_name: str) -> bool:
    Path(apkg_file).touch()
    return True


def _write_words(path: Path, words: list[str]) -> None:
    path.write_text("\n".join(words) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Basic correctness
# ---------------------------------------------------------------------------


def test_generate_cards_async_returns_structured_result(tmp_path):
    input_file = tmp_path / "words.txt"
    _write_words(input_file, ["你好", "谢谢"])

    async def run():
        def fake_provider(words: list[str]) -> str:
            return "\n".join(f"# {w}" for w in words)

        return await generate_cards_async(
            GenerationOptions(
                input_path=input_file,
                markdown_root=tmp_path / "md",
                anki_root=tmp_path / "apkg",
                history_path=tmp_path / "history.txt",
                ignore_history=True,
                chunk_size=2,
            ),
            provider=fake_provider,
            deck_generator=_fake_deck_generator,
        )

    result = asyncio.run(run())

    assert sorted(result.processed_words) == ["你好", "谢谢"]
    assert result.failed_chunks == []
    assert len(result.apkg_files) == 1


def test_generate_cards_async_preserves_output_order(tmp_path):
    """Async execution must not scramble word order in output files."""
    input_file = tmp_path / "words.txt"
    words = [str(i) for i in range(10)]
    _write_words(input_file, words)

    async def run():
        def fake_provider(chunk: list[str]) -> str:
            return "\n".join(f"# {w}" for w in chunk)

        return await generate_cards_async(
            GenerationOptions(
                input_path=input_file,
                markdown_root=tmp_path / "md",
                anki_root=tmp_path / "apkg",
                history_path=tmp_path / "history.txt",
                ignore_history=True,
                chunk_size=2,
                max_workers=4,
            ),
            provider=fake_provider,
            deck_generator=_fake_deck_generator,
        )

    result = asyncio.run(run())

    assert result.processed_words == words


def test_generate_cards_async_skips_history(tmp_path):
    input_file = tmp_path / "words.txt"
    _write_words(input_file, ["你好", "谢谢", "学习"])
    history_file = tmp_path / "history.txt"
    history_file.write_text("谢谢\n", encoding="utf-8")

    async def run():
        def fake_provider(words: list[str]) -> str:
            return "\n".join(f"# {w}" for w in words)

        return await generate_cards_async(
            GenerationOptions(
                input_path=input_file,
                markdown_root=tmp_path / "md",
                anki_root=tmp_path / "apkg",
                history_path=history_file,
                chunk_size=10,
            ),
            provider=fake_provider,
            deck_generator=_fake_deck_generator,
        )

    result = asyncio.run(run())

    assert result.skipped_words == ["谢谢"]
    assert "谢谢" not in result.processed_words


def test_generate_cards_async_returns_early_when_all_skipped(tmp_path):
    input_file = tmp_path / "words.txt"
    _write_words(input_file, ["你好"])
    history_file = tmp_path / "history.txt"
    history_file.write_text("你好\n", encoding="utf-8")

    async def run():
        def fake_provider(words: list[str]) -> str:
            return "# 你好"

        return await generate_cards_async(
            GenerationOptions(
                input_path=input_file,
                markdown_root=tmp_path / "md",
                anki_root=tmp_path / "apkg",
                history_path=history_file,
            ),
            provider=fake_provider,
            deck_generator=_fake_deck_generator,
        )

    result = asyncio.run(run())

    assert result.processed_words == []
    assert result.apkg_files == []


# ---------------------------------------------------------------------------
# Partial failures
# ---------------------------------------------------------------------------


def test_generate_cards_async_reports_failed_chunks(tmp_path):
    input_file = tmp_path / "words.txt"
    _write_words(input_file, ["你好", "谢谢"])

    async def run():
        def partially_failing_provider(words: list[str]) -> str:
            if words == ["谢谢"]:
                raise RuntimeError("model refused")
            return "# 你好"

        return await generate_cards_async(
            GenerationOptions(
                input_path=input_file,
                markdown_root=tmp_path / "md",
                anki_root=tmp_path / "apkg",
                history_path=tmp_path / "history.txt",
                chunk_size=1,
                continue_on_error=True,
                retry_attempts=1,
                retry_backoff_seconds=0,
            ),
            provider=partially_failing_provider,
            deck_generator=_fake_deck_generator,
        )

    result = asyncio.run(run())

    assert result.processed_words == ["你好"]
    assert len(result.failed_chunks) == 1
    assert result.failed_chunks[0].words == ["谢谢"]
    assert result.to_dict()["ok"] is False
