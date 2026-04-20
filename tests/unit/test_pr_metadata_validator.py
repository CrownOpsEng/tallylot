from __future__ import annotations

from pytest import MonkeyPatch

from tools.message_standards import validate_branch_name
from tools.validate_pr_metadata import (
    _validate_pr_body,
    _validate_pr_checkpoints,
    _validate_pr_title,
)


def _phase_label() -> str:
    return " ".join(("Phase", "2"))


def _phase_word_label() -> str:
    return "-".join(("phase", "zero"))


def _roadmap_label() -> str:
    return "roadmap"


def _body(
    *,
    why: str = "- keep multi-checkpoint history visible on main",
    issue_linkage: str = "- Closes #34: preserve multi-checkpoint history on main",
    follow_ups: str = "",
    included_checkpoints: str = "- `docs(commits): codify pull request standards`",
) -> str:
    body = (
        "Why:\n"
        f"{why}\n\n"
        "What:\n"
        "- document and validate pull request metadata\n\n"
        "Checks:\n"
        "- make quality\n\n"
        "Issue linkage:\n"
        f"{issue_linkage}\n\n"
        "Included checkpoints:\n"
        f"{included_checkpoints}\n"
    )
    if follow_ups:
        body += f"\nFollow-ups:\n{follow_ups}\n"
    return body


def test_pr_title_with_conventional_commit_subject_is_valid() -> None:
    errors = _validate_pr_title("refactor(guardrails): preserve fact model guardrails")

    assert not errors


def test_pr_title_without_conventional_commit_subject_is_rejected() -> None:
    errors = _validate_pr_title("cleanup repo history")

    assert errors == (
        "subject must match `type(scope): imperative summary` using one of: "
        "feat, fix, refactor, docs, test, chore, build, ci, perf, revert",
    )


def test_pr_title_with_generic_summary_is_rejected() -> None:
    errors = _validate_pr_title("docs(commits): cleanup")

    assert errors == (
        "subject summary must name a concrete repo surface or behavior; "
        "generic summaries such as `cleanup`, `misc fixes`, and "
        "`update branch` are not allowed",
    )


def test_pr_branch_with_standard_root_and_slug_is_valid() -> None:
    errors = validate_branch_name("docs/standards-skill-hardening")

    assert not errors


def test_pr_branch_rejects_non_standard_root() -> None:
    errors = validate_branch_name("control-plane/standards-hardening")

    assert errors == (
        "branch root must be one of: docs, chore, ci, build, feat, fix, "
        "refactor, test, repair",
    )


def test_pr_branch_rejects_nested_tree() -> None:
    errors = validate_branch_name("docs/standards/skill-hardening")

    assert errors == (
        "branch name must match `<root>/<slug>` with exactly one approved root "
        "and one lowercase kebab-case slug",
    )


def test_pr_branch_rejects_missing_root() -> None:
    errors = validate_branch_name("standards-skill-hardening")

    assert errors == (
        "branch name must match `<root>/<slug>` with exactly one approved root "
        "and one lowercase kebab-case slug",
    )


def test_pr_branch_rejects_uppercase_root_or_slug() -> None:
    root_errors = validate_branch_name("Docs/standards-hardening")
    slug_errors = validate_branch_name("docs/Standards-hardening")

    assert root_errors == (
        "branch root must be one of: docs, chore, ci, build, feat, fix, "
        "refactor, test, repair",
    )
    assert slug_errors == ("branch slug must be lowercase kebab-case ASCII",)


def test_pr_branch_rejects_phase_label() -> None:
    phase_label = "-".join(("phase", "0"))
    errors = validate_branch_name(f"docs/{phase_label}-hardening")

    assert errors == (
        "branch name must not use roadmap/phase labels on durable metadata "
        f"surfaces: {phase_label}",
    )


def test_pr_branch_rejects_spelled_out_phase_label() -> None:
    phase_word_label = _phase_word_label()
    errors = validate_branch_name(f"docs/{phase_word_label}-hardening")

    assert errors == (
        "branch name must not use roadmap/phase labels on durable metadata "
        f"surfaces: {phase_word_label}",
    )


def test_pr_body_with_required_sections_is_valid() -> None:
    errors = _validate_pr_body(_body())

    assert not errors


def test_pr_title_rejects_phase_label() -> None:
    phase_label = _phase_label()
    errors = _validate_pr_title(f"docs(standards): {phase_label} hardening")

    assert errors == (
        "PR title must not use roadmap/phase labels on durable metadata "
        f"surfaces: {phase_label}",
    )


def test_pr_title_rejects_spelled_out_phase_label() -> None:
    phase_word_title = " ".join(("Phase", "Zero"))
    errors = _validate_pr_title(f"docs(standards): {phase_word_title} hardening")

    assert errors == (
        "PR title must not use roadmap/phase labels on durable metadata "
        f"surfaces: {phase_word_title}",
    )


def test_pr_body_tolerates_leading_html_comment() -> None:
    body = f"<!-- markdownlint-disable-file MD041 MD032 -->\n\n{_body()}"

    errors = _validate_pr_body(body)

    assert not errors


def test_pr_body_rejects_missing_section() -> None:
    body = """\
Why:
- keep multi-checkpoint history visible on main

What:
- document and validate pull request metadata

Checks:
- make quality

Issue linkage:
- Closes #34: preserve multi-checkpoint history on main
"""

    errors = _validate_pr_body(body)

    assert errors == ("missing `Included checkpoints:` section",)


def test_pr_body_rejects_roadmap_label() -> None:
    roadmap_label = _roadmap_label()
    errors = _validate_pr_body(
        _body(why=f"- keep {roadmap_label} references out of PR metadata")
    )

    assert errors == (
        "PR body must not use roadmap/phase labels on durable metadata "
        f"surfaces: {roadmap_label}",
    )


def test_pr_body_rejects_spelled_out_phase_label() -> None:
    phase_word_label = _phase_word_label()
    errors = _validate_pr_body(
        _body(why=f"- keep {phase_word_label} references out of PR metadata")
    )

    assert errors == (
        "PR body must not use roadmap/phase labels on durable metadata "
        f"surfaces: {phase_word_label}",
    )


def test_pr_body_rejects_missing_issue_linkage_section() -> None:
    body = """\
Why:
- keep multi-checkpoint history visible on main

What:
- document and validate pull request metadata

Checks:
- make quality

Included checkpoints:
- `docs(commits): codify pull request standards`
"""

    errors = _validate_pr_body(body)

    assert errors == ("missing `Issue linkage:` section",)


def test_pr_body_rejects_non_bullet_content() -> None:
    body = """\
Why:
keep multi-checkpoint history visible on main

What:
- document and validate pull request metadata

Checks:
- make quality

Issue linkage:
- Closes #34: preserve multi-checkpoint history on main

Included checkpoints:
- `docs(commits): codify pull request standards`
"""

    errors = _validate_pr_body(body)

    assert errors == (
        "`Why:` entries must use `- ` bullets",
        "`Why:` must contain at least one bullet",
    )


def test_pr_body_accepts_optional_follow_ups_section() -> None:
    errors = _validate_pr_body(
        _body(
            issue_linkage="- Refs #34: preserve multi-checkpoint history on main",
            follow_ups="- Refs #35: tighten merge-repair automation",
        )
    )

    assert not errors


def test_pr_body_rejects_issue_linkage_in_why() -> None:
    errors = _validate_pr_body(
        _body(
            why="- Closes #34: preserve multi-checkpoint history on main",
            issue_linkage="- Refs #34: preserve multi-checkpoint history on main",
        )
    )

    assert errors == (
        "`Why:` must describe the motivating problem, trigger, constraint, or "
        "risk that makes the PR necessary; move issue linkage bullets to "
        "`Issue linkage:`",
    )


def test_pr_body_rejects_malformed_issue_linkage_closing_bullet() -> None:
    errors = _validate_pr_body(_body(issue_linkage="- Closes #34"))

    assert errors == (
        "`Issue linkage:` closing bullets must match "
        "`- Closes #123: problem statement`",
    )


def test_pr_body_rejects_bad_issue_linkage_reference_bullet() -> None:
    errors = _validate_pr_body(_body(issue_linkage="- Refs #34 because it is related"))

    assert errors == (
        "`Issue linkage:` reference bullets must match "
        "`- Refs #123` or `- Refs #123: note`",
    )


def test_pr_body_accepts_explicit_none_issue_linkage() -> None:
    errors = _validate_pr_body(
        _body(issue_linkage="- None: trivial maintenance slice with no existing issue")
    )

    assert not errors


def test_pr_body_rejects_bad_none_issue_linkage_bullet() -> None:
    errors = _validate_pr_body(_body(issue_linkage="- None"))

    assert errors == (
        "`Issue linkage:` no-issue bullets must match `- None: explanation`",
    )


def test_pr_body_rejects_none_issue_linkage_with_other_bullets() -> None:
    errors = _validate_pr_body(
        _body(
            issue_linkage=(
                "- None: trivial maintenance slice with no existing issue\n"
                "- Refs #34: preserve multi-checkpoint history on main"
            )
        )
    )

    assert errors == ("`Issue linkage:` `- None: ...` must be the only bullet",)


def test_pr_body_rejects_bad_follow_up_bullet() -> None:
    errors = _validate_pr_body(
        _body(
            issue_linkage="- Refs #34: preserve multi-checkpoint history on main",
            follow_ups="- follow up in #35",
        )
    )

    assert errors == (
        "`Follow-ups:` bullets must match `- Refs #123` or `- Refs #123: note`",
    )


def test_pr_checkpoints_match_commit_subjects(monkeypatch: MonkeyPatch) -> None:
    body = _body(
        issue_linkage="- Refs #34: preserve multi-checkpoint history on main",
        included_checkpoints=(
            "- `docs(commits): codify pull request standards`\n"
            "- `ci(workflows): tighten workflow metadata checks`"
        ),
    )

    def fake_loader(base_sha: str, head_sha: str) -> tuple[str, ...]:
        del base_sha, head_sha
        return (
            "docs(commits): codify pull request standards",
            "ci(workflows): tighten workflow metadata checks",
        )

    monkeypatch.setattr("tools.validate_pr_metadata._load_commit_subjects", fake_loader)

    errors = _validate_pr_checkpoints(
        body,
        base_sha="0000000",
        head_sha="1111111",
    )

    assert not errors


def test_pr_checkpoints_ignore_leading_html_comment(monkeypatch: MonkeyPatch) -> None:
    body = (
        "<!-- markdownlint-disable-file MD041 MD032 -->\n\n"
        f"{_body(issue_linkage='- Refs #34: preserve multi-checkpoint history on main')}"
    )

    def fake_loader(base_sha: str, head_sha: str) -> tuple[str, ...]:
        del base_sha, head_sha
        return ("docs(commits): codify pull request standards",)

    monkeypatch.setattr("tools.validate_pr_metadata._load_commit_subjects", fake_loader)

    errors = _validate_pr_checkpoints(body, base_sha="base", head_sha="head")

    assert not errors


def test_pr_checkpoints_reject_non_exact_commit_subjects(
    monkeypatch: MonkeyPatch,
) -> None:
    body = _body(
        issue_linkage="- Refs #34: preserve multi-checkpoint history on main",
        included_checkpoints="- docs(commits): codify pull request standards",
    )

    def fake_loader(base_sha: str, head_sha: str) -> tuple[str, ...]:
        del base_sha, head_sha
        return ("docs(commits): codify pull request standards",)

    monkeypatch.setattr("tools.validate_pr_metadata._load_commit_subjects", fake_loader)

    errors = _validate_pr_checkpoints(body, base_sha="base", head_sha="head")

    assert errors == (
        "`Included checkpoints:` entries must wrap commit subjects in backticks",
    )


def test_pr_checkpoints_reject_subject_mismatch(monkeypatch: MonkeyPatch) -> None:
    body = _body(issue_linkage="- Refs #34: preserve multi-checkpoint history on main")

    def fake_loader(base_sha: str, head_sha: str) -> tuple[str, ...]:
        del base_sha, head_sha
        return ("ci(workflows): tighten workflow metadata checks",)

    monkeypatch.setattr("tools.validate_pr_metadata._load_commit_subjects", fake_loader)

    errors = _validate_pr_checkpoints(body, base_sha="base", head_sha="head")

    assert errors == (
        "`Included checkpoints:` must exactly match the branch commit subjects in order",
    )
