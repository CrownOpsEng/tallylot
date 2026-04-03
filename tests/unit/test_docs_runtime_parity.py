from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import cast

from typer.main import Typer
from typer.models import CommandInfo

from tallylot.interfaces.cli import app
from tools.oracles.cli import app as oracle_app

REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_PATHS = [
    REPO_ROOT / "README.md",
    *sorted((REPO_ROOT / "docs").rglob("*.md")),
    *sorted((REPO_ROOT / ".claude").rglob("*.md")),
]
PRODUCTION_ROUTE_DOC_PATHS = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs" / "operations" / "operations-quickstart.md",
    REPO_ROOT / "docs" / "operations" / "wallet-inventory.md",
    REPO_ROOT / "docs" / "workspace" / "analysis" / "inventory" / "README.md",
    REPO_ROOT / ".claude" / "commands" / "source-intake.md",
    REPO_ROOT / ".claude" / "commands" / "wallet-inventory.md",
    REPO_ROOT / ".claude" / "commands" / "supporting-artifacts.md",
]
ORACLE_ROUTE_DOC_PATHS = [
    REPO_ROOT / "docs" / "operations" / "baseline-validation.md",
    REPO_ROOT / "docs" / "operations" / "export-checklist.md",
    REPO_ROOT / "docs" / "operations" / "operations-quickstart.md",
    REPO_ROOT / "docs" / "operations" / "mop.md",
    REPO_ROOT / ".claude" / "commands" / "round-verification.md",
    REPO_ROOT / ".claude" / "commands" / "source-diff.md",
]
ARCHITECTURE_DOC_PATHS = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "ROADMAP.md",
    REPO_ROOT / "docs" / "architecture" / "engineering-standards.md",
    REPO_ROOT / "docs" / "architecture" / "reconciliation-tax-implementation-plan.md",
    REPO_ROOT / ".claude" / "commands" / "source-intake.md",
]
PRODUCTION_COMMAND_ROUTE_PATTERN = re.compile(
    r"uv run tallylot "
    r"(?P<route>[a-z0-9_][a-z0-9_-]*(?: [a-z0-9_][a-z0-9_-]*){0,4})"
)
ORACLE_COMMAND_ROUTE_PATTERN = re.compile(
    r"uv run python -m tools\.oracles\.cli "
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
    documented_routes = _documented_routes(PRODUCTION_ROUTE_DOC_PATHS, PRODUCTION_COMMAND_ROUTE_PATTERN)
    registered_routes = _registered_routes(app)

    missing_routes = sorted(documented_routes - registered_routes)

    assert not missing_routes, f"documented CLI routes do not exist: {missing_routes}"


def test_documented_oracle_cli_routes_exist() -> None:
    documented_routes = _documented_routes(ORACLE_ROUTE_DOC_PATHS, ORACLE_COMMAND_ROUTE_PATTERN)
    registered_routes = _registered_routes(oracle_app)

    missing_routes = sorted(documented_routes - registered_routes)

    assert not missing_routes, f"documented oracle CLI routes do not exist: {missing_routes}"


def test_docs_do_not_reference_removed_legacy_paths() -> None:
    forbidden = ("06_scripts/", "07_skills/")

    for path in DOC_PATHS:
        text = path.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in text, f"{path} still references {needle}"


def test_documented_claude_command_routes_exist() -> None:
    command_paths = (
        ".claude/commands/source-intake.md",
        ".claude/commands/round-verification.md",
        ".claude/commands/wallet-inventory.md",
        ".claude/commands/normalization-exceptions.md",
        ".claude/commands/source-diff.md",
        ".claude/commands/supporting-artifacts.md",
        ".claude/commands/adapter-authoring.md",
        ".claude/commands/implementation-checkpoint.md",
    )

    for relative_path in command_paths:
        assert (REPO_ROOT / relative_path).exists(), f"missing documented command route: {relative_path}"


def test_documented_claude_command_routes_are_not_ignored() -> None:
    command_paths = (
        ".claude/commands/source-intake.md",
        ".claude/commands/round-verification.md",
        ".claude/commands/wallet-inventory.md",
        ".claude/commands/normalization-exceptions.md",
        ".claude/commands/source-diff.md",
        ".claude/commands/supporting-artifacts.md",
        ".claude/commands/adapter-authoring.md",
        ".claude/commands/implementation-checkpoint.md",
    )

    for relative_path in command_paths:
        result = subprocess.run(
            ("git", "check-ignore", "-q", relative_path),
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 1, f"ignored command route: {relative_path}"


def test_source_intake_route_mentions_current_typed_commands() -> None:
    text = (REPO_ROOT / ".claude" / "commands" / "source-intake.md").read_text(encoding="utf-8")

    for command in (
        "source intake plan",
        "source intake apply",
        "source manifest",
        "source profile",
        "source normalize",
        "checkpoint rebuild-wallet-inventory",
        "output render file",
    ):
        assert command in text


def test_round_verification_route_mentions_oracle_cli_commands() -> None:
    text = (REPO_ROOT / ".claude" / "commands" / "round-verification.md").read_text(encoding="utf-8")

    assert "uv run python -m tools.oracles.cli round scaffold" in text
    assert "uv run python -m tools.oracles.cli verification compare" in text


def test_supporting_route_mentions_checkpoint_pdf_balance_extraction_command() -> None:
    text = (REPO_ROOT / ".claude" / "commands" / "supporting-artifacts.md").read_text(encoding="utf-8")

    assert "checkpoint extract-pdf-balances" in text


def test_wallet_inventory_route_mentions_checkpoint_command() -> None:
    text = (REPO_ROOT / ".claude" / "commands" / "wallet-inventory.md").read_text(encoding="utf-8")

    assert "checkpoint rebuild-wallet-inventory" in text


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
    for path in ARCHITECTURE_DOC_PATHS:
        text = path.read_text(encoding="utf-8").lower()
        for needle in forbidden:
            assert needle not in text, f"{path} still references retired surface {needle!r}"


def test_docs_use_lowercase_filenames_except_readmes() -> None:
    for path in sorted((REPO_ROOT / "docs").rglob("*")):
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
        REPO_ROOT / "README.md",
        REPO_ROOT / "AGENTS.md",
        REPO_ROOT / "tallylot.toml",
        *sorted((REPO_ROOT / "docs").rglob("*.md")),
        *sorted((REPO_ROOT / ".claude").rglob("*.md")),
    )

    for path in paths:
        text = path.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in text, f"{path} still references personal workspace path {needle}"


def test_private_oracle_manifest_is_not_checked_in() -> None:
    assert not (REPO_ROOT / "docs" / "reference" / "cointracking-full-export-manifest.csv").exists()


def test_commit_standards_require_explicit_lint_amend_reverification() -> None:
    text = (REPO_ROOT / "docs" / "architecture" / "commit-standards.md").read_text(encoding="utf-8")

    assert "Do not describe `mypy` or `pyright` as covering `pylint` findings." in text
    assert "uv run pylint <touched-file>" in text
    assert "uv run pytest -q --no-cov <touched-test-file>" in text
    assert "git show HEAD:<path>" in text


def test_reference_docs_do_not_check_in_oracle_data_files() -> None:
    forbidden_suffixes = {".csv", ".json", ".zip", ".html", ".pdf"}

    for path in sorted((REPO_ROOT / "docs" / "reference").rglob("*")):
        if not path.is_file():
            continue
        assert path.suffix not in forbidden_suffixes, (
            f"repo reference docs should not contain oracle data files: {path}"
        )


def test_adapter_pack_goldens_do_not_embed_absolute_home_paths() -> None:
    forbidden = ("/home/user/", "CoinTracking.info/tallylot-2025")

    for path in sorted((REPO_ROOT / "tests" / "fixtures" / "adapter_packs").rglob("*.json")):
        text = path.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in text, f"{path} still embeds absolute local path content"
