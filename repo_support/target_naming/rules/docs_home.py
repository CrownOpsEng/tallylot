from __future__ import annotations

from ..catalog import TargetNamingCatalog
from ..model import DocumentModel, NamingFinding, SourceSpan
from ._common import build_finding


def docs_home_findings(
    document: DocumentModel,
    catalog: TargetNamingCatalog,
) -> tuple[NamingFinding, ...]:
    if document.path != "docs/README.md" or not catalog.reference_group_headings:
        return ()

    findings: list[NamingFinding] = []
    positions: list[int] = []
    for heading in catalog.reference_group_headings:
        count = document.raw_text.count(heading)
        if count != 1:
            findings.append(
                build_finding(
                    rule_id="docs_home.reference_groups",
                    document=document,
                    span=_line_one_span(),
                    message=f"docs home must contain exactly one {heading!r} heading",
                    suggestion="render the reference section with the canonical group headings",
                )
            )
            continue
        positions.append(document.raw_text.index(heading))
    if findings:
        return tuple(findings)
    if positions != sorted(positions):
        findings.append(
            build_finding(
                rule_id="docs_home.reference_groups",
                document=document,
                span=_line_one_span(),
                message="docs home reference groups are out of canonical order",
                suggestion="order reference groups as target, current-state, then oracle",
            )
        )
    return tuple(findings)


def _line_one_span() -> SourceSpan:
    return SourceSpan(line=1, column=1, end_line=1, end_column=1)
