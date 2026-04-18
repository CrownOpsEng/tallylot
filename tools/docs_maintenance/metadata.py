from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from urllib.parse import urlparse

import yaml

from repo_support.target_naming import (
    SUPPORTED_NAMING_SCOPES,
    default_naming_scope_for_path,
    load_target_naming_catalog,
    resolve_naming_scope,
    validate_summary_style as validate_target_summary_style,
    validate_title_style as validate_target_title_style,
)

from .links import heading_anchors
from .state import relative_path, repo_root

REQUIRED_FRONTMATTER_FIELDS = (
    "title",
    "summary",
    "doc_type",
    "audience",
    "owner",
    "status",
)
ALLOWED_DOC_TYPES = {"concept", "guide", "reference", "standard", "status"}
ALLOWED_AUDIENCES = {"human", "agent", "both"}
NAV_ORDER_ALLOWED_PREFIXES = (
    "docs/concepts/",
    "docs/guides/",
    "docs/reference/",
    "docs/status/",
    "docs/standards/",
)
FRONTMATTER_PATTERN = re.compile(r"\A---\n(.*?)\n---(?:\n|\Z)", re.DOTALL)


@dataclass(frozen=True)
class Document:
    path: Path
    relative_path: str
    frontmatter: dict[str, object]


def validate_related_target(path: Path, target: str) -> None:
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc:
        raise ValueError(
            f"{path} must use repo-relative related targets, got {target!r}"
        )

    target_path_text, anchor = target, None
    if "#" in target:
        target_path_text, anchor = target.split("#", 1)

    resolved = (
        path if not target_path_text else (repo_root() / target_path_text).resolve()
    )
    try:
        relative_path(resolved)
    except ValueError as error:
        raise ValueError(
            f"{path} related target must stay inside the repo: {target}"
        ) from error

    if not resolved.exists():
        raise ValueError(f"{path} uses missing related target {target_path_text}")

    if anchor is None:
        return

    if resolved.suffix != ".md":
        raise ValueError(
            f"{path} must use Markdown anchors only on Markdown related targets: {target}"
        )

    if anchor not in heading_anchors(resolved):
        raise ValueError(
            f"{path} uses missing related anchor #{anchor} in {target_path_text or relative_path(path)}"
        )


def parse_frontmatter(text: str, path: Path) -> dict[str, object]:
    match = FRONTMATTER_PATTERN.match(text)
    if match is None:
        raise ValueError(f"{path} is missing frontmatter")

    try:
        loaded: object = yaml.safe_load(match.group(1))
    except yaml.YAMLError as error:
        raise ValueError(f"{path} has invalid frontmatter: {error}") from error
    if not isinstance(loaded, Mapping):
        raise ValueError(f"{path} frontmatter must be a mapping")
    frontmatter: dict[str, object] = {}
    loaded_mapping = cast(Mapping[object, object], loaded)
    for key, value in loaded_mapping.items():
        if not isinstance(key, str):
            raise ValueError(f"{path} frontmatter keys must be strings")
        frontmatter[key] = value
    return frontmatter


def frontmatter_text(frontmatter: dict[str, object], key: str, path: Path) -> str:
    value = frontmatter.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path} must use a non-empty string for {key}")
    return value


def expected_doc_type(path: Path) -> str | None:
    relative = relative_path(path)
    if relative == "docs/README.md":
        return "reference"

    prefix_map = (
        ("docs/workspace/", "reference"),
        ("docs/concepts/", "concept"),
        ("docs/guides/", "guide"),
        ("docs/reference/", "reference"),
        ("docs/standards/", "standard"),
        ("docs/status/", "status"),
    )
    for prefix, doc_type in prefix_map:
        if relative.startswith(prefix):
            return doc_type
    return None


def expected_audience(path: Path) -> str | None:
    relative = relative_path(path)
    prefix_map = (
        ("agents/", "agent"),
        ("docs/workspace/", "both"),
        ("docs/", "human"),
    )
    for prefix, audience in prefix_map:
        if relative.startswith(prefix):
            return audience
    return None


def validate_summary_style(path: Path, summary: str) -> None:
    relative = relative_path(path)
    if not relative.startswith("docs/"):
        return

    frontmatter = parse_frontmatter(path.read_text(encoding="utf-8"), path)
    resolution = resolve_naming_scope(
        relative,
        frontmatter=frontmatter,
        root_file_scopes=load_target_naming_catalog().root_file_scopes,
    )
    findings = validate_target_summary_style(
        relative,
        summary,
        scope=resolution.scope,
        catalog=load_target_naming_catalog(),
    )
    if findings:
        raise ValueError(findings[0].message)


def _validate_required_frontmatter_fields(
    path: Path,
    frontmatter: dict[str, object],
    *,
    relative: str,
) -> None:
    required_fields = REQUIRED_FRONTMATTER_FIELDS + (
        ("naming_scope",) if relative.startswith("docs/") else ()
    )
    missing = [field for field in required_fields if field not in frontmatter]
    if missing:
        raise ValueError(f"{path} is missing frontmatter fields: {', '.join(missing)}")


def _validate_expected_doc_type_and_audience(
    path: Path,
    *,
    doc_type: str,
    audience: str,
) -> None:
    doc_type_expectation = expected_doc_type(path)
    if doc_type_expectation is not None and doc_type != doc_type_expectation:
        raise ValueError(f"{path} must use doc_type: {doc_type_expectation}")

    audience_expectation = expected_audience(path)
    if audience_expectation is not None and audience != audience_expectation:
        raise ValueError(f"{path} must use audience: {audience_expectation}")


def _validate_naming_scope(
    path: Path,
    frontmatter: dict[str, object],
    *,
    relative: str,
) -> str | None:
    if not relative.startswith("docs/"):
        return None

    naming_scope = frontmatter_text(frontmatter, "naming_scope", path)
    if naming_scope not in SUPPORTED_NAMING_SCOPES:
        raise ValueError(
            f"{path} must use naming_scope from: {', '.join(sorted(SUPPORTED_NAMING_SCOPES))}"
        )
    expected_scope = default_naming_scope_for_path(relative)
    if expected_scope is not None and naming_scope != expected_scope:
        raise ValueError(f"{path} must use naming_scope: {expected_scope}")
    return naming_scope


def _validate_summary_status_and_last_reviewed(
    path: Path,
    frontmatter: dict[str, object],
    *,
    relative: str,
    naming_scope: str | None,
) -> None:
    title = frontmatter_text(frontmatter, "title", path)
    title_findings = validate_target_title_style(
        relative,
        title,
        scope=naming_scope,
        catalog=load_target_naming_catalog(),
    )
    if title_findings:
        raise ValueError(title_findings[0].message)
    summary = frontmatter_text(frontmatter, "summary", path)
    findings = validate_target_summary_style(
        relative,
        summary,
        scope=naming_scope,
        catalog=load_target_naming_catalog(),
    )
    if findings:
        raise ValueError(findings[0].message)
    frontmatter_text(frontmatter, "status", path)

    last_reviewed = frontmatter.get("last_reviewed")
    if last_reviewed is not None and (
        not isinstance(last_reviewed, str) or not last_reviewed.strip()
    ):
        raise ValueError(f"{path} must use a non-empty string for last_reviewed")


def _validate_nav_order(
    path: Path, frontmatter: dict[str, object], *, relative: str
) -> None:
    nav_order = frontmatter.get("nav_order")
    allows_nav_order = any(
        relative.startswith(prefix) for prefix in NAV_ORDER_ALLOWED_PREFIXES
    )
    invalid_nav_order = nav_order is not None and (
        not allows_nav_order
        or isinstance(nav_order, bool)
        or not isinstance(nav_order, int)
    )
    if not invalid_nav_order:
        return
    if not allows_nav_order:
        raise ValueError(
            f"{path} must not use nav_order outside sync-managed human docs"
        )
    raise ValueError(f"{path} must use an integer for nav_order")


def _validate_related(path: Path, frontmatter: dict[str, object]) -> None:
    related = frontmatter.get("related")
    related_items = (
        cast(list[object] | None, related) if isinstance(related, list) else None
    )
    if related is not None and (
        related_items is None
        or not all(isinstance(item, str) and item.strip() for item in related_items)
    ):
        raise ValueError(f"{path} must use a list of non-empty strings for related")
    if related_items is None:
        return
    for item in cast(list[str], related_items):
        validate_related_target(path, item)


def validate_frontmatter(path: Path, frontmatter: dict[str, object]) -> None:
    relative = relative_path(path)
    _validate_required_frontmatter_fields(path, frontmatter, relative=relative)

    doc_type = frontmatter_text(frontmatter, "doc_type", path)
    if doc_type not in ALLOWED_DOC_TYPES:
        raise ValueError(f"{path} has invalid doc_type {doc_type!r}")

    audience = frontmatter_text(frontmatter, "audience", path)
    if audience not in ALLOWED_AUDIENCES:
        raise ValueError(f"{path} has invalid audience {audience!r}")

    if frontmatter_text(frontmatter, "owner", path) != "repo":
        raise ValueError(f"{path} must use owner: repo")

    _validate_expected_doc_type_and_audience(path, doc_type=doc_type, audience=audience)
    naming_scope = _validate_naming_scope(path, frontmatter, relative=relative)
    _validate_summary_status_and_last_reviewed(
        path,
        frontmatter,
        relative=relative,
        naming_scope=naming_scope,
    )
    _validate_nav_order(path, frontmatter, relative=relative)
    _validate_related(path, frontmatter)
