"""Cache module for managing word history."""

import os

CACHE_DIR = ".cache"
HISTORY_FILE = os.path.join(CACHE_DIR, "history.txt")


def ensure_cache_dir() -> None:
    """Create .cache directory if it doesn't exist.
    
    Example:
        >>> ensure_cache_dir()
    """
    os.makedirs(CACHE_DIR, exist_ok=True)


def load_history() -> set[str]:
    """Load previously parsed words from history file.
    
    Returns:
        Set of previously parsed words.
        
    Example:
        >>> history = load_history()
        >>> print(f"Found {len(history)} previously parsed words")
    """
    ensure_cache_dir()
    
    if not os.path.exists(HISTORY_FILE):
        return set()
    
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def save_to_history(words: list[str]) -> None:
    """Save newly parsed words to history file.
    
    Args:
        words: List of words to add to history.
        
    Example:
        >>> save_to_history(["你好", "谢谢"])
    """
    ensure_cache_dir()
    
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        for word in words:
            f.write(f"{word}\n")


def clear_history() -> None:
    """Clear the history file.
    
    Example:
        >>> clear_history()
    """
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)
