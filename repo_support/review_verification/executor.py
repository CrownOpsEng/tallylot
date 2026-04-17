from __future__ import annotations

import json
import shutil
import subprocess
import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from repo_support.parallel_work import run_parallel_batch
from repo_support.pyright_config import ensure_pyright_local_config
from repo_support.uv_environment import repo_uv_environment

from .catalog import CHECK_SPECS, CheckSpec
from .policy import VerificationPlan
from .surfaces import default_branch_ref

CheckStatus = Literal["passed", "failed", "skipped", "blocked"]


@dataclass(frozen=True)
class CheckExecutionContext:
    trigger: Literal["pull_request", "push_main", "local"]
    base_sha: str | None = None
    head_sha: str | None = None
    pr_title: str | None = None
    pr_body: str | None = None
    changed_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class CheckResult:
    check_id: str
    status: CheckStatus
    returncode: int | None
    elapsed: float
    stdout: str
    stderr: str
    reason: str | None = None


@dataclass(frozen=True)
class ExecutionSummary:
    results: tuple[CheckResult, ...]

    @property
    def has_blocking_failures(self) -> bool:
        for result in self.results:
            spec = CHECK_SPECS[result.check_id]
            if spec.blocking and result.status in {"failed", "blocked"}:
                return True
        return False


def _git_stdout(*args: str) -> str:
    result = subprocess.run(
        ("git", *args),
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _resolve_default_base_head(context: CheckExecutionContext) -> tuple[str, str]:
    if context.base_sha is not None and context.head_sha is not None:
        return context.base_sha, context.head_sha

    head_sha = context.head_sha or _git_stdout("rev-parse", "HEAD")
    if context.base_sha is not None:
        return context.base_sha, head_sha

    default_branch = default_branch_ref()
    try:
        base_sha = _git_stdout("merge-base", head_sha, default_branch)
    except subprocess.CalledProcessError:
        base_sha = f"{head_sha}^"
    return base_sha, head_sha


def _load_open_pr_metadata() -> tuple[str, str, str] | None:
    if shutil.which("gh") is None:
        return None

    result = subprocess.run(
        ("gh", "pr", "view", "--json", "title,body,baseRefOid"),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        if "no pull requests found" in result.stderr.lower():
            return None
        raise RuntimeError(
            result.stderr.strip() or "unable to load pull request metadata with gh"
        )

    payload = json.loads(result.stdout)
    title = payload.get("title")
    body = payload.get("body")
    base_ref_oid = payload.get("baseRefOid")
    if (
        not isinstance(title, str)
        or not isinstance(body, str)
        or not isinstance(base_ref_oid, str)
    ):
        raise RuntimeError("gh pr view returned incomplete pull request metadata")
    return title, body, base_ref_oid


def _resolved_pr_metadata(
    context: CheckExecutionContext,
) -> tuple[str, str, str, str]:
    base_sha, head_sha = _resolve_default_base_head(context)
    title = context.pr_title
    body = context.pr_body
    resolved_base = base_sha
    if title is not None and body is not None:
        return title, body, resolved_base, head_sha

    metadata = _load_open_pr_metadata()
    if metadata is None:
        raise RuntimeError(
            "pull request metadata is required; open a PR or pass "
            "--pr-title and --pr-body-file"
        )
    metadata_title, metadata_body, metadata_base = metadata
    return (
        title or metadata_title,
        body or metadata_body,
        context.base_sha or metadata_base,
        head_sha,
    )


def resolve_check_command(
    spec: CheckSpec, *, context: CheckExecutionContext
) -> tuple[str, ...]:
    command_parts = spec.command
    replacements: dict[str, str] = {}
    if any(
        placeholder in part
        for placeholder in ("{base_sha}", "{head_sha}")
        for part in command_parts
    ):
        base_sha, head_sha = _resolve_default_base_head(context)
        replacements["{base_sha}"] = base_sha
        replacements["{head_sha}"] = head_sha
    if any(
        placeholder in part
        for placeholder in ("{pr_title}", "{pr_body}")
        for part in command_parts
    ):
        title, body, base_sha, head_sha = _resolved_pr_metadata(context)
        replacements["{pr_title}"] = title
        replacements["{pr_body}"] = body
        replacements["{base_sha}"] = base_sha
        replacements["{head_sha}"] = head_sha

    command = tuple(
        part if not replacements else _replace_placeholders(part, replacements)
        for part in spec.command
    )
    if spec.id == "coverage-hotspots" and context.base_sha and context.head_sha:
        return (
            *command,
            "--base-sha",
            context.base_sha,
            "--head-sha",
            context.head_sha,
        )
    if spec.id == "target-naming" and context.changed_paths:
        return (*command, "--paths", *context.changed_paths)
    return command


def _replace_placeholders(part: str, replacements: dict[str, str]) -> str:
    value = part
    for placeholder, replacement in replacements.items():
        value = value.replace(placeholder, replacement)
    return value


def _print_result(result: CheckResult) -> None:
    reason = f" reason={result.reason}" if result.reason else ""
    returncode = "" if result.returncode is None else f" exit={result.returncode}"
    print(
        f"[{result.check_id}] status={result.status}{returncode} "
        f"elapsed={result.elapsed:.2f}s{reason}",
        flush=True,
    )
    if result.stdout:
        print(result.stdout.rstrip(), flush=True)
    if result.stderr:
        print(result.stderr.rstrip(), flush=True)


def run_check(spec: CheckSpec, *, context: CheckExecutionContext) -> CheckResult:
    command = resolve_check_command(spec, context=context)
    started = time.perf_counter()
    try:
        if spec.id == "pyright":
            ensure_pyright_local_config()
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            env=repo_uv_environment(),
        )
    except RuntimeError as error:
        return CheckResult(
            check_id=spec.id,
            status="failed",
            returncode=1,
            elapsed=time.perf_counter() - started,
            stdout="",
            stderr=str(error),
        )
    return CheckResult(
        check_id=spec.id,
        status="passed" if result.returncode == 0 else "failed",
        returncode=result.returncode,
        elapsed=time.perf_counter() - started,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def _blocked_result(check_id: str, *, reason: str) -> CheckResult:
    return CheckResult(
        check_id=check_id,
        status="blocked",
        returncode=None,
        elapsed=0.0,
        stdout="",
        stderr="",
        reason=reason,
    )


def _skipped_result(check_id: str, *, reason: str) -> CheckResult:
    return CheckResult(
        check_id=check_id,
        status="skipped",
        returncode=None,
        elapsed=0.0,
        stdout="",
        stderr="",
        reason=reason,
    )


def _print_summary(results: Sequence[CheckResult]) -> None:
    grouped = {
        "passed": [result.check_id for result in results if result.status == "passed"],
        "failed": [result.check_id for result in results if result.status == "failed"],
        "skipped": [
            result.check_id for result in results if result.status == "skipped"
        ],
        "blocked": [
            result.check_id for result in results if result.status == "blocked"
        ],
    }
    print("[summary] review verification", flush=True)
    for status in ("passed", "failed", "skipped", "blocked"):
        values = ", ".join(grouped[status]) or "none"
        print(f"[summary:{status}] {values}", flush=True)


def _run_ready_checks(
    ready_check_ids: tuple[str, ...],
    *,
    context: CheckExecutionContext,
    parallel: bool,
) -> tuple[CheckResult, ...]:
    if not parallel:
        return tuple(
            run_check(CHECK_SPECS[check_id], context=context)
            for check_id in ready_check_ids
        )
    return run_parallel_batch(
        ready_check_ids,
        runner=lambda check_id: run_check(CHECK_SPECS[check_id], context=context),
    )


def run_plan(
    plan: VerificationPlan,
    *,
    context: CheckExecutionContext,
    fail_fast: bool,
    parallel: bool = False,
) -> ExecutionSummary:
    results: list[CheckResult] = []
    results_by_check_id: dict[str, CheckResult] = {}
    stop_after_failure = False

    pending_check_ids: list[str] = list(plan.selected_check_ids)
    while pending_check_ids:
        if stop_after_failure:
            for check_id in pending_check_ids:
                result = _skipped_result(
                    check_id, reason=f"fail-fast after {results[-1].check_id}"
                )
                results.append(result)
                results_by_check_id[check_id] = result
                _print_result(result)
            break

        ready_check_ids: list[str] = []
        blocked_check_ids: list[tuple[str, str]] = []
        for check_id in pending_check_ids:
            spec = CHECK_SPECS[check_id]
            blocking_dependency = next(
                (
                    dependency_id
                    for dependency_id in spec.dependency_ids
                    if dependency_id in results_by_check_id
                    and results_by_check_id[dependency_id].status != "passed"
                ),
                None,
            )
            if blocking_dependency is not None:
                blocked_check_ids.append(
                    (check_id, f"dependency {blocking_dependency} did not pass")
                )
                continue
            if all(
                dependency_id in results_by_check_id
                for dependency_id in spec.dependency_ids
            ):
                ready_check_ids.append(check_id)

        if ready_check_ids:
            first_ready_check_id: str = ready_check_ids[0]
            batch_check_ids: tuple[str, ...] = (
                tuple(ready_check_ids) if parallel else (first_ready_check_id,)
            )
            ready_results = _run_ready_checks(
                batch_check_ids,
                context=context,
                parallel=parallel,
            )
            for result in ready_results:
                results.append(result)
                results_by_check_id[result.check_id] = result
                _print_result(result)
            pending_check_ids = [
                check_id
                for check_id in pending_check_ids
                if check_id not in batch_check_ids
            ]
            if fail_fast and any(
                CHECK_SPECS[result.check_id].blocking and result.status == "failed"
                for result in ready_results
            ):
                stop_after_failure = True
            continue

        if blocked_check_ids:
            blocked_check_id_set: set[str] = {
                blocked_check_id for blocked_check_id, _reason in blocked_check_ids
            }
            for check_id, reason in blocked_check_ids:
                result = _blocked_result(check_id, reason=reason)
                results.append(result)
                results_by_check_id[check_id] = result
                _print_result(result)
            pending_check_ids = [
                check_id
                for check_id in pending_check_ids
                if check_id not in blocked_check_id_set
            ]
            continue

        raise RuntimeError(
            "verification plan contains unresolved dependency cycle or missing dependency result"
        )

    _print_summary(results)
    return ExecutionSummary(results=tuple(results))
