# Chinese TXT to Anki — v1 Improvement Plan

**Release target:** 0.2.0
**Baseline:** `f9415a7` (docs: expand improvement plan with 4-phase roadmap)

**Goal:** Evolve the Chinese vocab → markdown → Anki package generator into a flexible, high-throughput, production-grade tool with clean app/dashboard integration surfaces.

**Architecture:** Provider-agnostic core with a registry pattern for pluggable backends. Async pipeline for throughput without manual thread tuning. A thin FastAPI layer for dashboard integration plus a local AnkiConnect bridge for one-click import.

---

## Scope

**In scope:**
- Provider registry and Ollama support
- Async pipeline and rate-limit-aware scheduling
- FastAPI generation + download endpoints
- AnkiConnect helper module
- Typed TOML config file
- Dead code removal
- CI, type checking, and linting

**Out of scope (deferred):**
- Provider-side streaming (Task D1) — mdanki consumes the full batch; streaming adds complexity without user-visible gain
- Webhook/async task queue (Task D2) — no concrete integration requirement yet; simple polling or synchronous calls cover current needs

---

## Phase 0: Foundations

Do this before any feature work. CI pays dividends across all subsequent phases; dead code removal prevents accidental dependencies on deprecated paths.

### Task 0.1 — CI, linting, and type checking

**Objective:** GitHub Actions CI that runs tests, type checks, and lint on every push/PR.

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `.pre-commit-config.yaml`
- Modify: `pyproject.toml` (add `[tool.ruff]` and `[tool.mypy]` config, add `mypy` to dev deps)

**Design:**

```yaml
# .github/workflows/ci.yml
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync --frozen
      - run: uv run mypy src/
      - run: uv run ruff check src/ tests/
      - run: uv run python -m pytest tests/ -q
```

```toml
# pyproject.toml additions
[tool.ruff]
target-version = "py311"
line-length = 100

[tool.mypy]
python_version = "3.11"
strict = true
```

**Verification:**

```bash
uv run mypy src/
uv run ruff check src/ tests/
uv run python -m pytest tests/ -q
```

### Task 0.2 — Dead code removal

**Objective:** Remove `call_deepseek_api()` from `src/api.py` (superseded by `src/providers.py`) and simplify `src/cache.py` (superseded by pipeline's configurable `history_path`).

**Files:**
- Modify: `src/api.py` — delete `call_deepseek_api()`, keep `create_prompt()` and `load_prompt_template()`
- Modify: `src/cache.py` — add a single deprecation note re-exporting from pipeline, or delete if unused
- Verify: no import of removed symbols in `src/main.py` or tests

**Verification:**

```bash
grep -r "call_deepseek_api\|from .cache" src/ tests/
uv run python -m pytest tests/ -q
```

---

## Phase 1: Provider Ecosystem

### Task 1.1 — Provider package + dynamic registry

**Objective:** Refactor `src/providers.py` into a `src/providers/` package and add a registry so any callable can be registered by name and selected via CLI/env. Bundle the Ollama provider as the first non-OpenAI example.

Combining the package refactor and registry into one task avoids an unrunnable in-between state.

**Files:**
- Delete: `src/providers.py`
- Create: `src/providers/__init__.py` (re-exports public API)
- Create: `src/providers/base.py` (registry + `register`, `get_provider`, `list_providers`)
- Create: `src/providers/openai_compat.py` (move `OpenAICompatibleProvider` here)
- Create: `src/providers/ollama.py` (thin wrapper)
- Modify: `src/pipeline.py` (import from new package)
- Modify: `src/main.py` (add `--provider`, `--list-providers` flags)
- Modify: `README.md` (document Ollama setup)
- Create: `tests/test_providers.py`

**Design:**

```python
# src/providers/base.py
_registry: dict[str, type | Callable] = {}

def register(name: str, provider_cls: type | Callable) -> None:
    _registry[name] = provider_cls

def get_provider(name: str, **kwargs) -> Callable[[list[str]], str]:
    cls = _registry.get(name)
    if cls is None:
        raise ValueError(f"Unknown provider '{name}'. Registered: {list(_registry)}")
    return cls(**kwargs) if isinstance(cls, type) else cls

def list_providers() -> list[str]:
    return list(_registry)
```

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

Auto-register `"openai"` and `"deepseek"` (both `OpenAICompatibleProvider`, different default base URLs) and `"ollama"` at import time.

**Integration test gating:** Ollama integration tests are skipped unless `OLLAMA_INTEGRATION_TEST=1` is set. Unit tests mock the HTTP call.

**CLI change:**

```
anki-gen --provider openai --model gpt-4o-mini
anki-gen --provider deepseek
anki-gen --provider ollama --model qwen2.5:7b
anki-gen --list-providers
```

**Verification:**

```bash
uv run python -m pytest tests/test_providers.py -q
uv run anki-gen --help          # shows --provider, --list-providers
uv run anki-gen --list-providers  # prints: deepseek, openai, ollama
```

### Task 1.2 — Injectable prompt template

**Objective:** Read `io/prompt.txt` once at startup instead of per-chunk. Make the prompt a first-class pipeline option.

**Files:**
- Modify: `src/pipeline.py` — add `prompt_template: str = ""` to `GenerationOptions`; read template file once before the chunk loop
- Modify: `src/providers/openai_compat.py` — accept optional `template` kwarg in `__call__`, fall back to internal default
- Modify: `src/main.py` — add `--prompt` flag to pass a template file path
- Modify: `tests/test_pipeline.py` — add `test_custom_prompt_template`

**Verification:**

```bash
uv run python -m pytest tests/test_pipeline.py::test_custom_prompt_template -v
```

---

## Phase 2: Throughput & Reliability

### Task 2.1 — Async pipeline

**Objective:** Add an async pipeline variant for higher throughput per worker. Keep the sync `generate_cards()` unchanged for simplicity; async is opt-in.

**Files:**
- Create: `src/pipeline_async.py`
- Modify: `src/main.py` — add `--async` flag
- Create: `tests/test_pipeline_async.py`

**Design:**

```python
# src/pipeline_async.py
import anyio
from openai import AsyncOpenAI

async def generate_cards_async(options: GenerationOptions, provider) -> GenerationResult:
    chunks = chunk_list(pending_words, options.chunk_size)
    results: list[...] = []
    async with anyio.create_task_group() as tg:
        for chunk in chunks:
            tg.start_soon(_process_chunk, chunk, provider, results)
    ...
```

**Dependencies to add:** `anyio` (runtime).

**Verification:**

```bash
uv run python -m pytest tests/test_pipeline_async.py -q
# 4+ tests: concurrency, order preservation under async, partial failure handling
```

### Task 2.2 — Rate-limit-aware scheduler

**Objective:** Respect provider rate limits (requests/min) instead of blindly retrying on 429s.

**Files:**
- Create: `src/rate_limiter.py`
- Modify: `src/pipeline.py` and `src/pipeline_async.py`
- Modify: `src/main.py` — add `--rate-limit` flag (requests/minute; 0 = unlimited)
- Create: `tests/test_rate_limiter.py`

**Design:**

```python
@dataclass
class RateLimitConfig:
    requests_per_minute: float = 0   # 0 = unlimited

class TokenBucketRateLimiter:
    def __init__(self, config: RateLimitConfig): ...
    async def acquire(self, tokens: int = 1) -> None:
        """Block until a request slot is available."""
```

**Verification:**

```bash
uv run python -m pytest tests/test_rate_limiter.py -q
# Timing test with small durations (sub-second bucket fill)
```

### Task 2.3 — Incremental history persistence

**Objective:** Persist processed words to history immediately after model response, not after mdanki conversion. Prevents duplicate re-generation if the process crashes mid-run.

**Files:**
- Modify: `src/pipeline.py` — move `append_history` call immediately after `_call_provider_ordered()` result, before deck generation
- Modify: `tests/test_pipeline.py` — add `test_early_history_persistence`

**Verification:**

```bash
uv run python -m pytest tests/test_pipeline.py::test_early_history_persistence -v
```

---

## Phase 3: App Integration

### Task 3.1 — FastAPI generation and download endpoints

**Objective:** Expose `/generate` and `/download/{filename}` REST endpoints for dashboard integration.

**Files:**
- Create: `src/web/__init__.py`
- Create: `src/web/app.py`
- Create: `src/web/schemas.py`
- Modify: `pyproject.toml` — add `[project.optional-dependencies] web = ["fastapi>=0.115,<1", "uvicorn>=0.32,<1"]`
- Create: `tests/test_web.py` (TestClient-based, no real server)

**Design:**

```python
# src/web/app.py
@app.post("/generate")
async def generate(body: GenerateRequest) -> GenerationResultSchema:
    ...

@app.get("/download/{filename}")
async def download(filename: str):
    # Security: validate filename contains no path separators or '..'
    # Only serve files under the configured anki_root directory
    safe_path = Path(settings.anki_root) / Path(filename).name
    if not safe_path.exists() or not safe_path.is_relative_to(settings.anki_root):
        raise HTTPException(404)
    return FileResponse(safe_path)
```

**Security note:** The `/download/{filename}` endpoint must sanitize the filename parameter. Only the basename is used; the resolved path must be verified to sit within `anki_root` before serving. This guards against path traversal (`../../etc/passwd`).

**CLI:** `uv run uvicorn src.web.app:app --host 127.0.0.1 --port 8080`

**Verification:**

```bash
uv run python -m pytest tests/test_web.py -q
# POST /generate returns JSON with apkg_files
# GET /download/<valid> serves file
# GET /download/../etc/passwd returns 404
# Error cases (missing words, provider failure)
```

### Task 3.2 — Hermes dashboard integration contract

**Objective:** Document the three integration modes so the Hermes dashboard can graduate from stdout/path scraping to a stable API.

**Files:**
- Create: `docs/HERMES_INTEGRATION.md`
- Modify: `README.md`

**Contract:**
- (a) Direct Python import: `from src.pipeline import generate_cards, GenerationOptions` — preferred when same runtime
- (b) HTTP: `POST /generate` — preferred when separate processes
- (c) CLI with `--json`: parse stdout — fallback only

**Verification:** Manual — start web server, POST a vocab list, confirm JSON has `apkg_files`.

### Task 3.3 — AnkiConnect helper module

**Objective:** A local-only module that pushes generated `.apkg` files into a running Anki instance via AnkiConnect.

**Files:**
- Create: `src/anki_connect.py`
- Modify: `src/main.py` — add `--auto-import` flag
- Modify: `README.md`
- Create: `tests/test_anki_connect.py` (mocked HTTP; real Anki behind `ANKI_CONNECT_REAL_TEST=1`)

**Design:**

```python
class AnkiConnectClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8765"): ...
    def deck_exists(self, deck_name: str) -> bool: ...
    def import_apkg(self, apkg_path: str) -> dict: ...
    def add_note(self, deck: str, front: str, back: str) -> int: ...
```

This runs on the user's local machine only. The generation server does not call AnkiConnect. Document this boundary explicitly.

**Verification:**

```bash
uv run python -m pytest tests/test_anki_connect.py -q
```

---

## Phase 4: Polish

### Task 4.1 — Typed TOML config file

**Objective:** Replace scattered env vars with a single typed config file. Env var overrides remain for flexibility.

**Files:**
- Create: `src/config.py`
- Create: `chinese-anki.example.toml`
- Modify: `src/main.py` — add `--config` flag
- Modify: `pyproject.toml` — no new deps needed (stdlib `tomllib` since Python 3.11)
- Create: `tests/test_config.py`

**Design:**

```toml
# chinese-anki.toml
[provider]
name = "deepseek"
model = "deepseek-chat"
temperature = 0.1
max_tokens = 4096
api_key = "env:MODEL_API_KEY"  # resolved from env var at load time

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

CLI flags override config values. `env:VAR_NAME` in string fields resolves from the environment at load time and raises `ConfigError` if the variable is missing.

**Verification:**

```bash
uv run python -m pytest tests/test_config.py -q
uv run anki-gen --config chinese-anki.example.toml --help
```

---

## Deferred Items

| ID | Item | Rationale | Destination |
|----|------|-----------|-------------|
| D1 | Provider-side streaming (SSE) | `mdanki` requires full batch; streaming adds complexity without user-visible gain | `planning/PLAN-FUTURE.md` |
| D2 | Webhook / async task queue | No concrete integration requirement yet; sync HTTP covers current needs | `planning/PLAN-FUTURE.md` |

---

## Verification Checklist (full pass)

- [ ] `uv run mypy src/` — clean
- [ ] `uv run ruff check src/ tests/` — clean
- [ ] `uv run python -m pytest tests/ -q` — all tests pass
- [ ] `uv run anki-gen --help` — shows `--provider`, `--list-providers`, `--async`, `--rate-limit`, `--auto-import`, `--config`, `--prompt`
- [ ] `uv run anki-gen --list-providers` — prints `deepseek, openai, ollama`
- [ ] Web server: `curl -X POST -H "Content-Type: application/json" -d '{"words":"你好","deck_name":"Test"}' http://localhost:8080/generate` returns JSON with `apkg_files`
- [ ] Download endpoint: path traversal attempt returns 404
- [ ] Config file: `anki-gen --config chinese-anki.example.toml` reads values correctly
- [ ] CI: push triggers GitHub Actions, all checks green
