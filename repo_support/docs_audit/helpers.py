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
    claude_commands_root,
    docs_root,
    repo_root,
)
from repo_support.target_naming.catalog import load_target_naming_catalog
from repo_support.target_naming.scope import (
    parse_frontmatter as parse_naming_frontmatter,
)

from .model import DocsAuditFinding

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


def relative_repo_paths(paths: tuple[Path, ...]) -> tuple[str, ...]:
    return tuple(path.relative_to(repo_root()).as_posix() for path in paths)


def repo_text(relative_path: str) -> str:
    return (repo_root() / relative_path).read_text(encoding="utf-8")


def path_exists(relative_path: str) -> bool:
    return (repo_root() / relative_path).exists()


def docs_path(relative_path: str) -> Path:
    return docs_root() / relative_path


def docs_text(relative_path: str) -> str:
    return docs_path(relative_path).read_text(encoding="utf-8")


def claude_text(filename: str) -> str:
    return (claude_commands_root() / filename).read_text(encoding="utf-8")


def architecture_doc_paths() -> tuple[Path, ...]:
    return (
        repo_root() / "README.md",
        docs_root() / "standards" / "engineering.md",
        docs_root() / "concepts" / "reconciliation-tax-architecture.md",
        claude_commands_root() / "source-intake.md",
    )


def forward_target_doc_paths() -> tuple[Path, ...]:
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
    return tuple(dict.fromkeys(paths))


def documented_production_routes() -> set[str]:
    return _documented_routes(
        (
            repo_root() / "README.md",
            docs_root() / "guides" / "operator-quickstart.md",
            docs_root() / "guides" / "source-intake.md",
            docs_root() / "guides" / "normalize-screen-stage.md",
            docs_root() / "reference" / "manual-balance-submission-artifacts.md",
            docs_root() / "reference" / "location-inventory-artifacts.md",
            docs_root() / "workspace" / "analysis" / "inventory" / "README.md",
            claude_commands_root() / "balance-submission-operations.md",
            claude_commands_root() / "reconciliation-balance-operations.md",
            claude_commands_root() / "source-intake.md",
            claude_commands_root() / "location-inventory.md",
            claude_commands_root() / "supporting-artifacts.md",
        ),
        PRODUCTION_COMMAND_ROUTE_PATTERN,
    )


def documented_oracle_routes() -> set[str]:
    return _documented_routes(
        (
            docs_root() / "reference" / "baseline-validation-contract.md",
            docs_root() / "reference" / "export-checklist.md",
            docs_root() / "guides" / "operator-quickstart.md",
            docs_root() / "guides" / "full-operator-workflow.md",
            docs_root() / "guides" / "normalize-screen-stage.md",
            docs_root() / "guides" / "verify-a-round.md",
            claude_commands_root() / "round-verification.md",
            claude_commands_root() / "source-diff.md",
        ),
        ORACLE_COMMAND_ROUTE_PATTERN,
    )


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


def _documented_routes(
    paths: tuple[Path, ...],
    pattern: re.Pattern[str],
) -> set[str]:
    routes: set[str] = set()
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for match in pattern.finditer(text):
            routes.add(match.group("route"))
    return routes


def check_not_ignored(relative_path: str) -> bool:
    result = subprocess.run(
        ("git", "check-ignore", "-q", relative_path),
        cwd=repo_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 1


def joined(*parts: str) -> str:
    return "".join(parts)


def normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_plain_bullets(
    text: str, start_heading: str, end_heading: str
) -> tuple[str, ...]:
    pattern = re.compile(
        rf"{re.escape(start_heading)}\n\n(?P<body>.*?)(?:\n{re.escape(end_heading)})",
        re.DOTALL,
    )
    match = pattern.search(text)
    if match is None:
        raise AssertionError(f"missing section {start_heading!r}")
    body = match.group("body").rstrip()
    return tuple(
        normalized(item.group("body"))
        for item in re.finditer(
            r"^- (?P<body>.*?)(?=\n- |\Z)",
            body,
            flags=re.MULTILINE | re.DOTALL,
        )
    )


def extract_code_bullets(
    text: str, start_heading: str, end_heading: str
) -> tuple[str, ...]:
    return tuple(
        canonical_text_value(item)
        for item in extract_plain_bullets(text, start_heading, end_heading)
    )


def extract_labeled_code_bullets(
    text: str, start_heading: str, end_heading: str
) -> tuple[str, ...]:
    body = section(text, start_heading, end_heading)
    return tuple(re.findall(r"^- `([^`]+)`:", body, flags=re.MULTILINE))


def split_table_line(line: str) -> tuple[str, ...]:
    return tuple(cell.strip() for cell in line.strip().strip("|").split("|"))


def extract_markdown_table(
    text: str, header_prefix: str
) -> tuple[tuple[str, ...], tuple[tuple[str, ...], ...]]:
    lines = text.splitlines()
    table_lines: list[str] = []
    capture = False
    for line in lines:
        if line.startswith(header_prefix):
            capture = True
        if capture:
            if not line.startswith("|"):
                break
            table_lines.append(line)
    if len(table_lines) < 3:
        raise AssertionError(
            f"missing or truncated markdown table starting with {header_prefix!r}"
        )
    header = split_table_line(table_lines[0])
    rows = tuple(split_table_line(line) for line in table_lines[2:])
    return header, rows


def extract_backticked_tokens(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"`([^`]+)`", text))


def split_matrix_clauses(text: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in text.split(";") if part.strip())


def canonical_text_value(text: str) -> str:
    return text.replace("`", "").strip()


def section(text: str, start_heading: str, end_heading: str) -> str:
    pattern = re.compile(
        rf"{re.escape(start_heading)}\n(?P<body>.*?)(?:\n{re.escape(end_heading)})",
        re.DOTALL,
    )
    match = pattern.search(text)
    if match is None:
        raise AssertionError(f"missing section {start_heading!r}")
    return match.group("body")


def finding(
    rule_id: str, path: str, message: str, suggestion: str | None = None
) -> DocsAuditFinding:
    return DocsAuditFinding(
        rule_id=rule_id,
        path=path,
        message=message,
        suggestion=suggestion,
    )


def failure_finding(
    rule_id: str,
    path: str,
    error: AssertionError,
    *,
    suggestion: str | None = None,
) -> DocsAuditFinding:
    message = str(error) or "rule failed"
    return finding(rule_id, path, message, suggestion)


def adapter_pack_json_paths() -> tuple[Path, ...]:
    return tuple(sorted(adapter_packs_root().rglob("*.json")))
