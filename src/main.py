"""Main entry point for Anki card generator."""

import argparse
import os
import sys

from dotenv import load_dotenv

from cache import load_history, save_to_history
from api import (
    create_prompt,
    call_deepseek_api,
)
from processing import (
    CHUNKS_PER_FILE,
    read_txt_file,
    create_timestamped_folders,
    save_md_file,
    generate_anki_deck,
    chunk_list,
)

load_dotenv()

INPUT_TXT_PATH = os.getenv("INPUT_TXT_PATH")
OUTPUT_MD_PATH = os.getenv("OUTPUT_MD_PATH")
OUTPUT_ANKI_PATH = os.getenv("OUTPUT_ANKI_PATH")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments.
    
    Returns:
        argparse.Namespace: Parsed command line arguments.
    """
    parser = argparse.ArgumentParser(description="Generate Anki cards from Chinese words")
    parser.add_argument(
        "--no-api",
        "-na",
        action="store_true",
        help="Skip DeepSeek API call (use existing markdown file)",
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
        help=f"Output Anki package name (default: {OUTPUT_ANKI_PATH})",
    )
    parser.add_argument(
        "--markdown",
        "-md",
        default=OUTPUT_MD_PATH,
        help=f"Markdown file to use/generate (default: {OUTPUT_MD_PATH})",
    )
    parser.add_argument(
        "--skip-history",
        "-sh",
        action="store_true",
        help="Skip filtering out previously parsed words",
    )

    return parser.parse_args()


def main() -> None:
    """Main function to orchestrate the Anki card generation pipeline.
    
    Steps:
    1. Parse command line arguments
    2. Read Chinese words from input file
    3. Filter out previously parsed words (unless --skip-history)
    4. Process words in chunks via DeepSeek API
    5. Save processed words to history
    6. Generate Anki package from markdown
    """
    args = parse_arguments()

    if args.no_api:
        # Skip API call, use existing markdown file
        print("Skipping DeepSeek API call (--no-api flag used)")
        if not os.path.exists(args.markdown):
            print(f"Error: Markdown file {args.markdown} not found")
            sys.exit(1)
    else:
        # Load history and read words
        history = load_history() if not args.skip_history else set()
        chinese_words = read_txt_file(args.input)
        
        if history:
            print(f"Loaded {len(history)} previously parsed words from history")
        
        print(f"Loaded {len(chinese_words)} Chinese words from input file")
        
        # Filter out previously parsed words
        if not args.skip_history:
            original_count = len(chinese_words)
            filtered_words = [word for word in chinese_words if word in history]
            chinese_words = [word for word in chinese_words if word not in history]
            filtered_count = len(filtered_words)
            
            if filtered_count > 0:
                print(f"Filtered out {filtered_count} previously parsed words:")
                print(f"  {', '.join(filtered_words)}")
            
            if not chinese_words:
                print("All words have been previously parsed. Nothing to do!")
                print("Use --skip-history flag to reprocess all words.")
                sys.exit(0)
        
        print(f"Processing {len(chinese_words)} new words")

        # Create timestamped output folders
        md_folder, apkg_folder = create_timestamped_folders()
        print(f"Created output folders:")
        print(f"  Markdown: {md_folder}/")
        print(f"  Anki: {apkg_folder}/")

        # Split words into chunks of 6
        chunk_size = 6
        chunks = chunk_list(chinese_words, chunk_size)
        print(f"Processing {len(chunks)} chunks of {chunk_size} words each...")

        if not DEEPSEEK_API_KEY:
            print("Error: Please set DEEPSEEK_API_KEY environment variable")
            sys.exit(1)

        # Process each chunk
        all_processed_words = []
        current_file_index = 1
        current_file_chunks = []
        
        for i, chunk in enumerate(chunks, 1):
            print(f"Processing chunk {i}/{len(chunks)}: {chunk}")

            prompt = create_prompt(chunk)
            markdown_content = call_deepseek_api(prompt, DEEPSEEK_API_KEY)

            if markdown_content:
                # Add to current file's chunks
                current_file_chunks.append(markdown_content)
                
                # Track successfully processed words from this chunk
                all_processed_words.extend(chunk)
                
                # Save this chunk to history immediately after successful processing
                save_to_history(chunk)

                print(f"✓ Successfully processed chunk {i}/{len(chunks)}")
                
                # Check if we should save the file (every CHUNKS_PER_FILE chunks or last chunk)
                if i % CHUNKS_PER_FILE == 0 or i == len(chunks):
                    # Create output files for this batch
                    md_file = os.path.join(md_folder, f"output_{current_file_index}.md")
                    apkg_file = os.path.join(apkg_folder, f"output_{current_file_index}.apkg")
                    
                    # Combine all chunks for this file
                    combined_content = "\n\n".join(current_file_chunks)
                    save_md_file(combined_content, md_file, "w")
                    
                    # Generate Anki deck for this batch
                    if generate_anki_deck(md_file, apkg_file):
                        print(f"  → Saved file {current_file_index}: {md_file}")
                        print(f"  → Saved file {current_file_index}: {apkg_file}")
                    else:
                        print(f"✗ Failed to generate Anki deck for file {current_file_index}")
                        sys.exit(1)
                    
                    # Reset for next file
                    current_file_index += 1
                    current_file_chunks = []
                    
            else:
                print(f"✗ Failed to get response for chunk {i}")
                sys.exit(1)

            # Small delay to be respectful to the API
            import time
            time.sleep(1)

        print(f"\n{'='*60}")
        print(f"Pipeline completed successfully!")
        print(f"Saved {len(all_processed_words)} words to history")
        print(f"Generated {current_file_index - 1} markdown files in: {md_folder}/")
        print(f"Generated {current_file_index - 1} Anki packages in: {apkg_folder}/")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
