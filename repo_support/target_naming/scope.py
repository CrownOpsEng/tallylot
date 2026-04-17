from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TypeGuard, cast

import yaml

from repo_support.paths import repo_root

from .model import NamingScope

FRONTMATTER_PATTERN = re.compile(r"\A---\n(.*?)\n---(?:\n|\Z)", re.DOTALL)
SUPPORTED_NAMING_SCOPES: frozenset[NamingScope] = frozenset(
    {
        "forward_target",
        "repo_policy",
        "current_state",
        "bridge_local",
        "oracle_local",
        "adapter_local",
        "workspace_reference",
    }
)
ENFORCED_NAMING_SCOPES: frozenset[NamingScope] = frozenset(
    {"forward_target", "repo_policy"}
)
EXACT_DOC_SCOPE_DEFAULTS: dict[str, NamingScope] = {
    "docs/README.md": "forward_target",
    "docs/concepts/current-bridge-contracts.md": "bridge_local",
    "docs/concepts/transaction-classification.md": "bridge_local",
    "docs/concepts/workspace-model.md": "workspace_reference",
    "docs/guides/write-an-adapter.md": "adapter_local",
    "docs/reference/baseline-validation-contract.md": "oracle_local",
    "docs/reference/canadian-crypto-tax-guide.md": "oracle_local",
    "docs/reference/cointracking-oracle-artifacts.md": "oracle_local",
    "docs/reference/export-checklist.md": "current_state",
    "docs/reference/location-inventory-artifacts.md": "current_state",
    "docs/reference/manual-balance-submission-artifacts.md": "current_state",
    "docs/reference/repository-history.md": "current_state",
    "docs/reference/tax-source-map.md": "oracle_local",
    "docs/reference/timezone-validation-artifacts.md": "current_state",
    "docs/status/current-state.md": "current_state",
}
PREFIX_DOC_SCOPE_DEFAULTS: tuple[tuple[str, NamingScope], ...] = (
    ("docs/workspace/", "workspace_reference"),
    ("docs/standards/", "repo_policy"),
    ("docs/guides/", "current_state"),
    ("docs/status/", "forward_target"),
    ("docs/concepts/", "forward_target"),
    ("docs/reference/", "forward_target"),
)


@dataclass(frozen=True)
class ScopeResolution:
    path: str
    scope: NamingScope | None
    requires_frontmatter_scope: bool
    missing_required_scope: bool


def repo_relative_path(path: Path | str) -> str:
    if isinstance(path, Path):
        return path.resolve().relative_to(repo_root()).as_posix()
    return path


def is_docs_markdown_path(path: str) -> bool:
    return path.startswith("docs/") and path.endswith(".md")


def parse_frontmatter(text: str) -> dict[str, object]:
    match = FRONTMATTER_PATTERN.match(text)
    if match is None:
        return {}
    loaded: object = yaml.safe_load(match.group(1))
    if not isinstance(loaded, Mapping):
        return {}
    return {
        str(key): value
        for key, value in cast(Mapping[object, object], loaded).items()
        if isinstance(key, str)
    }


def _is_naming_scope(value: str) -> TypeGuard[NamingScope]:
    return value in SUPPORTED_NAMING_SCOPES


def resolve_naming_scope(
    path: str,
    *,
    text: str | None = None,
    frontmatter: dict[str, object] | None = None,
    root_file_scopes: Mapping[str, str] | None = None,
) -> ScopeResolution:
    if is_docs_markdown_path(path):
        loaded_frontmatter = frontmatter or (
            parse_frontmatter(text) if text is not None else {}
        )
        raw_scope = loaded_frontmatter.get("naming_scope")
        if isinstance(raw_scope, str) and _is_naming_scope(raw_scope):
            return ScopeResolution(
                path=path,
                scope=raw_scope,
                requires_frontmatter_scope=True,
                missing_required_scope=False,
            )
        return ScopeResolution(
            path=path,
            scope=None,
            requires_frontmatter_scope=True,
            missing_required_scope=True,
        )

    if path.endswith(".md") and root_file_scopes is not None:
        root_scope = root_file_scopes.get(path)
        if isinstance(root_scope, str) and _is_naming_scope(root_scope):
            return ScopeResolution(
                path=path,
                scope=root_scope,
                requires_frontmatter_scope=False,
                missing_required_scope=False,
            )

    return ScopeResolution(
        path=path,
        scope=None,
        requires_frontmatter_scope=False,
        missing_required_scope=False,
    )


def scope_requires_target_naming(scope: NamingScope | None) -> bool:
    return scope in ENFORCED_NAMING_SCOPES


def default_naming_scope_for_path(path: str) -> NamingScope | None:
    exact = EXACT_DOC_SCOPE_DEFAULTS.get(path)
    if exact is not None:
        return exact
    for prefix, scope in PREFIX_DOC_SCOPE_DEFAULTS:
        if path.startswith(prefix):
            return scope
    return None
