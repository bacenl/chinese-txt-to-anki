# Chinese Anki Program Improvement Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Make the Chinese vocab -> markdown -> Anki package generator reliable as both a CLI and an app/dashboard backend.

**Architecture:** Keep the CLI thin and move reusable behavior into importable modules. Model calls go through injected provider adapters so DeepSeek remains the default while OpenAI-compatible or local providers can be added without rewriting the pipeline. The app integration should consume structured results, not scrape stdout.

**Tech Stack:** Python 3.11, `uv`, OpenAI-compatible chat completions client, `mdanki`, pytest.

---

## Current State

The repo originally had a working script-oriented pipeline in `src/main.py`:

1. read newline-delimited Chinese words,
2. filter history,
3. call DeepSeek sequentially,
4. write markdown batches,
5. convert markdown to `.apkg` through `mdanki`,
6. print paths to stdout.

This is good enough for manual CLI use, but weak for a dashboard/app because stdout parsing is brittle, DeepSeek/model selection is hardcoded, and every model request runs serially.

## Work Completed in This Pass

- [x] Replaced the repo `AGENTS.md` with the Lead-provided workflow file under the exact filename `AGENTS.md`.
- [x] Added `src/pipeline.py` with an importable `generate_cards()` API and structured `GenerationResult`.
- [x] Added provider injection so app code can pass any callable `provider(words) -> markdown`.
- [x] Added `src/providers.py` with an OpenAI-compatible provider adapter using env-configurable `MODEL_BASE_URL` and `MODEL_NAME` while preserving DeepSeek defaults.
- [x] Added `--chunk-size` and `--max-workers` CLI flags.
- [x] Added pytest coverage for structured artifacts, history filtering, order preservation, concurrent worker mode, retry behavior, partial failure reporting, and endpoint-safe JSON payloads.
- [x] Kept the dashboard-compatible CLI path working: `uv run anki-gen --input <words.txt> --deck-name <deck>`.
- [x] Added `--json`, `--retry-attempts`, `--retry-backoff-seconds`, and `--continue-on-error` for app integrations.

## Implementation Tasks

### Task 1: Stable importable pipeline API

**Objective:** Stop forcing app callers to shell out and parse stdout.

**Files:**
- Create: `src/pipeline.py`
- Modify: `src/main.py`
- Test: `tests/test_pipeline.py`

**Done:** `generate_cards(options, provider, deck_generator)` returns:

- `processed_words`
- `skipped_words`
- `markdown_files`
- `apkg_files`
- `output_markdown_dir`
- `output_anki_dir`
- `failed_chunks`

**Verification:**

```bash
uv run pytest tests/test_pipeline.py -q
uv run anki-gen --help
```

Expected: tests pass and help shows `--chunk-size` / `--max-workers`.

### Task 2: Provider extensibility

**Objective:** Make DeepSeek the default provider, not the only provider.

**Files:**
- Create: `src/providers.py`
- Modify later: `.env.example`, `README.md`

**Done:** `OpenAICompatibleProvider` accepts:

- `DEEPSEEK_API_KEY` for backwards-compatible auth,
- `MODEL_BASE_URL` for OpenAI-compatible providers,
- `MODEL_NAME` for model selection.

**Next refinement:** Rename the env var model in docs to avoid implying only DeepSeek keys are supported. A clean follow-up is:

```env
MODEL_API_KEY=
MODEL_BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-chat
```

while keeping `DEEPSEEK_API_KEY` as a compatibility fallback.

### Task 3: Throughput controls

**Objective:** Allow faster generation for larger vocab lists without breaking output order.

**Files:**
- Modify: `src/pipeline.py`
- Modify: `src/main.py`
- Test: `tests/test_pipeline.py`

**Done:** `max_workers > 1` runs model requests concurrently with `ThreadPoolExecutor`; results are written back in original chunk order.

**Care point:** Parallelism increases rate-limit pressure. Keep CLI default at `--max-workers 1`; users can opt in with values like `2` or `4` after checking provider limits.

### Task 4: App interaction endpoints / contract

**Objective:** Define what the Hermes dashboard or any future UI should call and receive.

**Recommended app contract:**

```python
from src.pipeline import GenerationOptions, generate_cards
from src.providers import OpenAICompatibleProvider

result = generate_cards(
    GenerationOptions(
        input_path="/tmp/words.txt",
        markdown_root="/tmp/chinese-anki/md",
        anki_root="/tmp/chinese-anki/apkg",
        deck_name="Chinese Vocabulary",
        chunk_size=6,
        max_workers=2,
    ),
    provider=OpenAICompatibleProvider.from_env(),
)
```

Return `result.apkg_files` to the browser/dashboard. Do not infer generated files from stdout.

**Done:** `--json` serializes `GenerationResult.to_dict()` so non-Python callers can use the same structured contract.

### Task 5: Reliability and safety follow-ups

**Objective:** Make generation resumable and safe under failures.

**Todo:**

- [x] Add `--json` CLI mode for structured machine-readable output.
- [x] Add retry/backoff around model calls with clear per-chunk failure reporting.
- [x] Add provider key fallback from `MODEL_API_KEY` to `DEEPSEEK_API_KEY`.
- [x] Add `.env.example` entries for `MODEL_BASE_URL`, `MODEL_NAME`, and `MODEL_API_KEY`.
- [x] Add provider generation knobs for `MODEL_TEMPERATURE` and `MODEL_MAX_TOKENS`.
- [x] Add exact dependency upper bounds in `pyproject.toml` (`openai>=1,<2`, `python-dotenv>=1,<2`) and refresh lockfile if present.
- [ ] Add direct in-process dashboard integration in Hermes after this repo's Python API is consumed there.
- [ ] Add local-only AnkiConnect helper as a separate optional module; do not make the remote server talk to local Anki directly.

## Commit Plan

Use atomic commits:

1. `docs: add agent workflow and implementation plan`
   - `AGENTS.md`
   - `docs/PLAN.md`
   - `docs/IMPLEMENTATION.md`
   - README docs-only updates if included
2. `feat: add importable generation pipeline`
   - `src/pipeline.py`
   - `src/providers.py`
   - `src/main.py`
   - tests for the new pipeline
3. `docs: document provider and throughput options`
   - `README.md`
   - `.env.example` if updated

Before each commit, stage only the files listed for that commit.
