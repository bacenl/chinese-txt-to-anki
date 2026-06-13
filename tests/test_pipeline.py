from pathlib import Path

import pytest

from src.main import parse_arguments
from src.pipeline import GenerationOptions, generate_cards
from src.providers import OpenAICompatibleProvider


def write_words(path: Path, words: list[str]) -> None:
    path.write_text("\n".join(words) + "\n", encoding="utf-8")


def test_generate_cards_returns_structured_artifacts_and_uses_provider(tmp_path):
    input_file = tmp_path / "words.txt"
    write_words(input_file, ["你好", "谢谢", "学习"])

    calls: list[list[str]] = []

    def fake_provider(words: list[str]) -> str:
        calls.append(words)
        return "\n".join(f"# {word}" for word in words)

    def fake_deck_generator(md_file: str, apkg_file: str, deck_name: str) -> bool:
        Path(apkg_file).write_text(f"deck={deck_name}\nsource={md_file}\n", encoding="utf-8")
        return True

    result = generate_cards(
        GenerationOptions(
            input_path=input_file,
            markdown_root=tmp_path / "md",
            anki_root=tmp_path / "apkg",
            deck_name="Test Deck",
            chunk_size=2,
            chunks_per_file=2,
            history_path=tmp_path / "history.txt",
            ignore_history=True,
            max_workers=1,
        ),
        provider=fake_provider,
        deck_generator=fake_deck_generator,
    )

    assert calls == [["你好", "谢谢"], ["学习"]]
    assert result.processed_words == ["你好", "谢谢", "学习"]
    assert result.skipped_words == []
    assert len(result.markdown_files) == 1
    assert len(result.apkg_files) == 1
    assert result.markdown_files[0].read_text(encoding="utf-8") == "# 你好\n# 谢谢\n\n# 学习"
    assert result.apkg_files[0].read_text(encoding="utf-8").startswith("deck=Test Deck")


def test_generate_cards_filters_history_and_preserves_input_order(tmp_path):
    input_file = tmp_path / "words.txt"
    write_words(input_file, ["你好", "谢谢", "学习", "工作"])
    history_file = tmp_path / "history.txt"
    history_file.write_text("谢谢\n", encoding="utf-8")

    def fake_provider(words: list[str]) -> str:
        return "\n".join(f"# {word}" for word in words)

    def fake_deck_generator(md_file: str, apkg_file: str, deck_name: str) -> bool:
        Path(apkg_file).touch()
        return True

    result = generate_cards(
        GenerationOptions(
            input_path=input_file,
            markdown_root=tmp_path / "md",
            anki_root=tmp_path / "apkg",
            deck_name="Test Deck",
            chunk_size=1,
            chunks_per_file=2,
            history_path=history_file,
            max_workers=2,
        ),
        provider=fake_provider,
        deck_generator=fake_deck_generator,
    )

    assert result.skipped_words == ["谢谢"]
    assert result.processed_words == ["你好", "学习", "工作"]
    assert history_file.read_text(encoding="utf-8").splitlines() == ["谢谢", "你好", "学习", "工作"]
    combined = "\n\n".join(path.read_text(encoding="utf-8") for path in result.markdown_files)
    assert combined == "# 你好\n\n# 学习\n\n# 工作"


def test_generation_result_to_dict_is_endpoint_safe(tmp_path):
    input_file = tmp_path / "words.txt"
    write_words(input_file, ["你好"])

    def fake_provider(words: list[str]) -> str:
        return "\n".join(f"# {word}" for word in words)

    def fake_deck_generator(md_file: str, apkg_file: str, deck_name: str) -> bool:
        Path(apkg_file).touch()
        return True

    result = generate_cards(
        GenerationOptions(
            input_path=input_file,
            markdown_root=tmp_path / "md",
            anki_root=tmp_path / "apkg",
            history_path=tmp_path / "history.txt",
            ignore_history=True,
        ),
        provider=fake_provider,
        deck_generator=fake_deck_generator,
    )

    payload = result.to_dict()

    assert payload["processed_words"] == ["你好"]
    assert payload["skipped_words"] == []
    assert payload["markdown_files"] == [str(result.markdown_files[0])]
    assert payload["apkg_files"] == [str(result.apkg_files[0])]
    assert payload["failed_chunks"] == []
    assert payload["ok"] is True


def test_generate_cards_retries_transient_provider_failures(tmp_path):
    input_file = tmp_path / "words.txt"
    write_words(input_file, ["你好"])
    attempts = 0

    def flaky_provider(words: list[str]) -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("temporary rate limit")
        return "# 你好"

    def fake_deck_generator(md_file: str, apkg_file: str, deck_name: str) -> bool:
        Path(apkg_file).touch()
        return True

    result = generate_cards(
        GenerationOptions(
            input_path=input_file,
            markdown_root=tmp_path / "md",
            anki_root=tmp_path / "apkg",
            history_path=tmp_path / "history.txt",
            retry_attempts=2,
            retry_backoff_seconds=0,
        ),
        provider=flaky_provider,
        deck_generator=fake_deck_generator,
    )

    assert attempts == 2
    assert result.processed_words == ["你好"]
    assert result.failed_chunks == []


def test_generate_cards_can_continue_and_report_failed_chunks(tmp_path):
    input_file = tmp_path / "words.txt"
    write_words(input_file, ["你好", "谢谢"])

    def partially_failing_provider(words: list[str]) -> str:
        if words == ["谢谢"]:
            raise RuntimeError("provider refused chunk")
        return "# 你好"

    def fake_deck_generator(md_file: str, apkg_file: str, deck_name: str) -> bool:
        Path(apkg_file).touch()
        return True

    result = generate_cards(
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
        deck_generator=fake_deck_generator,
    )

    assert result.processed_words == ["你好"]
    assert result.failed_chunks[0].words == ["谢谢"]
    assert "provider refused chunk" in result.failed_chunks[0].error
    assert result.to_dict()["ok"] is False


def test_openai_compatible_provider_prefers_generic_model_env(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "generic-key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-key")
    monkeypatch.setenv("MODEL_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("MODEL_NAME", "example-model")

    provider = OpenAICompatibleProvider.from_env()

    assert provider.config.api_key == "generic-key"
    assert provider.config.base_url == "https://example.test/v1"
    assert provider.config.model == "example-model"


def test_openai_compatible_provider_reads_generation_knobs(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "generic-key")
    monkeypatch.setenv("MODEL_TEMPERATURE", "0.2")
    monkeypatch.setenv("MODEL_MAX_TOKENS", "2048")

    provider = OpenAICompatibleProvider.from_env()

    assert provider.config.temperature == 0.2
    assert provider.config.max_tokens == 2048


def test_openai_compatible_provider_falls_back_to_deepseek_key(monkeypatch):
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-key")

    provider = OpenAICompatibleProvider.from_env()

    assert provider.config.api_key == "deepseek-key"


def test_openai_compatible_provider_requires_api_key(monkeypatch):
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    with pytest.raises(ValueError, match="MODEL_API_KEY"):
        OpenAICompatibleProvider.from_env()


def test_parse_arguments_accepts_endpoint_and_reliability_flags(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        [
            "anki-gen",
            "--input",
            "words.txt",
            "--json",
            "--continue-on-error",
            "--retry-attempts",
            "3",
            "--retry-backoff-seconds",
            "0.5",
        ],
    )

    args = parse_arguments()

    assert args.json is True
    assert args.continue_on_error is True
    assert args.retry_attempts == 3
    assert args.retry_backoff_seconds == 0.5
