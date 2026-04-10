from __future__ import annotations

import json

from pytest import CaptureFixture, MonkeyPatch

from repo_support.pr_review import classify_changed_paths
import tools.audit_pr_review as audit_pr_review


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


def test_docs_only_diff_maps_to_human_docs() -> None:
    plan = classify_changed_paths(("docs/guides/source-intake.md",))

    assert plan.surface_groups == ("human_docs",)
    assert plan.verification_level == "docs-maintenance"
    assert plan.requires_full_quality_gates is False
    assert plan.requires_ci_parity is False
    assert plan.requires_pre_merge_packaging_verification is False
    assert plan.requires_test_stress_checks is False
    assert plan.requires_coverage_hotspot_report is False
    assert [check.name for check in plan.targeted_checks] == ["docs-maintenance"]
    assert plan.unmapped_paths == ()


def test_control_plane_diff_maps_to_targeted_review_surface() -> None:
    plan = classify_changed_paths((".agents/skills/pr-review/SKILL.md",))

    assert plan.surface_groups == ("control_plane_text",)
    assert plan.verification_level == "control-plane-targeted"
    assert plan.requires_full_quality_gates is False
    assert plan.requires_ci_parity is False
    assert [check.name for check in plan.targeted_checks] == [
        "docs-maintenance",
        "repo-agent-skills",
    ]


def test_repo_code_diff_maps_to_full_quality_gates() -> None:
    plan = classify_changed_paths(
        ("src/tallylot/application/normalization/normalize_source.py",)
    )

    assert plan.surface_groups == ("repo_code_or_tooling",)
    assert plan.verification_level == "quality-gates-full"
    assert plan.requires_full_quality_gates is True
    assert plan.requires_ci_parity is False
    assert plan.requires_pre_merge_packaging_verification is False
    assert plan.requires_test_stress_checks is True
    assert plan.requires_coverage_hotspot_report is True
    assert "design and ownership" in plan.review_domains


def test_repo_root_conftest_maps_to_repo_code_review_surface() -> None:
    plan = classify_changed_paths(("conftest.py",))

    assert plan.surface_groups == ("repo_code_or_tooling",)
    assert plan.verification_level == "quality-gates-full"
    assert plan.requires_full_quality_gates is True
    assert plan.requires_test_stress_checks is True
    assert plan.unmapped_paths == ()


def test_packaging_sensitive_repo_code_adds_pre_merge_packaging_verification() -> None:
    plan = classify_changed_paths(("src/tallylot/interfaces/cli/source.py",))

    assert plan.surface_groups == ("repo_code_or_tooling",)
    assert plan.verification_level == "quality-gates-full"
    assert plan.requires_full_quality_gates is True
    assert plan.requires_pre_merge_packaging_verification is True
    assert plan.requires_test_stress_checks is True
    assert plan.requires_coverage_hotspot_report is True


def test_ci_workflow_diff_maps_to_ci_parity() -> None:
    plan = classify_changed_paths((".github/workflows/pr-review.yml",))

    assert plan.surface_groups == ("ci_or_release",)
    assert plan.verification_level == "ci-parity"
    assert plan.requires_full_quality_gates is False
    assert plan.requires_ci_parity is True
    assert plan.requires_pre_merge_packaging_verification is False
    assert plan.requires_test_stress_checks is True
    assert plan.requires_coverage_hotspot_report is False
    assert [check.name for check in plan.targeted_checks] == [
        "delivery-guardrails-audit",
        "run-pr-review-checks",
    ]


def test_github_action_diff_maps_to_ci_parity() -> None:
    plan = classify_changed_paths((".github/actions/setup-python-uv/action.yml",))

    assert plan.surface_groups == ("ci_or_release",)
    assert plan.verification_level == "ci-parity"
    assert plan.requires_ci_parity is True
    assert plan.requires_test_stress_checks is True
    assert [check.name for check in plan.targeted_checks] == ["ci-parity-tooling"]


def test_mixed_diff_uses_strongest_verification_level() -> None:
    plan = classify_changed_paths(
        (
            "docs/guides/source-intake.md",
            "src/tallylot/application/normalization/normalize_source.py",
        )
    )

    assert plan.surface_groups == ("human_docs", "repo_code_or_tooling")
    assert plan.verification_level == "quality-gates-full"
    assert plan.requires_full_quality_gates is True
    assert plan.requires_test_stress_checks is True
    assert plan.requires_coverage_hotspot_report is True
    assert [check.name for check in plan.targeted_checks] == ["docs-maintenance"]


def test_unmapped_paths_are_reported() -> None:
    plan = classify_changed_paths(("notes/todo.md",))

    assert plan.surface_groups == ()
    assert plan.unmapped_paths == ("notes/todo.md",)


def test_audit_pr_review_can_emit_json(
    monkeypatch: MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    monkeypatch.setattr(audit_pr_review, "changed_paths", _docs_changed_paths)

    assert audit_pr_review.main(["--json"]) == 0

    report = json.loads(capsys.readouterr().out)
    assert report["surface_groups"] == ["human_docs"]
    assert report["verification_level"] == "docs-maintenance"
    assert report["requires_pre_merge_packaging_verification"] is False
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
    assert "mandatory red-team repair loop" in output
    assert "next issue-finding pass" in output
