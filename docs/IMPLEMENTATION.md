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

## 2026-06-13 — Supply chain security hardening

- [x] Reviewed Lawrence Lee's supply-chain security guidance and applied repo-relevant practices.
- [x] Added upper bounds to direct runtime dependencies in `pyproject.toml`.
- [x] Added upper bound to the build backend requirement.
- [x] Regenerated `uv.lock` using a 7-day age gate: `UV_EXCLUDE_NEWER=$(date -d '7 days ago' -u +%Y-%m-%dT00:00:00Z) uv lock`.
- [x] Added `docs/SUPPLY_CHAIN_SECURITY.md` with local policy, commands, mdanki caveats, and incident-response notes.
- [x] Linked the supply-chain notes from `README.md` setup instructions.
- [x] Verification run: `UV_EXCLUDE_NEWER=$(date -d '7 days ago' -u +%Y-%m-%dT00:00:00Z) uv lock --check`, `uv sync --frozen`, `uv run pytest tests/test_pipeline.py -q`, and `uv run anki-gen --help`.
