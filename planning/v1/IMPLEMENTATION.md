# Chinese TXT to Anki — v1 Implementation Log

**Plan:** `planning/v1/PLAN.md`
**Release target:** 0.2.0
**Baseline:** `f9415a7`

---

## Pre-Analysis

> Fill this section before starting the punchlist.

**Threat hotspots:**
- `/download/{filename}` endpoint — path traversal risk; must validate basename + `is_relative_to(anki_root)` before serving
- `env:VAR_NAME` resolution in TOML config — must fail closed (raise `ConfigError`) if env var is missing, not silently use empty string
- Provider registry — `get_provider()` must raise on unknown name, not return `None`

**Runtime wiring checkpoints:**
- Provider registry is populated at import time via module-level `register()` calls; verify no circular imports after package split
- Async pipeline must preserve chunk order in `GenerationResult` (same invariant as sync pipeline)
- History persistence must happen before `generate_anki_deck()` is called, not inside it

**Validation scope:**
- Ordinary tasks: targeted unit/integration tests for the changed behavior only
- Milestone close: full `uv run python -m pytest tests/ -q` + mypy + ruff

**Refactor candidates (from REFACTOR.md):** n/a — no REFACTOR.md exists yet; opportunistic cleanup on file touch only

**Likely deferrals:** D1 (streaming), D2 (webhook) — already recorded in PLAN.md

---

## Punchlist

### Phase 0: Foundations

- [ ] **0.1** CI, linting, and type checking
  - [ ] `.github/workflows/ci.yml` — test, mypy, ruff on push/PR
  - [ ] `.pre-commit-config.yaml` — ruff + mypy hooks
  - [ ] `pyproject.toml` — add `[tool.ruff]`, `[tool.mypy]`, `mypy` to dev deps
  - [ ] Verification: `uv run mypy src/` clean, `uv run ruff check src/ tests/` clean, tests pass

- [ ] **0.2** Dead code removal
  - [ ] `src/api.py` — delete `call_deepseek_api()`
  - [ ] `src/cache.py` — remove or add deprecation shim
  - [ ] Verify no dangling imports: `grep -r "call_deepseek_api\|from .cache" src/ tests/`
  - [ ] Verification: all existing tests still pass

### Phase 1: Provider Ecosystem

- [ ] **1.1** Provider package + dynamic registry + Ollama
  - [ ] Delete `src/providers.py`
  - [ ] Create `src/providers/__init__.py` — public re-exports
  - [ ] Create `src/providers/base.py` — `register`, `get_provider`, `list_providers`
  - [ ] Create `src/providers/openai_compat.py` — move `OpenAICompatibleProvider` here
  - [ ] Create `src/providers/ollama.py` — thin wrapper around `OpenAICompatibleProvider`
  - [ ] Auto-register `deepseek`, `openai`, `ollama` at module import
  - [ ] Modify `src/pipeline.py` — update import path
  - [ ] Modify `src/main.py` — add `--provider`, `--list-providers` flags
  - [ ] Update `README.md` with Ollama setup instructions
  - [ ] Create `tests/test_providers.py` — registry, unknown provider, Ollama unit test (HTTP mocked), integration test behind `OLLAMA_INTEGRATION_TEST=1`
  - [ ] Verification: `uv run python -m pytest tests/test_providers.py -q`, `--list-providers` output

- [ ] **1.2** Injectable prompt template
  - [ ] `src/pipeline.py` — add `prompt_template: str = ""` to `GenerationOptions`; read file once before chunk loop
  - [ ] `src/providers/openai_compat.py` — accept `template` kwarg in `__call__`
  - [ ] `src/main.py` — add `--prompt` flag
  - [ ] `tests/test_pipeline.py` — add `test_custom_prompt_template`
  - [ ] Verification: `uv run python -m pytest tests/test_pipeline.py::test_custom_prompt_template -v`

### Phase 2: Throughput & Reliability

- [ ] **2.1** Async pipeline
  - [ ] Create `src/pipeline_async.py` with `generate_cards_async()`
  - [ ] `src/main.py` — add `--async` flag
  - [ ] Add `anyio` to runtime deps in `pyproject.toml`
  - [ ] Create `tests/test_pipeline_async.py` — concurrency, order preservation, partial failure
  - [ ] Verification: `uv run python -m pytest tests/test_pipeline_async.py -q`

- [ ] **2.2** Rate-limit-aware scheduler
  - [ ] Create `src/rate_limiter.py` — `RateLimitConfig`, `TokenBucketRateLimiter`
  - [ ] Wire into `src/pipeline.py` and `src/pipeline_async.py`
  - [ ] `src/main.py` — add `--rate-limit` flag
  - [ ] Create `tests/test_rate_limiter.py` — bucket timing (sub-second durations)
  - [ ] Verification: `uv run python -m pytest tests/test_rate_limiter.py -q`

- [ ] **2.3** Incremental history persistence
  - [ ] `src/pipeline.py` — move `append_history` before `generate_anki_deck()` call
  - [ ] `tests/test_pipeline.py` — add `test_early_history_persistence`
  - [ ] Verification: `uv run python -m pytest tests/test_pipeline.py::test_early_history_persistence -v`

### Phase 3: App Integration

- [ ] **3.1** FastAPI generation and download endpoints
  - [ ] Create `src/web/__init__.py`
  - [ ] Create `src/web/app.py` — `POST /generate`, `GET /download/{filename}` with path traversal guard
  - [ ] Create `src/web/schemas.py` — request/response models
  - [ ] `pyproject.toml` — add `[project.optional-dependencies] web = [...]`
  - [ ] Create `tests/test_web.py` — happy path, path traversal attempt (expect 404), error cases
  - [ ] Verification: `uv run python -m pytest tests/test_web.py -q`

- [ ] **3.2** Hermes dashboard integration contract
  - [ ] Create `docs/HERMES_INTEGRATION.md` — three integration modes documented
  - [ ] Update `README.md` to link to it
  - [ ] Verification: manual — start web server, POST vocab list, confirm JSON response

- [ ] **3.3** AnkiConnect helper module
  - [ ] Create `src/anki_connect.py` — `AnkiConnectClient` with `deck_exists`, `import_apkg`, `add_note`
  - [ ] `src/main.py` — add `--auto-import` flag
  - [ ] Update `README.md` with local-only usage note
  - [ ] Create `tests/test_anki_connect.py` — mocked HTTP; real tests behind `ANKI_CONNECT_REAL_TEST=1`
  - [ ] Verification: `uv run python -m pytest tests/test_anki_connect.py -q`

### Phase 4: Polish

- [ ] **4.1** Typed TOML config file
  - [ ] Create `src/config.py` — `load_config()`, `ConfigError`, `env:VAR_NAME` resolution
  - [ ] Create `chinese-anki.example.toml`
  - [ ] `src/main.py` — add `--config` flag; CLI flags override config values
  - [ ] Create `tests/test_config.py` — load, env resolution, missing env var raises `ConfigError`
  - [ ] Verification: `uv run python -m pytest tests/test_config.py -q`

---

## Milestone Close Checklist

- [ ] `uv run mypy src/` — clean
- [ ] `uv run ruff check src/ tests/` — clean
- [ ] `uv run python -m pytest tests/ -q` — all tests pass, zero skips without recorded rationale
- [ ] Full verification checklist in `planning/v1/PLAN.md` — all items checked
- [ ] `DEFERRALS` section up to date — D1 and D2 have destination in `planning/PLAN-FUTURE.md`
- [ ] `docs/IMPLEMENTATION.md` updated to record v1 completion
- [ ] `pyproject.toml` version bumped to `0.2.0`
- [ ] Commit tag requested from human lead before push

---

## Deferrals

| ID | Item | Rationale | Target |
|----|------|-----------|--------|
| D1 | Provider-side streaming | `mdanki` requires full batch; no user-visible gain | `planning/PLAN-FUTURE.md` |
| D2 | Webhook / async task queue | No concrete integration requirement | `planning/PLAN-FUTURE.md` |

---

## Worklog

> Record commands, outcomes, and decisions here as tasks are completed.

<!-- format: date — task ID — command + outcome / decision -->
