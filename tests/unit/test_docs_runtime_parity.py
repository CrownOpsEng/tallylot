from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import cast

from typer.main import Typer
from typer.models import CommandInfo

from repo_support.paths import (
    adapter_packs_root,
    agents_root,
    claude_commands_root,
    docs_root,
    repo_root,
)
from tallylot.infrastructure.workspace.layout import SEED_FILES
from tallylot.interfaces.cli import app
from tools.oracles.cli import app as oracle_app

PRODUCTION_COMMAND_ROUTE_PATTERN = re.compile(
    r'(?:UV_PROJECT_ENVIRONMENT="\$HOME/\.venvs/tallylot-py312" )?uv run tallylot '
    r"(?P<route>[a-z0-9_][a-z0-9_-]*(?: [a-z0-9_][a-z0-9_-]*){0,4})"
)


def production_route_doc_paths() -> list[Path]:
    commands_root = claude_commands_root()
    docs = docs_root()
    return [
        repo_root() / "README.md",
        docs / "guides" / "operator-quickstart.md",
        docs / "guides" / "source-intake.md",
        docs / "guides" / "normalize-screen-stage.md",
        docs / "reference" / "manual-balance-submission-artifacts.md",
        docs / "reference" / "wallet-inventory-artifacts.md",
        docs / "workspace" / "analysis" / "inventory" / "README.md",
        commands_root / "balance-submission-operations.md",
        commands_root / "reconciliation-balance-operations.md",
        commands_root / "source-intake.md",
        commands_root / "wallet-inventory.md",
        commands_root / "supporting-artifacts.md",
    ]


def oracle_route_doc_paths() -> list[Path]:
    commands_root = claude_commands_root()
    docs = docs_root()
    return [
        docs / "reference" / "baseline-validation-contract.md",
        docs / "reference" / "export-checklist.md",
        docs / "guides" / "operator-quickstart.md",
        docs / "guides" / "full-operator-workflow.md",
        docs / "guides" / "normalize-screen-stage.md",
        docs / "guides" / "verify-a-round.md",
        commands_root / "round-verification.md",
        commands_root / "source-diff.md",
    ]


def architecture_doc_paths() -> list[Path]:
    commands_root = claude_commands_root()
    docs = docs_root()
    return [
        repo_root() / "README.md",
        repo_root() / "ROADMAP.md",
        docs / "standards" / "engineering.md",
        docs / "concepts" / "reconciliation-tax-architecture.md",
        commands_root / "source-intake.md",
    ]


def env_prefix_required_doc_paths() -> tuple[Path, ...]:
    commands_root = claude_commands_root()
    docs = docs_root()
    return (
        repo_root() / "README.md",
        docs / "guides" / "operator-quickstart.md",
        docs / "guides" / "full-operator-workflow.md",
        docs / "guides" / "source-intake.md",
        docs / "guides" / "normalize-screen-stage.md",
        docs / "guides" / "verify-a-round.md",
        docs / "reference" / "baseline-validation-contract.md",
        docs / "reference" / "export-checklist.md",
        docs / "reference" / "wallet-inventory-artifacts.md",
        docs / "workspace" / "analysis" / "inventory" / "README.md",
        commands_root / "adapter-authoring.md",
        commands_root / "balance-submission-operations.md",
        commands_root / "implementation-checkpoint.md",
        commands_root / "normalization-exceptions.md",
        commands_root / "reconciliation-balance-operations.md",
        commands_root / "reconciliation-tax-build.md",
        commands_root / "round-verification.md",
        commands_root / "source-diff.md",
        commands_root / "source-intake.md",
        commands_root / "supporting-artifacts.md",
        commands_root / "wallet-inventory.md",
    )


ORACLE_COMMAND_ROUTE_PATTERN = re.compile(
    r'(?:UV_PROJECT_ENVIRONMENT="\$HOME/\.venvs/tallylot-py312" )?uv run python -m tools\.oracles\.cli '
    r"(?P<route>[a-z0-9_][a-z0-9_-]*(?: [a-z0-9_][a-z0-9_-]*){0,4})"
)


def _documented_routes(paths: list[Path], pattern: re.Pattern[str]) -> set[str]:
    routes: set[str] = set()
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for match in pattern.finditer(text):
            routes.add(match.group("route"))
    return routes


def _registered_routes(typer_app: Typer) -> set[str]:
    routes: set[str] = set()

    def command_name(command: CommandInfo) -> str:
        if command.name is not None:
            return command.name
        callback = cast(Callable[..., object], command.callback)
        return callback.__name__.replace("_", "-")

    def walk(current_app: Typer, prefix: tuple[str, ...] = ()) -> None:
        for command in current_app.registered_commands:
            routes.add(" ".join((*prefix, command_name(command))))
        for group in current_app.registered_groups:
            if group.typer_instance is not None and group.name is not None:
                walk(group.typer_instance, (*prefix, group.name))

    walk(typer_app)
    return routes


def test_documented_cli_routes_exist() -> None:
    documented_routes = _documented_routes(
        production_route_doc_paths(), PRODUCTION_COMMAND_ROUTE_PATTERN
    )
    registered_routes = _registered_routes(app)

    missing_routes = sorted(documented_routes - registered_routes)

    assert not missing_routes, f"documented CLI routes do not exist: {missing_routes}"


def test_documented_oracle_cli_routes_exist() -> None:
    documented_routes = _documented_routes(
        oracle_route_doc_paths(), ORACLE_COMMAND_ROUTE_PATTERN
    )
    registered_routes = _registered_routes(oracle_app)

    missing_routes = sorted(documented_routes - registered_routes)

    assert not missing_routes, (
        f"documented oracle CLI routes do not exist: {missing_routes}"
    )


def test_documented_claude_command_routes_exist() -> None:
    command_paths = (
        ".claude/commands/source-intake.md",
        ".claude/commands/round-verification.md",
        ".claude/commands/wallet-inventory.md",
        ".claude/commands/normalization-exceptions.md",
        ".claude/commands/source-diff.md",
        ".claude/commands/supporting-artifacts.md",
        ".claude/commands/adapter-authoring.md",
        ".claude/commands/balance-submission-operations.md",
        ".claude/commands/implementation-checkpoint.md",
        ".claude/commands/issue-workflow.md",
        ".claude/commands/pr-review.md",
        ".claude/commands/reconciliation-balance-operations.md",
        ".claude/commands/reconciliation-tax-build.md",
    )

    for relative_path in command_paths:
        assert (repo_root() / relative_path).exists(), (
            f"missing documented command route: {relative_path}"
        )


def test_documented_claude_command_routes_are_not_ignored() -> None:
    command_paths = (
        ".claude/commands/source-intake.md",
        ".claude/commands/round-verification.md",
        ".claude/commands/wallet-inventory.md",
        ".claude/commands/normalization-exceptions.md",
        ".claude/commands/source-diff.md",
        ".claude/commands/supporting-artifacts.md",
        ".claude/commands/adapter-authoring.md",
        ".claude/commands/balance-submission-operations.md",
        ".claude/commands/implementation-checkpoint.md",
        ".claude/commands/issue-workflow.md",
        ".claude/commands/pr-review.md",
        ".claude/commands/reconciliation-balance-operations.md",
        ".claude/commands/reconciliation-tax-build.md",
    )

    for relative_path in command_paths:
        result = subprocess.run(
            ("git", "check-ignore", "-q", relative_path),
            cwd=repo_root(),
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 1, f"ignored command route: {relative_path}"


def test_source_intake_route_mentions_current_typed_commands() -> None:
    text = (claude_commands_root() / "source-intake.md").read_text(encoding="utf-8")

    for command in (
        "source intake plan",
        "source intake apply",
        "source manifest",
        "source profile",
        "source normalize",
        "checkpoint rebuild-location-inventory",
        "output render file",
    ):
        assert command in text
    assert "source_label_map.csv" in text


def test_round_verification_route_mentions_oracle_cli_commands() -> None:
    text = (claude_commands_root() / "round-verification.md").read_text(
        encoding="utf-8"
    )

    scaffold_command = 'UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.oracles.cli round scaffold'
    compare_command = 'UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.oracles.cli verification compare'

    assert scaffold_command in text
    assert compare_command in text


def test_reconciliation_balance_route_mentions_current_balance_commands() -> None:
    text = (claude_commands_root() / "reconciliation-balance-operations.md").read_text(
        encoding="utf-8"
    )

    for command in (
        "reconciliation balances inspect",
        "reconciliation balances check",
        "reconciliation balances summarize",
    ):
        assert command in text
    assert "cross_source_assertions.csv" in text
    assert "balance-submission-operations.md" in text


def test_balance_submission_route_mentions_current_checkpoint_commands() -> None:
    text = (claude_commands_root() / "balance-submission-operations.md").read_text(
        encoding="utf-8"
    )

    for command in (
        "checkpoint scaffold-balance-submission",
        "checkpoint submit-balances",
        "reconciliation balances inspect",
        "reconciliation balances check",
        "reconciliation balances summarize",
    ):
        assert command in text


def test_manual_balance_submission_docs_mention_checkpoint_commands() -> None:
    paths = (
        docs_root() / "reference" / "manual-balance-submission-artifacts.md",
        docs_root() / "guides" / "operator-quickstart.md",
        docs_root() / "guides" / "normalize-screen-stage.md",
    )

    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "checkpoint scaffold-balance-submission" in text
        assert "checkpoint submit-balances" in text


def test_workspace_docs_reference_manual_balance_submission_paths() -> None:
    workspace_home = (docs_root() / "workspace" / "README.md").read_text(
        encoding="utf-8"
    )
    supporting_text = (
        docs_root() / "workspace" / "working" / "supporting_artifacts" / "README.md"
    ).read_text(encoding="utf-8")
    package_text = (
        docs_root()
        / "workspace"
        / "working"
        / "supporting_artifacts"
        / "balance_submissions"
        / "README.md"
    ).read_text(encoding="utf-8")

    assert (
        "working/supporting_artifacts/balance_submissions/README.md" in workspace_home
    )
    assert "balance_submissions/README.md" in supporting_text
    assert "working/supporting_artifacts/balance_submissions/<source>/" in package_text


def test_reconciliation_workspace_docs_mention_cross_source_sidecars() -> None:
    text = (
        docs_root() / "workspace" / "analysis" / "reconciliation" / "README.md"
    ).read_text(encoding="utf-8")

    for artifact in (
        "cross_source_assertions.csv",
        "cross_source_issues.csv",
        "cross_source_summary.json",
    ):
        assert artifact in text


def test_supporting_route_mentions_checkpoint_pdf_balance_extraction_command() -> None:
    text = (claude_commands_root() / "supporting-artifacts.md").read_text(
        encoding="utf-8"
    )

    assert "checkpoint extract-pdf-balances" in text


def test_location_inventory_route_mentions_checkpoint_command() -> None:
    text = (claude_commands_root() / "wallet-inventory.md").read_text(encoding="utf-8")

    assert "checkpoint rebuild-location-inventory" in text


def test_docs_do_not_reference_retired_service_or_model_buckets() -> None:
    forbidden = (
        "application/services",
        "application/models",
        "domain/models",
        "source diff",
        "baseline validate",
        "verification compare",
        "batch stage",
        "batch screen",
        "round scaffold",
        "supporting extract-pdf-balances",
        "wallet inventory rebuild",
    )
    for path in architecture_doc_paths():
        text = path.read_text(encoding="utf-8").lower()
        for needle in forbidden:
            assert needle not in text, (
                f"{path} still references retired surface {needle!r}"
            )


def test_docs_use_lowercase_filenames_except_readmes() -> None:
    for path in sorted(docs_root().rglob("*")):
        if not path.is_file():
            continue
        if path.name == "README.md":
            continue
        assert path.name == path.name.lower(), f"doc filename is not lowercase: {path}"


def test_repo_docs_do_not_reference_personal_workspace_roots() -> None:
    forbidden = (
        "/home/user/",
        "Documents/",
        "~/Documents/",
    )
    paths = (
        repo_root() / "README.md",
        repo_root() / "AGENTS.md",
        repo_root() / "tallylot.toml",
        *sorted(docs_root().rglob("*.md")),
        *sorted(agents_root().rglob("*.md")),
        *sorted((repo_root() / ".claude").rglob("*.md")),
    )

    for path in paths:
        text = path.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in text, (
                f"{path} still references personal workspace path {needle}"
            )


def test_private_oracle_manifest_is_not_checked_in() -> None:
    assert not (
        docs_root() / "reference" / "cointracking-full-export-manifest.csv"
    ).exists()


def test_workspace_issue_log_seed_header_matches_template() -> None:
    template_header = (
        (docs_root() / "workspace" / "analysis" / "issues" / "issue-log-template.csv")
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    seeded_header = next(
        seed.content.strip()
        for seed in SEED_FILES
        if seed.relative_path == "analysis/issues/issue_log.csv"
    )

    assert seeded_header == template_header


def test_workspace_source_inventory_seed_header_matches_template() -> None:
    template_header = (
        (
            docs_root()
            / "workspace"
            / "analysis"
            / "issues"
            / "source-inventory-template.csv"
        )
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    seeded_header = next(
        seed.content.strip()
        for seed in SEED_FILES
        if seed.relative_path == "analysis/issues/source_inventory.csv"
    )

    assert seeded_header == template_header


def test_workspace_source_label_map_seed_header_matches_template() -> None:
    template_header = (
        (
            docs_root()
            / "workspace"
            / "analysis"
            / "issues"
            / "source-label-map-template.csv"
        )
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    seeded_header = next(
        seed.content.strip()
        for seed in SEED_FILES
        if seed.relative_path == "analysis/issues/source_label_map.csv"
    )

    assert seeded_header == template_header


def test_commit_standards_require_explicit_lint_amend_reverification() -> None:
    text = (docs_root() / "standards" / "commits.md").read_text(encoding="utf-8")

    assert "Do not describe `mypy` or `pyright` as covering `pylint` findings." in text
    assert (
        'UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run pylint <touched-file>'
        in text
    )
    assert (
        'UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run pytest -q --no-cov <touched-test-file>'
        in text
    )
    assert "git show HEAD:<path>" in text


def test_commit_standards_document_hybrid_pr_merge_policy() -> None:
    text = (docs_root() / "standards" / "commits.md").read_text(encoding="utf-8")
    implementation_text = (docs_root() / "standards" / "implementation.md").read_text(
        encoding="utf-8"
    )
    pr_template = (repo_root() / ".github" / "pull_request_template.md").read_text(
        encoding="utf-8"
    )

    assert "`main` is a merge-commit branch by default." in text
    assert "Use squash merges only for the narrow single-checkpoint exception." in text
    assert "do not squash multi-checkpoint PRs" in text
    assert "non-pushed checkpoint commit may be amended" in text
    assert "single-checkpoint exception" in implementation_text
    assert "search existing open issues first" in implementation_text
    assert "use the repo-standard issue structure" in implementation_text
    assert "Single-checkpoint PRs must squash." in pr_template


def test_implementation_anchor_references_use_explicit_doc_paths() -> None:
    paths = (
        repo_root() / "AGENTS.md",
        docs_root() / "standards" / "implementation.md",
    )

    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "implementation plan" not in text.lower(), (
            f"{path} still uses vague implementation-plan wording"
        )


def test_reference_docs_do_not_check_in_oracle_data_files() -> None:
    forbidden_suffixes = {".csv", ".json", ".zip", ".html", ".pdf"}

    for path in sorted((docs_root() / "reference").rglob("*")):
        if not path.is_file():
            continue
        assert path.suffix not in forbidden_suffixes, (
            f"repo reference docs should not contain oracle data files: {path}"
        )


def test_adapter_pack_goldens_do_not_embed_absolute_home_paths() -> None:
    forbidden = ("/home/user/", "CoinTracking.info/tallylot-2025")

    for path in sorted(adapter_packs_root().rglob("*.json")):
        text = path.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in text, (
                f"{path} still embeds absolute local path content"
            )
