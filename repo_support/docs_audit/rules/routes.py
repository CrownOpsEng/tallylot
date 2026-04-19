from __future__ import annotations

from tallylot.interfaces.cli import app
from tools.oracles.cli import app as oracle_app
from repo_support.paths import repo_root

from ._common import build_rule
from ..helpers import (
    check_not_ignored,
    claude_text,
    documented_oracle_routes,
    documented_production_routes,
    docs_path,
    registered_routes,
)


ROUTE_RULES = (
    build_rule(
        "routes.documented_cli_routes_exist",
        "README.md",
        lambda: (
            lambda missing: (
                None
                if not missing
                else (_ for _ in ()).throw(
                    AssertionError(
                        f"documented CLI routes do not exist: {sorted(missing)}"
                    )
                )
            )
        )(documented_production_routes() - registered_routes(app)),
    ),
    build_rule(
        "routes.documented_oracle_cli_routes_exist",
        "docs/reference/baseline-validation-contract.md",
        lambda: (
            lambda missing: (
                None
                if not missing
                else (_ for _ in ()).throw(
                    AssertionError(
                        f"documented oracle CLI routes do not exist: {sorted(missing)}"
                    )
                )
            )
        )(documented_oracle_routes() - registered_routes(oracle_app)),
    ),
    build_rule(
        "routes.documented_claude_command_routes_exist",
        ".claude/commands",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(f"missing documented command route: {relative_path}")
            )
            for relative_path in (
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
            if not (repo_root() / relative_path).exists()
        ],
    ),
    build_rule(
        "routes.documented_claude_command_routes_are_not_ignored",
        ".claude/commands",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(f"ignored command route: {relative_path}")
            )
            for relative_path in (
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
            if not check_not_ignored(relative_path)
        ],
    ),
    build_rule(
        "routes.source_intake_route_mentions_current_typed_commands",
        ".claude/commands/source-intake.md",
        lambda: [
            (_ for _ in ()).throw(AssertionError(f"missing route text {needle!r}"))
            for needle in (
                "source intake plan",
                "source intake apply",
                "source manifest",
                "source profile",
                "source normalize",
                "checkpoint rebuild-location-inventory",
                "output render file",
                "source_label_map.csv",
                "meaning parity",
            )
            if needle not in claude_text("source-intake.md")
        ],
    ),
    build_rule(
        "routes.round_verification_route_mentions_oracle_cli_commands",
        ".claude/commands/round-verification.md",
        lambda: [
            (_ for _ in ()).throw(AssertionError(f"missing route text {needle!r}"))
            for needle in (
                "make oracle ARGS='round scaffold'",
                "make oracle ARGS='verification compare'",
            )
            if needle not in claude_text("round-verification.md")
        ],
    ),
    build_rule(
        "routes.reconciliation_balance_route_mentions_current_balance_commands",
        ".claude/commands/reconciliation-balance-operations.md",
        lambda: [
            (_ for _ in ()).throw(AssertionError(f"missing route text {needle!r}"))
            for needle in (
                "reconciliation balances inspect",
                "reconciliation balances check",
                "reconciliation balances summarize",
                "cross_source_assertions.csv",
                "balance-submission-operations.md",
            )
            if needle not in claude_text("reconciliation-balance-operations.md")
        ],
    ),
    build_rule(
        "routes.balance_submission_route_mentions_current_checkpoint_commands",
        ".claude/commands/balance-submission-operations.md",
        lambda: [
            (_ for _ in ()).throw(AssertionError(f"missing route text {needle!r}"))
            for needle in (
                "checkpoint scaffold-balance-submission",
                "checkpoint submit-balances",
                "reconciliation balances inspect",
                "reconciliation balances check",
                "reconciliation balances summarize",
            )
            if needle not in claude_text("balance-submission-operations.md")
        ],
    ),
    build_rule(
        "routes.supporting_route_mentions_checkpoint_pdf_balance_extraction_command",
        ".claude/commands/supporting-artifacts.md",
        lambda: (
            None
            if "checkpoint extract-pdf-balances"
            in claude_text("supporting-artifacts.md")
            else (_ for _ in ()).throw(
                AssertionError("missing checkpoint extract-pdf-balances route")
            )
        ),
    ),
    build_rule(
        "routes.location_inventory_route_mentions_checkpoint_command",
        ".claude/commands/location-inventory.md",
        lambda: (
            None
            if "checkpoint rebuild-location-inventory"
            in claude_text("location-inventory.md")
            else (_ for _ in ()).throw(
                AssertionError("missing checkpoint rebuild-location-inventory route")
            )
        ),
    ),
    build_rule(
        "routes.operator_guides_include_source_assemble_stage",
        "docs/guides",
        lambda: [
            (_ for _ in ()).throw(AssertionError(f"{path} is missing source assemble"))
            for path in (
                docs_path("guides/operator-quickstart.md"),
                docs_path("guides/source-intake.md"),
                docs_path("guides/normalize-screen-stage.md"),
                docs_path("guides/full-operator-workflow.md"),
            )
            if "source assemble" not in path.read_text(encoding="utf-8")
        ],
    ),
)
