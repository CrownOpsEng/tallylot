from __future__ import annotations

import subprocess

from pytest import MonkeyPatch

from tools.validate_commit_message import (
    _fallback_rev_range,
    _load_commit_messages_from_range,
    _validate_commit_message_text,
)


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

    errors = _validate_commit_message_text(message)

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

    errors = _validate_commit_message_text(message)

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

    errors = _validate_commit_message_text(message)

    assert not errors


def test_merge_commit_message_is_allowed() -> None:
    errors = _validate_commit_message_text("Merge branch 'feature/refactor'\n")

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

    errors = _validate_commit_message_text(message)

    assert not errors


def test_squash_merge_commit_message_allows_wrapped_bullet_lines() -> None:
    message = """\
feat(docs): reshape repo docs and harden maintenance workflow (#14)

Why:
- reshape the repo docs into a cleaner human-first structure without
losing agent routing or mirrored workspace guidance
- make the public and internal entrypoints easier to navigate and keep
aligned with the actual TallyLot product surface

What:
- rewrite the public README, docs homepage, agent routing, and
supporting standards around the new concepts, guides, reference,
standards, and status model

Checks:
- `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run pytest
tests/unit/test_docs_maintenance.py
tests/unit/test_docs_runtime_parity.py -q --no-cov`

Included checkpoints:
- `docs(roadmap): clarify planning and state docs`
"""

    errors = _validate_commit_message_text(message)

    assert not errors


def test_invalid_type_is_rejected() -> None:
    errors = _validate_commit_message_text(
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
    errors = _validate_commit_message_text(
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
    errors = _validate_commit_message_text(
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
    errors = _validate_commit_message_text(
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
    errors = _validate_commit_message_text(
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
    errors = _validate_commit_message_text("docs: route agents to narrow standards\n")

    assert errors == ("commit message body is required with `Why:`, `What:`, `Checks:` sections",)


def test_authored_commit_message_rejects_included_checkpoints_section() -> None:
    errors = _validate_commit_message_text(
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


def test_fallback_rev_range_uses_head_commit_only() -> None:
    assert _fallback_rev_range("deadbeef..cafebabe") == "cafebabe^!"


def test_fallback_rev_range_rejects_non_range_input() -> None:
    assert _fallback_rev_range("HEAD^!") is None


def test_load_commit_messages_from_range_falls_back_for_rewritten_history(
    monkeypatch: MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        del check, capture_output, text
        command_tuple = tuple(command)
        calls.append(command_tuple)
        if command_tuple == ("git", "rev-list", "--reverse", "before..after"):
            raise subprocess.CalledProcessError(
                returncode=128,
                cmd=command,
                stderr="fatal: Invalid revision range before..after",
            )
        if command_tuple == ("git", "rev-list", "--reverse", "after^!"):
            return subprocess.CompletedProcess(command, 0, stdout="after\n", stderr="")
        if command_tuple == ("git", "show", "--quiet", "--format=%B", "after"):
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=(
                    "docs: codify pull request merge policy (#35)\n\n"
                    "Why:\n- keep history clean\n\n"
                    "What:\n- rewrite the commit record\n\n"
                    "Checks:\n- uv run pytest\n\n"
                    "Included checkpoints:\n"
                    "- `docs: codify pull request merge policy`\n"
                ),
                stderr="",
            )
        raise AssertionError(f"unexpected command: {command_tuple}")

    monkeypatch.setattr("tools.validate_commit_message.subprocess.run", fake_run)

    messages = _load_commit_messages_from_range("before..after")

    assert [message.label for message in messages] == ["commit after"]
    assert calls[:2] == [
        ("git", "rev-list", "--reverse", "before..after"),
        ("git", "rev-list", "--reverse", "after^!"),
    ]
