from __future__ import annotations

import subprocess

from tallylot.interfaces.cli import app
from tools.oracles.cli import app as oracle_app

from tests.support.docs_runtime_parity import (
    claude_commands_root,
    documented_oracle_routes,
    documented_production_routes,
    docs_root,
    registered_routes,
    repo_root,
)


def test_documented_cli_routes_exist() -> None:
    missing_routes = sorted(documented_production_routes() - registered_routes(app))
    assert not missing_routes, f"documented CLI routes do not exist: {missing_routes}"


def test_documented_oracle_cli_routes_exist() -> None:
    missing_routes = sorted(documented_oracle_routes() - registered_routes(oracle_app))
    assert not missing_routes, (
        f"documented oracle CLI routes do not exist: {missing_routes}"
    )


def test_documented_claude_command_routes_exist() -> None:
    command_paths = (
        ".claude/commands/source-intake.md",
        ".claude/commands/round-verification.md",
        ".claude/commands/location-inventory.md",
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
        ".claude/commands/location-inventory.md",
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
    assert "meaning parity" in text


def test_round_verification_route_mentions_oracle_cli_commands() -> None:
    text = (claude_commands_root() / "round-verification.md").read_text(
        encoding="utf-8"
    )

    scaffold_command = "make oracle ARGS='round scaffold'"
    compare_command = "make oracle ARGS='verification compare'"

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


def test_supporting_route_mentions_checkpoint_pdf_balance_extraction_command() -> None:
    text = (claude_commands_root() / "supporting-artifacts.md").read_text(
        encoding="utf-8"
    )

    assert "checkpoint extract-pdf-balances" in text


def test_location_inventory_route_mentions_checkpoint_command() -> None:
    text = (claude_commands_root() / "location-inventory.md").read_text(
        encoding="utf-8"
    )

    assert "checkpoint rebuild-location-inventory" in text


def test_operator_guides_include_source_assemble_stage() -> None:
    paths = (
        docs_root() / "guides" / "operator-quickstart.md",
        docs_root() / "guides" / "source-intake.md",
        docs_root() / "guides" / "normalize-screen-stage.md",
        docs_root() / "guides" / "full-operator-workflow.md",
    )

    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "source assemble" in text
