from __future__ import annotations

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
