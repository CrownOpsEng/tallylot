from __future__ import annotations

from pathlib import PurePosixPath

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
    "tools/install_git_hooks.py",
    "tools/message_standards.py",
    "tools/pre_commit_hook.py",
    "tools/run_ci_parity_checks.py",
    "tools/run_pr_review_checks.py",
    "tools/run_quality_gates.py",
    "tools/validate_commit_message.py",
    "tools/validate_pr_metadata.py",
)
CI_OR_RELEASE_PREFIXES = (".github/actions/", ".github/workflows/")
PACKAGING_SENSITIVE_EXACT_PATHS = (
    "pyproject.toml",
    "uv.lock",
    "tools/run_ci_parity_checks.py",
)
PACKAGING_SENSITIVE_PREFIXES = (
    ".github/actions/",
    ".github/workflows/",
    "src/tallylot/interfaces/cli/",
)


def is_human_docs(path: str) -> bool:
    return path in {"README.md", "CHANGELOG.md"} or (
        path.startswith("docs/") and not path.startswith("docs/standards/")
    )


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


def path_targeted_check_names(path: str) -> tuple[str, ...]:
    check_names: list[str] = []
    pure_path = PurePosixPath(path)
    if path.startswith(".agents/skills/"):
        check_names.append("repo-agent-skills")

    condition_checks = (
        (
            path == "AGENTS.md"
            or path == "ROADMAP.md"
            or path.startswith("docs/standards/")
            or path.startswith(".claude/commands/"),
            ("standards-guards",),
        ),
        (
            path.startswith(".claude/commands/"),
            ("docs-runtime-parity",),
        ),
        (
            path.startswith(".github/workflows/")
            or path == ".github/CODEOWNERS"
            or path == "docs/standards/delivery-guardrails.md"
            or path == "tools/audit_delivery_guardrails.py",
            ("delivery-guardrails-audit",),
        ),
        (
            path
            in {
                ".github/pull_request_template.md",
                "docs/standards/commits.md",
                "docs/standards/issues.md",
                "tools/message_standards.py",
                "tools/validate_pr_metadata.py",
            },
            ("pr-metadata-validator",),
        ),
        (
            path
            in {
                "docs/standards/commits.md",
                "tools/message_standards.py",
                "tools/validate_commit_message.py",
            },
            ("commit-message-validator",),
        ),
        (
            path
            in {
                "tools/run_quality_gates.py",
                "repo_support/quality_gates.py",
                "repo_support/pytest_commands.py",
            },
            ("quality-gates-tooling",),
        ),
        (
            path
            in {
                ".pre-commit-config.yaml",
                "repo_support/pytest_commands.py",
                "tools/pre_commit_hook.py",
                "tools/run_fast_pytest.py",
            },
            ("pre-commit-hook-tooling",),
        ),
        (
            path.startswith(".github/actions/")
            or path in {".github/workflows/ci.yml", "tools/run_ci_parity_checks.py"},
            ("ci-parity-tooling",),
        ),
        (
            path
            in {
                "repo_support/pr_review.py",
                "repo_support/pr_review_paths.py",
                "tools/audit_pr_review.py",
            },
            ("audit-pr-review",),
        ),
        (
            path
            in {
                "repo_support/pr_review.py",
                "repo_support/pr_review_paths.py",
                "tools/run_pr_review_checks.py",
                ".github/workflows/pr-review.yml",
            },
            ("run-pr-review-checks",),
        ),
        (path == "tools/run_test_stress_checks.py", ("test-stress-checks",)),
        (path == "tools/report_coverage_hotspots.py", ("coverage-hotspots",)),
    )
    for condition, names in condition_checks:
        if condition:
            check_names.extend(names)
    if pure_path.parts[:2] == ("tools", "docs_maintenance"):
        check_names.append("standards-guards")
    return tuple(check_names)
