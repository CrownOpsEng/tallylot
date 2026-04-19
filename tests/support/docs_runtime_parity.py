from __future__ import annotations

import re
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
from repo_support.target_naming.catalog import load_target_naming_catalog
from repo_support.target_naming.scope import (
    parse_frontmatter as parse_naming_frontmatter,
)

PRODUCTION_COMMAND_ROUTE_PATTERN = re.compile(
    r"make cli ARGS=['\"]"
    r"(?P<route>[a-z0-9_][a-z0-9_-]*(?: [a-z0-9_][a-z0-9_-]*){0,4})"
    r"(?:[^'\"]*)['\"]"
)

ORACLE_COMMAND_ROUTE_PATTERN = re.compile(
    r"make oracle ARGS=['\"]"
    r"(?P<route>[a-z0-9_][a-z0-9_-]*(?: [a-z0-9_][a-z0-9_-]*){0,4})"
    r"(?:[^'\"]*)['\"]"
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
        docs / "reference" / "location-inventory-artifacts.md",
        docs / "workspace" / "analysis" / "inventory" / "README.md",
        commands_root / "balance-submission-operations.md",
        commands_root / "reconciliation-balance-operations.md",
        commands_root / "source-intake.md",
        commands_root / "location-inventory.md",
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


def forward_target_doc_paths() -> list[Path]:
    catalog = load_target_naming_catalog()
    paths = [
        repo_root() / path
        for path, scope in sorted(catalog.root_file_scopes.items())
        if scope == "forward_target"
    ]
    for path in sorted(docs_root().rglob("*.md")):
        frontmatter = parse_naming_frontmatter(path.read_text(encoding="utf-8"))
        if frontmatter.get("naming_scope") == "forward_target":
            paths.append(path)
    return list(dict.fromkeys(paths))


def _documented_routes(paths: list[Path], pattern: re.Pattern[str]) -> set[str]:
    routes: set[str] = set()
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for match in pattern.finditer(text):
            routes.add(match.group("route"))
    return routes


def documented_production_routes() -> set[str]:
    return _documented_routes(
        production_route_doc_paths(),
        PRODUCTION_COMMAND_ROUTE_PATTERN,
    )


def documented_oracle_routes() -> set[str]:
    return _documented_routes(oracle_route_doc_paths(), ORACLE_COMMAND_ROUTE_PATTERN)


def registered_routes(typer_app: Typer) -> set[str]:
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


__all__ = [
    "adapter_packs_root",
    "agents_root",
    "architecture_doc_paths",
    "claude_commands_root",
    "docs_root",
    "documented_oracle_routes",
    "documented_production_routes",
    "forward_target_doc_paths",
    "registered_routes",
    "repo_root",
]
