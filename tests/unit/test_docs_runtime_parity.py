from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import cast

from typer.main import Typer
from typer.models import CommandInfo

from crypto_reconciliation.interfaces.cli import app

REPO_ROOT = Path(__file__).resolve().parents[2]
ROUTE_DOC_PATHS = [
    REPO_ROOT / "README.md",
]
ARCHITECTURE_DOC_PATHS = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "ROADMAP.md",
    REPO_ROOT / "docs" / "architecture" / "engineering-standards.md",
    REPO_ROOT / "docs" / "architecture" / "reconciliation-tax-implementation-plan.md",
    REPO_ROOT / ".claude" / "commands" / "source-intake.md",
]
DOC_COMMAND_ROUTE_PATTERN = re.compile(
    r"uv run crypto-reconciliation "
    r"(?P<route>[a-z0-9_][a-z0-9_-]*(?: [a-z0-9_][a-z0-9_-]*){0,4})"
)


def _documented_cli_routes() -> set[str]:
    routes: set[str] = set()
    for path in ROUTE_DOC_PATHS:
        text = path.read_text(encoding="utf-8")
        for match in DOC_COMMAND_ROUTE_PATTERN.finditer(text):
            routes.add(match.group("route"))
    return routes


def _registered_cli_routes() -> set[str]:
    routes: set[str] = set()

    def command_name(command: CommandInfo) -> str:
        if command.name is not None:
            return command.name
        callback = cast(Callable[..., object], command.callback)
        return callback.__name__.replace("_", "-")

    def walk(typer_app: Typer, prefix: tuple[str, ...] = ()) -> None:
        for command in typer_app.registered_commands:
            routes.add(" ".join((*prefix, command_name(command))))
        for group in typer_app.registered_groups:
            if group.typer_instance is not None and group.name is not None:
                walk(group.typer_instance, (*prefix, group.name))

    walk(app)
    return routes


def test_documented_cli_routes_exist() -> None:
    documented_routes = _documented_cli_routes()
    registered_routes = _registered_cli_routes()

    missing_routes = sorted(documented_routes - registered_routes)

    assert not missing_routes, f"documented CLI routes do not exist: {missing_routes}"


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
