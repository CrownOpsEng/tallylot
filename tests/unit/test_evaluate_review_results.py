from __future__ import annotations

from pytest import CaptureFixture

from tools import evaluate_review_results


def test_nonblocking_missing_job_result_is_ignored() -> None:
    exit_code = evaluate_review_results.main(
        [
            "--selected-checks-json",
            '["ruff", "coverage-hotspots"]',
            "--nonblocking-checks-json",
            '["coverage-hotspots"]',
            "--needs-json",
            '{"ruff": {"result": "success"}}',
        ]
    )

    assert exit_code == 0


def test_blocking_missing_job_result_fails() -> None:
    exit_code = evaluate_review_results.main(
        [
            "--selected-checks-json",
            '["ruff", "pytest-full"]',
            "--nonblocking-checks-json",
            "[]",
            "--needs-json",
            '{"ruff": {"result": "success"}}',
        ]
    )

    assert exit_code == 1


def test_planner_failure_with_blank_outputs_reports_planner_result(
    capsys: CaptureFixture[str],
) -> None:
    exit_code = evaluate_review_results.main(
        [
            "--selected-checks-json",
            "",
            "--nonblocking-checks-json",
            "",
            "--needs-json",
            '{"plan-main-ci": {"result": "failure", "outputs": {}}}',
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "plan-main-ci: result=failure" in captured.err


def test_blank_outputs_without_planner_failure_fail_cleanly(
    capsys: CaptureFixture[str],
) -> None:
    exit_code = evaluate_review_results.main(
        [
            "--selected-checks-json",
            "",
            "--nonblocking-checks-json",
            "[]",
            "--needs-json",
            '{"plan-main-ci": {"result": "success"}}',
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "selected checks: missing workflow output" in captured.err
