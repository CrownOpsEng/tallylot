from __future__ import annotations

from pytest import CaptureFixture, MonkeyPatch

from repo_support.pr_review import classify_changed_paths
import tools.run_pr_review_checks as run_pr_review_checks


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


def test_docs_only_diff_runs_docs_maintenance_only() -> None:
    plan = classify_changed_paths(("docs/guides/source-intake.md",))

    assert [step.name for step in run_pr_review_checks._steps_for_plan(plan)] == [
        "docs-maintenance"
    ]


def test_control_plane_route_diff_runs_targeted_policy_checks() -> None:
    plan = classify_changed_paths((".claude/commands/pr-review.md",))

    assert [step.name for step in run_pr_review_checks._steps_for_plan(plan)] == [
        "docs-maintenance",
        "standards-guards",
        "docs-runtime-parity",
    ]


def test_repo_code_diff_runs_full_quality_gates() -> None:
    plan = classify_changed_paths(("src/tallylot/interfaces/cli/source.py",))

    assert [step.name for step in run_pr_review_checks._steps_for_plan(plan)] == [
        "quality-gates-full"
    ]


def test_ci_workflow_diff_runs_ci_parity_and_targeted_audits() -> None:
    plan = classify_changed_paths((".github/workflows/ci.yml",))

    assert [step.name for step in run_pr_review_checks._steps_for_plan(plan)] == [
        "delivery-guardrails-audit",
        "ci-parity-tooling",
        "ci-parity",
    ]


def test_mixed_docs_and_code_diff_keeps_surface_specific_checks() -> None:
    plan = classify_changed_paths(
        ("docs/guides/source-intake.md", "src/tallylot/interfaces/cli/source.py")
    )

    assert [step.name for step in run_pr_review_checks._steps_for_plan(plan)] == [
        "docs-maintenance",
        "quality-gates-full",
    ]


def test_run_pr_review_checks_fails_closed_for_unmapped_paths(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(run_pr_review_checks, "changed_paths", _unmapped_changed_paths)

    assert run_pr_review_checks.main([]) == 1


def test_run_pr_review_checks_runs_expected_steps(
    monkeypatch: MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    monkeypatch.setattr(run_pr_review_checks, "changed_paths", _docs_changed_paths)
    steps_seen: list[str] = []

    def fake_run_step(step: run_pr_review_checks.ReviewCheckStep) -> int:
        steps_seen.append(step.name)
        return 0

    monkeypatch.setattr(run_pr_review_checks, "_run_step", fake_run_step)

    assert run_pr_review_checks.main([]) == 0
    assert steps_seen == ["docs-maintenance"]
    assert "no changed paths detected" not in capsys.readouterr().out
