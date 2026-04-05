"""Workspace-backed loading for source-label map control data."""

from __future__ import annotations

import re
from pathlib import Path

from tallylot.ports.artifacts import ArtifactStorePort

from .models import SourceLabelConfigIssue, SourceLabelContext, SourceLabelRule

_WINDOWS_ABSOLUTE_PREFIX = re.compile(r"^[A-Za-z]:/")


def load_source_label_context(
    artifacts: ArtifactStorePort,
    workspace_root: Path,
) -> SourceLabelContext:
    rules: list[SourceLabelRule] = []
    issues: list[SourceLabelConfigIssue] = []
    inventory_sources = _inventory_sources(artifacts, workspace_root)
    map_path = workspace_root / "analysis" / "issues" / "source_label_map.csv"
    if not map_path.exists():
        return SourceLabelContext(rules=(), issues=())
    grouped_rows: dict[str, list[tuple[int, str]]] = {}
    for row_number, row in enumerate(artifacts.read_rows(map_path), start=2):
        prefix_value = (row.get("incoming_path_prefix") or "").strip()
        source_value = (row.get("source") or "").strip()
        normalized_prefix, error_message = _normalize_prefix(prefix_value)
        if error_message:
            issues.append(
                SourceLabelConfigIssue(
                    relative_path=f"analysis/issues/source_label_map.csv:{row_number}",
                    severity="error",
                    kind="source_label_map_invalid_prefix",
                    message=error_message,
                    review_code="source_map_invalid_prefix",
                )
            )
            continue
        if not source_value:
            issues.append(
                SourceLabelConfigIssue(
                    relative_path=f"analysis/issues/source_label_map.csv:{row_number}",
                    severity="error",
                    kind="source_label_map_unknown_source",
                    message="Source label map row must include a source value.",
                    matching_prefix=normalized_prefix,
                    review_code="source_map_unknown_source",
                )
            )
            continue
        if source_value not in inventory_sources:
            issues.append(
                SourceLabelConfigIssue(
                    relative_path=f"analysis/issues/source_label_map.csv:{row_number}",
                    severity="error",
                    kind="source_label_map_unknown_source",
                    message=(
                        f"Mapped source {source_value} is not present in "
                        "analysis/issues/source_inventory.csv."
                    ),
                    matching_prefix=normalized_prefix,
                    review_code="source_map_unknown_source",
                )
            )
            continue
        grouped_rows.setdefault(normalized_prefix, []).append(
            (row_number, source_value)
        )
    for prefix, rows in grouped_rows.items():
        sources = sorted({source for _, source in rows})
        if len(sources) > 1:
            line_list = ", ".join(str(line) for line, _ in rows)
            issues.append(
                SourceLabelConfigIssue(
                    relative_path="analysis/issues/source_label_map.csv",
                    severity="error",
                    kind="source_label_map_conflict",
                    message=(
                        f"Conflicting source label map rows for prefix {prefix} on lines "
                        f"{line_list}: {', '.join(sources)}"
                    ),
                    matching_prefix=prefix,
                    review_code="source_map_conflict",
                )
            )
            continue
        rules.append(SourceLabelRule(prefix=prefix, source=sources[0]))
    rules.sort(key=lambda item: (len(item.prefix), item.prefix), reverse=True)
    issues.sort(key=lambda item: (item.relative_path, item.kind, item.message))
    return SourceLabelContext(rules=tuple(rules), issues=tuple(issues))


def _inventory_sources(artifacts: ArtifactStorePort, workspace_root: Path) -> set[str]:
    source_inventory_path = (
        workspace_root / "analysis" / "issues" / "source_inventory.csv"
    )
    if not source_inventory_path.exists():
        return set()
    return {
        source
        for row in artifacts.read_rows(source_inventory_path)
        if (source := (row.get("source") or "").strip())
    }


def _normalize_prefix(value: str) -> tuple[str, str]:
    normalized = value.replace("\\", "/")
    if not normalized:
        return "", "Source label map row must include an incoming_path_prefix value."
    if normalized == ".":
        return ".", ""
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if not normalized:
        return ".", ""
    if normalized.startswith("/") or _WINDOWS_ABSOLUTE_PREFIX.match(normalized):
        return (
            "",
            f"Source label map prefix {value!r} must stay relative to the incoming capture root.",
        )
    left, separator, right = normalized.partition("::")
    normalized_left, left_error = _normalize_part(left)
    if left_error:
        return "", left_error
    if not separator:
        return normalized_left, ""
    normalized_right, right_error = _normalize_part(right)
    if right_error:
        return "", right_error
    return f"{normalized_left}::{normalized_right}", ""


def _normalize_part(value: str) -> tuple[str, str]:
    segments: list[str] = []
    for segment in value.split("/"):
        if segment in {"", "."}:
            continue
        if segment == "..":
            return "", "Source label map prefixes must not traverse upward with '..'."
        segments.append(segment)
    if segments:
        return "/".join(segments), ""
    return (
        "",
        "Source label map prefixes must identify a path inside the incoming capture.",
    )
