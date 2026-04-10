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


def _mixed_ci_and_repo_code_changed_paths(
    base_sha: str | None = None, head_sha: str | None = None
) -> tuple[str, ...]:
    del base_sha, head_sha
    return (
        ".github/workflows/ci.yml",
        "src/tallylot/application/normalization/normalize_source.py",
    )


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
    plan = classify_changed_paths(
        ("src/tallylot/application/normalization/normalize_source.py",)
    )

    assert [step.name for step in run_pr_review_checks._steps_for_plan(plan)] == [
        "quality-gates-full",
        "test-stress-checks",
        "coverage-hotspots",
    ]


def test_packaging_sensitive_repo_code_runs_packaging_verification() -> None:
    plan = classify_changed_paths(("src/tallylot/interfaces/cli/source.py",))

    assert [step.name for step in run_pr_review_checks._steps_for_plan(plan)] == [
        "quality-gates-full",
        "test-stress-checks",
        "pre-merge-packaging",
        "coverage-hotspots",
    ]


def test_ci_workflow_diff_runs_ci_parity_and_targeted_audits() -> None:
    plan = classify_changed_paths((".github/workflows/ci.yml",))

    assert [step.name for step in run_pr_review_checks._steps_for_plan(plan)] == [
        "delivery-guardrails-audit",
        "ci-parity-tooling",
        "ci-parity",
        "test-stress-checks",
    ]


def test_mixed_repo_code_and_ci_diff_uses_ci_parity_as_broad_runner() -> None:
    plan = classify_changed_paths(
        (
            ".github/workflows/ci.yml",
            "src/tallylot/application/normalization/normalize_source.py",
        )
    )

    assert [step.name for step in run_pr_review_checks._steps_for_plan(plan)] == [
        "delivery-guardrails-audit",
        "ci-parity-tooling",
        "ci-parity",
        "test-stress-checks",
        "coverage-hotspots",
    ]


def test_mixed_docs_and_code_diff_keeps_surface_specific_checks() -> None:
    plan = classify_changed_paths(
        ("docs/guides/source-intake.md", "src/tallylot/interfaces/cli/source.py")
    )

    assert [step.name for step in run_pr_review_checks._steps_for_plan(plan)] == [
        "docs-maintenance",
        "quality-gates-full",
        "test-stress-checks",
        "pre-merge-packaging",
        "coverage-hotspots",
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
    output = capsys.readouterr().out
    assert "no changed paths detected" not in output
    assert run_pr_review_checks.REVIEW_LOOP_REMINDER in output
    assert "continue the red-team review loop" in output


def test_run_pr_review_checks_explains_ci_parity_subsumes_quality(
    monkeypatch: MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        run_pr_review_checks,
        "changed_paths",
        _mixed_ci_and_repo_code_changed_paths,
    )

    def fake_run_step(step: run_pr_review_checks.ReviewCheckStep) -> int:
        del step
        return 0

    monkeypatch.setattr(run_pr_review_checks, "_run_step", fake_run_step)

    assert run_pr_review_checks.main([]) == 0
    output = capsys.readouterr().out
    assert "ci-parity is the broad runner for this diff" in output
    assert "duplicate quality-gates-full is intentionally skipped" in output
