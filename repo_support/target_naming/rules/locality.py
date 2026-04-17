from __future__ import annotations

import re

from ..catalog import ExceptionRule, TargetNamingCatalog
from ..model import DocumentModel, MarkerBlock, MarkerLabel, NamingFinding, TextBlock
from ._common import block_is_covered_by_marker, build_finding


def locality_findings(
    document: DocumentModel,
    catalog: TargetNamingCatalog,
) -> tuple[NamingFinding, ...]:
    if document.scope is None:
        return ()
    findings: list[NamingFinding] = []
    rules_by_term: dict[str, list[ExceptionRule]] = {}
    for rule in catalog.exceptions:
        for term in rule.allowed_terms:
            rules_by_term.setdefault(term, []).append(rule)

    for block in document.text_blocks:
        if block.kind == "fence":
            continue
        for term, rules in rules_by_term.items():
            if _term_column(block.text, term) is None:
                continue
            if any(_term_allowed(document, block, rule) for rule in rules):
                continue
            matching_rule = next(
                (
                    rule
                    for rule in rules
                    if document.scope in rule.allowed_scopes
                    and (document.path in rule.allowed_paths or not rule.allowed_paths)
                ),
                rules[0],
            )
            findings.append(
                build_finding(
                    rule_id=_locality_rule_id(matching_rule),
                    document=document,
                    span=block.span,
                    message=(
                        f"{term!r} requires the marker "
                        f"**{matching_rule.required_marker}:** in an allowed "
                        "governed block"
                    ),
                    suggestion=_locality_suggestion(matching_rule),
                    exception_id=matching_rule.exception_id,
                )
            )
    return tuple(dict.fromkeys(findings))


def _term_allowed(
    document: DocumentModel,
    block: TextBlock,
    rule: ExceptionRule,
) -> bool:
    if document.scope not in rule.allowed_scopes:
        return False
    if rule.allowed_paths and document.path not in rule.allowed_paths:
        return False
    if rule.allowed_section_labels and not set(
        rule.allowed_section_labels
    ).intersection(block.section_path):
        return False
    marker = _marker_covering(document, block, rule.required_marker)
    if marker is None:
        return False
    if not rule.required_rationale:
        return True
    return _marker_has_rationale(marker)


def _marker_covering(
    document: DocumentModel,
    block: TextBlock,
    required_marker: MarkerLabel,
) -> MarkerBlock | None:
    for marker in document.markers:
        if marker.label != required_marker:
            continue
        if block_is_covered_by_marker(document, block, required_marker):
            return marker
    return None


def _marker_has_rationale(marker: MarkerBlock) -> bool:
    marker_prefix = f"{marker.label}:"
    if marker.text.strip() != marker_prefix:
        if marker.text.strip().removeprefix(marker_prefix).strip():
            return True
    return marker.governed_span.end_line > marker.span.end_line


def _locality_rule_id(rule: ExceptionRule) -> str:
    if rule.required_marker in {"Exception rationale", "Migration-only root rationale"}:
        return "locality.root.exception_rationale"
    if rule.required_marker == "Slice-only example":
        return "locality.example.slice_only"
    return "locality.field.exception_restatement"


def _locality_suggestion(rule: ExceptionRule) -> str:
    return (
        f"keep the term only inside an allowed block labeled "
        f"**{rule.required_marker}:** and include the required rationale"
    )


def _term_column(text: str, term: str) -> int | None:
    pattern = re.compile(
        rf"(?<![A-Za-z0-9_]){re.escape(term)}(?![A-Za-z0-9_])",
        flags=re.IGNORECASE,
    )
    match = pattern.search(text)
    if match is None:
        return None
    return match.start() + 1
