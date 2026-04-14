from __future__ import annotations

import subprocess

from pytest import MonkeyPatch

from repo_support.review_verification import (
    CheckExecutionContext,
    ExecutionSummary,
    CheckResult,
    build_verification_plan,
    check_spec,
    resolve_check_command,
    run_plan,
)


def test_resolve_commit_message_command_uses_default_branch_merge_base(
    monkeypatch: MonkeyPatch,
) -> None:
    def fake_git_stdout(*args: str) -> str:
        if args == ("symbolic-ref", "--short", "refs/remotes/origin/HEAD"):
            return "origin/main"
        if args == ("rev-parse", "HEAD"):
            return "def456"
        if args == ("merge-base", "def456", "origin/main"):
            return "abc123"
        raise AssertionError(args)

    monkeypatch.setattr(
        "repo_support.review_verification.executor._git_stdout",
        fake_git_stdout,
    )

    command = resolve_check_command(
        check_spec("commit-messages"),
        context=CheckExecutionContext(trigger="local"),
    )

    assert command[-1] == "abc123..def456"


def test_run_plan_blocks_dependency_when_build_fails(
    monkeypatch: MonkeyPatch,
) -> None:
    def fake_run(
        command: tuple[str, ...],
        *,
        capture_output: bool,
        text: bool,
        check: bool,
        env: dict[str, str],
    ) -> subprocess.CompletedProcess[str]:
        del capture_output, text, check, env
        return subprocess.CompletedProcess(
            command,
            1 if command[:2] == ("uv", "build") else 0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    plan = build_verification_plan(
        paths=("src/tallylot/interfaces/cli/source.py",),
        trigger="push_main",
        mode="planned",
    )

    summary = run_plan(
        plan,
        context=CheckExecutionContext(trigger="push_main"),
        fail_fast=False,
    )

    results = {result.check_id: result for result in summary.results}
    assert results["build"].status == "failed"
    assert results["verify-wheel"].status == "blocked"


def test_run_plan_fail_fast_skips_remaining_checks(monkeypatch: MonkeyPatch) -> None:
    commands_seen: list[tuple[str, ...]] = []

    def fake_run(
        command: tuple[str, ...],
        *,
        capture_output: bool,
        text: bool,
        check: bool,
        env: dict[str, str],
    ) -> subprocess.CompletedProcess[str]:
        del capture_output, text, check, env
        commands_seen.append(command)
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    plan = build_verification_plan(
        paths=("src/tallylot/application/normalization/normalize_source.py",),
        trigger="push_main",
        mode="planned",
    )

    summary = run_plan(
        plan,
        context=CheckExecutionContext(trigger="push_main"),
        fail_fast=True,
    )

    assert summary.results[0].check_id == "ruff"
    assert summary.results[0].status == "failed"
    assert summary.results[1].status == "skipped"
    assert commands_seen == [("ruff", "check", ".")]


def test_execution_summary_detects_blocking_failures() -> None:
    summary = ExecutionSummary(
        results=(
            CheckResult(
                check_id="ruff",
                status="passed",
                returncode=0,
                elapsed=0.1,
                stdout="",
                stderr="",
            ),
            CheckResult(
                check_id="coverage-hotspots",
                status="failed",
                returncode=1,
                elapsed=0.1,
                stdout="",
                stderr="",
            ),
            CheckResult(
                check_id="build",
                status="blocked",
                returncode=None,
                elapsed=0.0,
                stdout="",
                stderr="",
                reason="dependency failed",
            ),
        )
    )

    assert summary.has_blocking_failures is True
