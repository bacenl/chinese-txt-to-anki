"""Main entry point for Anki card generator."""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from .pipeline import GenerationOptions, generate_cards
from .processing import create_timestamped_folders, generate_anki_deck
from .providers import OpenAICompatibleProvider

load_dotenv()

INPUT_TXT_PATH = os.getenv("INPUT_TXT_PATH")
OUTPUT_MD_PATH = os.getenv("OUTPUT_MD_PATH")
OUTPUT_ANKI_PATH = os.getenv("OUTPUT_ANKI_PATH")


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        argparse.Namespace: Parsed command line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Generate Anki cards from Chinese words"
    )
    parser.add_argument(
        "--no-api",
        "-na",
        action="store_true",
        help="Skip model API call and convert an existing markdown file",
    )
    parser.add_argument(
        "--input",
        "-i",
        default=INPUT_TXT_PATH,
        help=f"Input file with Chinese words (default: {INPUT_TXT_PATH})",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=OUTPUT_ANKI_PATH,
        help=f"Output Anki package root/path (default: {OUTPUT_ANKI_PATH})",
    )
    parser.add_argument(
        "--markdown",
        "-md",
        default=OUTPUT_MD_PATH,
        help=f"Markdown file/root to use or generate (default: {OUTPUT_MD_PATH})",
    )
    parser.add_argument(
        "--ignore-history",
        "-ih",
        action="store_true",
        help="Parse all input words, even if they appear in .cache/history.txt",
    )
    parser.add_argument(
        "--deck-name",
        "-d",
        default="Chinese Vocabulary",
        help="Name of the Anki deck to import cards to (default: Chinese Vocabulary)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=6,
        help="Words to send per model request (default: 6)",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=1,
        help="Concurrent model requests to run (default: 1)",
    )

    return parser.parse_args()


def _convert_existing_markdown(args: argparse.Namespace) -> None:
    """Convert an existing markdown file to an Anki package."""

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
    """Run the CLI wrapper around the importable generation pipeline."""

    args = parse_arguments()

    if args.no_api:
        print("Skipping model API call (--no-api flag used)")
        _convert_existing_markdown(args)
        return

    if not args.input:
        print("Error: input file is required. Set INPUT_TXT_PATH or pass --input")
        sys.exit(1)

    try:
        provider = OpenAICompatibleProvider.from_env()
        md_folder, apkg_folder = create_timestamped_folders()
        result = generate_cards(
            GenerationOptions(
                input_path=args.input,
                markdown_root=md_folder,
                anki_root=apkg_folder,
                deck_name=args.deck_name,
                chunk_size=args.chunk_size,
                ignore_history=args.ignore_history,
                max_workers=args.max_workers,
            ),
            provider=provider,
        )
    except Exception as exc:
        print(f"Error: {exc}")
        sys.exit(1)

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
