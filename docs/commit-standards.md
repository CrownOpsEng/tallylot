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
- uv run ruff check .
- uv run mypy
- uv run pyright
- uv run pylint src tests tools
- uv run pytest
```

Standard footers are allowed, including `BREAKING CHANGE:`.

## Stable Checkpoint Commits

Commit at stable checkpoints by default. In this repo that is an expected
working agreement, not optional guidance to ignore once a change is stable.

A stable checkpoint means:

- the change slice is coherent and reviewable
- the tree is internally consistent
- relevant checks have passed

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
git config --local commit.template .gitmessage.txt
uv run pre-commit install --hook-type pre-commit --hook-type commit-msg
```

Do not replace this with ad hoc wrappers unless the docs are updated in the
same change and the wrapper exactly preserves the documented behavior.

Validate messages directly when needed:

```bash
uv run python -m tools.validate_commit_message .git/COMMIT_EDITMSG
uv run python -m tools.validate_commit_message --rev-range HEAD~3..HEAD
```
