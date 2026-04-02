# Commit Standards

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
- uv run pre-commit run markdownlint --all-files
- uv run python -m tools.run_quality_gates --full-tests
```

Standard footers are allowed, including `BREAKING CHANGE:`.

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

Do not batch unrelated fixes together. Do not split one bounded change into a
series of micro-commits with no practical review value.

## Local Setup

Install the repo hooks and commit template in each clone before doing stable
work:

```bash
uv run python -m tools.install_git_hooks
```

The installed `pre-commit` hook formats safe staged Python files with Ruff
before running the remaining hooks once. It skips auto-restaging for partially
staged Python files so unrelated unstaged hunks are not accidentally committed.

Validate messages directly when needed:

```bash
uv run python -m tools.validate_commit_message .git/COMMIT_EDITMSG
uv run python -m tools.validate_commit_message --rev-range HEAD~3..HEAD
```

## Commit-Time Test Policy

The `pre-commit` `pytest` hook is intentionally scoped to fast unit coverage:

```bash
uv run pytest -m "unit and not slow" --no-cov -q
```

That hook is meant to protect local commits without paying the cost of
coverage, contract tests, or end-to-end CLI flows on every commit. Full
verification still means running:

```bash
uv run pre-commit run markdownlint --all-files
uv run python -m tools.run_quality_gates --full-tests
```

Do not also run `uv run pre-commit run --all-files` in addition to the
parallel quality-gate runner unless you are validating the hooks themselves.

Re-benchmark suite segments before broadening or shrinking the fast test slice:

```bash
uv run python -m tools.benchmark_tests
uv run python -m tools.benchmark_tests --parallel
```

For explicit local verification outside the hook path, the repo also ships a
parallel quality-gate runner:

```bash
uv run python -m tools.run_quality_gates
uv run python -m tools.run_quality_gates --full-tests
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
uv run pylint <touched-file>
uv run pytest -q --no-cov <touched-test-file>
git show HEAD:<path>
```

Use the `git show HEAD:<path>` step when the warning or failure was reported
against the just-amended file so the verification is tied to the committed
content rather than an older staged or working-tree state.
