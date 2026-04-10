from __future__ import annotations

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass

from repo_support.pr_review_paths import (
    is_control_plane_text,
    is_human_docs,
    is_packaging_sensitive_path,
    is_production_code_path,
    path_surface_groups,
    path_targeted_check_names,
)

SURFACE_GROUP_ORDER = (
    "human_docs",
    "control_plane_text",
    "repo_code_or_tooling",
    "ci_or_release",
)
VERIFICATION_LEVEL_ORDER = {
    "none": 0,
    "docs-maintenance": 1,
    "control-plane-targeted": 2,
    "quality-gates-full": 3,
    "ci-parity": 4,
}
SURFACE_REVIEW_DOMAINS = {
    "human_docs": (
        "factual accuracy",
        "metadata and link integrity",
        "audience and type placement",
    ),
    "control_plane_text": (
        "policy correctness",
        "route-skill-standard alignment",
        "delivery behavior",
        "compaction and context-loss recovery",
        "issue and privacy handling",
    ),
    "repo_code_or_tooling": (
        "design and ownership",
        "correctness and behavior",
        "complexity and over-engineering",
        "tests and regression value",
        "naming and public terminology",
        "documentation and control-plane alignment",
    ),
    "ci_or_release": (
        "workflow correctness",
        "delivery enforcement",
        "metadata parity",
    ),
}
SURFACE_VERIFICATION_LEVEL = {
    "human_docs": "docs-maintenance",
    "control_plane_text": "control-plane-targeted",
    "repo_code_or_tooling": "quality-gates-full",
    "ci_or_release": "ci-parity",
}


@dataclass(frozen=True)
class TargetedCheck:
    name: str
    command: tuple[str, ...]


@dataclass(frozen=True)
class PrReviewPlan:
    changed_paths: tuple[str, ...]
    grouped_paths: tuple[tuple[str, tuple[str, ...]], ...]
    surface_groups: tuple[str, ...]
    review_domains: tuple[str, ...]
    targeted_checks: tuple[TargetedCheck, ...]
    verification_level: str
    requires_full_quality_gates: bool
    requires_ci_parity: bool
    requires_pre_merge_packaging_verification: bool
    requires_test_stress_checks: bool
    requires_coverage_hotspot_report: bool
    unmapped_paths: tuple[str, ...]


DOCS_MAINTENANCE_CHECK = TargetedCheck(
    name="docs-maintenance",
    command=("uv", "run", "python", "-m", "tools.docs_maintenance", "sync", "--check"),
)
TARGETED_CHECKS_BY_NAME = {
    "repo-agent-skills": TargetedCheck(
        name="repo-agent-skills",
        command=(
            "uv",
            "run",
            "pytest",
            "--no-cov",
            "-q",
            "tests/unit/test_repo_agent_skills.py",
        ),
    ),
    "standards-guards": TargetedCheck(
        name="standards-guards",
        command=(
            "uv",
            "run",
            "pytest",
            "--no-cov",
            "-q",
            "tests/contract/test_standards_guards.py",
        ),
    ),
    "docs-runtime-parity": TargetedCheck(
        name="docs-runtime-parity",
        command=(
            "uv",
            "run",
            "pytest",
            "--no-cov",
            "-q",
            "tests/unit/test_docs_runtime_parity.py",
        ),
    ),
    "delivery-guardrails-audit": TargetedCheck(
        name="delivery-guardrails-audit",
        command=(
            "uv",
            "run",
            "pytest",
            "--no-cov",
            "-q",
            "tests/unit/test_delivery_guardrails_audit.py",
        ),
    ),
    "pr-metadata-validator": TargetedCheck(
        name="pr-metadata-validator",
        command=(
            "uv",
            "run",
            "pytest",
            "--no-cov",
            "-q",
            "tests/unit/test_pr_metadata_validator.py",
        ),
    ),
    "commit-message-validator": TargetedCheck(
        name="commit-message-validator",
        command=(
            "uv",
            "run",
            "pytest",
            "--no-cov",
            "-q",
            "tests/unit/test_commit_message_validator.py",
        ),
    ),
    "pre-commit-hook-tooling": TargetedCheck(
        name="pre-commit-hook-tooling",
        command=(
            "uv",
            "run",
            "pytest",
            "--no-cov",
            "-q",
            "tests/unit/test_pre_commit_hook.py",
        ),
    ),
    "quality-gates-tooling": TargetedCheck(
        name="quality-gates-tooling",
        command=(
            "uv",
            "run",
            "pytest",
            "--no-cov",
            "-q",
            "tests/unit/test_quality_gates.py",
        ),
    ),
    "ci-parity-tooling": TargetedCheck(
        name="ci-parity-tooling",
        command=(
            "uv",
            "run",
            "pytest",
            "--no-cov",
            "-q",
            "tests/unit/test_ci_parity_checks.py",
        ),
    ),
    "audit-pr-review": TargetedCheck(
        name="audit-pr-review",
        command=(
            "uv",
            "run",
            "pytest",
            "--no-cov",
            "-q",
            "tests/unit/test_audit_pr_review.py",
        ),
    ),
    "run-pr-review-checks": TargetedCheck(
        name="run-pr-review-checks",
        command=(
            "uv",
            "run",
            "pytest",
            "--no-cov",
            "-q",
            "tests/unit/test_run_pr_review_checks.py",
        ),
    ),
    "test-stress-checks": TargetedCheck(
        name="test-stress-checks",
        command=(
            "uv",
            "run",
            "pytest",
            "--no-cov",
            "-q",
            "tests/unit/test_run_test_stress_checks.py",
        ),
    ),
    "coverage-hotspots": TargetedCheck(
        name="coverage-hotspots",
        command=(
            "uv",
            "run",
            "pytest",
            "--no-cov",
            "-q",
            "tests/unit/test_report_coverage_hotspots.py",
        ),
    ),
}


def _git_stdout(*args: str) -> str:
    result = subprocess.run(
        ("git", *args),
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _default_branch_ref() -> str:
    try:
        return _git_stdout("symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    except subprocess.CalledProcessError:
        return "origin/main"


def changed_paths(
    base_sha: str | None = None, head_sha: str | None = None
) -> tuple[str, ...]:
    head = head_sha or "HEAD"
    if base_sha is not None:
        base = base_sha
    else:
        default_branch = _default_branch_ref()
        try:
            base = _git_stdout("merge-base", head, default_branch)
        except subprocess.CalledProcessError:
            base = f"{head}^"

    result = subprocess.run(
        ("git", "diff", "--name-only", "--diff-filter=ACMR", base, head),
        check=True,
        capture_output=True,
        text=True,
    )
    return tuple(line for line in result.stdout.splitlines() if line)


def classify_changed_paths(paths: Sequence[str]) -> PrReviewPlan:
    grouped_paths: dict[str, list[str]] = {name: [] for name in SURFACE_GROUP_ORDER}
    review_domains: list[str] = []
    targeted_checks: list[TargetedCheck] = []
    verification_level = "none"
    requires_full_quality_gates = False
    requires_ci_parity = False
    requires_test_stress_checks = False
    requires_coverage_hotspot_report = False
    has_packaging_sensitive_repo_code = False
    unmapped_paths: list[str] = []

    if any(is_human_docs(path) or is_control_plane_text(path) for path in paths):
        targeted_checks.append(DOCS_MAINTENANCE_CHECK)

    for path in paths:
        groups = path_surface_groups(path)
        if not groups:
            unmapped_paths.append(path)
            continue
        for group in groups:
            grouped_paths[group].append(path)
            verification_level = max(
                verification_level,
                SURFACE_VERIFICATION_LEVEL[group],
                key=lambda level: VERIFICATION_LEVEL_ORDER[level],
            )
            for domain in SURFACE_REVIEW_DOMAINS[group]:
                if domain not in review_domains:
                    review_domains.append(domain)
        if "repo_code_or_tooling" in groups:
            requires_full_quality_gates = True
            requires_test_stress_checks = True
        if "ci_or_release" in groups:
            requires_ci_parity = True
            requires_test_stress_checks = True
        if is_production_code_path(path):
            requires_coverage_hotspot_report = True
        if "repo_code_or_tooling" in groups and is_packaging_sensitive_path(path):
            has_packaging_sensitive_repo_code = True
        for check_name in path_targeted_check_names(path):
            check = TARGETED_CHECKS_BY_NAME[check_name]
            if check not in targeted_checks:
                targeted_checks.append(check)

    grouped = tuple(
        (group, tuple(paths_for_group))
        for group, paths_for_group in grouped_paths.items()
        if paths_for_group
    )
    surface_groups = tuple(group for group, _ in grouped)
    return PrReviewPlan(
        changed_paths=tuple(paths),
        grouped_paths=grouped,
        surface_groups=surface_groups,
        review_domains=tuple(review_domains),
        targeted_checks=tuple(targeted_checks),
        verification_level=verification_level,
        requires_full_quality_gates=requires_full_quality_gates,
        requires_ci_parity=requires_ci_parity,
        requires_pre_merge_packaging_verification=(
            requires_full_quality_gates
            and not requires_ci_parity
            and has_packaging_sensitive_repo_code
        ),
        requires_test_stress_checks=requires_test_stress_checks,
        requires_coverage_hotspot_report=requires_coverage_hotspot_report,
        unmapped_paths=tuple(unmapped_paths),
    )
