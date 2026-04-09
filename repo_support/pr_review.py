from __future__ import annotations

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath

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
CONTROL_PLANE_EXACT_PATHS = (
    "AGENTS.md",
    "ROADMAP.md",
    ".github/pull_request_template.md",
    ".github/CODEOWNERS",
)
CONTROL_PLANE_PREFIXES = (
    ".agents/skills/",
    ".claude/commands/",
    "docs/standards/",
    ".github/ISSUE_TEMPLATE/",
)
CI_OR_RELEASE_EXACT_PATHS = (
    ".pre-commit-config.yaml",
    ".pylintrc-tests",
    "pyproject.toml",
    "pyrightconfig.json",
    "pyrightconfig.tests.json",
    "uv.lock",
    "tools/audit_delivery_guardrails.py",
    "tools/audit_pr_review.py",
    "tools/install_git_hooks.py",
    "tools/message_standards.py",
    "tools/pre_commit_hook.py",
    "tools/run_ci_parity_checks.py",
    "tools/run_pr_review_checks.py",
    "tools/run_quality_gates.py",
    "tools/validate_commit_message.py",
    "tools/validate_pr_metadata.py",
)
CI_OR_RELEASE_PREFIXES = (".github/workflows/",)


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


def _is_human_docs(path: str) -> bool:
    return path in {"README.md", "CHANGELOG.md"} or (
        path.startswith("docs/") and not path.startswith("docs/standards/")
    )


def _is_control_plane_text(path: str) -> bool:
    return path in CONTROL_PLANE_EXACT_PATHS or path.startswith(CONTROL_PLANE_PREFIXES)


def _is_repo_code_or_tooling(path: str) -> bool:
    return (
        path.startswith(("src/", "tests/", "repo_support/"))
        or path.startswith("tools/")
        and path.endswith(".py")
    )


def _is_ci_or_release(path: str) -> bool:
    return path in CI_OR_RELEASE_EXACT_PATHS or path.startswith(CI_OR_RELEASE_PREFIXES)


def _path_surface_groups(path: str) -> tuple[str, ...]:
    groups: list[str] = []
    if _is_human_docs(path):
        groups.append("human_docs")
    if _is_control_plane_text(path):
        groups.append("control_plane_text")
    if _is_repo_code_or_tooling(path):
        groups.append("repo_code_or_tooling")
    if _is_ci_or_release(path):
        groups.append("ci_or_release")
    return tuple(groups)


def _path_targeted_check_names(path: str) -> tuple[str, ...]:
    check_names: list[str] = []
    pure_path = PurePosixPath(path)
    if path.startswith(".agents/skills/"):
        check_names.append("repo-agent-skills")
    if (
        path == "AGENTS.md"
        or path == "ROADMAP.md"
        or path.startswith("docs/standards/")
        or path.startswith(".claude/commands/")
    ):
        check_names.append("standards-guards")
    if path.startswith(".claude/commands/"):
        check_names.append("docs-runtime-parity")
    if (
        path.startswith(".github/workflows/")
        or path == ".github/CODEOWNERS"
        or path == "docs/standards/delivery-guardrails.md"
        or path == "tools/audit_delivery_guardrails.py"
    ):
        check_names.append("delivery-guardrails-audit")
    if path in {
        ".github/pull_request_template.md",
        "docs/standards/commits.md",
        "docs/standards/issues.md",
        "tools/message_standards.py",
        "tools/validate_pr_metadata.py",
    }:
        check_names.append("pr-metadata-validator")
    if path in {
        "docs/standards/commits.md",
        "tools/message_standards.py",
        "tools/validate_commit_message.py",
    }:
        check_names.append("commit-message-validator")
    if path == "tools/run_quality_gates.py":
        check_names.append("quality-gates-tooling")
    if path in {".github/workflows/ci.yml", "tools/run_ci_parity_checks.py"}:
        check_names.append("ci-parity-tooling")
    if path in {"repo_support/pr_review.py", "tools/audit_pr_review.py"}:
        check_names.append("audit-pr-review")
    if path in {
        "repo_support/pr_review.py",
        "tools/run_pr_review_checks.py",
        ".github/workflows/pr-review.yml",
    }:
        check_names.append("run-pr-review-checks")
    if pure_path.parts[:2] == ("tools", "docs_maintenance"):
        check_names.append("standards-guards")
    return tuple(check_names)


def classify_changed_paths(paths: Sequence[str]) -> PrReviewPlan:
    grouped_paths: dict[str, list[str]] = {name: [] for name in SURFACE_GROUP_ORDER}
    review_domains: list[str] = []
    targeted_checks: list[TargetedCheck] = []
    verification_level = "none"
    unmapped_paths: list[str] = []

    if any(_is_human_docs(path) or _is_control_plane_text(path) for path in paths):
        targeted_checks.append(DOCS_MAINTENANCE_CHECK)

    for path in paths:
        groups = _path_surface_groups(path)
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
        for check_name in _path_targeted_check_names(path):
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
        unmapped_paths=tuple(unmapped_paths),
    )
