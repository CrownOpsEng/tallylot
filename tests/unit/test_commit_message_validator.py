from __future__ import annotations

from tools.validate_commit_message import validate_commit_message_text


def test_commit_message_without_scope_is_valid() -> None:
    message = """\
docs: route agents to narrow standards

Why:
- keep routing guidance explicit

What:
- point agents to the narrowest applicable standards doc

Checks:
- uv run python -m tools.validate_commit_message .git/COMMIT_EDITMSG
"""

    errors = validate_commit_message_text(message)

    assert not errors


def test_commit_message_with_scope_is_valid() -> None:
    message = """\
refactor(adapters): split structured CSV parsing

Why:
- keep adapter parsing seams reviewable

What:
- move structured CSV parsing into bounded helpers

Checks:
- uv run pytest tests/unit/test_commit_message_validator.py
"""

    errors = validate_commit_message_text(message)

    assert not errors


def test_commit_message_with_structured_body_and_breaking_footer_is_valid() -> None:
    message = """\
feat(cli): rename verification command

Why:
- align command naming with the service layer

What:
- rename the CLI command
- update docs

Checks:
- uv run pytest

BREAKING CHANGE: verification compare is now verification diff
"""

    errors = validate_commit_message_text(message)

    assert not errors


def test_merge_commit_message_is_allowed() -> None:
    errors = validate_commit_message_text("Merge branch 'feature/refactor'\n")

    assert not errors


def test_squash_merge_commit_message_with_included_checkpoints_is_valid() -> None:
    message = """\
refactor: source verification and routing (#11)

Why:
- keep the squash-merge record reviewable on main

What:
- preserve the validated pull request summary

Checks:
- GitHub Actions `ci` workflow on this PR

Included checkpoints:
- `fix(sources): harden live export parsing and verification`
- `refactor(sources): harden on-chain ids and family routing`
"""

    errors = validate_commit_message_text(message)

    assert not errors


def test_invalid_type_is_rejected() -> None:
    errors = validate_commit_message_text(
        """\
update: change commit docs

Why:
- tighten docs

What:
- rewrite the standard

Checks:
- uv run pytest
"""
    )

    assert errors == (
        "subject must match `type(scope): imperative summary` or "
        "`type: imperative summary` using one of: feat, fix, refactor, docs, "
        "test, chore, build, ci, perf, revert",
    )


def test_missing_summary_is_rejected() -> None:
    errors = validate_commit_message_text(
        """\
docs(scope): 

Why:
- tighten docs

What:
- rewrite the standard

Checks:
- uv run pytest
"""
    )

    assert errors == (
        "subject must match `type(scope): imperative summary` or "
        "`type: imperative summary` using one of: feat, fix, refactor, docs, "
        "test, chore, build, ci, perf, revert",
    )


def test_subject_over_72_characters_is_rejected() -> None:
    errors = validate_commit_message_text(
        """\
refactor(adapters): split structured CSV normalization into smaller modules today

Why:
- keep adapter seams small

What:
- split the parser

Checks:
- uv run pytest
"""
    )

    assert errors == ("subject must be 72 characters or fewer",)


def test_trailing_period_is_rejected() -> None:
    errors = validate_commit_message_text(
        """\
docs: update commit guidance.

Why:
- tighten docs

What:
- rewrite the standard

Checks:
- uv run pytest
"""
    )

    assert errors == ("subject must not end with a period",)


def test_malformed_scope_is_rejected() -> None:
    errors = validate_commit_message_text(
        """\
docs(agent_router): tighten commit rules

Why:
- tighten docs

What:
- rewrite the standard

Checks:
- uv run pytest
"""
    )

    assert errors == (
        "subject must match `type(scope): imperative summary` or "
        "`type: imperative summary` using one of: feat, fix, refactor, docs, "
        "test, chore, build, ci, perf, revert",
    )


def test_missing_structured_body_is_rejected() -> None:
    errors = validate_commit_message_text("docs: route agents to narrow standards\n")

    assert errors == ("commit message body is required with `Why:`, `What:`, `Checks:` sections",)


def test_authored_commit_message_rejects_included_checkpoints_section() -> None:
    errors = validate_commit_message_text(
        """\
docs: route agents to narrow standards

Why:
- keep routing guidance explicit

What:
- point agents to the narrowest applicable standards doc

Checks:
- uv run python -m tools.validate_commit_message .git/COMMIT_EDITMSG

Included checkpoints:
- `docs: route agents to narrow standards`
"""
    )

    assert errors == (
        "unsupported structured label: Included checkpoints:",
        "unexpected trailing content: - `docs: route agents to narrow standards`",
    )
