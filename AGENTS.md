# AGENTS.md - Chinese to Anki Card Generator

This file provides essential guidelines for agentic coding agents working on this Chinese Markdown to Anki card generator project.

## Project Overview

This Python project generates Anki flashcards from Chinese vocabulary using the DeepSeek API. It processes Chinese words in chunks, generates detailed markdown content with linguistic analysis, and converts it to Anki-compatible `.apkg` files using the external `mdanki` tool.

## Development Environment

- **Python**: >=3.11 (as specified in pyproject.toml)
- **Package Manager**: Uses both `requirements.txt` and `pyproject.toml` (uv.lock indicates modern tooling)
- **Virtual Environment**: Located in `.venv/` (already set up)

## Build & Run Commands

### Core Commands
```bash
# Install dependencies
pip install -r requirements.txt
# OR with uv (if available)
uv sync

# Run main application
python src/main.py

# Run with specific arguments
python src/main.py --input custom_words.txt --output custom_deck.apkg

# Skip API calls (use existing markdown)
python src/main.py --no-api

# Skip history filtering
python src/main.py --skip-history
```

### Testing Commands
```bash
# No formal test suite currently exists
# Manual testing workflow:
python src/main.py --help  # Test argument parsing
python src/main.py --no-api  # Test with existing files
```

### External Dependencies
```bash
# Required external tool (Node.js package)
npm install -g mdanki
# Ensure Node.js is installed for Anki deck generation
```

## Code Style Guidelines

### Import Organization
- Standard library imports first, then third-party, then local imports
- Use `from .module import function` for relative imports within the `src/` package
- Environment variable loading with `python-dotenv` should be done at module level

```python
# Standard library
import os
import sys
import argparse
from datetime import datetime

# Third-party
from openai import OpenAI
from dotenv import load_dotenv

# Local imports
from .api import create_prompt, call_deepseek_api
from .processing import CHUNKS_PER_FILE, read_txt_file
```

### Type Hints
- All functions should have complete type annotations
- Use Python 3.11+ syntax: `list[str]`, `tuple[str, str]`, `set[str]`
- Return types explicitly declared even for `None`

```python
def process_words(words: list[str], chunk_size: int = 6) -> tuple[list[list[str]], int]:
    """Process words into chunks and return chunks with total count."""
    chunks = chunk_list(words, chunk_size)
    return chunks, len(words)
```

### Function Documentation
- Every function needs a docstring following the pattern shown in existing code
- Include Args, Returns, and Example sections
- Use triple quotes with consistent formatting

### Naming Conventions
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `CHUNKS_PER_FILE`, `DEEPSEEK_API_KEY`)
- **Functions**: `snake_case` with descriptive names
- **Variables**: `snake_case`, prefer clarity over brevity
- **Private functions**: Use leading underscore only if truly internal

### Error Handling
- Use descriptive error messages with context
- Include file paths and operation details in error messages
- Graceful degradation for optional external dependencies
- Environment variable validation at startup

```python
if not DEEPSEEK_API_KEY:
    print("Error: Please set DEEPSEEK_API_KEY environment variable")
    sys.exit(1)
```

### Environment Variables
All configuration through `.env` file:
- `INPUT_TXT_PATH`: Default input file location
- `OUTPUT_MD_PATH`: Default markdown output path  
- `OUTPUT_ANKI_PATH`: Default Anki package output path
- `DEEPSEEK_API_KEY`: API authentication key
- `PROMPT_PATH`: Location of prompt template file

### File Structure & Patterns
- **Main entry point**: `src/main.py` with argument parsing and orchestration
- **API interactions**: `src/api.py` for external service calls
- **File processing**: `src/processing.py` for file I/O and Anki generation
- **Caching**: `src/cache.py` for history management
- **Output**: Timestamped folders in `io/output_md/` and `io/output_apkg/`

### Code Organization Principles
- Single responsibility per module
- Configuration centralized through environment variables
- Chunking strategy for API rate limit management (6 words per chunk, 8 chunks per file)
- History tracking to avoid reprocessing words
- Immediate history saves after successful API calls

### Integration Notes
- **External dependency**: `mdanki` tool must be available in PATH
- **Subprocess usage**: Used only for `mdanki` calls with proper error handling
- **File encoding**: Always use UTF-8 for Chinese text handling
- **Atomic operations**: Save to history immediately after successful processing

### Development Workflow
1. Test argument parsing with `--help`
2. Validate environment variables are set
3. Test `--no-api` mode with existing markdown files
4. Test full pipeline with small input files
5. Verify Anki package generation with `mdanki` availability

## Key Constants to Remember
- `CHUNKS_PER_FILE = 8`: Number of chunks before creating new files
- Default chunk size: 6 words per API call
- Cache directory: `.cache/history.txt`
- Default deck name: "Chinese Vocabulary"