from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import yaml

from .state import relative_path

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


def parse_frontmatter(text: str, path: Path) -> dict[str, object]:
    match = FRONTMATTER_PATTERN.match(text)
    if match is None:
        raise ValueError(f"{path} is missing frontmatter")

    loaded: object = yaml.safe_load(match.group(1))
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


def validate_frontmatter(path: Path, frontmatter: dict[str, object]) -> None:
    missing = [field for field in REQUIRED_FRONTMATTER_FIELDS if field not in frontmatter]
    if missing:
        raise ValueError(f"{path} is missing frontmatter fields: {', '.join(missing)}")

    doc_type = frontmatter_text(frontmatter, "doc_type", path)
    if doc_type not in ALLOWED_DOC_TYPES:
        raise ValueError(f"{path} has invalid doc_type {doc_type!r}")

    audience = frontmatter_text(frontmatter, "audience", path)
    if audience not in ALLOWED_AUDIENCES:
        raise ValueError(f"{path} has invalid audience {audience!r}")

    if frontmatter_text(frontmatter, "owner", path) != "repo":
        raise ValueError(f"{path} must use owner: repo")

    doc_type_expectation = expected_doc_type(path)
    if doc_type_expectation is not None and doc_type != doc_type_expectation:
        raise ValueError(f"{path} must use doc_type: {doc_type_expectation}")

    audience_expectation = expected_audience(path)
    if audience_expectation is not None and audience != audience_expectation:
        raise ValueError(f"{path} must use audience: {audience_expectation}")

    frontmatter_text(frontmatter, "title", path)
    frontmatter_text(frontmatter, "summary", path)
    frontmatter_text(frontmatter, "status", path)

    last_reviewed = frontmatter.get("last_reviewed")
    if last_reviewed is not None and (not isinstance(last_reviewed, str) or not last_reviewed.strip()):
        raise ValueError(f"{path} must use a non-empty string for last_reviewed")

    nav_order = frontmatter.get("nav_order")
    relative = relative_path(path)
    allows_nav_order = any(relative.startswith(prefix) for prefix in NAV_ORDER_ALLOWED_PREFIXES)
    invalid_nav_order = nav_order is not None and (
        not allows_nav_order or isinstance(nav_order, bool) or not isinstance(nav_order, int)
    )
    if invalid_nav_order:
        if not allows_nav_order:
            raise ValueError(f"{path} must not use nav_order outside sync-managed human docs")
        raise ValueError(f"{path} must use an integer for nav_order")

    related = frontmatter.get("related")
    related_items = cast(list[object] | None, related) if isinstance(related, list) else None
    if related is not None and (
        related_items is None or not all(isinstance(item, str) and item.strip() for item in related_items)
    ):
        raise ValueError(f"{path} must use a list of non-empty strings for related")
