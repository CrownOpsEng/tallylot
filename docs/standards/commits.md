---
title: "Commit Standards"
summary: "Conventional Commit, checkpoint, and PR body rules for stable repo history."
doc_type: standard
audience: human
owner: repo
status: active
nav_order: 30
---

Use Conventional Commits for all authored commits. Keep commit history small,
cohesive, and checkpoint-oriented.

Auto-generated merge commits are tolerated by the validator, but authored
commits should use the Conventional Commit format.

## Subject Format

Use this format for the first line:

```text
type(scope): imperative summary
```

The scope is optional:

```text
type: imperative summary
```

Allowed types:

- `feat`
- `fix`
- `refactor`
- `docs`
- `test`
- `chore`
- `build`
- `ci`
- `perf`
- `revert`

Subject rules:

- lowercase type
- optional lowercase kebab-case scope
- non-empty imperative summary
- maximum 72 characters for the full subject line
- no trailing period

## Body Template

Use a blank line after the subject when adding a body.

Preferred body sections:

- `Why:`
- `What:`
- `Checks:`

Example:

```text
refactor(adapters): split structured CSV mapping

Why:
- reduce adapter bloat and isolate row parsing rules

What:
- move row parsing into adapter-local helpers
- keep ADAPTER discovery entry point unchanged

Checks:
- UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run pre-commit run markdownlint --all-files
- UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.run_quality_gates --full-tests
```

Standard footers are allowed, including `BREAKING CHANGE:`.

## Pull Request And Squash Merge Standard

`main` uses squash merges. Treat the pull request title and description as the
canonical source for the commit that lands on `main`.

PR title rules:

- use the same Conventional Commit subject format required for authored commits
- keep the title history-ready on its own because the squash subject becomes
  `<pr title> (#<pr number>)`
- do not use generic titles such as `update branch`, `cleanup`, or `misc fixes`

PR body rules:

- include these sections in this exact order:
  - `Why:`
  - `What:`
  - `Checks:`
  - `Included checkpoints:`
- use flat hyphen bullets under every section
- keep `Included checkpoints:` in chronological order using the exact
  checkpoint subjects from the branch
- wrap every `Included checkpoints:` entry in backticks using the exact commit
  subject, because CI validates that the list matches the branch history
- describe the engineering outcome and reviewable behavior, not branch
  choreography or replay mechanics
- for a one-commit PR, still list that single checkpoint under
  `Included checkpoints:`

The GitHub-generated squash commit on `main` may retain the validated
`Included checkpoints:` section from the PR body. Treat that as allowed for the
generated mainline commit record, even though authored checkpoint commits
should only use `Why:`, `What:`, and `Checks:` sections.

Preferred PR body template:

```text
Why:
- explain the problem or constraint this PR resolves

What:
- summarize the engineering changes that matter for review

Checks:
- list the verification you actually ran

Included checkpoints:
- `refactor(example): first checkpoint subject`
- `fix(example): second checkpoint subject`
```

## Stable Checkpoint Commits

Commit at stable checkpoints by default. In this repo that is an expected
working agreement, not optional guidance to ignore once a change is stable.

A stable checkpoint means:

- the change slice is coherent and reviewable
- the tree is internally consistent
- relevant checks have passed
- the commit has actually been created before the task is closed

Heuristics:

- trivial one-file or one-concern task: usually one commit
- medium multi-part task: usually 1 to 3 commits by concern
- larger risky refactor: split only where rollback or review value is real
- broad but separable docs or repo-structure refactor: checkpoint each stable
  slice instead of batching everything into one umbrella commit

Do not batch unrelated fixes together. Do not split one bounded change into a
series of micro-commits with no practical review value.

For multi-slice refactors, use designated checkpoint commits whenever the slice
already leaves the tree coherent, linked, and narrow-check verified. A giant
single-commit rewrite is only acceptable when the change cannot be reviewed or
validated incrementally.

## Local Setup

Install the repo hooks and commit template in each clone before doing stable
work:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.install_git_hooks
```

The installed `pre-commit` hook formats safe staged Python files with Ruff
before running the remaining hooks once. It skips auto-restaging for partially
staged Python files so unrelated unstaged hunks are not accidentally committed.
It also refuses to run when the sibling `commit-msg` validator hook is missing
or stale, so clone-local hook drift cannot silently bypass commit-message
validation.

Validate messages directly when needed:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.validate_commit_message .git/COMMIT_EDITMSG
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.validate_commit_message --rev-range HEAD~3..HEAD
```

## Commit-Time Test Policy

The `pre-commit` `pytest` hook is intentionally scoped to fast unit coverage:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run pytest -m "unit and not slow" --no-cov -q
```

That hook is meant to protect local commits without paying the cost of
coverage, contract tests, or end-to-end CLI flows on every commit. Full
verification still means running:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.run_quality_gates --full-tests
```

Do not also run `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run pre-commit run --all-files` in addition to the
parallel quality-gate runner unless you are validating the hooks themselves.

Re-benchmark suite segments before broadening or shrinking the fast test slice:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.benchmark_tests
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.benchmark_tests --parallel
```

For explicit local verification outside the hook path, the repo also ships a
parallel quality-gate runner:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.run_quality_gates
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.run_quality_gates --full-tests
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.run_ci_parity_checks
```

Use `tools.run_quality_gates --full-tests` as the default final local
verification command. Use `tools.run_ci_parity_checks` only when changing CI,
packaging, release, or other workflow surfaces where exact local parity with
GitHub Actions is worth the extra time. Add `--include-commit-messages` when
you also want the parity run to validate the current branch commit-message
range before running the full quality and build path. Add `--pr-title` plus
`--pr-body-file` when you also want the parity run to validate the current
branch PR title, body, and `Included checkpoints:` list against the branch
history.
Do not run `tools.run_quality_gates --full-tests` immediately before
`tools.run_ci_parity_checks`; the parity runner already includes the full
quality gate pass.

Example:

```bash
gh pr view <pr-number> --json title,body --jq '.title' > /tmp/pr-title.txt
gh pr view <pr-number> --json title,body --jq '.body' > /tmp/pr-body.md
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.run_ci_parity_checks \
  --include-commit-messages \
  --pr-title "$(cat /tmp/pr-title.txt)" \
  --pr-body-file /tmp/pr-body.md
```

`pylint` remains part of the parallel quality-gate runner, but it is not part
of the `pre-commit` hook path because it is materially slower than the other
commit-time checks.

Do not describe `mypy` or `pyright` as covering `pylint` findings. Type checks
and lint checks catch different failure classes and must be reported
separately.

After a lint-driven amend on a touched file, rerun the narrow checks against
that exact file before treating the checkpoint as closed:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run pylint <touched-file>
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run pytest -q --no-cov <touched-test-file>
git show HEAD:<path>
```

Use the `git show HEAD:<path>` step when the warning or failure was reported
against the just-amended file so the verification is tied to the committed
content rather than an older staged or working-tree state.
