---
title: "Commit Standards"
summary: "Conventional Commit subjects, reviewable commit boundaries, and PR body rules for stable repo history."
doc_type: standard
audience: human
owner: repo
status: active
nav_order: 30
---

Use Conventional Commits for all authored commits. Keep commit history small,
cohesive, and reviewable. Every authored commit must stay bounded to one
reviewable change. When a task spans more than one separable change, land it
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
- required lowercase kebab-case scope
- non-empty imperative summary
- summary names a concrete repo area or behavior
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

- `Why:` states the motivating repo problem, trigger, constraint, or risk that
  makes this commit necessary now
- `Why:` should answer the question "Why is this commit being made?" in repo
  terms, not restate the implementation steps, rename list, or branch
  choreography
- `Why:` should still make sense if `What:` is hidden; if it only paraphrases
  the diff, rewrite it
- `Why:` should name the consequence of leaving the repo unchanged when that
  consequence is material: ambiguity, broken behavior, drift, blocked follow-on
  work, policy mismatch, or review risk
- `What:` states the behavior, structure, or contract changed in this patch
- do not use `Why:` to restate the implementation, rename list, or document
  inventory
- do not use `What:` to repeat generic intent without naming the concrete
  repo change

Bad `Why:` bullets are diff summaries such as:

- `rename ReadinessRollupRecord`
- `update naming docs`
- `refactor commit wording`

Those belong in `What:`, not `Why:`.

Example:

```text
refactor(adapters): split structured CSV mapping

Why:
- the adapter mixed translation, row parsing, and file-family concerns in one
  hotspot, which made follow-on changes harder to review and harder to test

What:
- move row parsing into adapter-local helpers
- keep ADAPTER discovery entry point unchanged

Checks:
- make precommit ARGS='run markdownlint --all-files'
- make quality
```

Standard footers are allowed, including `BREAKING CHANGE:`.

## Pull Request Merge Strategy Standard

`main` is a merge-commit branch by default. Preserve pull requests with
multiple authored commits as merge commits so the reviewed commit history
remains visible in Git. Use squash merges only for the narrow single-commit
exception.

Treat the pull request title and description as the review record that governs
merge and mainline history for every PR. For the single-commit exception, that
same metadata also becomes the generated squash commit that lands on `main`.

Protected-branch rule:

- land changes on `main` through pull requests only
- do not push directly to `main`
- do not use branch-protection bypass or force-push for normal delivery
- do not rewrite a merged `main` commit when the original pull request must
  remain attached to the merged commit; open a new pull request repair instead
- if a protected-branch repair exception is explicitly requested, limit that
  exception to the exact repair action, verify the remote branch tip
  immediately afterward, and restore PR-only flow before continuing

PR title rules:

- use the same Conventional Commit subject format required for authored commits
- keep the title history-ready on its own because it remains the PR headline
  and, for a single-commit PR, the squash subject becomes
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
- for a one-commit PR, still list that single commit under
  `Included checkpoints:`

Merge method rules:

- if `Included checkpoints:` lists more than one commit, the PR must merge with
  a merge commit
- if `Included checkpoints:` lists exactly one commit, the PR must squash merge
- do not squash PRs with multiple authored commits
- do not create a merge commit for a single-commit PR unless the user
  explicitly requests a one-off repair in the current thread
- when merging a PR with multiple authored commits, override GitHub's default merge subject
  with a deterministic subject that keeps the PR number visible instead of
  producing `Merge pull request ...`
- for a merge commit, use `<pr title> (#<pr number>)` as the merge subject and
  keep the merge body in the same `Why:`, `What:`, `Checks:`,
  `Included checkpoints:` format as the PR body so the mainline commit record
  matches the reviewed PR record
- if a repair PR supersedes an older pull request, add the repo's neutral
  duplicate/superseded label to the older PR as the primary marker before
  closing the older PR
- use a neutral comment on the older PR only when the repo has no suitable
  label or the user explicitly asks for explanatory prose

For a single-commit PR, the GitHub-generated squash commit on `main` may
retain the validated `Included checkpoints:` and `Follow-ups:` sections from
the PR body. Treat that as allowed for the generated mainline commit record,
even though authored checkpoint commits should only use `Why:`, `What:`, and
`Checks:` sections.

Preferred PR body template:

```text
Why:
- state the motivating problem, trigger, or risk this PR resolves and why the
  PR is needed now

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

- the commit covers one bounded reviewable change
- the change is coherent and reviewable
- the tree is internally consistent
- relevant checks have passed
- the commit has actually been created before the task is closed

Heuristics:

- trivial one-file or one-concern task: usually one commit
- medium multi-part task: usually 1 to 3 commits by concern
- larger risky refactor: split only where rollback or review value is real
- broad but separable docs or repo-structure refactor: checkpoint each stable
  change instead of batching everything into one umbrella commit

For large scopes, the default end state is still bounded commits. Do not wait
until the end of the branch and then collapse several reviewable changes into
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
For multi-part refactors, use designated checkpoint commits whenever the change
already leaves the tree coherent, linked, and narrow-check verified. A giant
single-commit rewrite is only acceptable when the change cannot be reviewed or
validated incrementally.

## Local Setup

Install the repo hooks and commit template in each clone before doing stable
work:

```bash
make install-hooks
```

The installed `pre-commit` hook is intentionally narrow. It formats safe
staged Python files with Ruff before commit creation, skips auto-restaging
for partially staged Python files so unrelated unstaged hunks are not
accidentally committed, and then runs the repo's change-sensitive planned
verification selection against the staged paths. It also refuses to run when
the sibling `commit-msg` validator hook is missing or stale, so clone-local
hook drift cannot silently bypass commit-message validation.

Validate messages directly when needed:

```bash
make validate-commit-message ARGS='.git/COMMIT_EDITMSG'
make validate-commit-message ARGS='--rev-range HEAD~3..HEAD'
```

When structured commit messages or PR bodies include backticks, quotes, or
other shell-sensitive text, use file/stdin authoring forms rather than inline
`-m` or `--body` arguments so the metadata stays literal.

## Commit-Time Verification Policy

Commit-time hooks should enforce bounded local safety checks without rerunning
the full repo-wide verification matrix. Keep the hook path limited to safe
staged Ruff autofixes plus the staged-path checks selected by the repo's
planned verification policy, along with commit-message validation.

In practice that means:

- docs-only staged changes run docs-maintenance and markdownlint
- control-plane or workflow changes run the targeted guard tests selected by
  the planner
- production-code changes may still escalate to the broader Python quality
  suite when the planner marks that change area as relevant
- commit-message validation stays in the separate `commit-msg` hook

Standard final verification still means running:

```bash
make quality
```

Do not also run `make precommit ARGS='run --all-files'` in addition to the
shared quality-gate or PR-review runners unless you are validating hook
behavior itself.

For explicit local verification outside the hook path, the repo also ships a
parallel quality-gate runner:

```bash
make quality
make quality-full
make pr-review-full
```

Use `tools.run_quality_gates` as the default final local
verification command. Use `tools.run_pr_review_checks --mode full` when
changing CI, packaging, release, or other workflow areas where the local
verification pass should mirror the final non-draft PR suite before handoff.
Add `--pr-title`
plus `--pr-body-file` when you also want the full review run to validate the
current branch PR title, body, and `Included checkpoints:` list against the
branch history. Treat `tools.run_quality_gates --full-tests` as an explicit
full-suite escape hatch rather than the normal agent close-out path, and avoid
it unless there is a specific reason to use the override. Do not run
`tools.run_quality_gates --full-tests`
immediately before `tools.run_pr_review_checks --mode full`; the full
PR-review runner already includes the full quality gate pass plus the extra
workflow-sensitive lanes. Both local runners may apply safe autofixes to
staged Python and Markdown files before validation; CI remains read-only.

Example:

```bash
gh pr view <pr-number> --json title,body --jq '.title' > /tmp/pr-title.txt
gh pr view <pr-number> --json title,body --jq '.body' > /tmp/pr-body.md
make tool TOOL=run_pr_review_checks ARGS='--mode full --pr-title "$$(cat /tmp/pr-title.txt)" --pr-body-file /tmp/pr-body.md'
```

`pylint`, full-repo `ruff`, and the full `pytest` suite still belong primarily
to the shared quality and PR-review runners. The commit-time hook should stay
change-sensitive so docs-only and similarly narrow changes do not rerun
irrelevant Python scanners, even though some staged code or workflow areas
may still escalate to broader checks.

Do not describe `mypy` or `pyright` as covering `pylint` findings. Type checks
and lint checks catch different failure classes and must be reported
separately.

After a lint-driven amend on a touched file, rerun the narrow checks against
that exact file before treating the checkpoint as closed:

```bash
make pylint ARGS='<touched-file>'
make pytest ARGS='-q --no-cov <touched-test-file>'
git show HEAD:<path>
```

Use the `git show HEAD:<path>` step when the warning or failure was reported
against the just-amended file so the verification is tied to the committed
content rather than an older staged or working-tree state.
