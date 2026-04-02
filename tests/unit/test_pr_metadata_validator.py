from __future__ import annotations

from tools.validate_pr_metadata import validate_pr_body, validate_pr_title


def test_pr_title_with_conventional_commit_subject_is_valid() -> None:
    errors = validate_pr_title("refactor: preserve fact model guardrails")

    assert not errors


def test_pr_title_without_conventional_commit_subject_is_rejected() -> None:
    errors = validate_pr_title("cleanup repo history")

    assert errors == (
        "subject must match `type(scope): imperative summary` or "
        "`type: imperative summary` using one of: feat, fix, refactor, docs, "
        "test, chore, build, ci, perf, revert",
    )


def test_pr_body_with_required_sections_is_valid() -> None:
    body = """\
Why:
- keep mainline history concise

What:
- document and validate squash-merge metadata

Checks:
- uv run python -m tools.run_quality_gates

Included checkpoints:
- `docs: codify pull request standards`
"""

    errors = validate_pr_body(body)

    assert not errors


def test_pr_body_rejects_missing_section() -> None:
    body = """\
Why:
- keep mainline history concise

What:
- document and validate squash-merge metadata

Checks:
- uv run python -m tools.run_quality_gates
"""

    errors = validate_pr_body(body)

    assert errors == ("missing `Included checkpoints:` section",)


def test_pr_body_rejects_non_bullet_content() -> None:
    body = """\
Why:
keep mainline history concise

What:
- document and validate squash-merge metadata

Checks:
- uv run python -m tools.run_quality_gates

Included checkpoints:
- `docs: codify pull request standards`
"""

    errors = validate_pr_body(body)

    assert errors == ("`Why:` entries must use `- ` bullets", "`Why:` must contain at least one bullet")
