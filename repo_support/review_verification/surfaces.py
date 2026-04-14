from __future__ import annotations

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass

SURFACE_GROUP_ORDER = (
    "human_docs",
    "control_plane_text",
    "repo_code_or_tooling",
    "ci_or_release",
)
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
REPO_CODE_OR_TOOLING_EXACT_PATHS = ("conftest.py",)
CI_OR_RELEASE_EXACT_PATHS = (
    ".pre-commit-config.yaml",
    ".pylintrc",
    ".pylintrc-tests",
    "pyproject.toml",
    "pyrightconfig.json",
    "pyrightconfig.tests.json",
    "uv.lock",
    "tools/audit_delivery_guardrails.py",
    "tools/audit_pr_review.py",
    "tools/evaluate_review_results.py",
    "tools/install_git_hooks.py",
    "tools/message_standards.py",
    "tools/pre_commit_hook.py",
    "tools/pre_push_hook.py",
    "tools/run_pr_review_checks.py",
    "tools/run_quality_gates.py",
    "tools/run_review_check.py",
    "tools/validate_commit_message.py",
    "tools/validate_pr_metadata.py",
    "tools/verify_built_wheel.py",
)
CI_OR_RELEASE_PREFIXES = (".github/actions/", ".github/workflows/")
PACKAGING_SENSITIVE_EXACT_PATHS = (
    "pyproject.toml",
    "uv.lock",
    "tools/verify_built_wheel.py",
)
PACKAGING_SENSITIVE_PREFIXES = (
    ".github/actions/",
    ".github/workflows/",
    "src/tallylot/interfaces/cli/",
)


@dataclass(frozen=True)
class SurfaceReport:
    changed_paths: tuple[str, ...]
    grouped_paths: tuple[tuple[str, tuple[str, ...]], ...]
    surface_groups: tuple[str, ...]
    review_domains: tuple[str, ...]
    unmapped_paths: tuple[str, ...]


def is_human_docs(path: str) -> bool:
    return path in {
        "README.md",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "CLA.md",
        "LICENSE",
        "LICENSE.docs",
    } or (path.startswith("docs/") and not path.startswith("docs/standards/"))


def is_control_plane_text(path: str) -> bool:
    return path in CONTROL_PLANE_EXACT_PATHS or path.startswith(CONTROL_PLANE_PREFIXES)


def is_repo_code_or_tooling(path: str) -> bool:
    return (
        path in REPO_CODE_OR_TOOLING_EXACT_PATHS
        or path.startswith(("src/", "tests/", "repo_support/"))
        or path.startswith("tools/")
        and path.endswith(".py")
    )


def is_ci_or_release(path: str) -> bool:
    return path in CI_OR_RELEASE_EXACT_PATHS or path.startswith(CI_OR_RELEASE_PREFIXES)


def is_packaging_sensitive_path(path: str) -> bool:
    return path in PACKAGING_SENSITIVE_EXACT_PATHS or path.startswith(
        PACKAGING_SENSITIVE_PREFIXES
    )


def is_production_code_path(path: str) -> bool:
    return path.startswith("src/tallylot/")


def path_surface_groups(path: str) -> tuple[str, ...]:
    groups: list[str] = []
    if is_human_docs(path):
        groups.append("human_docs")
    if is_control_plane_text(path):
        groups.append("control_plane_text")
    if is_repo_code_or_tooling(path):
        groups.append("repo_code_or_tooling")
    if is_ci_or_release(path):
        groups.append("ci_or_release")
    return tuple(groups)


def classify_changed_paths(paths: Sequence[str]) -> SurfaceReport:
    grouped_paths: dict[str, list[str]] = {name: [] for name in SURFACE_GROUP_ORDER}
    review_domains: list[str] = []
    unmapped_paths: list[str] = []

    for path in paths:
        groups = path_surface_groups(path)
        if not groups:
            unmapped_paths.append(path)
            continue
        for group in groups:
            grouped_paths[group].append(path)
            for domain in SURFACE_REVIEW_DOMAINS[group]:
                if domain not in review_domains:
                    review_domains.append(domain)

    grouped = tuple(
        (group, tuple(paths_for_group))
        for group, paths_for_group in grouped_paths.items()
        if paths_for_group
    )
    surface_groups = tuple(group for group, _paths in grouped)
    return SurfaceReport(
        changed_paths=tuple(paths),
        grouped_paths=grouped,
        surface_groups=surface_groups,
        review_domains=tuple(review_domains),
        unmapped_paths=tuple(unmapped_paths),
    )


def _git_stdout(*args: str) -> str:
    result = subprocess.run(
        ("git", *args),
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def default_branch_ref() -> str:
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
        default_branch = default_branch_ref()
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
