"""Generate Anki cards from Chinese words using DeepSeek API."""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
TXT_PATH = os.getenv("TXT_PATH")
MD_PATH = os.getenv("MD_PATH")
ANKI_PATH = os.getenv("ANKI_PATH")


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments.
    
    Returns:
        argparse.Namespace: Parsed command line arguments.
        
    Example:
        >>> args = parse_arguments()
        >>> print(args.input)
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
        default=TXT_PATH,
        help=f"Input file with Chinese words (default: {TXT_PATH})",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=ANKI_PATH,
        help=f"Output Anki package name (default: {ANKI_PATH})",
    )
    parser.add_argument(
        "--markdown",
        "-md",
        default=MD_PATH,
        help=f"Markdown file to use/generate (default: {MD_PATH})",
    )

    return parser.parse_args()


def read_txt_file(input_path: str = TXT_PATH) -> list[str]:
    """Read Chinese words from a text file.
    
    Args:
        input_path: Path to the input text file.
        
    Returns:
        List of Chinese words with empty lines filtered out.
        
    Raises:
        FileNotFoundError: If the input file doesn't exist.
        
    Example:
        >>> words = read_txt_file("words.txt")
        >>> print(f"Found {len(words)} words")
    """
    with open(input_path, "r", encoding="utf-8") as file:
        words = [line.strip() for line in file if line.strip()]
    return words


def create_prompt(words: list[str]) -> str:
    """Create a formatted prompt for DeepSeek API.
    
    Args:
        words: List of Chinese words to analyze.
        
    Returns:
        Formatted prompt string for the API.
        
    Example:
        >>> prompt = create_prompt(["你好", "谢谢"])
        >>> print(len(prompt))
    """
    words_text = "\n".join(words)
    prompt = f"""I want to understand the following Chinese word(s) in deep, cultural, and practical context:

{words_text}

Please analyze each word using the following structured framework:

    0. **Word**
    *   Provide the word
    *   Provide the pinyin (on a separate line)
    *   State the word type (noun, verb, adjectival verb, adjective, adverb, etc.)
    *   Prepend with ## 

1.  **Core Meaning & Character Breakdown:**
    *   Provide the pinyin and core English translation(s).
    *   Deconstruct the character(s) etymologically and visually. Explain the radicals and components and what they contribute to the overall meaning.

2.  **Key Dimensions & Nuances:**
    *   Go beyond the dictionary definition. Explain the word's philosophical, emotional, or social connotations.
    *   If applicable, mention its origin (e.g., Classical Chinese, Buddhist influence, modern slang).

3.  **Usage in Everyday Life:**
    *   Provide common words, phrases, or idioms that use this character.
    *   Give a short, practical example sentence for each, with pinyin and English translation.
    *   Explain the context or feeling these phrases evoke.

4.  **A Guiding Philosophy:**
    *   Summarize the core concept behind the word. How can one use this concept as a lens for viewing life, relationships, or society? Offer an analogy if helpful.

Analyze each word on the list individually and thoroughly.
ONLY RESPOND WITH THE ANSWERS TO THE QUERY. DO NOT PROVIDE ANY OTHER STATEMENTS.

Example
## 混账 

(hùnzhàng)
Noun

**1. Core Meaning & Character Breakdown:**
- **Translation:** Scoundrel; bastard; son of a bitch (a severe insult).
- **Breakdown:**
    - **混 (hùn):** 'To mix,' 'to confuse,' 'muddled.' Carries a sense of being irresponsible, muddle-headed, or just getting by (e.g., 混日子, to idle away one's life).
    - **账 (zhàng):** 'Account,' 'bill,' 'debt.' In historical context, keeping accurate accounts was a matter of honor and trust.

**2. Key Dimensions & Nuances:**
- This is a powerful curse word. It originally implied someone who has muddled their accounts—a dishonest, untrustworthy person who doesn't keep their word. It's now a general-purpose insult questioning someone's character and moral standing, often with a connotation of anger and contempt.

**3. Usage in Everyday Life:**
- It's used as a direct insult or an exclamation of fury.
    - **Phrase:** 你这个混账！ (Nǐ zhège hùnzhàng!)
    - **Example:** '你竟敢骗我，混账！' (Nǐ jìng gǎn piàn wǒ, hùnzhàng!) - 'How dare you cheat me, you bastard!'
    - **Feeling:** Intense anger, betrayal, and deep disrespect.

**4. A Guiding Philosophy:**
- It reflects a cultural emphasis on integrity and trust, especially in financial and social obligations. To call someone 混账 is to say they have violated the fundamental trust that holds relationships together.
"""
    return prompt


def call_deepseek_api(prompt: str) -> str:
    """Call DeepSeek API with the given prompt.
    
    Args:
        prompt: The prompt to send to the API.
        
    Returns:
        API response content as string.
        
    Raises:
        Exception: If API call fails.
        
    Example:
        >>> response = call_deepseek_api("Explain 你好")
        >>> print(response[:100])
    """
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user", "content": prompt},
        ],
        stream=False,
    )

    return response.choices[0].message.content


def save_md_file(file_content: str, md_path: str = MD_PATH, mode: str = "w") -> None:
    """Save content to markdown file.
    
    Args:
        file_content: Content to write to the file.
        md_path: Path to the markdown file.
        mode: File mode - 'w' for write, 'a' for append.
        
    Example:
        >>> save_md_file("# Heading", "output.md")
        >>> save_md_file("More content", "output.md", "a")
    """
    with open(md_path, mode, encoding="utf-8") as f:
        f.write(file_content)
        if mode == "a" and not file_content.endswith("\n"):
            f.write("\n")


def generate_anki_deck(md_file: str = MD_PATH, output_file: str = ANKI_PATH) -> bool:
    """Generate Anki package from markdown file using mdanki.
    
    Args:
        md_file: Path to input markdown file.
        output_file: Path to output Anki package.
        
    Returns:
        True if successful, False otherwise.
        
    Example:
        >>> success = generate_anki_deck("cards.md", "chinese.apkg")
        >>> print(f"Generation successful: {success}")
    """
    try:
        result = subprocess.run(
            ["mdanki", md_file, output_file, "--deck", "Chinese Vocabulary"],
            shell=True,
            capture_output=True,
            text=True,
            check=True,
        )

        print("Anki Cards Generated Successfully!")
        return True

    except subprocess.CalledProcessError as e:
        print(f"Error generating Anki package: {e}")
        print(f"stderr: {e.stderr}")
        return False

    except FileNotFoundError:
        print("Error: mdanki not found. Make sure Node.js is installed and run: npm install")
        return False


def chunk_list(lst: list, chunk_size: int) -> list[list]:
    """Split list into chunks of specified size.
    
    Args:
        lst: List to chunk.
        chunk_size: Size of each chunk.
        
    Returns:
        List of chunks.
        
    Example:
        >>> chunks = chunk_list([1, 2, 3, 4, 5], 2)
        >>> print(chunks)
        [[1, 2], [3, 4], [5]]
    """
    return [lst[i : i + chunk_size] for i in range(0, len(lst), chunk_size)]


def main() -> None:
    """Main function to orchestrate the Anki card generation pipeline.
    
    Steps:
    1. Parse command line arguments
    2. Read Chinese words from input file
    3. Process words in chunks via DeepSeek API
    4. Generate Anki package from markdown
    
    Example:
        >>> main()
    """
    args = parse_arguments()

    if args.no_api:
        # Skip API call, use existing markdown file
        print("Skipping DeepSeek API call (--no-api flag used)")
        if not os.path.exists(args.markdown):
            print(f"Error: Markdown file {args.markdown} not found")
            sys.exit(1)
    else:
        # Generate prompt and call API in chunks
        chinese_words = read_txt_file(args.input)
        print(f"Loaded {len(chinese_words)} Chinese words")

        # Clear the markdown file to start fresh
        if os.path.exists(args.markdown):
            os.remove(args.markdown)
            print(f"Cleared existing markdown file: {args.markdown}")

        # Split words into chunks of 6
        chunk_size = 6
        chunks = chunk_list(chinese_words, chunk_size)
        print(f"Processing {len(chunks)} chunks of {chunk_size} words each...")

        if not DEEPSEEK_API_KEY:
            print("Error: Please set DEEPSEEK_API_KEY environment variable")
            sys.exit(1)

        # Process each chunk
        for i, chunk in enumerate(chunks, 1):
            print(f"Processing chunk {i}/{len(chunks)}: {chunk}")

            prompt = create_prompt(chunk)
            markdown_content = call_deepseek_api(prompt)

            if markdown_content:
                # Append to the markdown file
                mode = "a" if i > 1 else "w"
                save_md_file(markdown_content, args.markdown, mode)

                # Add spacing between chunks if not the last one
                if i < len(chunks):
                    save_md_file("\n\n", args.markdown, "a")

                print(f"✓ Successfully processed chunk {i}/{len(chunks)}")
            else:
                print(f"✗ Failed to get response for chunk {i}")
                sys.exit(1)

            # Small delay to be respectful to the API
            time.sleep(1)

        print(f"Markdown file saved: {args.markdown}")

    # Generate Anki package (always do this)
    print("Generating Anki package...")
    if generate_anki_deck(args.markdown, args.output):
        print("Pipeline completed successfully!")
        print(f"Anki package created: {args.output}")
    else:
        print("Failed to generate Anki package")


if __name__ == "__main__":
    main()
