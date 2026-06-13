"""Importable generation pipeline for Chinese Anki decks."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence

from .processing import CHUNKS_PER_FILE, chunk_list, generate_anki_deck, save_md_file

Provider = Callable[[list[str]], str]
DeckGenerator = Callable[[str, str, str], bool]


@dataclass(frozen=True)
class GenerationOptions:
    """Options for the Chinese vocab to Anki generation pipeline."""

    input_path: str | Path
    markdown_root: str | Path = "io/output_md"
    anki_root: str | Path = "io/output_apkg"
    deck_name: str = "Chinese Vocabulary"
    chunk_size: int = 6
    chunks_per_file: int = CHUNKS_PER_FILE
    history_path: str | Path = ".cache/history.txt"
    ignore_history: bool = False
    max_workers: int = 1


@dataclass(frozen=True)
class GenerationResult:
    """Structured result returned to CLIs, dashboards, and tests."""

    processed_words: list[str]
    skipped_words: list[str]
    markdown_files: list[Path]
    apkg_files: list[Path]
    output_markdown_dir: Path
    output_anki_dir: Path
    failed_chunks: list[list[str]] = field(default_factory=list)


def read_words(input_path: str | Path) -> list[str]:
    """Read newline-delimited vocab items, ignoring empty lines."""

    return [
        line.strip()
        for line in Path(input_path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_history(history_path: str | Path) -> set[str]:
    """Load processed vocab history from a configurable file path."""

    path = Path(history_path)
    if not path.exists():
        return set()
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def append_history(history_path: str | Path, words: Sequence[str]) -> None:
    """Append processed words to a configurable history file."""

    if not words:
        return
    path = Path(history_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for word in words:
            handle.write(f"{word}\n")


def _make_output_dirs(markdown_root: str | Path, anki_root: str | Path) -> tuple[Path, Path]:
    """Create deterministic output directories supplied by the caller."""

    md_dir = Path(markdown_root)
    apkg_dir = Path(anki_root)
    md_dir.mkdir(parents=True, exist_ok=True)
    apkg_dir.mkdir(parents=True, exist_ok=True)
    return md_dir, apkg_dir


def _call_provider_ordered(chunks: list[list[str]], provider: Provider, max_workers: int) -> list[str]:
    """Call the provider sequentially or concurrently while preserving chunk order."""

    if max_workers <= 1 or len(chunks) <= 1:
        return [provider(chunk) for chunk in chunks]

    results: list[str | None] = [None] * len(chunks)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(provider, chunk): index for index, chunk in enumerate(chunks)
        }
        for future in as_completed(futures):
            results[futures[future]] = future.result()

    return [result or "" for result in results]


def generate_cards(
    options: GenerationOptions,
    provider: Provider,
    deck_generator: DeckGenerator = generate_anki_deck,
) -> GenerationResult:
    """Generate markdown and Anki artifacts from a vocab file.

    The provider is injected so the CLI can use DeepSeek today while dashboards
    and future callers can select other OpenAI-compatible or local model clients.
    """

    if options.chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if options.chunks_per_file <= 0:
        raise ValueError("chunks_per_file must be greater than zero")
    if options.max_workers <= 0:
        raise ValueError("max_workers must be greater than zero")

    words = read_words(options.input_path)
    history = set() if options.ignore_history else load_history(options.history_path)
    skipped_words = [word for word in words if word in history]
    pending_words = [word for word in words if options.ignore_history or word not in history]

    md_dir, apkg_dir = _make_output_dirs(options.markdown_root, options.anki_root)
    if not pending_words:
        return GenerationResult(
            processed_words=[],
            skipped_words=skipped_words,
            markdown_files=[],
            apkg_files=[],
            output_markdown_dir=md_dir,
            output_anki_dir=apkg_dir,
        )

    chunks = chunk_list(pending_words, options.chunk_size)
    responses = _call_provider_ordered(chunks, provider, options.max_workers)

    markdown_files: list[Path] = []
    apkg_files: list[Path] = []
    processed_words: list[str] = []

    for file_index, first_chunk_index in enumerate(
        range(0, len(chunks), options.chunks_per_file), start=1
    ):
        last_chunk_index = first_chunk_index + options.chunks_per_file
        batch_chunks = chunks[first_chunk_index:last_chunk_index]
        batch_responses = responses[first_chunk_index:last_chunk_index]
        batch_words = [word for chunk in batch_chunks for word in chunk]

        md_file = md_dir / f"output_{file_index}.md"
        apkg_file = apkg_dir / f"output_{file_index}.apkg"
        save_md_file("\n\n".join(batch_responses), str(md_file), "w")

        if not deck_generator(str(md_file), str(apkg_file), options.deck_name):
            raise RuntimeError(f"failed to generate Anki deck for {md_file}")

        append_history(options.history_path, batch_words)
        processed_words.extend(batch_words)
        markdown_files.append(md_file)
        apkg_files.append(apkg_file)

    return GenerationResult(
        processed_words=processed_words,
        skipped_words=skipped_words,
        markdown_files=markdown_files,
        apkg_files=apkg_files,
        output_markdown_dir=md_dir,
        output_anki_dir=apkg_dir,
    )
