"""Processing module for handling files and Anki deck generation."""

import subprocess


def read_txt_file(input_path: str) -> list[str]:
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


def save_md_file(file_content: str, md_path: str, mode: str = "w") -> None:
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


def generate_anki_deck(md_file: str, output_file: str) -> bool:
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
