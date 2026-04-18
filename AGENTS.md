# AGENTS.md

## Objective

Work in the rebuilt typed application architecture under `src/tallylot/`.
Treat the repo as code, tests, docs, templates, and automation. Treat the live
workspace as external to the repo.

## Invariants

- Do not add legacy wrappers, migration utilities, or one-off repair code.
- Do not add repo-local live workspace assumptions.
- Keep strict layer boundaries:
  - `domain` has no infrastructure imports
  - `application` depends on `domain` and `ports`
  - `infrastructure` implements `ports`
  - `interfaces` only orchestrates services
- Keep financial values in `Decimal`, never `float`.
- Surface unsupported or ambiguous data as explicit issues.
- Keep adapter metadata, implementation, and tests aligned.
- Preserve current runtime truth in docs while using the final target-doc
  vocabulary for the future architecture.
- Preserve or strengthen parity through refactors; do not silently weaken
  tests.
- Update `ROADMAP.md` when making decisions that affect later rollout phases.

## Read Only What You Need

Start with this file, then load only the narrow doc required for the task.
Do not pre-load every repo doc by default.

| Task | Read |
| ---- | ---- |
| Code placement, typing, modularization, naming | `docs/standards/engineering.md` |
| Active implementation execution discipline | `docs/standards/implementation.md`, `docs/standards/commits.md` |
| Repo standards, docs placement, doc authoring rules, or agent-default enforcement changes | `AGENTS.md`, `docs/README.md`, `docs/status/current-state.md`, `docs/reference/repository-history.md`, `docs/standards/implementation.md`, `docs/standards/commits.md`, `tools/docs_maintenance/cli.py`, `tools/docs_maintenance/metadata.py` |
| Issue templates, issue-writing policy, or proactive follow-up issue creation | `AGENTS.md`, `docs/standards/issues.md`, `docs/standards/implementation.md`, `docs/standards/delivery-guardrails.md`, `docs/standards/commits.md`, `.claude/commands/issue-workflow.md` |
| Delivery guardrails, protected-branch behavior, or agent-assisted Git operations | `docs/standards/delivery-guardrails.md`, `docs/standards/commits.md`, `tools/audit_delivery_guardrails.py` |
| PR review or review-loop recovery | `docs/standards/delivery-guardrails.md`, `docs/standards/implementation.md`, `docs/standards/commits.md`, `.claude/commands/pr-review.md` |
| Planning sequence, phased delivery steps, MVP scope, or rollout checkpoints | `ROADMAP.md`, `docs/status/migration-sequence.md` |
| Reconciliation, checkpoint, journal, tax-engine implementation, or target pipeline products | `docs/concepts/reconciliation-tax-architecture.md`, `docs/reference/target-ids-and-refs.md`, `docs/reference/target-persistence-reference.md`, `ROADMAP.md`, `docs/status/migration-sequence.md`, `docs/concepts/oracle-boundaries.md`, `docs/concepts/transaction-classification.md` |
| Platform-agnostic boundaries, classification mapping, or migration order | `docs/concepts/oracle-boundaries.md`, `docs/concepts/transaction-classification.md`, `docs/status/migration-sequence.md` |
| Source or output adapter work | `docs/status/adapter-delivery-plan.md`, `docs/concepts/unified-adapter-architecture.md`, `docs/guides/write-an-adapter.md` |
| High-level architecture orientation | `docs/concepts/architecture-overview.md`, `docs/status/current-state.md`, `docs/concepts/reconciliation-tax-architecture.md` |
| Docs structure, generated index sections, doc placement, or doc authoring rules | `AGENTS.md`, `docs/README.md`, `tools/docs_maintenance/cli.py`, `tools/docs_maintenance/metadata.py` |
| External workspace layout and seeded files | `docs/concepts/workspace-model.md`, `docs/workspace/README.md` |
| Operational state or manual workflow | `docs/status/current-state.md`, `docs/guides/operator-quickstart.md`, `docs/guides/source-intake.md`, `docs/guides/normalize-screen-stage.md`, `docs/guides/verify-a-round.md`, `docs/guides/full-operator-workflow.md` |
| Repo-specific baseline and verification context | `docs/status/current-state.md`, `docs/reference/repository-history.md` |
| Workspace subtree conventions, checklists, or templates | `docs/workspace/README.md` |
| Commit messages, templates, and checkpoint behavior | `docs/standards/commits.md` |
| Final pre-close implementation checks | `.claude/commands/implementation-checkpoint.md` |

## Documentation Maintenance Rules

- Human docs live under `docs/`.
- `docs/workspace/` remains the mirrored workspace reference subtree.
- Agent routing and repo execution rules live in `AGENTS.md` and
  `.claude/commands/`.
- Agent-only repo routing and maintenance rules live in this file and
  `.claude/commands/`.
- When editing repo docs or Markdown, use the `markdown` skill if available.
- When editing repo standards, automation, or other control-plane files, use
  the repo-local workflow for the active area and reload the narrow repo
  guidance listed in this file before editing.
- Keep tracked docs, templates, and control-plane text neutral and durable.
- Keep current-state docs accurate to the implemented runtime, and keep
  forward-looking docs detailed enough to implement from without inventing
  missing stage structure later.
- Use final target product names in forward-looking docs after the mapping is
  established, and keep bridge-era names only where current implementation
  accuracy requires them.
- Do not store scratch review notes, hardening ledgers, or temporary process
  bookkeeping in tracked files.
- Keep repository issues repo-scoped and privacy-safe:
  - no personal information
  - no secrets or raw evidence
  - no local absolute paths
- Agent-only context must not live in `docs/` unless it is genuinely useful to
  humans.
- Every new doc must have one primary type: concept, guide, reference,
  standard, or status.
- Avoid duplicate routing pages. Prefer `README.md`, `docs/README.md`, and
  this file over adding another switchboard.
- Broad docs or repo-structure reshapes should land as checkpoint commits at
  stable stopping points, not as one giant umbrella commit unless the change
  cannot be validated incrementally.

## Execution Rules

- This repo intentionally uses the external uv environment at
  `$HOME/.venvs/tallylot-py312`.
- Use the root `Makefile` as the standard local command interface. It prepends
  `$(HOME)/.venvs/tallylot-py312/bin` to `PATH`, which keeps repo commands
  machine-neutral and sandbox-safe without inline environment prefixes.
- Bootstrap each clone before doing stable work. This refreshes the shared
  external project environment for the current checkout and installs repo git
  hooks, which clears stale editable package paths after repo relocation or
  history rebuilds:
  - `make install-hooks`
- Do not consider work ready until the repo's selected verification for the
  changed files passes. For agent-default local verification, use the
  standard `tools.run_quality_gates` path rather than forcing the explicit
  full-suite override.
- Do not consider non-trivial work ready until the verified checkpoint commit
  already exists.
- Prefer fresh VS Code workspace diagnostics for instant static-analysis
  feedback when the `vscode-problems` skill or MCP snapshot is available and
  current. Treat that signal as advisory only.
- For explicit local verification, prefer:
  - `make quality`
  - `make pr-review-full`
  - `make quality-full`
- Benchmark quality-gate scheduling or test-bundle changes before changing the
  default verification path:
  - `make benchmark-quality`
  - `make benchmark-tests`
- Do not run `make precommit ARGS='run --all-files'` in addition to the
  parallel quality-gate runner unless you are debugging hook behavior itself.
- Use `tools.run_quality_gates` as the normal final local verification
  command.
- Use `tools.run_pr_review_checks --mode full` when changes touch CI,
  packaging, release, or other workflow areas where the local verification
  pass should mirror the final non-draft PR suite before handoff.
- `tools.run_quality_gates --full-tests` is not the standard agent close-out
  path. Avoid it unless there is a specific reason to reach for the explicit
  full-suite override.
- Do not run `tools.run_quality_gates --full-tests` immediately before
  `tools.run_pr_review_checks --mode full`; the full PR-review runner already
  includes the full quality gate pass plus the additional CI-sensitive lanes.
- Keep commit-time hooks narrow:
  - safe staged Ruff autofixes
  - commit-message validation
  - the staged-path checks selected by the planned verifier
  - do not turn the hook path into a second full-suite verification pass
- Treat commits as stable checkpoints by default:
  - prefer small cohesive commits
  - keep every authored commit bounded to one reviewable change
  - avoid micro-commits with no rollback or review value
  - split large but separable work into multiple bounded checkpoint commits
    instead of one umbrella commit
  - end the task on a clean, meaningful checkpoint commit
- Keep commit, PR, and doc language neutral and direct:
  - `Why:` states the motivating repo problem, trigger, constraint, or risk
    that makes the patch necessary now
  - `What:` states the concrete repo behavior or structure changed
  - avoid rhetorical, promotional, or exaggerated wording in repo history
- Add tests only when they protect meaningful behavior, contracts,
  non-trivial decision logic, or fixed regressions.
- Do not delete tests, silently remove assertions, or simplify fixtures in a
  way that weakens coverage without explicit human approval.
- When tests move or consolidate, record the parity outcome in the checkpoint
  summary:
  - what old behavior was covered
  - where that behavior is covered now
  - whether the assertion became stronger, weaker, or simply moved
- Before shaping a non-trivial change, reload the narrow roadmap,
  architecture, migration, or owning-boundary guidance for that area.
- Keep public-facing names simple and ergonomic. Prefer short neutral command
  and API names over long implementation labels, and only add qualifiers when
  a real ambiguity exists.
- Treat protected branches as PR-only branches:
  - do not push directly to `main`
  - do not bypass branch protection for ordinary delivery
  - do not rewrite a merged `main` commit when preserving the original pull
    request association matters; use a new pull request repair instead
  - do not force-push protected branches unless the user explicitly requests a
    one-time repair in the current thread after branch protection has been
    temporarily adjusted
  - after any explicit one-time repair, verify the remote branch tip and return
    to PR-only delivery before continuing
- Treat repo cleanup as forward-only by default:
  - do not run `rm -rf`, `git restore`, `git reset`, `git checkout --`, or
    other destructive rollback commands unless the user explicitly asks for
    that cleanup in the current thread
  - prefer additive fixes, follow-up commits, or leaving cleanup for the user
    over destructive local undo
- If a repair pull request supersedes an older pull request, leave a neutral
  duplicate/superseded label on the older PR before closing the repair loop.
- Use a neutral replacement comment only when the repo has no suitable label
  or the user explicitly asks for explanatory prose.
- Open pull requests as draft by default and keep them draft through the
  hardening loop.
- Mark a PR ready for review only as a separate action after a clean hardening
  pass.
- Never close a PR autonomously without explicit user instruction.
- For multi-checkpoint PR merges, set the merge subject to
  `<pr title> (#<pr number>)` so the PR number remains visible in mainline
  history.
- If a flat directory would exceed 2 same-prefix files for one capability,
  regroup that capability into a package in the same task.
- If a feature already has a package, keep new helpers inside that package
  instead of beside it as flat sibling modules.

## Workspace Configuration

Workspace resolution order:

1. `CRYPTO_RECON_WORKSPACE_ROOT`
2. repo config in `tallylot.toml`
3. default `~/tallylot-workspace`

## Current Runtime

- Python `3.12`
- `uv`
- CLI and library only
- Filesystem-backed storage implementation
- SQLite and provider-backed AI remain stubbed behind interfaces

## Current Build Direction

- Treat `docs/concepts/reconciliation-tax-architecture.md` as the
  implementation anchor for reconciliation, checkpoint, journal, and tax
  computation.
- Treat `docs/concepts/architecture-overview.md` as the concise orientation
  page and `docs/concepts/reconciliation-tax-architecture.md` as the detailed
  implementation anchor.
- Do not treat CoinTracking as the live ledger for new architecture work.
  CoinTracking is now a compatibility and oracle layer.
- Do not treat CoinTracking tax or accounting reports as normal runtime
  inputs. They are development-only oracle support artifacts unless an
  explicit one-time checkpoint import workflow adopts them with provenance.
- Do not expand the current fact-path bridge into the long-term center of the
  system. Current `EconomicActivityDraft`, `TransactionFact`, and shared
  balance artifacts are the active bridge into the target pipeline, not the
  final architecture center. New structural work should target the runtime
  pipeline products and stage contracts described in
  `docs/concepts/reconciliation-tax-architecture.md` and sequenced in
  `ROADMAP.md`.
- Forward-looking docs use the final target product names:
  `EvidenceSet`, `ClaimSet`, `EconomicFacts`, `ReconciliationState`,
  `Checkpoint`, `Journal`, `TaxInputs`, and `TaxOutputs`.
- Do not push unresolved tax ambiguity downward into earlier stages just to
  keep facts or reconciliation outputs looking complete. Preserve uncertainty
  until the owning later stage decides it.
- Keep `pydantic` at boundaries:
  - config
  - external artifact parsing
  - report row validation
  - request validation
  - discovery-time manifest validation
- Keep domain models centered on frozen dataclasses, enums, and value objects.
- Follow `docs/standards/implementation.md` during coding:
  - structure first
  - tests alongside behavior, but only when they add real regression value
  - refactor obvious shared boundaries during the task
  - commit at stable checkpoints without waiting to be reminded
- When work affects architecture, schema, or execution sequencing, update
  `ROADMAP.md` and `docs/concepts/reconciliation-tax-architecture.md`
  together.
- When work affects delivery policy, branch protection expectations, or
  agent-default Git behavior, update `docs/standards/delivery-guardrails.md`
  with the relevant repo standards.
