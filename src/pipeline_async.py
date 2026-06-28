"""Async generation pipeline for higher-throughput card generation."""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Callable

import anyio

from .pipeline import (
    DeckGenerator,
    FailedChunk,
    GenerationOptions,
    GenerationResult,
    Provider,
    _ChunkResult,
    _call_provider_with_retries,
    _make_output_dirs,
    append_history,
    load_history,
    read_words,
)
from .processing import CHUNKS_PER_FILE, chunk_list, generate_anki_deck, save_md_file


async def generate_cards_async(
    options: GenerationOptions,
    provider: Provider,
    deck_generator: DeckGenerator = generate_anki_deck,
) -> GenerationResult:
    """Async variant of generate_cards for higher-throughput generation.

    Provider calls run concurrently (bounded by max_workers). Chunk order is
    preserved in the output regardless of completion order.
    """
    words = read_words(options.input_path)
    history = set() if options.ignore_history else load_history(options.history_path)
    skipped_words = [w for w in words if w in history]
    pending_words = [w for w in words if options.ignore_history or w not in history]

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
    chunk_results: list[_ChunkResult | None] = [None] * len(chunks)
    semaphore = anyio.Semaphore(max(1, options.max_workers))

    async def process_chunk(i: int, chunk: list[str]) -> None:
        async with semaphore:
            result = await anyio.to_thread.run_sync(
                functools.partial(
                    _call_provider_with_retries,
                    chunk,
                    provider,
                    options.retry_attempts,
                    options.retry_backoff_seconds,
                    options.prompt_template,
                )
            )
            chunk_results[i] = result
            if result.failure and not options.continue_on_error:
                raise RuntimeError(
                    f"provider failed for chunk {result.failure.words}: {result.failure.error}"
                )

    async with anyio.create_task_group() as tg:
        for i, chunk in enumerate(chunks):
            tg.start_soon(process_chunk, i, chunk)

    completed: list[_ChunkResult] = [r for r in chunk_results if r is not None]

    failed_chunks = [r.failure for r in completed if r.failure]
    successful = [r for r in completed if r.content is not None]

    markdown_files: list[Path] = []
    apkg_files: list[Path] = []
    processed_words: list[str] = []

    chunks_per_file = options.chunks_per_file
    for file_index, start in enumerate(range(0, len(successful), chunks_per_file), start=1):
        batch = successful[start : start + chunks_per_file]
        batch_content = "\n\n".join(r.content or "" for r in batch)
        batch_words = [w for r in batch for w in r.words]

        md_file = md_dir / f"output_{file_index}.md"
        apkg_file = apkg_dir / f"output_{file_index}.apkg"
        save_md_file(batch_content, str(md_file), "w")

        append_history(options.history_path, batch_words)

        if not deck_generator(str(md_file), str(apkg_file), options.deck_name):
            raise RuntimeError(f"failed to generate Anki deck for {md_file}")

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
        failed_chunks=failed_chunks,  # type: ignore[arg-type]
    )
