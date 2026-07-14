# AGENTS.md / CLAUDE.md

Ground rules, process, and behavior notes for AI-assisted development in this repository.

---

## Repo Layout

*(Document your own repo structure here.)*

---

## First Principles

**Read `docs/DESIGN-PHILOSOPHY.md` before starting any code work.** It is the governing document for all design decisions.

---

## Development Philosophy

### Spec → Plan → Test → Implement

Every non-trivial feature follows this cycle:

1. **Spec**: Define requirements in `planning/` before coding
2. **Plan**: Create an implementation plan with an affected-files tree
3. **Test**: Write tests *before* implementation
4. **Implement**: Write minimal code to pass the tests
5. **Validate**: All tests must pass
6. **Commit**: Atomic commits with passing tests only

### Interactive / Ad-hoc Development

Not all work starts from a sprint punchlist. Interactive sessions still follow the same principles, scaled to the change:

1. **Track the work.** Before implementing, add a brief entry to the active milestone plan and implementation docs (e.g., `planning/vN/PLAN.md` and `planning/vN/IMPLEMENTATION.md`; create the active file(s) if missing). Exception: for work explicitly unscoped to any milestone/release, log it in `planning/WORKLOG.md`.
2. **Write tests first.** Ad-hoc does not mean untested.
3. **Validate before committing.** Run the targeted tests and static checks for the repo you are changing.

**Post-implementation review is expected.** Ad-hoc commits should receive an independent review pass before any release is cut.

**When the change outgrows ad-hoc.** If a request touches multiple components, changes security-relevant behavior, or grows beyond a single focused commit, escalate to the full spec → plan → test → implement cycle with a proper spec in `planning/`.

---

## Roles

We use separate lanes for development work:

- **Planner**: produces/updates specs and punchlists in `planning/` (typically between sprints).
- **Coder**: owns all implementation patches (code + tests) in the appropriate repo.
- **Reviewer**: analysis-only; must not edit files. Output is conversational only — the coder records the review trace in planning docs.
- **Human lead**: arbitrates scope, risk, and disagreements; decides what is a blocker vs. a deferral.

### Role Rules

- Reviewers provide findings + rationale + suggested fixes, but do not edit files. Reviewer deliverables are conversation output only.
- Reviewers must not use edit, write, or git commit/staging commands. The coder is responsible for recording findings and confirmation traces in the punchlist.
- Reviewers do not run tests, static checks, behavioral suites, live harnesses, or other execution-side validation. They inspect code, tests, plans, and coder-provided validation evidence only.
- Coders translate reviewer findings into tracked punchlist/checklist entries before implementing fixes.
- Coders must triage all reviewer feedback, including notes labeled non-blocking or informational. If the feedback is valid, fix it in the active remediation loop or record an explicit no-change/defer rationale approved by the human lead; severity affects priority, not whether valid feedback can be ignored. Stylistic or preferential findings ("consider rewording," "this could be clearer") may be acknowledged in aggregate without individual rationale, as long as factual findings (wrong version, missing row, overclaimed state) each receive explicit disposition.
- Coders must actively watch for reviewer scope creep during remediation (OPT-27). A finding that proposes a new preference, policy, or constraint not grounded in the milestone's spec/contract/invariants is out of scope for the current milestone remediation loop, even when defensible. Record it as `WONTFIX` or `NOTABUG` in the active milestone worklog with finding ID + one-line rationale + followup destination (next-milestone punchlist or `planning/PLAN-FUTURE.md`) and move on. A third disposition, `Superseded by <contract>`, is valid when a reviewed-green contract change makes a prior finding structurally unreachable. Genuine bugs, docs-parity fixes, invariant violations, and previously-agreed-contract findings are NOT `WONTFIX` candidates; when in doubt, fix it.
- Do not spend a re-review round on a remediation batch that contains **only** `WONTFIX` / `NOTABUG` dispositions with no code/test/docs change. Treat that reviewer's finding set as green for this milestone and record "closed via OPT-27 disposition, no re-review lane spent" in the worklog with the finding IDs. The final full milestone gate and `ReleaseClose` fanout re-examine all dispositions.
- Every `WONTFIX` / `NOTABUG` disposition carried forward from the milestone loop **must** be surfaced in the release-close reviewer packet (`scope-creep dispositions:` line in the preflight summary) and re-examined by the final full `ReleaseClose` fanout. Reviewers and the human lead may concur (finding stays `WONTFIX`), promote back to blocker, or defer with recorded rationale. Nothing escapes the release without the full panel and lead seeing the disposition. See `implement/RELEASE-CLOSE.md` step 11.
- Reviewer follow-up is confirmation-only (resolved / unresolved with rationale), not file changes.
- For closure purposes, reviewer "green" means no remaining valid open findings for the reviewed scope. "Not a blocker" by itself is not enough if the reviewer also raised a valid issue that remains unfixed and undeferred.

---

## Workflow Expectations

### Before Picking Up Work

- Check git status/log for recent changes
- Review existing docs and tests for context (start with the latest `planning/vN/IMPLEMENTATION.md` punchlist)
- Review `planning/REFACTOR.md` and identify only truly opportunistic candidates (same-file touch as planned milestone work); record selected RF IDs (or explicit `none`) in the milestone pre-analysis
- Re-read `docs/DESIGN-PHILOSOPHY.md` and explicitly note any product/behavioral-contract implications in the milestone pre-analysis
- Complete a milestone pre-analysis before a coder starts the punchlist (threat hotspots, runtime wiring checkpoints, validation scope, and likely deferrals)
- Record pre-analysis notes in the active `planning/vN/IMPLEMENTATION.md` before implementation begins

### During Execution

- Write tests first for new functionality
- Keep commits atomic and focused
- Document security-relevant decisions

**Regex/prose-classifier tripwire**: before adding or expanding regex, keyword tables, edit-distance heuristics, token-overlap checks, or similar classifiers, ask whether the input space is finite and machine-defined. If the code is deciding user intent, negation scope, topic attribution, valence, phrase boundaries, or another natural-language meaning question, stop and apply `docs/DESIGN-PHILOSOPHY.md` (Fifth Principle) and `docs/adr/DESIGN-structural-vs-linguistic.md` before patching. A first reviewer finding that requires expanding such a classifier is a process signal, not just another edge case; record the bounded-vs-unbounded decision in the active worklog before continuing.

**Opportunistic cleanup on file touch**: when editing a file for milestone work, remove dead code, stale imports, and unused helper methods in the same file. If a cleanup requires touching files outside the active file set, defer it to `planning/REFACTOR.md`.

**Refactor backlog**: check `planning/REFACTOR.md` for approved opportunistic hooks when starting a milestone.

### Validation Cadence

- Ordinary implementation and review-remediation loops should run the smallest targeted tests and static checks that directly cover the changed behavior. Do not default to broad behavioral or live suites after every remediation.
- Small or localized remediations may be closed with targeted validation only when that evidence is proportional to the scope and the commands/outcomes are recorded in the active milestone worklog or `planning/WORKLOG.md`.
- Behavioral validation is milestone-close evidence. Run it before marking a milestone closeable unless the human lead explicitly narrows the closure claim.
- First-principles gate validation is the high-signal behavioral subset. Once `tests/behavioral/test_first_principles_gates.py` exists, run and record it before milestone close and release close. A release-close claim must not rely on unresolved `xfail`, `xpass`, skipped, or failed first-principles gate cases unless the human lead explicitly narrows the release claim and the rationale is recorded.
- Live end-user evaluation is execution evidence, not reviewer work. By default, live smoke runs during release-close after the deterministic bundle and first-principles gate target are green, not before every milestone close.
- Run live smoke before a milestone close only when that milestone materially changes live planner/provider behavior, user interaction, confirmation flow, memory recall, or default install posture enough that deterministic tests cannot represent the risk. Record that scope-specific reason in the active implementation worklog.
- The full release-close bundle (adversarial, behavioral, and live validation) is version/release-close evidence. Do not treat it as an every-milestone or every-remediation default.
- Reviewers are read-only analysis lanes. They assess whether the coder's validation is sufficient for the current scope and phase, but they do not execute tests or harnesses themselves.

### After Changes (commit on completion)

**When you finish a task, commit.** A "task" is a complete logical unit of work — not every individual file edit.

- Run targeted local validation relevant to the touched code (unit tests, type-checks, or focused smoke tests), then commit when the logical unit is complete
- Update relevant planning docs to reflect completed work

---

## Git Practices

- **Commit on task completion** — when a logical task is done, commit without being asked
- **No bylines** or co-author footers in commits
- **Use conventional commits**: `feat:`, `fix:`, `docs:`, `plan:`, `test:`, `refactor:`, `meta:`, `chore:`
- **NEVER** use `git add .`, `git add -A`, or `git commit -a`
- **ALWAYS** add files explicitly: `git add <file>`
- **ALWAYS** verify staged files before commit: `git diff --staged --name-only`
- **Atomic commits** — group related changes, separate unrelated ones

### Commit Message Format

```
type: short summary (imperative mood)

- Bullet points for details if needed
- What changed and why
```

### GitHub / Hosting Platform

- Prefer the authenticated CLI (e.g., `gh`) for public, user-visible writes (issue comments, PR comments) so the visible authoring context is tied to the authenticated account rather than a connector app.
- Connector-backed APIs are appropriate for structured reads, PR/issue metadata, review-thread inspection, and cases where the CLI lacks coverage or is unavailable.
- Before posting public issues, comments, PR notes, release notes, or public docs, reread the exact text for **private-process leakage**. Do not name private-repo files, paths, branches, worklogs, planning filenames, internal tooling, review lanes, reviewer models, run IDs, private hashes, or private issue/work item IDs. Refer generically to "internal planning," "deferred planning," "review evidence," or "maintainer follow-up" when that context is useful publicly. Public posts should cite public files, public issues/PRs, public commits, and user-visible behavior only.

### External Contributor PRs

- Preserve contributor credit, but do not merge external PRs as-is by default. Every accepted external PR requires a maintainer code-quality/security pass, proportional validation, and either an explicit no-change disposition or maintainer fixup commits before merge.
- When `maintainerCanModify=true`, prefer pushing maintainer fixup commits to the contributor's PR head branch so the contributor remains the submitter and the PR history records the quality pass.
- Use `planning/DEV-pull-requests.md` as the active process reference for external PR intake, attribution, validation, public communication, and merge shape.

---

## Docs, Metrics, and Claim Integrity

- Treat `planning/vN/IMPLEMENTATION.md` as the authoritative execution punchlist; keep checkboxes/worklog in sync with code changes.
- Require a pre-analysis entry in `planning/vN/IMPLEMENTATION.md` at milestone start.
- Fix doc-to-code drift immediately (especially around security guarantees and runtime enforcement semantics).
- During release-close, if dependency resolutions or workflow/action trust anchors change, include the relevant supply-chain audit doc in the same docs-parity pass.
- When writing release stats or quoting numbers (tests, churn, LOC), scope calculations to a specific tag/commit and include the commands used.
- Treat `status/` as the canonical location for release-line development statistics reports; keep report metadata and cited command evidence reproducible.
- If code-scanning alerts appear during release-close or on a remediation branch, inspect them before falling back to manual UI triage. Only dismiss alerts after the human lead or reviewer has confirmed the disposition, and record the alert IDs plus rationale in the active implementation worklog when they affect release status.

### Status Reports (`status/`)

- Use `status/` reports for release-line closeout or explicit historical backfill tasks. Do not replace milestone punchlist/worklog evidence with status reports.
- Naming:
  - Single shipped release tag: `status/STATUS-vX.Y.0-dev-stats.md`
  - Multiple shipped point releases in one line: `status/STATUS-vX.Y.x-dev-stats.md`
- Minimum report contents:
  - Scope and exact baseline/final refs (tag and commit hash where available)
  - What changed (high-level)
  - Metrics snapshot tables (churn/test/codebase) scoped to explicit refs
  - Methodology and exact command list used to produce every quoted number
  - Caveats/history notes when repo history changes (e.g., repo split/rewrite)
- Closeout steps when a status report is created/updated:
  1. Update the target `status/STATUS-*.md` file
  2. Update `planning/README.md` so the report is discoverable
  3. Record the task in the active milestone implementation worklog, or in `planning/WORKLOG.md` if unscoped
  4. Commit as a task-scoped docs/meta change with explicit staged files only

### Claim Integrity (Done/Shipped/Complete)

Any claim of "done," "shipped," "complete," or "closed" must include evidence for all three:

- **Runtime wiring evidence**: where the behavior is enforced in the live runtime path.
- **Test evidence**: exact validation command(s) + outcomes.
- **Docs parity evidence**: punchlist/worklog updated, and security analysis/non-claims updated when behavior/guarantees change.

Truth-in-claims:
- Use truth-scoped wording; do not overclaim universal behavior when behavior is conditional.
- Prefer "when X is enabled" / "in mode Y" / "fails closed when Z is unavailable" over "always / guarantees / prevents."

### Deferrals

- Unresolved items stay in the active milestone's `DEFERRALS` list in `planning/vN/IMPLEMENTATION.md` (add the section if missing).
- Each deferral must include: **ID**, **rationale**, **risk**, and **target milestone**.
- Use `planning/PLAN-FUTURE.md` only for items beyond the final milestone of the current release scope.
- No orphan deferrals: a deferred item must be linked to an executable destination before milestone/release closure.
- If a deferral is carried forward, update both sides in the same change.

### Review Trace (Findings → IDs → Commits)

- Convert reviewer findings into tracked IDs before remediation (e.g., `M#.R-open.#`, `M#.RR#.#`).
- Convert every valid finding into either a remediation ID or an explicit accepted-no-change/deferral note with rationale before closure, including findings a reviewer described as non-blocking.
- Commit messages for remediation should include milestone + finding IDs.
- Log the exact validation commands + outcomes in the milestone/worklog notes when closing items.

---

## Milestone / Release Closure Checklist

Use the Validation Cadence above for ordinary implementation and remediation work. The checklist below applies when a milestone or release is actually being closed.

- [ ] **0. Behavioral tests pass** before milestone closure
- [ ] **0a. First-principles gates pass** before milestone/release closure. For release-close evidence, zero failed/xfailed/xpassed/skipped gate cases are allowed unless the human lead explicitly narrowed the release claim and the rationale is recorded.
- [ ] **0b. Release-close validation bundle recorded**: before any release-close or publish claim, run and record the full release bundle (substituting your project's actual test commands):
  - Adversarial test suite
  - Full behavioral test suite
  - Live/integration smoke lane(s)

  Run live lanes sequentially, not in parallel; overlapping them can create harness-level startup timeouts and invalidate the evidence. If any live lane cannot run, record why before marking the release closeable.
- [ ] **0c. New capabilities have behavioral tests**: if the milestone ships a new user-facing capability, at least one behavioral test must exercise the end-to-end product contract for that capability. "Existing tests still pass" is necessary but not sufficient. Record which behavioral tests were added (or justify why none were needed) in the milestone worklog.
- [ ] **0d. Tool/dependency status reviewed**
- [ ] **0e. Live runner evidence recorded** for runtime-facing scope
- [ ] **0f. Live end-user smoke evidence recorded** for runtime-facing release close: after deterministic release validation and first-principles gates are green, run the live smoke lane and record command, environment posture, transcript/log path, evaluator model, system-under-test model/provider, and outcome. If it cannot run, record why before marking the release closeable.
- [ ] **0g. Valid review feedback closed**: every valid reviewer issue, including non-blocking notes, is either fixed and re-reviewed or explicitly rejected/deferred with rationale approved by the human lead.
- [ ] **0g2. Scope-creep dispositions surfaced (OPT-27)**: before release close, every `WONTFIX` / `NOTABUG` disposition recorded during the milestone remediation loop is enumerated in the ReleaseClose reviewer packet (finding ID + rationale + followup destination + lead sign-off status) and re-examined by the final full `ReleaseClose` fanout. If the milestone loop had zero such dispositions, record `scope-creep dispositions: none` explicitly.
- [ ] **0h. Release-close preflight before reviewer fanout**: run the deterministic checklist in `implement/RELEASE-CLOSE.md` before the first `ReleaseClose` review. Batch obvious release-state/docs-parity fixes (README, CHANGELOG, ROADMAP, supply-chain audit, status, active planning docs) before spending reviewer lanes.
- [ ] **0i. Scoped staleness for release-close (OPT-21)**: a green `ReleaseClose` review is bound to its *reviewed scope*, not a bare commit hash. Private planning commits and public docs-only commits do **not** stale the review. Substantive source, test, script, config, workflow, and agent-instruction file changes do. Any unknown public path defaults to stale. Small post-green docs corrections can pin reviewers to the bounded delta instead of the full scope. See `implement/RELEASE-CLOSE.md` §10 and `implement/FIXES.md` (OPT-21).
- [ ] **1.** Stage only explicit task files: `git add <file> ...`
- [ ] **2.** Verify staged file set: `git diff --staged --name-only`
- [ ] **3.** Review staged patch: `git diff --staged`
- [ ] **4.** Commit with a conventional message
- [ ] **5.** Report commit evidence
- [ ] **6.** Tag/push only when explicitly requested by the human lead
- [ ] **7.** Verify every open deferral has a destination
- [ ] **8.** Run a refactor-cadence sweep on `planning/REFACTOR.md`
- [ ] **9.** For release-close, run an orphan sweep across the release docs
- [ ] **10.** For release-close, run a docs-parity sweep for top-level operator docs
- [ ] **11.** For release-close, create/update the line-level `status/STATUS-*.md` report (or record explicit rationale for defer), and update `planning/README.md` index links

---

## Meta: Evolving This File

This file is a living document. Update it when:

- You discover a workflow pattern that helps
- Something caused confusion
- A new tool or process gets introduced
- You learn something that would help the next person

Keep changes focused on process/behavior. Project-specific details belong in `planning/`.

