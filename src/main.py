"""Main entry point for Anki card generator."""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from .pipeline import GenerationOptions, generate_cards
from .processing import create_timestamped_folders, generate_anki_deck
from .providers import OpenAICompatibleProvider, get_provider, list_providers

load_dotenv()

INPUT_TXT_PATH = os.getenv("INPUT_TXT_PATH")
OUTPUT_MD_PATH = os.getenv("OUTPUT_MD_PATH")
OUTPUT_ANKI_PATH = os.getenv("OUTPUT_ANKI_PATH")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Anki cards from Chinese words")
    parser.add_argument(
        "--no-api", "-na", action="store_true",
        help="Skip model API call and convert an existing markdown file",
    )
    parser.add_argument(
        "--input", "-i", default=INPUT_TXT_PATH,
        help=f"Input file with Chinese words (default: {INPUT_TXT_PATH})",
    )
    parser.add_argument(
        "--output", "-o", default=OUTPUT_ANKI_PATH,
        help=f"Output Anki package root/path (default: {OUTPUT_ANKI_PATH})",
    )
    parser.add_argument(
        "--markdown", "-md", default=OUTPUT_MD_PATH,
        help=f"Markdown file/root to use or generate (default: {OUTPUT_MD_PATH})",
    )
    parser.add_argument(
        "--ignore-history", "-ih", action="store_true",
        help="Parse all input words, even if they appear in history",
    )
    parser.add_argument(
        "--deck-name", "-d", default="Chinese Vocabulary",
        help="Name of the Anki deck (default: Chinese Vocabulary)",
    )
    parser.add_argument(
        "--chunk-size", type=int, default=6,
        help="Words to send per model request (default: 6)",
    )
    parser.add_argument(
        "--max-workers", type=int, default=1,
        help="Concurrent model requests to run (default: 1)",
    )
    parser.add_argument(
        "--retry-attempts", type=int, default=1,
        help="Attempts per model request before failing (default: 1)",
    )
    parser.add_argument(
        "--retry-backoff-seconds", type=float, default=1.0,
        help="Linear backoff seconds between retries (default: 1.0)",
    )
    parser.add_argument(
        "--continue-on-error", action="store_true",
        help="Continue generating and report failed chunks instead of aborting",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Print machine-readable GenerationResult JSON",
    )
    parser.add_argument(
        "--provider", default="deepseek",
        help="Provider name: deepseek, openai, ollama (default: deepseek)",
    )
    parser.add_argument(
        "--list-providers", action="store_true",
        help="List registered provider names and exit",
    )
    parser.add_argument(
        "--async", dest="use_async", action="store_true",
        help="Use the async pipeline for higher throughput",
    )
    parser.add_argument(
        "--rate-limit", type=float, default=0,
        help="Max requests per minute (0 = unlimited)",
    )
    parser.add_argument(
        "--auto-import", action="store_true",
        help="Push generated .apkg files into a running Anki via AnkiConnect",
    )
    parser.add_argument(
        "--config", default=None, metavar="PATH",
        help="Path to a TOML config file",
    )
    parser.add_argument(
        "--prompt", default=None, metavar="PATH",
        help="Path to a custom prompt template file",
    )
    return parser.parse_args()


def _convert_existing_markdown(args: argparse.Namespace) -> None:
    markdown_path = Path(args.markdown)
    if not markdown_path.exists() or not markdown_path.is_file():
        print(f"Error: Markdown file {markdown_path} not found")
        sys.exit(1)

    output_path = Path(args.output or "io/output_apkg/output.apkg")
    if output_path.suffix != ".apkg":
        output_path.mkdir(parents=True, exist_ok=True)
        output_path = output_path / f"{markdown_path.stem}.apkg"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not generate_anki_deck(str(markdown_path), str(output_path), args.deck_name):
        sys.exit(1)

    print("Pipeline completed successfully!")
    print(f"Generated Anki package: {output_path}")


def main() -> None:
    args = parse_arguments()

    if args.list_providers:
        print(", ".join(list_providers()))
        return

    if args.no_api:
        print("Skipping model API call (--no-api flag used)")
        _convert_existing_markdown(args)
        return

    if not args.input:
        message = "input file is required. Set INPUT_TXT_PATH or pass --input"
        if args.json:
            print(json.dumps({"ok": False, "error": message}))
        else:
            print(f"Error: {message}")
        sys.exit(1)

    prompt_template = ""
    if args.prompt:
        prompt_template = Path(args.prompt).read_text(encoding="utf-8")

    try:
        provider = get_provider(args.provider)
        md_folder, apkg_folder = create_timestamped_folders()
        options = GenerationOptions(
            input_path=args.input,
            markdown_root=md_folder,
            anki_root=apkg_folder,
            deck_name=args.deck_name,
            chunk_size=args.chunk_size,
            ignore_history=args.ignore_history,
            max_workers=args.max_workers,
            retry_attempts=args.retry_attempts,
            retry_backoff_seconds=args.retry_backoff_seconds,
            continue_on_error=args.continue_on_error,
            prompt_template=prompt_template,
        )

        if args.use_async:
            from .pipeline_async import generate_cards_async
            result = asyncio.run(generate_cards_async(options, provider=provider))
        else:
            result = generate_cards(options, provider=provider)
    except Exception as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        else:
            print(f"Error: {exc}")
        sys.exit(1)

    if args.auto_import:
        from .anki_connect import AnkiConnectClient
        client = AnkiConnectClient()
        for apkg_path in result.apkg_files:
            client.import_apkg(str(apkg_path))

    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False))
        return

    if result.skipped_words:
        print(f"Filtered out {len(result.skipped_words)} previously parsed words:")
        print(f"  {', '.join(result.skipped_words)}")

    if not result.processed_words:
        print("All words have been previously parsed. Nothing to do!")
        print("Use --ignore-history flag to reprocess all words.")
        return

    print(f"\n{'=' * 60}")
    print("Pipeline completed successfully!")
    print(f"Saved {len(result.processed_words)} words to history")
    print(f"Generated {len(result.markdown_files)} markdown files in: {result.output_markdown_dir}/")
    print(f"Generated {len(result.apkg_files)} Anki packages in: {result.output_anki_dir}/")
    for path in result.apkg_files:
        print(f"  → {path}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
