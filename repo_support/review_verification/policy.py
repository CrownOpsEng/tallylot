from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Literal

from .catalog import (
    CHECK_ORDER,
    CHECK_SPECS,
)
from .surfaces import (
    SurfaceReport,
    classify_changed_paths,
    is_packaging_sensitive_path,
    is_production_code_path,
)

VerificationMode = Literal["planned", "full"]
VerificationTrigger = Literal["pull_request", "push_main", "local"]
FULL_PR_CHECK_IDS = (
    "commit-messages",
    "pr-metadata",
    "docs-maintenance",
    "markdownlint",
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
FULL_QUALITY_CHECK_IDS = (
    "ruff",
    "mypy",
    "pyright",
    "pylint",
    "pytest-full",
    "test-stress-checks",
)
FULL_LOCAL_CHECK_IDS = tuple(
    check_id
    for check_id in FULL_PR_CHECK_IDS
    if check_id not in {"commit-messages", "pr-metadata"}
)
SHARED_VERIFICATION_SUBSTRATE_EXACT_PATHS = {
    "pyproject.toml",
    "uv.lock",
    "repo_support/quality_gates.py",
    "tools/audit_pr_review.py",
    "tools/evaluate_review_results.py",
    "tools/run_pr_review_checks.py",
    "tools/run_quality_gates.py",
    "tools/run_review_check.py",
    "tools/verify_built_wheel.py",
}
SHARED_VERIFICATION_SUBSTRATE_PREFIXES = {
    "repo_support/review_verification/",
}


@dataclass(frozen=True)
class SuppressedCheck:
    check_id: str
    reason: str


@dataclass(frozen=True)
class VerificationPlan:
    trigger: VerificationTrigger
    mode: VerificationMode
    surface_report: SurfaceReport
    selected_check_ids: tuple[str, ...]
    blocking_check_ids: tuple[str, ...]
    nonblocking_check_ids: tuple[str, ...]
    suppressed_checks: tuple[SuppressedCheck, ...]


def _is_markdown_path(path: str) -> bool:
    return PurePosixPath(path).suffix in {".md", ".mdx"}


def _is_shared_verification_substrate_path(path: str) -> bool:
    return path in SHARED_VERIFICATION_SUBSTRATE_EXACT_PATHS or any(
        path.startswith(prefix) for prefix in SHARED_VERIFICATION_SUBSTRATE_PREFIXES
    )


def _path_targeted_check_ids(path: str) -> tuple[str, ...]:
    targeted: list[str] = []
    if path.startswith(".agents/skills/"):
        targeted.append("repo-agent-skills")
    if (
        path == "AGENTS.md"
        or path == "ROADMAP.md"
        or path.startswith("docs/standards/")
        or path.startswith(".claude/commands/")
        or path.startswith("tools/docs_maintenance/")
    ):
        targeted.append("standards-guards")
    if path.startswith(".claude/commands/"):
        targeted.append("docs-runtime-parity")
    if (
        path.startswith(".github/workflows/")
        or path == ".github/CODEOWNERS"
        or path == "docs/standards/delivery-guardrails.md"
        or path == "tools/audit_delivery_guardrails.py"
    ):
        targeted.append("delivery-guardrails-audit")
    if path in {
        ".github/pull_request_template.md",
        "docs/standards/commits.md",
        "docs/standards/issues.md",
        "tools/message_standards.py",
        "tools/pre_push_hook.py",
        "tools/validate_pr_metadata.py",
    }:
        targeted.append("pr-metadata-validator")
    if path in {
        "docs/standards/commits.md",
        "tools/message_standards.py",
        "tools/validate_commit_message.py",
    }:
        targeted.append("commit-message-validator")
    if path in {
        "repo_support/quality_gates.py",
        "tools/run_quality_gates.py",
    }:
        targeted.append("quality-gates-tooling")
    if path in {
        ".pre-commit-config.yaml",
        "repo_support/pytest_commands.py",
        "tools/pre_commit_hook.py",
        "tools/pre_push_hook.py",
        "tools/run_fast_pytest.py",
    }:
        targeted.append("pre-commit-hook-tooling")
    if path in {
        "repo_support/review_verification/policy.py",
        "repo_support/review_verification/surfaces.py",
        "tools/audit_pr_review.py",
    }:
        targeted.append("audit-pr-review")
    if path in {
        "repo_support/review_verification/policy.py",
        "repo_support/review_verification/catalog.py",
        "repo_support/review_verification/executor.py",
        "repo_support/review_verification/surfaces.py",
        "tools/run_pr_review_checks.py",
        ".github/workflows/pr-review.yml",
    }:
        targeted.append("run-pr-review-checks")
    if (
        path.startswith(".github/actions/")
        or path.startswith(".github/workflows/")
        or path
        in {
            "tools/evaluate_review_results.py",
            "tools/run_review_check.py",
            "tools/verify_built_wheel.py",
        }
    ):
        targeted.append("ci-tooling")
    return tuple(dict.fromkeys(targeted))


def _ordered_check_ids(check_ids: set[str]) -> tuple[str, ...]:
    return tuple(check_id for check_id in CHECK_ORDER if check_id in check_ids)


def _apply_dominance(
    check_ids: set[str],
) -> tuple[set[str], tuple[SuppressedCheck, ...]]:
    suppressed: list[SuppressedCheck] = []
    selected = set(check_ids)
    for check_id in CHECK_ORDER:
        if check_id not in selected:
            continue
        for dominated_id in CHECK_SPECS[check_id].dominance_ids:
            if dominated_id not in selected:
                continue
            selected.remove(dominated_id)
            suppressed.append(
                SuppressedCheck(
                    check_id=dominated_id,
                    reason=f"suppressed by {check_id} dominance",
                )
            )
    return selected, tuple(suppressed)


def _planned_check_ids(surface_report: SurfaceReport) -> tuple[set[str], bool]:
    selected: set[str] = set()
    has_production_code = False
    has_packaging_sensitive = False
    has_shared_verification_substrate = False

    if any(
        group in {"human_docs", "control_plane_text"}
        for group in surface_report.surface_groups
    ):
        selected.add("docs-maintenance")

    for path in surface_report.changed_paths:
        if _is_markdown_path(path):
            selected.add("markdownlint")
        if path.startswith(".github/workflows/"):
            selected.add("actionlint")
        for check_id in _path_targeted_check_ids(path):
            selected.add(check_id)
        if is_packaging_sensitive_path(path):
            has_packaging_sensitive = True
        if is_production_code_path(path):
            has_production_code = True
        if _is_shared_verification_substrate_path(path):
            has_shared_verification_substrate = True

    if (
        "repo_code_or_tooling" in surface_report.surface_groups
        or has_shared_verification_substrate
    ):
        selected.update(FULL_QUALITY_CHECK_IDS)

    if "ci_or_release" in surface_report.surface_groups:
        selected.add("ci-tooling")

    if has_packaging_sensitive or has_shared_verification_substrate:
        selected.update({"build", "verify-wheel"})

    if "pytest-full" in selected and has_production_code:
        selected.add("coverage-hotspots")

    return selected, has_production_code


def build_verification_plan(
    *,
    paths: tuple[str, ...],
    trigger: VerificationTrigger,
    mode: VerificationMode,
) -> VerificationPlan:
    surface_report = classify_changed_paths(paths)

    if trigger == "pull_request":
        selected: set[str] = set(FULL_PR_CHECK_IDS)
    else:
        selected, _has_production_code = _planned_check_ids(surface_report)
        if mode == "full":
            selected = set(FULL_LOCAL_CHECK_IDS)

    selected, suppressed = _apply_dominance(selected)

    ordered_selected = _ordered_check_ids(selected)
    blocking = tuple(
        check_id for check_id in ordered_selected if CHECK_SPECS[check_id].blocking
    )
    nonblocking = tuple(
        check_id for check_id in ordered_selected if not CHECK_SPECS[check_id].blocking
    )

    return VerificationPlan(
        trigger=trigger,
        mode=mode,
        surface_report=surface_report,
        selected_check_ids=ordered_selected,
        blocking_check_ids=blocking,
        nonblocking_check_ids=nonblocking,
        suppressed_checks=suppressed,
    )
