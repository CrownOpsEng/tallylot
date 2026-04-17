from __future__ import annotations

import re

from ..model import (
    DocumentModel,
    MarkerLabel,
    NamingFinding,
    Severity,
    SourceSpan,
    TextBlock,
)


def find_phrase_column(text: str, term: str, *, case_sensitive: bool) -> int | None:
    flags = 0 if case_sensitive else re.IGNORECASE
    match = re.search(re.escape(term), text, flags=flags)
    if match is None:
        return None
    return match.start() + 1


def span_is_covered_by_marker(
    document: DocumentModel,
    span: SourceSpan,
    marker: MarkerLabel,
) -> bool:
    current_section = _best_section(document, span.line)
    for block in document.markers:
        if block.label != marker:
            continue
        if block.section_path not in ((), current_section[: len(block.section_path)]):
            continue
        if block.governed_span.line <= span.line <= block.governed_span.end_line:
            return True
    return False


def span_is_covered_by_any_marker(
    document: DocumentModel,
    span: SourceSpan,
    marker: MarkerLabel,
) -> bool:
    return span_is_covered_by_marker(document, span, marker)


def block_is_covered_by_marker(
    document: DocumentModel,
    block: TextBlock,
    marker: MarkerLabel,
) -> bool:
    return span_is_covered_by_marker(document, block.span, marker)


# pylint: disable=too-many-arguments
def build_finding(
    *,
    rule_id: str,
    document: DocumentModel,
    span: SourceSpan,
    message: str,
    suggestion: str,
    exception_id: str | None = None,
    severity: Severity = "error",
) -> NamingFinding:
    return NamingFinding(
        rule_id=rule_id,
        severity=severity,
        path=document.path,
        line=span.line,
        column=span.column,
        scope=document.scope,
        message=message,
        suggestion=suggestion,
        exception_id=exception_id,
    )


def _best_section(document: DocumentModel, line: int) -> tuple[str, ...]:
    best: tuple[str, ...] = ()
    for heading in document.headings:
        if heading.span.line > line:
            break
        best = heading.section_path
    return best
