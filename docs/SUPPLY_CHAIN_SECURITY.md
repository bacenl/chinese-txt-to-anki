# Supply Chain Security Notes

This repo follows the practical guidance from Lawrence Lee's supply-chain security write-up:

- Source: https://gist.github.com/lhl/f171eaea45df31a0b9287d7bf380657a
- Local focus: Python/uv dependencies and the external `mdanki` Node tool.

## Policy

1. **Commit lockfiles.** Keep `uv.lock` in git and install with frozen lockfiles.
2. **Use a 7-day dependency cooldown.** Avoid resolving package versions published in the last 7 days unless deliberately bypassing for an urgent security fix.
3. **Use bounded dependency ranges.** Direct Python dependencies should have an upper bound, e.g. `>=1.0.0,<2`.
4. **Prefer wheels and isolated environments.** Use `uv` virtual environments; avoid installing Python packages into the system interpreter.
5. **Do not run random package executables.** Avoid ad-hoc `npx`/global installs for unreviewed tools. `mdanki` is currently an external prerequisite and should be installed deliberately.
6. **Keep CI/install commands deterministic.** Use `uv sync --frozen`; do not run unconstrained dependency resolution in CI.

## Recommended Local Commands

Resolve dependencies with the 7-day age gate:

```bash
UV_EXCLUDE_NEWER=$(date -d '7 days ago' -u +%Y-%m-%dT00:00:00Z) uv lock
```

Install exactly what is in the lockfile:

```bash
uv sync --frozen
```

Check the lockfile is up to date:

```bash
uv lock --check
```

Run tests after dependency changes:

```bash
uv run pytest tests/test_pipeline.py -q
```

## Current Repo Status

- `pyproject.toml` direct runtime dependencies are upper-bounded.
- `uv.lock` is committed and includes hashes/artifact metadata.
- There are no GitHub Actions workflows in this repo right now. If workflows are added, pin third-party actions to full commit SHAs and set least-privilege `permissions:`.

## External Tool Care: mdanki

This repo calls `mdanki` to build `.apkg` files. Because it is installed from the Node ecosystem, treat it as part of the supply chain:

- Prefer installing a reviewed, pinned version instead of `npm install -g mdanki` with no version.
- Do not install/update it on machines with unnecessary secrets loaded in the environment.
- If adding Node project files later, commit the lockfile and use `npm ci`/`pnpm install --frozen-lockfile`, not unconstrained installs.

## Incident Response Reminder

If a malicious dependency or tool version may have run on the machine:

1. Stop running installs/builds on that environment.
2. Rotate API keys, tokens, SSH keys, and cloud credentials accessible to the process.
3. Inspect lockfile diffs and recently updated packages.
4. Check for unexpected outbound network activity, services, or files.
5. Rebuild from a clean environment after dependency versions are known-good.
