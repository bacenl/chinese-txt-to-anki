# Chinese Anki Program — Next-Phase Improvement Plan

> **For Hermes:** Use subagent-driven-development to implement this plan task-by-task.

**Goal:** Evolve the Chinese vocab → markdown → Anki package generator into a flexible, high-throughput, production-grade tool with clean app/dashboard integration surfaces.

**Architecture:** Provider-agnostic core with a registry pattern for pluggable backends. Async pipeline for throughput without manual thread tuning. A thin HTTP/WSGI layer for dashboard integration plus a local AnkiConnect bridge for one-click import.

**Tech Stack:** Python 3.11+, `uv`, openai client, httpx/anyio, FastAPI (optional web layer), mdanki, pytest.

---

## Current State

The repo already has:

- `src/pipeline.py` — importable `generate_cards()` with `GenerationOptions` / `GenerationResult` dataclasses
- `src/providers.py` — `OpenAICompatibleProvider` with env-based config (key, base URL, model, temperature, max tokens)
- `src/main.py` — thin CLI wrapping the pipeline with `--json`, `--chunk-size`, `--max-workers`, `--retry-attempts`, `--continue-on-error`
- `src/processing.py` — utility functions (chunking, timestamp folders, mdanki subprocess)
- `src/api.py` — prompt template loading and `create_prompt()` (still hardcoded to DeepSeek at the core)
- `src/cache.py` — word history tracking (partially superseded by pipeline's configurable history path)
- `tests/test_pipeline.py` — 10 tests covering structured output, history filtering, order preservation, retry, partial failures, endpoint-safe JSON, and provider env fallback

**What still needs work:**

### Extensibility gaps
- No dynamic provider registration (must import `OpenAICompatibleProvider` directly)
- `src/api.py` still references `call_deepseek_api()` with hardcoded `https://api.deepseek.com`
- Prompt templates live on disk but aren't injectable at the pipeline level
- No non-OpenAI provider examples (Ollama, Anthropic, Google)

### Throughput gaps
- Thread-based parallelism (`ThreadPoolExecutor`) works for I/O-bound model calls but doesn't scale beyond a handful of workers
- No rate-limit-aware scheduling (if provider rate-limits at N req/min, overshooting causes retry churn)
- No streaming — full response arrives before any card is written
- History appending happens inside the loop after mdanki conversion; if mdanki is slow, history isn't persisted early

### App integration gaps
- No standard web API — dashboards shell out to the CLI or import Python directly
- No AnkiConnect helper for local one-click import
- Dashboard caller currently manual-copies `.apkg` from server; no download endpoint
- No webhook/callback for async generation (e.g., "generate this vocab list and POST the result to a callback URL")

### Reliability & polish gaps
- No typed config file (only env vars with no schema validation)
- Prompt reload on every chunk (disk I/O for every batch)
- `src/api.py` and `src/cache.py` are dead-ish — partially superseded by pipeline but still importable
- No CI/CD, no pre-commit, no linting

---

## Implementation Phases

---

### Phase 1: Provider Ecosystem

Make adding a provider a one-liner registration, not a code change.

#### Task 1.1 — Dynamic provider registry

**Objective:** Replace the single hardcoded `OpenAICompatibleProvider` with a registry so any callable can be registered by name and selected via CLI/env.

**Files:**
- Modify: `src/providers.py`
- Test: `tests/test_providers.py` (new)

**Design:**

```python
# src/providers.py

_providers: dict[str, type[BaseProvider] | Callable] = {}

def register(name: str, provider_cls: type[BaseProvider] | Callable) -> None:
    _providers[name] = provider_cls

def get_provider(name: str, **kwargs) -> Callable[[list[str]], str]:
    cls = _providers.get(name)
    if cls is None:
        raise ValueError(f"Unknown provider '{name}'. Registered: {list(_providers)}")
    return cls(**kwargs) if isinstance(cls, type) else cls

def list_providers() -> list[str]:
    return list(_providers)
```

- Auto-register `"openai"` and `"deepseek"` (both map to `OpenAICompatibleProvider`, just default base URL differs).
- `OpenAICompatibleProvider.from_env()` picks up `PROVIDER_NAME` / `--provider` to decide defaults.

**CLI change:** `anki-gen --provider openai --model gpt-4o-mini` or `--provider deepseek` or `--provider ollama`.

**Verification:**

```bash
uv run pytest tests/test_providers.py -q
uv run anki-gen --help  # shows --provider flag
```

#### Task 1.2 — Ollama / Local provider example

**Objective:** Show a real non-OpenAI provider working end-to-end without extra deps.

**Files:**
- Create: `src/providers/__init__.py`, `src/providers/openai_compat.py`, `src/providers/ollama.py` (refactor into a package)
- Modify: `README.md`
- Test: `tests/test_providers.py`

**Design:**

```python
# src/providers/ollama.py
class OllamaProvider:
    """Uses Ollama's OpenAI-compatible endpoint at localhost:11434/v1."""
    def __init__(self, model: str = "qwen2.5:7b", base_url: str = "http://localhost:11434/v1"):
        self._inner = OpenAICompatibleProvider(
            OpenAICompatibleProviderConfig(api_key="ollama", base_url=base_url, model=model)
        )

    def __call__(self, words: list[str]) -> str:
        return self._inner(words)
```

Document in README: install Ollama, pull a model, run with `--provider ollama --model qwen2.5:7b`.

**Verification:**

```bash
# Integration test if Ollama is available; otherwise unit test that it calls through
uv run pytest tests/test_providers.py::test_ollama_provider_invokes_openai_compat -v
```

#### Task 1.3 — Injectable prompt template

**Objective:** Stop re-reading `io/prompt.txt` on every chunk. Make the prompt a pipeline option.

**Files:**
- Modify: `src/pipeline.py` (add `prompt_template: str = ""` to `GenerationOptions`)
- Modify: `src/providers.py` (provider `__call__` gets the template from pipeline or uses its own default)
- Modify: `src/api.py` — simplify or deprecate
- Test: `tests/test_pipeline.py`

**Design:**

```python
@dataclass(frozen=True)
class GenerationOptions:
    ...
    prompt_template: str = ""   # if empty, provider uses default
```

The pipeline reads the template file once (not per-chunk), passes it into each `provider(chunk, template=template)` call. The provider's responsibility to interpolate words into the template.

**Verification:**

```bash
uv run pytest tests/test_pipeline.py::test_custom_prompt_template -v
```

---

### Phase 2: Throughput & Reliability

Make the pipeline faster, smarter about rate limits, and safer under partial failures.

#### Task 2.1 — Async pipeline with anyio/httpx

**Objective:** Replace `ThreadPoolExecutor` with async concurrency for higher throughput per worker, less overhead.

**Files:**
- Create: `src/pipeline_async.py` (new async pipeline)
- Modify: `src/main.py` (optional async mode behind `--async`)
- Test: `tests/test_pipeline_async.py` (new)

**Design:**

```python
# src/pipeline_async.py
import anyio
from openai import AsyncOpenAI

async def generate_cards_async(options, provider) -> GenerationResult:
    chunks = chunk_list(pending_words, options.chunk_size)
    async with anyio.create_task_group() as tg:
        for chunk in chunks:
            tg.start_soon(_process_chunk, chunk, provider)
    ...
```

Keep the sync `generate_cards()` unchanged for simplicity. The async version is opt-in via `--async` or by calling `generate_cards_async()` directly.

**CLI change:** `anki-gen --async --max-workers 8`.

**Verification:**

```bash
uv run pytest tests/test_pipeline_async.py -q
# 4+ async-specific tests: concurrency, order preservation, rate limit simulation
```

#### Task 2.2 — Rate-limit-aware scheduler

**Objective:** If the provider advertises a rate limit (requests/min or tokens/min), the scheduler respects it instead of blindly retrying.

**Files:**
- Create: `src/rate_limiter.py`
- Modify: `src/pipeline.py` and/or `src/pipeline_async.py`
- Test: `tests/test_rate_limiter.py` (new)

**Design:**

```python
# src/rate_limiter.py
@dataclass
class RateLimitConfig:
    requests_per_minute: float = 0        # 0 = unlimited
    tokens_per_minute: float = 0

class TokenBucketRateLimiter:
    def __init__(self, config: RateLimitConfig):
        self.capacity = config.requests_per_minute
        ...

    async def acquire(self, tokens: int = 1):
        """Block until a request slot is available."""
```

CLI option: `--rate-limit 30` (requests/minute). Provider metadata can suggest defaults (e.g., DeepSeek free tier ≈ 10 RPM).

**Verification:**

```bash
uv run pytest tests/test_rate_limiter.py -q
# Token bucket timing test (fast — small durations)
```

#### Task 2.3 — Incremental history & early persistence

**Objective:** Persist processed words to history immediately after model response, not after mdanki conversion.

**Files:**
- Modify: `src/pipeline.py` — move `append_history` call before the deck generator
- Test: `tests/test_pipeline.py`

**Design:**

In `generate_cards()`, after `_call_provider_ordered()` but during result processing: for each chunk result, append to history as soon as content arrives (not after mdanki). Prevents duplicate re-generation on crash.

**Verification:**

```bash
uv run pytest tests/test_pipeline.py::test_early_history_persistence -v
```

#### Task 2.4 — Provider-side streaming

**Objective:** Reduce time-to-first-card by consuming SSE streams instead of waiting for complete responses.

**Files:**
- Modify: `src/providers.py` — add `stream: bool` flag
- Modify: `src/main.py` — add `--stream` flag
- Test: `tests/test_providers.py`

**Design:**

```python
class OpenAICompatibleProvider:
    def __call__(self, words: list[str], *, stream: bool = False) -> str:
        if stream:
            return self._call_streaming(words)
        return self._call_blocking(words)
```

Streaming response accumulates chunks into the same markdown output format. For the pipeline, streaming writes a partial file earlier but the final result is the same `GenerationResult`.

**Verification:**

```bash
uv run pytest tests/test_providers.py::test_provider_streaming -v
# Mock the streaming API response
```

---

### Phase 3: App Integration

Build the web API layer and local-import bridge so any dashboard/web UI can drive this directly.

#### Task 3.1 — FastAPI generation endpoint

**Objective:** Expose a `/generate` REST endpoint that accepts a vocab list and returns a `GenerationResult` JSON with download URLs.

**Files:**
- Create: `src/web/__init__.py`, `src/web/app.py`
- Create: `src/web/schemas.py`
- Modify: `pyproject.toml` (add `fastapi`, `uvicorn` as optional deps under `[project.optional-dependencies] web = [...]`)
- Test: `tests/test_web.py` (new, using TestClient)

**Design:**

```python
# src/web/app.py
from fastapi import FastAPI, Form
from fastapi.responses import FileResponse

app = FastAPI(title="Chinese Anki Generator")

@app.post("/generate")
async def generate(
    words: str = Form(),
    deck_name: str = Form("Chinese Vocabulary"),
    provider: str = Form("deepseek"),
    chunk_size: int = Form(6),
    max_workers: int = Form(1),
):
    ...
    return GenerationResultSchema.from_result(result)

@app.get("/download/{filename}")
async def download(filename: str):
    """Serve generated .apkg files for dashboard download."""
    ...
```

This creates the contract Padall mentioned: "ensuring that the interaction endpoints with the app make sense."

**CLI:** `uv run uvicorn src.web.app:app --host 127.0.0.1 --port 8080`

**Verification:**

```bash
uv run pytest tests/test_web.py -q
# POST /generate returns JSON, GET /download serves file, error cases
```

#### Task 3.2 — Hermes dashboard direct integration

**Objective:** Replace the shell-out-to-CLI pattern in the Hermes dashboard with a direct `import generate_cards` or a HTTP call to the web layer.

**Files:**
- New: `CHINESE_ANKI_INTEGRATION.md` in this repo documenting the contract
- Modify: `README.md`

**Contract:** The dashboard can either:
- (a) Import `from src.pipeline import generate_cards, GenerationOptions` — preferred when dashboard and repo share a Python runtime.
- (b) POST to the `/generate` endpoint — preferred when they're separate processes.
- (c) Shell out with `--json` and parse stdout — fallback for minimal integration.

**Verification:** Manual — start the web server, POST a vocab list, confirm JSON output has `apkg_files` with downloadable paths.

#### Task 3.3 — AnkiConnect helper module

**Objective:** A local-only module that pushes generated `.apkg` content directly into a running Anki instance via AnkiConnect.

**Files:**
- Create: `src/anki_connect.py`
- Modify: `README.md`
- Test: `tests/test_anki_connect.py` (unit tests with mocked HTTP)

**Design:**

```python
# src/anki_connect.py
class AnkiConnectClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8765"):
        self.base_url = base_url

    def deck_exists(self, deck_name: str) -> bool:
        ...

    def import_apkg(self, apkg_path: str) -> dict:
        """Import a .apkg file through AnkiConnect's multiAction."""
        ...

    def add_note(self, deck: str, front: str, back: str) -> int:
        ...
```

This runs on the user's local machine only — not on the remote generation server. Document this separation clearly.

**CLI:** `anki-gen ... --auto-import` invokes AnkiConnect after generation.

**Verification:**

```bash
uv run pytest tests/test_anki_connect.py -q
# Mocked HTTP responses; no real Anki needed
# Integration test only if ANKI_CONNECT_REAL_TEST env var is set
```

---

### Phase 4: Polish & Packaging

Make the project maintainable, installable, and safe to run unattended.

#### Task 4.1 — Typed config file (YAML or TOML)

**Objective:** Replace scattered env vars with a single typed config file. Keep env var overrides for flexibility.

**Files:**
- Create: `src/config.py`
- Modify: `pyproject.toml` (add dependency on `pyyaml` or use stdlib `tomllib`)
- Test: `tests/test_config.py`

**Design (TOML example):**

```toml
# chinese-anki.toml
[provider]
name = "deepseek"
model = "deepseek-chat"
temperature = 0.1
max_tokens = 4096
api_key = "env:MODEL_API_KEY"  # resolves from env var

[pipeline]
chunk_size = 6
max_workers = 2
retry_attempts = 3
continue_on_error = true

[output]
markdown_root = "io/output_md"
anki_root = "io/output_apkg"

[anki_connect]
enabled = false
host = "127.0.0.1"
port = 8765
```

**CLI:** `anki-gen --config chinese-anki.toml`. CLI flags override config values.

**Verification:**

```bash
uv run pytest tests/test_config.py -q
uv run anki-gen --config chinese-anki.toml
```

#### Task 4.2 — Clean up dead code

**Objective:** Remove or redirect `src/cache.py` (superseded by pipeline's configurable history path) and `src/api.py`'s `call_deepseek_api()` (dead code since providers module exists).

**Files:**
- Modify: `src/cache.py` — add deprecation warning re-exporting from pipeline
- Modify: `src/api.py` — remove `call_deepseek_api()`, keep `create_prompt()` and `load_prompt_template()`
- Test: ensure no imports break

**Verification:**

```bash
uv run pytest tests/ -q
# All 10+ existing tests still pass
```

#### Task 4.3 — CI, linting, pre-commit

**Objective:** Add GitHub Actions CI that runs tests on push/PR, plus ruff/uv lock check.

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `.pre-commit-config.yaml`
- Modify: `pyproject.toml` (add `[tool.ruff]` config)

**Verification:**

```bash
# Local
ruff check src/ tests/
uv lock --check
uv run pytest -q
```

#### Task 4.4 — Structured error reporting & webhook callback

**Objective:** Support async generation with a callback URL. Pipeline returns an `async_id` that the caller polls or receives via webhook.

**Files:**
- Create: `src/web/tasks.py` (background task queue using anyio)
- Modify: `src/web/app.py`
- Test: `tests/test_web.py`

**Design:**

```python
@app.post("/generate-async")
async def generate_async(words: str, callback_url: str = "", ...):
    task_id = str(uuid4())
    # Spawn background task
    # Return {"task_id": task_id, "status": "queued"}
    # On completion: POST result to callback_url or store for polling

@app.get("/status/{task_id}")
async def get_status(task_id: str):
    # Return {"status": "completed"|"failed"|"running", "result": {...}}
```

**Verification:**

```bash
uv run pytest tests/test_web.py::test_async_generation -v
```

---

## Commit Plan

Group by phase, commit atomically:

1. **Phase 1 — Provider ecosystem**
   - `feat: add dynamic provider registry`
   - `feat: add Ollama local provider example`
   - `feat: make prompt template injectable`

2. **Phase 2 — Throughput & reliability**
   - `feat: add async pipeline variant`
   - `feat: add rate-limit-aware scheduler`
   - `feat: persist history incrementally before deck gen`
   - `feat: add streaming support to providers`

3. **Phase 3 — App integration**
   - `feat: add FastAPI generation endpoint`
   - `docs: document Hermes dashboard integration contract`
   - `feat: add AnkiConnect helper module`

4. **Phase 4 — Polish & packaging**
   - `feat: add typed TOML config file`
   - `chore: clean up dead code (cache, legacy api)`
   - `ci: add GitHub Actions CI and pre-commit`
   - `feat: add async webhook callback support`

---

## Verification Checklist (full pass)

- [ ] `uv run pytest tests/ -q` — all tests pass
- [ ] `uv run anki-gen --help` — shows all new flags (`--provider`, `--config`, `--async`, `--stream`, `--auto-import`)
- [ ] `uv run anki-gen --list-providers` — prints `deepseek, openai, ollama`
- [ ] Provider registry: `--provider ollama --model qwen2.5:7b` works with Ollama running
- [ ] Web server: `curl -X POST -F "words=你好" http://localhost:8080/generate` returns JSON with apkg_files
- [ ] Config file: `anki-gen --config test.toml` overrides env defaults
- [ ] CI: push triggers GitHub Actions, tests pass, lint passes
- [ ] Async endpoint: `POST /generate-async` returns task_id, `GET /status/{id}` returns result
- [ ] AnkiConnect: `anki-gen ... --auto-import` pushes cards into running Anki (local only)
