# Chinese .txt to .apkg (Anki) Tool

> Built this for myself to help myself study Chinese. I could already recognize a good amount of characters, but wanted a better way to compartmentalize new radicals / characters in case I haven't seen them before.

Generates .apkg files (Anki flashcards) from a list of Chinese words using the DeepSeek API. Each word gets a deep, culturally-aware breakdown, allowing for better contextualization and learning.

> [!IMPORTANT]
> Still kind of just for personal use, so there may be issues if using on other machines (oops)

## How it works

1. Read a plain-text list of Chinese words (from `/io/input.txt`)
2. Send them in batches to the DeepSeek API using a structured prompt
3. Save the responses as markdown files
4. Convert the markdown to Anki packages (`.apkg`) via `mdanki`
5. Track processed words in a history file to avoid duplicates on future runs

## Current workflow with Hermes dashboard

This repository owns the Chinese vocab -> markdown -> `.apkg` generation logic. The Hermes Personal Workspace dashboard calls this project instead of duplicating the Anki pipeline.

Current flow:

1. Open the Hermes dashboard from the local machine where Anki is running.
2. Go to the Chinese Anki tab (`/chinese-anki`).
3. Paste a vocab list.
4. The remote Hermes server writes the vocab list to a temporary `.txt` file and runs this repo's CLI, usually through `uv run anki-gen --input <words.txt> --deck-name <deck>`.
5. The dashboard records the batch, captures stdout/stderr, copies discovered `.apkg` outputs into Hermes' profile workspace, and exposes download links.
6. The dashboard probes browser-to-local AnkiConnect at `http://127.0.0.1:8765` as the basis for one-click import.
7. If AnkiConnect is unavailable or blocked by browser/CORS settings, download the generated `.apkg` and import it manually in Anki.

This keeps local Anki private/local while letting the remote server do the card-generation work.

## Setup

1. Clone the repo

```
git clone https://github.com/bacenl/chinese-txt-to-anki ~/YOUR/PATH/HERE
```

2. Copy `.env.example` to `.env` and fill in the values:

```env
MODEL_API_KEY=your_api_key_here
MODEL_BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-chat

# Backwards-compatible alias for older setups; prefer MODEL_API_KEY for new configs.
DEEPSEEK_API_KEY=

INPUT_TXT_PATH=io/input.txt
OUTPUT_MD_PATH=io/output_md
OUTPUT_ANKI_PATH=io/output_apkg
PROMPT_PATH=io/prompt.txt
```

3. Edit / Create your input file (default is `io/input.txt`)— one Chinese word per line:

```
你好
谢谢
```

4. Install dependencies:

<details>
<summary>With uv (recommended)</summary>

```bash
uv sync
```

</details>

<details>
<summary>Without uv</summary>

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

</details>

5. Install [`mdanki`](https://github.com/ashlinchak/mdanki) (Node.js, required for `.apkg` generation):

```bash
# Prefer a reviewed pinned version if you know the version you want.
npm install -g mdanki
```

Supply-chain note: keep `uv.lock` committed, use `uv sync --frozen`, and see `docs/SUPPLY_CHAIN_SECURITY.md` before changing dependencies or globally installed tools.

## Usage

<details>
<summary>With uv</summary>

```bash
# Full pipeline: call API and generate Anki decks
uv run anki-gen

# Use a custom input file
uv run anki-gen --input path/to/words.txt

# Skip the API call and convert an existing markdown file
uv run anki-gen --no-api --markdown path/to/file.md

# Export to a specific Anki deck name
uv run anki-gen --deck-name "HSK 3"

# Process all words, even if they have appeared in .cache/history
uv run anki-gen --ignore-history

# Tune model request batching and opt into parallel requests
uv run anki-gen --chunk-size 6 --max-workers 2
```

</details>

<details>
<summary>Without uv</summary>

Activate the virtual environment first:

```bash
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
```

Then run:

```bash
# Full pipeline: call API and generate Anki decks
python -m src.main

# Use a custom input file
python -m src.main --input path/to/words.txt

# Skip the API call and convert an existing markdown file
python -m src.main --no-api --markdown path/to/file.md

# Export to a specific Anki deck name
python -m src.main --deck-name "HSK 3"

# Process all words, even if they have appeared in .cache/history
python -m src.main --ignore-history
```

</details>

### All flags

| Flag | Short | Description |
|---|---|---|
| `--input` | `-i` | Input `.txt` file with Chinese words |
| `--output` | `-o` | Output Anki package path |
| `--markdown` | `-md` | Markdown file to use or generate |
| `--no-api` | `-na` | Skip API call, use existing markdown file |
| `--ignore-history` | `-ih` | Reprocess previously parsed words |
| `--deck-name` | `-d` | Anki deck name (default: `Chinese Vocabulary`) |
| `--chunk-size` | | Words per model request (default: `6`) |
| `--max-workers` | | Concurrent model requests (default: `1`; raise carefully to avoid rate limits) |

Output is organized into timestamped subdirectories under `io/output_md/` and `io/output_apkg/`.

## Prompt

The prompt used to generate card content lives in `io/prompt.txt`. Feel free to edit it.

## Future work

- **Hermes dashboard integration** — exposed through the Hermes Personal Workspace Chinese Anki tab with paste-to-generate, batch history, `.apkg` download, and AnkiConnect probing. Next step: direct add-note/import action after AnkiConnect CORS is confirmed in the local browser.
- **Machine-readable CLI output** — add `--json` so non-Python callers can consume structured paths without stdout scraping.
- **Model flexibility** — `MODEL_BASE_URL` and `MODEL_NAME` support OpenAI-compatible providers; next step is documenting tested provider presets and adding local-model/Ollama examples.

## License

MIT
