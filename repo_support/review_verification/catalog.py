from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Trigger = Literal["pull_request", "push_main", "local"]


@dataclass(frozen=True)
class CheckSpec:
    id: str
    job_name: str
    command: tuple[str, ...]
    tags: frozenset[str]
    triggers: frozenset[Trigger]
    dependency_ids: tuple[str, ...] = ()
    blocking: bool = True
    dominance_ids: tuple[str, ...] = ()


# A small constructor keeps the check catalog readable even though the spec
# shape naturally needs several metadata fields.
# pylint: disable=too-many-arguments
def _spec(
    check_id: str,
    *,
    job_name: str,
    command: tuple[str, ...],
    tags: tuple[str, ...],
    triggers: tuple[Trigger, ...] = ("pull_request", "push_main", "local"),
    dependency_ids: tuple[str, ...] = (),
    blocking: bool = True,
    dominance_ids: tuple[str, ...] = (),
) -> CheckSpec:
    return CheckSpec(
        id=check_id,
        job_name=job_name,
        command=command,
        tags=frozenset(tags),
        triggers=frozenset(triggers),
        dependency_ids=dependency_ids,
        blocking=blocking,
        dominance_ids=dominance_ids,
    )


TARGETED_SUBSET_TEST_IDS = (
    "repo-agent-skills",
    "standards-guards",
    "docs-runtime-parity",
    "delivery-guardrails-audit",
    "pr-metadata-validator",
    "commit-message-validator",
    "pre-commit-hook-tooling",
    "quality-gates-tooling",
    "audit-pr-review",
    "run-pr-review-checks",
    "ci-tooling",
)
QUALITY_CHECK_IDS = (
    "markdownlint",
    "target-naming",
    "actionlint",
    "ruff",
    "mypy",
    "pyright",
    "pylint",
    "pytest-full",
)
CHECK_ORDER = (
    "commit-messages",
    "pr-metadata",
    "docs-maintenance",
    "markdownlint",
    "target-naming",
    "actionlint",
    "ruff",
    "mypy",
    "pyright",
    "pylint",
    "repo-agent-skills",
    "standards-guards",
    "docs-runtime-parity",
    "delivery-guardrails-audit",
    "pr-metadata-validator",
    "commit-message-validator",
    "pre-commit-hook-tooling",
    "quality-gates-tooling",
    "audit-pr-review",
    "run-pr-review-checks",
    "ci-tooling",
    "pytest-full",
    "test-stress-checks",
    "build",
    "verify-wheel",
    "coverage-hotspots",
)
CHECK_SPECS = {
    spec.id: spec
    for spec in (
        _spec(
            "commit-messages",
            job_name="Validate commit messages",
            command=(
                "python",
                "-m",
                "tools.validate_commit_message",
                "--rev-range",
                "{base_sha}..{head_sha}",
            ),
            tags=("review", "metadata"),
            triggers=("pull_request", "local"),
        ),
        _spec(
            "pr-metadata",
            job_name="Validate PR metadata",
            command=(
                "python",
                "-m",
                "tools.validate_pr_metadata",
                "--title",
                "{pr_title}",
                "--body",
                "{pr_body}",
                "--base-sha",
                "{base_sha}",
                "--head-sha",
                "{head_sha}",
            ),
            tags=("review", "metadata"),
            triggers=("pull_request", "local"),
        ),
        _spec(
            "docs-maintenance",
            job_name="Docs maintenance",
            command=(
                "python",
                "-m",
                "tools.docs_maintenance",
                "sync",
                "--check",
            ),
            tags=("docs",),
        ),
        _spec(
            "markdownlint",
            job_name="Markdown lint",
            command=("pre-commit", "run", "markdownlint", "--all-files"),
            tags=("quality", "docs"),
        ),
        _spec(
            "target-naming",
            job_name="Target naming",
            command=("python", "-m", "tools.target_naming", "check"),
            tags=("docs", "review-tooling"),
        ),
        _spec(
            "actionlint",
            job_name="Workflow lint",
            command=("actionlint", "-color"),
            tags=("quality", "ci"),
        ),
        _spec(
            "ruff",
            job_name="Ruff",
            command=("ruff", "check", "."),
            tags=("quality", "python"),
        ),
        _spec(
            "mypy",
            job_name="Mypy",
            command=("mypy",),
            tags=("quality", "python"),
        ),
        _spec(
            "pyright",
            job_name="Pyright",
            command=("pyright", "--project", ".pyrightconfig.local.json"),
            tags=("quality", "python"),
        ),
        _spec(
            "pylint",
            job_name="Pylint",
            command=("python", "-m", "tools.run_pylint"),
            tags=("quality", "python"),
        ),
        _spec(
            "repo-agent-skills",
            job_name="Repo agent skills tooling",
            command=(
                "pytest",
                "--no-cov",
                "-q",
                "tests/unit/test_repo_agent_skills.py",
            ),
            tags=("review-tooling",),
            triggers=("pull_request", "push_main", "local"),
        ),
        _spec(
            "standards-guards",
            job_name="Standards guards",
            command=(
                "pytest",
                "--no-cov",
                "-q",
                "tests/contract/test_standards_guards.py",
            ),
            tags=("review-tooling",),
            triggers=("pull_request", "push_main", "local"),
        ),
        _spec(
            "docs-runtime-parity",
            job_name="Docs runtime parity",
            command=(
                "pytest",
                "--no-cov",
                "-q",
                "tests/unit/docs_runtime_parity",
            ),
            tags=("review-tooling",),
            triggers=("pull_request", "push_main", "local"),
        ),
        _spec(
            "delivery-guardrails-audit",
            job_name="Delivery guardrails audit",
            command=(
                "pytest",
                "--no-cov",
                "-q",
                "tests/unit/test_delivery_guardrails_audit.py",
            ),
            tags=("review-tooling", "ci"),
            triggers=("pull_request", "push_main", "local"),
        ),
        _spec(
            "pr-metadata-validator",
            job_name="PR metadata validator tooling",
            command=(
                "pytest",
                "--no-cov",
                "-q",
                "tests/unit/test_pr_metadata_validator.py",
            ),
            tags=("review-tooling",),
            triggers=("pull_request", "push_main", "local"),
        ),
        _spec(
            "commit-message-validator",
            job_name="Commit message validator tooling",
            command=(
                "pytest",
                "--no-cov",
                "-q",
                "tests/unit/test_commit_message_validator.py",
            ),
            tags=("review-tooling",),
            triggers=("pull_request", "push_main", "local"),
        ),
        _spec(
            "pre-commit-hook-tooling",
            job_name="Pre-commit hook tooling",
            command=(
                "pytest",
                "--no-cov",
                "-q",
                "tests/unit/test_pre_commit_hook.py",
            ),
            tags=("review-tooling",),
            triggers=("pull_request", "push_main", "local"),
        ),
        _spec(
            "quality-gates-tooling",
            job_name="Quality gates tooling",
            command=(
                "pytest",
                "--no-cov",
                "-q",
                "tests/unit/test_quality_gates.py",
            ),
            tags=("review-tooling",),
            triggers=("pull_request", "push_main", "local"),
        ),
        _spec(
            "audit-pr-review",
            job_name="PR review audit tooling",
            command=(
                "pytest",
                "--no-cov",
                "-q",
                "tests/unit/test_audit_pr_review.py",
            ),
            tags=("review-tooling",),
            triggers=("pull_request", "push_main", "local"),
        ),
        _spec(
            "run-pr-review-checks",
            job_name="PR review check runner tooling",
            command=(
                "pytest",
                "--no-cov",
                "-q",
                "tests/unit/test_run_pr_review_checks.py",
            ),
            tags=("review-tooling",),
            triggers=("pull_request", "push_main", "local"),
        ),
        _spec(
            "ci-tooling",
            job_name="Workflow contract tooling",
            command=(
                "pytest",
                "--no-cov",
                "-q",
                "tests/unit/test_review_verification_workflows.py",
            ),
            tags=("review-tooling", "ci"),
            triggers=("pull_request", "push_main", "local"),
        ),
        _spec(
            "pytest-full",
            job_name="Pytest full suite",
            command=("pytest",),
            tags=("quality", "tests"),
            dominance_ids=TARGETED_SUBSET_TEST_IDS,
        ),
        _spec(
            "test-stress-checks",
            job_name="Stress checks",
            command=("python", "-m", "tools.run_test_stress_checks"),
            tags=("tests",),
        ),
        _spec(
            "build",
            job_name="Build distribution",
            command=("uv", "build"),
            tags=("packaging",),
        ),
        _spec(
            "verify-wheel",
            job_name="Verify built wheel",
            command=("python", "-m", "tools.verify_built_wheel"),
            tags=("packaging",),
            dependency_ids=("build",),
        ),
        _spec(
            "coverage-hotspots",
            job_name="Coverage hotspots",
            command=("python", "-m", "tools.report_coverage_hotspots"),
            tags=("report",),
            dependency_ids=("pytest-full",),
            blocking=False,
        ),
    )
}


def check_spec(check_id: str) -> CheckSpec:
    return CHECK_SPECS[check_id]


def ordered_check_specs(
    check_ids: set[str] | frozenset[str] | tuple[str, ...],
) -> tuple[CheckSpec, ...]:
    selected = set(check_ids)
    return tuple(
        CHECK_SPECS[check_id] for check_id in CHECK_ORDER if check_id in selected
    )
