from __future__ import annotations

import re
from dataclasses import dataclass

from ..catalog import (
    IdentifierContextRule,
    IdentifierSurfaceKind,
    TargetNamingCatalog,
)
from ..model import DocumentModel, NamingFinding, SourceSpan
from ._common import build_finding

LABEL_PATTERN = re.compile(r"^[A-Z][A-Za-z0-9 /'()&-]*:$")
SNAKE_IDENTIFIER_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
QUALIFIED_FIELD_PATTERN = re.compile(
    r"\b[A-Z][A-Za-z0-9]*\.(?P<suffix>[a-z][a-z0-9_]*)\b"
)
ARRAY_PATTERN = re.compile(r"\[(?P<components>[^\[\]]*)\]")


@dataclass(frozen=True)
class IdentifierRegion:
    rule: IdentifierContextRule
    start_line: int
    end_line: int


@dataclass(frozen=True)
class IdentifierLookup:
    regions: tuple[IdentifierRegion, ...]
    slot_by_canonical: dict[str, str]
    canonical_by_slot: dict[str, str]


def identifier_namespace_findings(
    document: DocumentModel,
    catalog: TargetNamingCatalog,
) -> tuple[NamingFinding, ...]:
    slot_by_canonical = catalog.local_id_slot_by_canonical_id
    if document.scope is None or not slot_by_canonical:
        return ()
    lookup = IdentifierLookup(
        regions=_identifier_regions(document, catalog),
        slot_by_canonical=slot_by_canonical,
        canonical_by_slot=catalog.local_id_slot_by_slot,
    )
    findings: list[NamingFinding] = []
    for block in document.text_blocks:
        if block.kind != "inline_code":
            continue
        findings.extend(
            _surface_findings(
                document=document,
                text=block.text,
                span=block.span,
                lookup=lookup,
            )
        )
    for table in document.tables:
        for row in (table.header, *table.rows):
            for cell in row.cells:
                findings.extend(
                    _surface_findings(
                        document=document,
                        text=cell.text,
                        span=cell.span,
                        lookup=lookup,
                    )
                )
    return tuple(dict.fromkeys(findings))


def _surface_findings(
    *,
    document: DocumentModel,
    text: str,
    span: SourceSpan,
    lookup: IdentifierLookup,
) -> tuple[NamingFinding, ...]:
    findings: list[NamingFinding] = []
    findings.extend(
        _field_slot_findings(
            document=document,
            text=text,
            span=span,
            lookup=lookup,
        )
    )
    findings.extend(
        _array_component_findings(
            document=document,
            text=text,
            span=span,
            lookup=lookup,
        )
    )
    findings.extend(
        _qualified_field_suffix_findings(
            document=document,
            text=text,
            span=span,
            lookup=lookup,
        )
    )
    return tuple(findings)


def _field_slot_findings(
    *,
    document: DocumentModel,
    text: str,
    span: SourceSpan,
    lookup: IdentifierLookup,
) -> tuple[NamingFinding, ...]:
    token = text.strip()
    if not SNAKE_IDENTIFIER_PATTERN.fullmatch(token):
        return ()
    finding = _identifier_finding(
        document=document,
        observed=token,
        span=span,
        surface_kind="field_slot",
        lookup=lookup,
    )
    return (finding,) if finding is not None else ()


def _array_component_findings(
    *,
    document: DocumentModel,
    text: str,
    span: SourceSpan,
    lookup: IdentifierLookup,
) -> tuple[NamingFinding, ...]:
    findings: list[NamingFinding] = []
    for match in ARRAY_PATTERN.finditer(text):
        components = (
            component.strip() for component in match.group("components").split(",")
        )
        for component in components:
            if not SNAKE_IDENTIFIER_PATTERN.fullmatch(component):
                continue
            finding = _identifier_finding(
                document=document,
                observed=component,
                span=span,
                surface_kind="array_component",
                lookup=lookup,
            )
            if finding is not None:
                findings.append(finding)
    return tuple(findings)


def _qualified_field_suffix_findings(
    *,
    document: DocumentModel,
    text: str,
    span: SourceSpan,
    lookup: IdentifierLookup,
) -> tuple[NamingFinding, ...]:
    findings: list[NamingFinding] = []
    for match in QUALIFIED_FIELD_PATTERN.finditer(text):
        finding = _identifier_finding(
            document=document,
            observed=match.group("suffix"),
            span=span,
            surface_kind="qualified_field_suffix",
            lookup=lookup,
        )
        if finding is not None:
            findings.append(finding)
    return tuple(findings)


def _identifier_finding(
    *,
    document: DocumentModel,
    observed: str,
    span: SourceSpan,
    surface_kind: IdentifierSurfaceKind,
    lookup: IdentifierLookup,
) -> NamingFinding | None:
    canonical_id = (
        observed
        if observed in lookup.slot_by_canonical
        else lookup.canonical_by_slot.get(observed)
    )
    if canonical_id is None:
        return None
    local_slot = lookup.slot_by_canonical[canonical_id]
    mode = _identifier_mode(
        canonical_id=canonical_id,
        line=span.line,
        surface_kind=surface_kind,
        regions=lookup.regions,
    )
    if observed == canonical_id and mode == "local_short":
        return build_finding(
            rule_id="identifier.namespace.local_short_required",
            document=document,
            span=span,
            message=(
                f"use owner-local slot {local_slot!r} instead of canonical id "
                f"{canonical_id!r} on this declared local-short surface"
            ),
            suggestion=(
                f"replace {canonical_id!r} with {local_slot!r} in this declared "
                "owner-local zone"
            ),
        )
    if observed == local_slot and mode == "canonical":
        return build_finding(
            rule_id="identifier.namespace.canonical_required",
            document=document,
            span=span,
            message=(
                f"use canonical id {canonical_id!r} instead of owner-local slot "
                f"{local_slot!r} outside a declared local-short surface"
            ),
            suggestion=(
                f"replace {local_slot!r} with {canonical_id!r} unless the catalog "
                "declares this exact owner-local surface"
            ),
        )
    return None


def _identifier_mode(
    *,
    canonical_id: str,
    line: int,
    surface_kind: IdentifierSurfaceKind,
    regions: tuple[IdentifierRegion, ...],
) -> str:
    for region in regions:
        if region.rule.surface_kind != surface_kind:
            continue
        if canonical_id not in region.rule.canonical_ids:
            continue
        if region.start_line <= line <= region.end_line:
            return region.rule.mode
    return "canonical"


def _identifier_regions(
    document: DocumentModel,
    catalog: TargetNamingCatalog,
) -> tuple[IdentifierRegion, ...]:
    body_lines = _body_lines(document.raw_text)
    total_lines = max(1, len(body_lines))
    regions: list[IdentifierRegion] = []
    for rule in catalog.identifier_context_rules:
        if rule.path != document.path:
            continue
        section_range = _section_line_range(document, rule.section_path, total_lines)
        if section_range is None:
            continue
        section_start, section_end = section_range
        region_range = _region_line_range(
            body_lines=body_lines,
            section_start=section_start,
            section_end=section_end,
            region_label=rule.region_label,
        )
        if region_range is None:
            continue
        region_start, region_end = region_range
        regions.append(
            IdentifierRegion(
                rule=rule,
                start_line=region_start,
                end_line=region_end,
            )
        )
    return tuple(regions)


def _section_line_range(
    document: DocumentModel,
    section_path: tuple[str, ...],
    total_lines: int,
) -> tuple[int, int] | None:
    for index, heading in enumerate(document.headings):
        normalized_heading_path = tuple(
            part.strip("`") for part in heading.section_path
        )
        if normalized_heading_path[-len(section_path) :] != section_path:
            continue
        end_line = total_lines
        for later_heading in document.headings[index + 1 :]:
            if later_heading.level <= heading.level:
                end_line = later_heading.span.line - 1
                break
        return (heading.span.line, end_line)
    return None


def _region_line_range(
    *,
    body_lines: list[str],
    section_start: int,
    section_end: int,
    region_label: str,
) -> tuple[int, int] | None:
    label_lines = [
        line_number
        for line_number in range(section_start + 1, section_end + 1)
        if _is_label_line(body_lines[line_number - 1].strip())
    ]
    target_line = next(
        (
            line_number
            for line_number in label_lines
            if body_lines[line_number - 1].strip() == f"{region_label}:"
        ),
        None,
    )
    if target_line is None:
        return None
    next_label_line = next(
        (line_number for line_number in label_lines if line_number > target_line),
        None,
    )
    return (
        target_line + 1,
        (next_label_line - 1) if next_label_line is not None else section_end,
    )


def _is_label_line(line: str) -> bool:
    return bool(line) and bool(LABEL_PATTERN.fullmatch(line))


def _body_lines(raw_text: str) -> list[str]:
    return _strip_frontmatter(raw_text).splitlines() or [""]


def _strip_frontmatter(text: str) -> str:
    if text.startswith("---\n"):
        _, separator, remainder = text.partition("\n---\n")
        if separator:
            return remainder
    return text


__all__ = ["identifier_namespace_findings"]
