from __future__ import annotations

import subprocess
import threading

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


def test_resolve_pr_metadata_command_includes_branch_name() -> None:
    command = resolve_check_command(
        check_spec("pr-metadata"),
        context=CheckExecutionContext(
            trigger="pull_request",
            base_sha="abc123",
            head_sha="def456",
            branch_name="docs/metadata-hardening",
            pr_title="docs(commits): harden durable metadata policy",
            pr_body="Why:\n- test\n\nWhat:\n- test\n\nChecks:\n- test\n\nIssue linkage:\n- None: test\n\nIncluded checkpoints:\n- `docs(commits): harden durable metadata policy`\n",
        ),
    )

    assert "--branch-name" in command
    assert "docs/metadata-hardening" in command


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


def test_run_plan_can_execute_ready_checks_in_parallel(
    monkeypatch: MonkeyPatch,
) -> None:
    barrier = threading.Barrier(3)

    def fake_run_check(spec: object, *, context: CheckExecutionContext) -> CheckResult:
        del context
        barrier.wait(timeout=1.0)
        check_id = getattr(spec, "id")
        return CheckResult(
            check_id=check_id,
            status="passed",
            returncode=0,
            elapsed=0.0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(
        "repo_support.review_verification.executor.run_check",
        fake_run_check,
    )
    plan = build_verification_plan(
        paths=("docs/guides/source-intake.md",),
        trigger="local",
        mode="planned",
    )

    summary = run_plan(
        plan,
        context=CheckExecutionContext(trigger="local"),
        fail_fast=True,
        parallel=True,
    )

    assert tuple(result.check_id for result in summary.results) == (
        "docs-maintenance",
        "markdownlint",
        "docs-audit",
    )


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
