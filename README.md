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

## Setup

1. Clone the repo

```
git clone https://github.com/bacenl/chinese-txt-to-anki-tool ~/YOUR/PATH/HERE
```

2. Copy `.env.example` to `.env` and fill in the values:

```env
DEEPSEEK_API_KEY=your_api_key_here
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
npm install -g mdanki
```

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

Output is organized into timestamped subdirectories under `io/output_md/` and `io/output_apkg/`.

## Prompt

The prompt used to generate card content lives in `io/prompt.txt`. Feel free to edit it.

## Future work

- **Web interface** — deploy as a website so no local setup is needed
- **Model flexibility** — support other API providers (OpenAI, Anthropic, Ollama, etc.) other than just DeepSeek

## License

MIT
