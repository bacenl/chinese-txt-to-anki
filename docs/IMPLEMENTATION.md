# Chinese TXT to Anki Implementation Log

## 2026-06-08 — Dashboard integration planning

- [x] Copied Lead workflow `AGENTS.md` into this repo.
- [x] Updated `README.md` to describe the planned Hermes dashboard workflow.
- [x] Documented target one-click path: remote generation through this CLI plus browser-to-local AnkiConnect import.
- [x] Documented `.apkg` download fallback.

## 2026-06-10 — Hermes dashboard MVP wired

- [x] Confirmed the Hermes Personal Workspace dashboard shells out to this repo via `uv run anki-gen --input <words.txt> --deck-name <deck>`.
- [x] Updated `README.md` from planned target flow to current dashboard flow: batch creation, generation, `.apkg` download links, and AnkiConnect probing.
- [x] Left the stable library/JSON-output work as the next repo-local improvement; current integration still depends on CLI stdout/path discovery.

Next implementation task: expose a stable Python library function around the current CLI pipeline so the Hermes dashboard can call this repo without depending on stdout/path scraping.

## 2026-06-13 — Pipeline/API, provider, and throughput pass

- [x] Verified repo state before starting: existing uncommitted docs/dashboard integration updates were present in `AGENTS.md`, `README.md`, and `docs/`.
- [x] Rewrote `AGENTS.md` using the Lead-provided content and kept the exact repo filename `AGENTS.md`.
- [x] Replaced the older dashboard integration plan with `docs/PLAN.md` covering extensibility, throughput, and app interaction contracts.
- [x] Added strict pytest coverage before production implementation for structured pipeline output, history filtering, order preservation, and provider env fallback.
- [x] Added `src/pipeline.py` with `GenerationOptions`, `GenerationResult`, and `generate_cards()` for app/dashboard callers.
- [x] Added `src/providers.py` with `OpenAICompatibleProvider`, generic `MODEL_API_KEY`, `MODEL_BASE_URL`, `MODEL_NAME`, and fallback to legacy `DEEPSEEK_API_KEY`.
- [x] Updated `src/main.py` into a thin CLI wrapper around the importable pipeline and added `--chunk-size` / `--max-workers` flags.
- [x] Updated `.env.example` and `README.md` to document provider and throughput options.
- [x] Verification run: `uv run pytest tests/test_pipeline.py -q` and `uv run anki-gen --help`.

Next implementation tasks:

- [ ] Add `--json` output mode for machine-readable CLI integration.
- [ ] Add retries/backoff and per-chunk failure reporting.
- [ ] Update Hermes dashboard integration to import `generate_cards()` directly instead of parsing stdout.

## 2026-06-13 — App-facing reliability and endpoint pass

Planned subtasks:

- [x] Add machine-readable serialization for `GenerationResult` and CLI `--json` output.
- [x] Add configurable provider retry/backoff with per-chunk failure metadata.
- [x] Add tests for endpoint-safe JSON, provider config knobs, and retry behavior.
- [x] Update README/PLAN with the app interaction contract and model/throughput controls.
- [x] Run tests/smoke checks and commit changes atomically.

Verification:

- `uv run pytest tests/test_pipeline.py -q` → 10 passed.
- `uv run anki-gen --help` shows endpoint/retry flags.
- `git diff --check` passed.

Notes:

- `GenerationResult.to_dict()` now serializes paths and failed chunks for dashboards/apps.
- CLI now accepts `--json`, `--retry-attempts`, `--retry-backoff-seconds`, and `--continue-on-error`.
- Provider config now reads `MODEL_TEMPERATURE` and `MODEL_MAX_TOKENS` in addition to API key/base URL/model.

## 2026-06-13 — Supply chain security hardening

- [x] Reviewed Lawrence Lee's supply-chain security guidance and applied repo-relevant practices.
- [x] Added upper bounds to direct runtime dependencies in `pyproject.toml`.
- [x] Added upper bound to the build backend requirement.
- [x] Regenerated `uv.lock` using a 7-day age gate: `UV_EXCLUDE_NEWER=$(date -d '7 days ago' -u +%Y-%m-%dT00:00:00Z) uv lock`.
- [x] Added `docs/SUPPLY_CHAIN_SECURITY.md` with local policy, commands, mdanki caveats, and incident-response notes.
- [x] Linked the supply-chain notes from `README.md` setup instructions.
- [x] Verification run: `UV_EXCLUDE_NEWER=$(date -d '7 days ago' -u +%Y-%m-%dT00:00:00Z) uv lock --check`, `uv sync --frozen`, `uv run pytest tests/test_pipeline.py -q`, and `uv run anki-gen --help`.

## 2026-06-27 — Next-phase improvement plan drafted

- [x] Replaced `docs/PLAN.md` with the comprehensive next-phase plan covering:
  - Phase 1: Provider ecosystem (dynamic registry, Ollama example, injectable prompt template)
  - Phase 2: Throughput & reliability (async pipeline, rate-limit-aware scheduler, incremental history, streaming)
  - Phase 3: App integration (FastAPI endpoint, Hermes dashboard integration contract, AnkiConnect helper)
  - Phase 4: Polish & packaging (typed TOML config, dead code cleanup, CI/lint/pre-commit, webhook callback)
- [ ] Implementation deferred — plan ready for task-by-task execution.

## 2026-06-27 — v1 planning docs created

- [x] Reviewed `docs/PLAN.md` and identified sequencing issues, security gap, low-ROI tasks, and missing concerns.
- [x] Created `planning/v1/PLAN.md` — revised plan incorporating:
  - Phase 0 (Foundations): CI + type checking first; dead code removal before new features
  - Tasks 1.1 and 1.2 (provider package refactor + registry) merged to avoid unrunnable in-between state
  - Path traversal sanitization note added to download endpoint
  - Integration test gating strategy documented (env var per external service)
  - Type checking (mypy) added alongside ruff in CI task
  - Streaming (D1) and webhook/task-queue (D2) explicitly deferred with rationale
- [x] Created `planning/v1/IMPLEMENTATION.md` — punchlist with pre-analysis, per-task checkboxes, milestone close checklist, and worklog.
