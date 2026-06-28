"""API utilities for prompt construction."""

import os

from dotenv import load_dotenv

load_dotenv()

PROMPT_PATH = os.getenv("PROMPT_PATH")


def load_prompt_template() -> str:
    """Load the prompt template from the file at PROMPT_PATH."""
    if not PROMPT_PATH or not os.path.exists(PROMPT_PATH):
        raise FileNotFoundError(
            f"Prompt template not found at {PROMPT_PATH!r}. "
            "Set the PROMPT_PATH environment variable."
        )
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()


def create_prompt(words: list[str]) -> str:
    """Build a formatted prompt for the configured template."""
    template = load_prompt_template()
    return template.replace("{words_text}", "\n".join(words))
