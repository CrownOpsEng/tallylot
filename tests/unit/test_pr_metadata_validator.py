from __future__ import annotations

from pytest import MonkeyPatch

from tools.validate_pr_metadata import (
    _validate_pr_body,
    _validate_pr_checkpoints,
    _validate_pr_title,
)


def test_pr_title_with_conventional_commit_subject_is_valid() -> None:
    errors = _validate_pr_title("refactor: preserve fact model guardrails")

    assert not errors


def test_pr_title_without_conventional_commit_subject_is_rejected() -> None:
    errors = _validate_pr_title("cleanup repo history")

    assert errors == (
        "subject must match `type(scope): imperative summary` or "
        "`type: imperative summary` using one of: feat, fix, refactor, docs, "
        "test, chore, build, ci, perf, revert",
    )


def test_pr_body_with_required_sections_is_valid() -> None:
    body = """\
Why:
- Closes #34: preserve multi-checkpoint history on main
- keep multi-checkpoint history visible on main

What:
- document and validate pull request metadata

Checks:
- uv run python -m tools.run_quality_gates

Included checkpoints:
- `docs: codify pull request standards`
"""

    errors = _validate_pr_body(body)

    assert not errors


def test_pr_body_tolerates_leading_html_comment() -> None:
    body = """\
<!-- markdownlint-disable-file MD041 MD032 -->

Why:
- Closes #34: preserve multi-checkpoint history on main
- keep multi-checkpoint history visible on main

What:
- document and validate pull request metadata

Checks:
- uv run python -m tools.run_quality_gates

Included checkpoints:
- `docs: codify pull request standards`
"""

    errors = _validate_pr_body(body)

    assert not errors


def test_pr_body_rejects_missing_section() -> None:
    body = """\
Why:
- keep multi-checkpoint history visible on main

What:
- document and validate pull request metadata

Checks:
- uv run python -m tools.run_quality_gates
"""

    errors = _validate_pr_body(body)

    assert errors == ("missing `Included checkpoints:` section",)


def test_pr_body_rejects_non_bullet_content() -> None:
    body = """\
Why:
keep multi-checkpoint history visible on main

What:
- document and validate pull request metadata

Checks:
- uv run python -m tools.run_quality_gates

Included checkpoints:
- `docs: codify pull request standards`
"""

    errors = _validate_pr_body(body)

    assert errors == (
        "`Why:` entries must use `- ` bullets",
        "`Why:` must contain at least one bullet",
    )


def test_pr_body_accepts_optional_follow_ups_section() -> None:
    body = """\
Why:
- keep multi-checkpoint history visible on main

What:
- document and validate pull request metadata

Checks:
- uv run python -m tools.run_quality_gates

Included checkpoints:
- `docs: codify pull request standards`

Follow-ups:
- Refs #34: tighten merge-repair automation
"""

    errors = _validate_pr_body(body)

    assert not errors


def test_pr_body_rejects_malformed_why_closing_bullet() -> None:
    body = """\
Why:
- Closes #34
- keep multi-checkpoint history visible on main

What:
- document and validate pull request metadata

Checks:
- uv run python -m tools.run_quality_gates

Included checkpoints:
- `docs: codify pull request standards`
"""

    errors = _validate_pr_body(body)

    assert errors == (
        "`Why:` issue-closing bullets must match `- Closes #123: problem statement`",
    )


def test_pr_body_rejects_late_why_closing_bullet() -> None:
    body = """\
Why:
- keep multi-checkpoint history visible on main
- Closes #34: preserve multi-checkpoint history on main

What:
- document and validate pull request metadata

Checks:
- uv run python -m tools.run_quality_gates

Included checkpoints:
- `docs: codify pull request standards`
"""

    errors = _validate_pr_body(body)

    assert errors == ("`Why:` issue-closing bullets must come before other bullets",)


def test_pr_body_rejects_bad_follow_up_bullet() -> None:
    body = """\
Why:
- keep multi-checkpoint history visible on main

What:
- document and validate pull request metadata

Checks:
- uv run python -m tools.run_quality_gates

Included checkpoints:
- `docs: codify pull request standards`

Follow-ups:
- follow up in #34
"""

    errors = _validate_pr_body(body)

    assert errors == (
        "`Follow-ups:` bullets must match `- Refs #123` or `- Refs #123: note`",
    )


def test_pr_checkpoints_match_commit_subjects(monkeypatch: MonkeyPatch) -> None:
    body = """\
Why:
- keep multi-checkpoint history visible on main

What:
- document and validate pull request metadata

Checks:
- uv run python -m tools.run_quality_gates

Included checkpoints:
- `docs: codify pull request standards`
- `ci: tighten workflow metadata checks`
"""

    def fake_loader(base_sha: str, head_sha: str) -> tuple[str, ...]:
        del base_sha, head_sha
        return (
            "docs: codify pull request standards",
            "ci: tighten workflow metadata checks",
        )

    monkeypatch.setattr("tools.validate_pr_metadata._load_commit_subjects", fake_loader)

    errors = _validate_pr_checkpoints(
        body,
        base_sha="0000000",
        head_sha="1111111",
    )

    assert not errors


def test_pr_checkpoints_ignore_leading_html_comment(monkeypatch: MonkeyPatch) -> None:
    body = """\
<!-- markdownlint-disable-file MD041 MD032 -->

Why:
- keep multi-checkpoint history visible on main

What:
- document and validate pull request metadata

Checks:
- uv run python -m tools.run_quality_gates

Included checkpoints:
- `docs: codify pull request standards`
"""

    def fake_loader(base_sha: str, head_sha: str) -> tuple[str, ...]:
        del base_sha, head_sha
        return ("docs: codify pull request standards",)

    monkeypatch.setattr("tools.validate_pr_metadata._load_commit_subjects", fake_loader)

    errors = _validate_pr_checkpoints(body, base_sha="base", head_sha="head")

    assert not errors


def test_pr_checkpoints_reject_non_exact_commit_subjects(
    monkeypatch: MonkeyPatch,
) -> None:
    body = """\
Why:
- keep multi-checkpoint history visible on main

What:
- document and validate pull request metadata

Checks:
- uv run python -m tools.run_quality_gates

Included checkpoints:
- docs: codify pull request standards
"""

    def fake_loader(base_sha: str, head_sha: str) -> tuple[str, ...]:
        del base_sha, head_sha
        return ("docs: codify pull request standards",)

    monkeypatch.setattr("tools.validate_pr_metadata._load_commit_subjects", fake_loader)

    errors = _validate_pr_checkpoints(body, base_sha="base", head_sha="head")

    assert errors == (
        "`Included checkpoints:` entries must wrap commit subjects in backticks",
    )


def test_pr_checkpoints_reject_subject_mismatch(monkeypatch: MonkeyPatch) -> None:
    body = """\
Why:
- keep multi-checkpoint history visible on main

What:
- document and validate pull request metadata

Checks:
- uv run python -m tools.run_quality_gates

Included checkpoints:
- `docs: codify pull request standards`
"""

    def fake_loader(base_sha: str, head_sha: str) -> tuple[str, ...]:
        del base_sha, head_sha
        return ("ci: tighten workflow metadata checks",)

    monkeypatch.setattr("tools.validate_pr_metadata._load_commit_subjects", fake_loader)

    errors = _validate_pr_checkpoints(body, base_sha="base", head_sha="head")

    assert errors == (
        "`Included checkpoints:` must exactly match the branch commit subjects in order",
    )
