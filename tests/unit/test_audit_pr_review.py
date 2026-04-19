from __future__ import annotations

import json

from pytest import CaptureFixture, MonkeyPatch

import tools.audit_pr_review as audit_pr_review
from repo_support.review_verification import build_verification_plan


def _docs_changed_paths(
    base_sha: str | None = None, head_sha: str | None = None
) -> tuple[str, ...]:
    del base_sha, head_sha
    return ("docs/guides/source-intake.md",)


def _unmapped_changed_paths(
    base_sha: str | None = None, head_sha: str | None = None
) -> tuple[str, ...]:
    del base_sha, head_sha
    return ("notes/todo.md",)


def test_docs_only_diff_maps_to_docs_checks() -> None:
    plan = build_verification_plan(
        paths=("docs/guides/source-intake.md",),
        trigger="local",
        mode="planned",
    )

    assert plan.surface_report.surface_groups == ("human_docs",)
    assert plan.selected_check_ids == (
        "docs-maintenance",
        "markdownlint",
        "docs-audit",
    )
    assert plan.nonblocking_check_ids == ()
    assert plan.surface_report.unmapped_paths == ()


def test_control_plane_diff_selects_docs_and_skill_checks() -> None:
    plan = build_verification_plan(
        paths=(".agents/skills/pr-review/SKILL.md",),
        trigger="local",
        mode="planned",
    )

    assert plan.surface_report.surface_groups == ("control_plane_text",)
    assert plan.selected_check_ids == (
        "docs-maintenance",
        "markdownlint",
        "repo-agent-skills",
    )


def test_control_plane_doc_diff_selects_targeted_control_plane_checks() -> None:
    plan = build_verification_plan(
        paths=("docs/standards/commits.md",),
        trigger="local",
        mode="planned",
    )

    assert plan.surface_report.surface_groups == ("control_plane_text",)
    assert plan.selected_check_ids == (
        "docs-maintenance",
        "markdownlint",
        "target-naming",
        "docs-audit",
        "standards-guards",
        "pr-metadata-validator",
        "commit-message-validator",
    )


def test_commit_template_diff_selects_control_plane_checks() -> None:
    plan = build_verification_plan(
        paths=(".gitmessage.txt",),
        trigger="local",
        mode="planned",
    )

    assert plan.surface_report.surface_groups == ("control_plane_text",)
    assert plan.selected_check_ids == (
        "docs-maintenance",
        "standards-guards",
    )


def test_target_naming_catalog_diff_stays_control_plane_only() -> None:
    plan = build_verification_plan(
        paths=("tools/target_naming_catalog.yaml",),
        trigger="local",
        mode="planned",
    )

    assert plan.surface_report.surface_groups == ("control_plane_text",)
    assert plan.selected_check_ids == (
        "docs-maintenance",
        "target-naming",
        "docs-audit",
    )


def test_repo_code_diff_selects_full_quality_suite() -> None:
    plan = build_verification_plan(
        paths=("src/tallylot/application/normalization/normalize_source.py",),
        trigger="push_main",
        mode="planned",
    )

    assert plan.surface_report.surface_groups == ("repo_code_or_tooling",)
    assert plan.selected_check_ids == (
        "ruff",
        "mypy",
        "pyright",
        "pylint",
        "pytest-full",
        "test-stress-checks",
        "coverage-hotspots",
    )
    assert plan.blocking_check_ids[-1] == "test-stress-checks"
    assert plan.nonblocking_check_ids == ("coverage-hotspots",)


def test_packaging_sensitive_repo_code_adds_build_and_verify() -> None:
    plan = build_verification_plan(
        paths=("src/tallylot/interfaces/cli/source.py",),
        trigger="push_main",
        mode="planned",
    )

    assert "build" in plan.selected_check_ids
    assert "verify-wheel" in plan.selected_check_ids


def test_ci_workflow_diff_selects_targeted_ci_checks() -> None:
    plan = build_verification_plan(
        paths=(".github/workflows/ci.yml",),
        trigger="push_main",
        mode="planned",
    )

    assert plan.surface_report.surface_groups == ("ci_or_release",)
    assert plan.selected_check_ids == (
        "target-naming",
        "actionlint",
        "delivery-guardrails-audit",
        "ci-tooling",
        "build",
        "verify-wheel",
    )


def test_pull_request_docs_only_diff_stays_change_sensitive() -> None:
    plan = build_verification_plan(
        paths=("docs/guides/source-intake.md",),
        trigger="pull_request",
        mode="planned",
    )

    assert plan.mode == "planned"
    assert plan.selected_check_ids == (
        "commit-messages",
        "pr-metadata",
        "docs-maintenance",
        "markdownlint",
        "docs-audit",
    )


def test_forward_looking_target_doc_diff_selects_target_naming() -> None:
    plan = build_verification_plan(
        paths=("docs/concepts/pipeline-stage-contracts.md",),
        trigger="local",
        mode="planned",
    )

    assert plan.surface_report.surface_groups == ("human_docs",)
    assert plan.selected_check_ids == (
        "docs-maintenance",
        "markdownlint",
        "target-naming",
        "docs-audit",
    )


def test_docs_home_diff_selects_target_naming() -> None:
    plan = build_verification_plan(
        paths=("docs/README.md",),
        trigger="local",
        mode="planned",
    )

    assert plan.surface_report.surface_groups == ("human_docs",)
    assert plan.selected_check_ids == (
        "docs-maintenance",
        "markdownlint",
        "target-naming",
        "docs-audit",
    )


def test_roadmap_only_diff_skips_docs_audit() -> None:
    plan = build_verification_plan(
        paths=("ROADMAP.md",),
        trigger="local",
        mode="planned",
    )

    assert plan.surface_report.surface_groups == ("control_plane_text",)
    assert plan.selected_check_ids == (
        "docs-maintenance",
        "markdownlint",
        "target-naming",
        "standards-guards",
    )


def test_bridge_local_doc_diff_skips_target_naming() -> None:
    plan = build_verification_plan(
        paths=("docs/concepts/transaction-classification.md",),
        trigger="local",
        mode="planned",
    )

    assert plan.surface_report.surface_groups == ("human_docs",)
    assert plan.selected_check_ids == (
        "docs-maintenance",
        "markdownlint",
        "docs-audit",
    )


def test_pull_request_mode_can_still_force_full_suite() -> None:
    plan = build_verification_plan(
        paths=("docs/guides/source-intake.md",),
        trigger="pull_request",
        mode="full",
    )

    assert plan.mode == "full"
    assert plan.selected_check_ids == (
        "commit-messages",
        "pr-metadata",
        "docs-maintenance",
        "markdownlint",
        "target-naming",
        "docs-audit",
        "actionlint",
        "ruff",
        "mypy",
        "pyright",
        "pylint",
        "pytest-full",
        "test-stress-checks",
        "build",
        "verify-wheel",
        "coverage-hotspots",
    )


def test_full_quality_selection_suppresses_targeted_subset_tests() -> None:
    plan = build_verification_plan(
        paths=(
            ".github/workflows/ci.yml",
            "repo_support/review_verification/policy.py",
        ),
        trigger="push_main",
        mode="planned",
    )

    suppressed_ids = {check.check_id for check in plan.suppressed_checks}
    assert "ci-tooling" in suppressed_ids
    assert "audit-pr-review" in suppressed_ids
    assert "run-pr-review-checks" in suppressed_ids
    assert "pytest-full" in plan.selected_check_ids


def test_unmapped_paths_are_reported() -> None:
    plan = build_verification_plan(
        paths=("notes/todo.md",),
        trigger="local",
        mode="planned",
    )

    assert plan.surface_report.surface_groups == ()
    assert plan.surface_report.unmapped_paths == ("notes/todo.md",)


def test_audit_pr_review_can_emit_json(
    monkeypatch: MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    monkeypatch.setattr(audit_pr_review, "changed_paths", _docs_changed_paths)

    assert audit_pr_review.main(["--json"]) == 0

    report = json.loads(capsys.readouterr().out)
    assert report["surface_groups"] == ["human_docs"]
    assert report["mode"] == "planned"
    assert report["selected_checks"] == [
        "docs-maintenance",
        "markdownlint",
        "docs-audit",
    ]
    assert report["manual_red_team_review_required"] is True


def test_audit_pr_review_fails_closed_for_unmapped_paths(
    monkeypatch: MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    monkeypatch.setattr(audit_pr_review, "changed_paths", _unmapped_changed_paths)

    assert audit_pr_review.main([]) == 1
    assert "unmapped paths" in capsys.readouterr().out


def test_audit_pr_review_emits_red_team_review_reminder(
    monkeypatch: MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    monkeypatch.setattr(audit_pr_review, "changed_paths", _docs_changed_paths)

    assert audit_pr_review.main([]) == 0

    output = capsys.readouterr().out
    assert "manual red-team review: required" in output
    assert "selected verification mode: planned" in output
    assert "mandatory red-team repair loop" in output
