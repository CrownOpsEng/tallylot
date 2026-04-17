from __future__ import annotations

from pathlib import Path
from typing import cast

from pytest import CaptureFixture, MonkeyPatch

import tools.run_pr_review_checks as run_pr_review_checks
from repo_support.review_verification import (
    CheckExecutionContext,
    CheckResult,
    ExecutionSummary,
)


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


def test_run_pr_review_checks_fails_closed_for_unmapped_paths(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(run_pr_review_checks, "changed_paths", _unmapped_changed_paths)

    assert run_pr_review_checks.main([]) == 1


def test_run_pr_review_checks_runs_expected_plan(
    monkeypatch: MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    monkeypatch.setattr(run_pr_review_checks, "changed_paths", _docs_changed_paths)
    monkeypatch.setattr(run_pr_review_checks, "run_local_autofix", lambda: 0)
    contexts: list[CheckExecutionContext] = []

    def fake_run_plan(*_args: object, **kwargs: object) -> ExecutionSummary:
        contexts.append(cast(CheckExecutionContext, kwargs["context"]))
        return ExecutionSummary(
            results=(
                CheckResult(
                    check_id="docs-maintenance",
                    status="passed",
                    returncode=0,
                    elapsed=0.0,
                    stdout="",
                    stderr="",
                ),
                CheckResult(
                    check_id="markdownlint",
                    status="passed",
                    returncode=0,
                    elapsed=0.0,
                    stdout="",
                    stderr="",
                ),
                CheckResult(
                    check_id="target-naming",
                    status="passed",
                    returncode=0,
                    elapsed=0.0,
                    stdout="",
                    stderr="",
                ),
            )
        )

    monkeypatch.setattr(run_pr_review_checks, "run_plan", fake_run_plan)

    assert run_pr_review_checks.main([]) == 0
    assert len(contexts) == 1
    output = capsys.readouterr().out
    assert run_pr_review_checks.REVIEW_LOOP_REMINDER in output
    assert "verification complete" in output


def test_run_pr_review_checks_returns_failure_on_blocking_failures(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(run_pr_review_checks, "changed_paths", _docs_changed_paths)
    monkeypatch.setattr(run_pr_review_checks, "run_local_autofix", lambda: 0)

    def fake_run_plan(*_args: object, **_kwargs: object) -> ExecutionSummary:
        return ExecutionSummary(
            results=(
                CheckResult(
                    check_id="docs-maintenance",
                    status="failed",
                    returncode=1,
                    elapsed=0.0,
                    stdout="",
                    stderr="boom",
                ),
            )
        )

    monkeypatch.setattr(run_pr_review_checks, "run_plan", fake_run_plan)

    assert run_pr_review_checks.main([]) == 1


def test_run_pr_review_checks_reads_pr_body_file(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(run_pr_review_checks, "changed_paths", _docs_changed_paths)
    monkeypatch.setattr(run_pr_review_checks, "run_local_autofix", lambda: 0)
    pr_body_path = tmp_path / "pr.md"
    pr_body_path.write_text("Why:\n- explain\n", encoding="utf-8")
    seen_contexts: list[CheckExecutionContext] = []

    def fake_run_plan(*_args: object, **kwargs: object) -> ExecutionSummary:
        seen_contexts.append(cast(CheckExecutionContext, kwargs["context"]))
        return ExecutionSummary(results=())

    monkeypatch.setattr(run_pr_review_checks, "run_plan", fake_run_plan)

    assert (
        run_pr_review_checks.main(
            ["--mode", "full", "--pr-body-file", str(pr_body_path)]
        )
        == 0
    )
    assert seen_contexts[0].pr_body == "Why:\n- explain\n"


def test_run_pr_review_checks_can_skip_local_autofix(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(run_pr_review_checks, "changed_paths", _docs_changed_paths)
    calls: list[str] = []

    def fake_run_plan(*_args: object, **_kwargs: object) -> ExecutionSummary:
        return ExecutionSummary(results=())

    monkeypatch.setattr(run_pr_review_checks, "run_plan", fake_run_plan)

    def fake_run_local_autofix() -> int:
        calls.append("autofix")
        return 0

    monkeypatch.setattr(
        run_pr_review_checks, "run_local_autofix", fake_run_local_autofix
    )

    assert run_pr_review_checks.main(["--no-auto-fix"]) == 0
    assert calls == []
