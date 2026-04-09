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
cohesive, and checkpoint-oriented. Every authored commit must stay bounded to
one reviewable slice. When a task spans more than one separable slice, land it
as multiple bounded checkpoint commits instead of one umbrella commit.

Use Conventional Commit subjects and the structured body sections for merge
commits too. Do not rely on GitHub's default `Merge pull request ...` subject.
Keep commit and pull request language neutral, direct, and specific. Do not use
rhetorical, promotional, or exaggerated wording in repo history.

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
- summary names a concrete repo surface or behavior
- maximum 72 characters for the full subject line
- no trailing period
- do not use generic summaries such as `cleanup`, `misc fixes`, or
  `update branch`

## Body Template

Use a blank line after the subject when adding a body.

Preferred body sections:

- `Why:`
- `What:`
- `Checks:`

Write `Why:` and `What:` directly:

- `Why:` states the problem, constraint, or risk the change addresses
- `What:` states the behavior, structure, or contract changed in this patch
- do not use `Why:` to restate the implementation
- do not use `What:` to repeat generic intent without naming the concrete
  repo change

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

## Pull Request Merge Strategy Standard

`main` is a merge-commit branch by default. Preserve multi-checkpoint pull
requests with merge commits so the reviewed checkpoint history remains visible
in Git. Use squash merges only for the narrow single-checkpoint exception.

Treat the pull request title and description as the canonical review record
for every PR. For the single-checkpoint exception, that same metadata also
becomes the generated squash commit that lands on `main`.

Protected-branch rule:

- land changes on `main` through pull requests only
- do not push directly to `main`
- do not use branch-protection bypass or force-push for normal delivery
- do not rewrite a merged `main` commit when the original pull request must
  remain attached to the landing commit; open a new pull request repair instead
- if a protected-branch repair exception is explicitly requested, limit that
  exception to the exact repair action, verify the remote branch tip
  immediately afterward, and restore PR-only flow before continuing

PR title rules:

- use the same Conventional Commit subject format required for authored commits
- keep the title history-ready on its own because it remains the PR headline
  and, for a single-checkpoint PR, the squash subject becomes
  `<pr title> (#<pr number>)`
- do not use generic titles such as `update branch`, `cleanup`, or `misc fixes`

PR body rules:

- include these sections in this exact order:
  - `Why:`
  - `What:`
  - `Checks:`
  - `Issue linkage:`
  - `Included checkpoints:`
- an optional `Follow-ups:` section is allowed after `Included checkpoints:`
- use flat hyphen bullets under every section
- `Issue linkage:` is required for every PR
- use `Issue linkage:` with `- Closes #123: <problem statement>` when the PR
  resolves an existing issue
- use `Issue linkage:` with `- Refs #123` or `- Refs #123: <note>` when the
  PR links to tracked work without closing it
- use `Issue linkage:` with `- None: <reason>` only when no existing issue
  applies after search
- keep `Included checkpoints:` in chronological order using the exact
  checkpoint subjects from the branch
- wrap every `Included checkpoints:` entry in backticks using the exact commit
  subject, because CI validates that the list matches the branch history
- describe the engineering outcome and reviewable behavior, not branch
  choreography or replay mechanics
- use `Follow-ups:` for non-closing references such as `- Refs #456` or
  `- Refs #456: deferred cleanup`
- use `Follow-ups:` for proactively opened out-of-scope issues discovered
  during implementation or PR hardening when that work should stay separate
  from the active PR
- keep authored commit messages on `Why:`, `What:`, and `Checks:` without
  issue-closing keywords unless the user explicitly requests otherwise
- for a one-commit PR, still list that single checkpoint under
  `Included checkpoints:`

Merge method rules:

- if `Included checkpoints:` lists more than one commit, the PR must merge with
  a merge commit
- if `Included checkpoints:` lists exactly one commit, the PR must squash merge
- do not squash multi-checkpoint PRs
- do not create a merge commit for a single-checkpoint PR unless the user
  explicitly requests a one-off repair in the current thread
- when merging a multi-checkpoint PR, override GitHub's default merge subject
  with a deterministic subject that keeps the PR number visible instead of
  landing `Merge pull request ...`
- for a merge commit, use `<pr title> (#<pr number>)` as the merge subject and
  keep the merge body in the same `Why:`, `What:`, `Checks:`,
  `Included checkpoints:` format as the PR body so the mainline commit record
  matches the reviewed PR record
- if a repair PR supersedes an older pull request, add the repo's neutral
  duplicate/superseded label to the older PR as the primary marker before
  closing the repair loop
- use a neutral comment on the older PR only when the repo has no suitable
  label or the user explicitly asks for explanatory prose

For a single-checkpoint PR, the GitHub-generated squash commit on `main` may
retain the validated `Included checkpoints:` and `Follow-ups:` sections from
the PR body. Treat that as allowed for the generated mainline commit record,
even though authored checkpoint commits should only use `Why:`, `What:`, and
`Checks:` sections.

Preferred PR body template:

```text
Why:
- state the problem or constraint this PR resolves

What:
- state the engineering changes that matter for review

Checks:
- list the verification you actually ran

Issue linkage:
- Closes #123: state the resolved issue, link non-closing tracked work, or explain why no issue applies

Included checkpoints:
- `refactor(example): first checkpoint subject`
- `fix(example): second checkpoint subject`

Follow-ups:
- Refs #456
```

## Stable Checkpoint Commits

Commit at stable checkpoints by default. In this repo that is an expected
working agreement, not optional guidance to ignore once a change is stable.

A stable checkpoint means:

- the commit covers one bounded reviewable slice
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

For large scopes, the default end state is still bounded commits. Do not wait
until the end of the branch and then collapse several reviewable slices into
one authored commit just because the broader task was related.

Do not batch unrelated fixes together. Do not split one bounded change into a
series of micro-commits with no practical review value.

Before a checkpoint commit is pushed, fold a small, scoped follow-up patch into
the owning checkpoint when that produces a cleaner review boundary. A
non-pushed checkpoint commit may be amended for small cleanups and fixes that
still belong to that same checkpoint. Use `git commit --amend`, `git rebase`,
or fixup-based consolidation for that limited cleanup only, and update the
amended commit message so `Why:`, `What:`, and `Checks:` remain accurate for
the final commit content. Do not use repeated amend cycles to grow one broad
commit that should be split into separate stable checkpoints.
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

The installed `pre-commit` hook is intentionally narrow. It formats safe
staged Python files with Ruff before commit creation and skips auto-restaging
for partially staged Python files so unrelated unstaged hunks are not
accidentally committed. It also refuses to run when the sibling `commit-msg`
validator hook is missing or stale, so clone-local hook drift cannot silently
bypass commit-message validation.

Validate messages directly when needed:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.validate_commit_message .git/COMMIT_EDITMSG
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.validate_commit_message --rev-range HEAD~3..HEAD
```

When structured commit messages or PR bodies include backticks, quotes, or
other shell-sensitive text, use file/stdin authoring forms rather than inline
`-m` or `--body` arguments so the metadata stays literal.

## Commit-Time Verification Policy

Commit-time hooks should enforce the bounded local safety checks we expect on
every checkpoint commit without rerunning the full repo-wide verification
matrix. Keep the hook path limited to safe staged Ruff autofixes plus the
commit-time checks that protect every commit:

- `markdownlint`
- `mypy`
- `pyright`
- `pytest -m "unit and not slow" --no-cov -q`
- commit-message validation

Full verification still means running:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.run_quality_gates --full-tests
```

Do not also run `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run pre-commit run --all-files` in addition to the
shared quality-gate or CI-parity runners unless you are validating hook
behavior itself.

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

`pylint`, full-repo `ruff`, and the full `pytest` suite belong to the shared
quality and CI-parity runners rather than the commit-time hook path. The fast
hook checks should stay narrower than the full parity matrix so the same broad
suite is not rerun twice inside one explicit verification pass.

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
