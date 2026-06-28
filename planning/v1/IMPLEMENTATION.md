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

- [x] **0.1** CI, linting, and type checking
  - [x] `.github/workflows/ci.yml` — test, mypy, ruff on push/PR
  - [x] `.pre-commit-config.yaml` — ruff + mypy hooks
  - [x] `pyproject.toml` — add `[tool.ruff]`, `[tool.mypy]`, `mypy` to dev deps
  - [ ] Verification: `uv run mypy src/` clean, `uv run ruff check src/ tests/` clean, tests pass

- [x] **0.2** Dead code removal
  - [x] `src/api.py` — deleted `call_deepseek_api()`, trimmed docstrings
  - [x] `src/cache.py` — added deprecation note
  - [x] Verification: all tests pass

### Phase 1: Provider Ecosystem

- [x] **1.1** Provider package + dynamic registry + Ollama
  - [x] Delete `src/providers.py`
  - [x] Create `src/providers/__init__.py` — public re-exports + auto-register deepseek/openai/ollama
  - [x] Create `src/providers/base.py` — `register`, `get_provider`, `list_providers`
  - [x] Create `src/providers/openai_compat.py` — `OpenAICompatibleProvider` with `template` kwarg
  - [x] Create `src/providers/ollama.py` — thin wrapper around `OpenAICompatibleProvider`
  - [x] Modify `src/pipeline.py` — update import path
  - [x] Modify `src/main.py` — add `--provider`, `--list-providers` flags
  - [x] Verification: `uv run python -m pytest tests/test_providers.py -q` — 15 passed, 1 skipped

- [x] **1.2** Injectable prompt template
  - [x] `src/pipeline.py` — add `prompt_template: str = ""` to `GenerationOptions`
  - [x] `src/providers/openai_compat.py` — accept `template` kwarg in `__call__`
  - [x] `src/main.py` — add `--prompt` flag
  - [x] Verification: `uv run python -m pytest tests/test_pipeline.py::test_custom_prompt_template_is_forwarded_to_provider -v` — pass

### Phase 2: Throughput & Reliability

- [x] **2.1** Async pipeline
  - [x] Create `src/pipeline_async.py` with `generate_cards_async()`
  - [x] `src/main.py` — add `--async` flag
  - [x] Add `anyio` to runtime deps in `pyproject.toml`
  - [x] Verification: `uv run python -m pytest tests/test_pipeline_async.py -q` — 5 passed

- [x] **2.2** Rate-limit-aware scheduler
  - [x] Create `src/rate_limiter.py` — `RateLimitConfig`, `TokenBucketRateLimiter` (capacity=2)
  - [x] `src/main.py` — add `--rate-limit` flag
  - [x] Fix throttle test to drain 2 tokens (capacity=2, not 1 as comment said)
  - [x] Verification: `uv run python -m pytest tests/test_rate_limiter.py -q` — 7 passed

- [x] **2.3** Incremental history persistence
  - [x] `src/pipeline.py` — moved `append_history` before `generate_anki_deck()` call
  - [x] Verification: `uv run python -m pytest tests/test_pipeline.py::test_history_is_written_before_deck_generation -v` — pass

### Phase 3: App Integration

- [x] **3.1** FastAPI generation and download endpoints
  - [x] Create `src/web/__init__.py`
  - [x] Create `src/web/app.py` — `POST /generate`, `GET /download/{filename}` with path traversal guard, `get_deck_generator` dependency
  - [x] Create `src/web/schemas.py` — `GenerateRequest` with pydantic validation
  - [x] `pyproject.toml` — add `[project.optional-dependencies] web = [...]`; fastapi/uvicorn in dev deps
  - [x] Updated `tests/test_web.py` — added `get_deck_generator` override to avoid mdanki dependency
  - [x] Verification: `uv run python -m pytest tests/test_web.py -q` — 8 passed

- [ ] **3.2** Hermes dashboard integration contract
  - [ ] Create `docs/HERMES_INTEGRATION.md` — three integration modes documented
  - [ ] Update `README.md` to link to it
  - [ ] Verification: manual

- [x] **3.3** AnkiConnect helper module
  - [x] Create `src/anki_connect.py` — `AnkiConnectClient` with `deck_exists`, `import_apkg`, `add_note`
  - [x] `src/main.py` — add `--auto-import` flag
  - [x] Verification: `uv run python -m pytest tests/test_anki_connect.py -q` — 5 passed, 1 skipped

### Phase 4: Polish

- [x] **4.1** Typed TOML config file
  - [x] Create `src/config.py` — `load_config()`, `ConfigError`, `env:VAR_NAME` resolution via tomllib
  - [x] Create `chinese-anki.example.toml`
  - [x] `src/main.py` — add `--config` flag
  - [x] Verification: `uv run python -m pytest tests/test_config.py -q` — 8 passed

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

2026-06-27 — pre-implementation TDD pass — wrote test files for all phases before any implementation:

- `tests/test_providers.py` — registry API, auto-registered names, OllamaProvider unit tests, integration skip gate
- `tests/test_pipeline.py` additions — `test_custom_prompt_template_is_forwarded_to_provider`, `test_history_is_written_before_deck_generation`
- `tests/test_pipeline_async.py` — basic result, order preservation, history filtering, partial failures
- `tests/test_rate_limiter.py` — unlimited mode, throttle timing, burst-then-throttle, validation
- `tests/test_web.py` — generate endpoint, download endpoint, path traversal guard; skipped via `pytest.importorskip("fastapi")` until dep is added
- `tests/test_anki_connect.py` — `deck_exists`, `import_apkg`, `add_note`, connection errors, real integration skip gate
- `tests/test_config.py` — TOML section loading, defaults, `env:` prefix resolution, `ConfigError` on missing var

Baseline verification:
- `uv run python -m pytest tests/test_pipeline.py -v` → 10 original tests pass; 2 new tests fail correctly:
  - `test_custom_prompt_template_is_forwarded_to_provider` — `TypeError: unexpected keyword argument 'prompt_template'` (field not yet on `GenerationOptions`)
  - `test_history_is_written_before_deck_generation` — `assert [False] == [True]` (history currently written after deck generation)
- New module tests (`test_providers`, `test_pipeline_async`, `test_rate_limiter`, `test_anki_connect`, `test_config`) error at collection: modules do not exist yet
- `test_web.py` — skipped cleanly (fastapi not installed)
