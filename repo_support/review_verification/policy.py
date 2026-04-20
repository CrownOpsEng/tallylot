from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Literal

from repo_support.docs_audit import is_docs_audit_substrate_path
from repo_support.target_naming import is_target_naming_sensitive_path

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
    "target-naming",
    "docs-audit",
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
PLANNED_PR_CHECK_IDS = (
    "commit-messages",
    "pr-metadata",
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
STANDARDS_GUARD_EXACT_PATHS = {
    "AGENTS.md",
    "ROADMAP.md",
    "Makefile",
    ".gitmessage.txt",
    ".gitignore",
    ".vscode/settings.json",
}
STANDARDS_GUARD_PREFIXES = (
    "docs/standards/",
    ".claude/commands/",
    "tools/docs_maintenance/",
)
DELIVERY_GUARDRAILS_AUDIT_PATHS = {
    ".github/CODEOWNERS",
    "docs/standards/delivery-guardrails.md",
    "tools/audit_delivery_guardrails.py",
}
PR_METADATA_VALIDATOR_PATHS = {
    ".github/pull_request_template.md",
    "docs/standards/commits.md",
    "docs/standards/issues.md",
    "tools/message_standards.py",
    "tools/pre_push_hook.py",
    "tools/validate_pr_metadata.py",
}
COMMIT_MESSAGE_VALIDATOR_PATHS = {
    "docs/standards/commits.md",
    "tools/message_standards.py",
    "tools/validate_commit_message.py",
}
QUALITY_GATES_TOOLING_PATHS = {
    "repo_support/quality_gates.py",
    "tools/run_quality_gates.py",
}
PRE_COMMIT_HOOK_TOOLING_PATHS = {
    ".pre-commit-config.yaml",
    "repo_support/pytest_commands.py",
    "tools/pre_commit_hook.py",
    "tools/pre_push_hook.py",
    "tools/run_fast_pytest.py",
}
AUDIT_PR_REVIEW_PATHS = {
    "repo_support/review_verification/policy.py",
    "repo_support/review_verification/surfaces.py",
    "tools/audit_pr_review.py",
}
RUN_PR_REVIEW_CHECKS_PATHS = {
    "repo_support/review_verification/policy.py",
    "repo_support/review_verification/catalog.py",
    "repo_support/review_verification/executor.py",
    "repo_support/review_verification/surfaces.py",
    "tools/run_pr_review_checks.py",
    ".github/workflows/pr-review.yml",
}
CI_TOOLING_PATHS = {
    "tools/evaluate_review_results.py",
    "tools/run_review_check.py",
    "tools/verify_built_wheel.py",
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


def _is_docs_audit_markdown_path(path: str) -> bool:
    return (
        path.startswith("docs/")
        or path in {"README.md", "AGENTS.md", "ROADMAP.md"}
        or path.startswith(".claude/commands/")
    )


def _targets_delivery_guardrails_audit(path: str) -> bool:
    return (
        path.startswith(".github/workflows/") or path in DELIVERY_GUARDRAILS_AUDIT_PATHS
    )


def _targets_ci_tooling(path: str) -> bool:
    return (
        path.startswith(".github/actions/")
        or path.startswith(".github/workflows/")
        or path in CI_TOOLING_PATHS
    )


def _collect_exact_path_checks(path: str) -> tuple[str, ...]:
    checks: list[str] = []
    exact_groups = (
        ("pr-metadata-validator", PR_METADATA_VALIDATOR_PATHS),
        ("commit-message-validator", COMMIT_MESSAGE_VALIDATOR_PATHS),
        ("quality-gates-tooling", QUALITY_GATES_TOOLING_PATHS),
        ("pre-commit-hook-tooling", PRE_COMMIT_HOOK_TOOLING_PATHS),
        ("audit-pr-review", AUDIT_PR_REVIEW_PATHS),
        ("run-pr-review-checks", RUN_PR_REVIEW_CHECKS_PATHS),
    )
    for check_id, paths in exact_groups:
        if path in paths:
            checks.append(check_id)
    return tuple(checks)


def _update_selected_checks_for_path(
    selected: set[str],
    path: str,
) -> None:
    if _is_markdown_path(path):
        selected.add("markdownlint")
    if _is_docs_audit_markdown_path(path):
        selected.add("docs-audit")
    if path.startswith(".github/workflows/"):
        selected.add("actionlint")
    for check_id in _path_targeted_check_ids(path):
        selected.add(check_id)


def _path_targeted_check_ids(path: str) -> tuple[str, ...]:
    targeted: list[str] = []
    if path.startswith(".agents/skills/"):
        targeted.append("repo-agent-skills")
    if path in STANDARDS_GUARD_EXACT_PATHS or path.startswith(STANDARDS_GUARD_PREFIXES):
        targeted.append("standards-guards")
    if path.startswith(".claude/commands/"):
        targeted.append("docs-audit")
    if _targets_delivery_guardrails_audit(path):
        targeted.append("delivery-guardrails-audit")
    targeted.extend(_collect_exact_path_checks(path))
    if is_target_naming_sensitive_path(path):
        targeted.append("target-naming")
    if is_docs_audit_substrate_path(path):
        targeted.append("docs-audit")
    if _targets_ci_tooling(path):
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

    has_docs_or_control_plane = any(
        group in {"human_docs", "control_plane_text"}
        for group in surface_report.surface_groups
    )
    if has_docs_or_control_plane:
        selected.add("docs-maintenance")

    for path in surface_report.changed_paths:
        _update_selected_checks_for_path(selected, path)
        if is_packaging_sensitive_path(path):
            has_packaging_sensitive = True
        if is_production_code_path(path):
            has_production_code = True
        if _is_shared_verification_substrate_path(path):
            has_shared_verification_substrate = True

    needs_full_quality = (
        "repo_code_or_tooling" in surface_report.surface_groups
        or has_shared_verification_substrate
    )
    if needs_full_quality:
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

    if trigger == "pull_request" and mode == "full":
        selected: set[str] = set(FULL_PR_CHECK_IDS)
    else:
        selected, _has_production_code = _planned_check_ids(surface_report)
        if trigger == "pull_request":
            selected.update(PLANNED_PR_CHECK_IDS)
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
