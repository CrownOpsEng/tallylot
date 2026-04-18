from __future__ import annotations

from ..catalog import TargetNamingCatalog
from ..model import DocumentModel, NamingFinding, SourceSpan
from ._common import build_finding


def title_findings(
    document: DocumentModel,
    catalog: TargetNamingCatalog,
) -> tuple[NamingFinding, ...]:
    expected_title = catalog.title_expectations.get(document.path)
    if expected_title is None:
        return ()
    if document.title == expected_title:
        return ()
    return (
        build_finding(
            rule_id="title.canonical",
            document=document,
            span=SourceSpan(line=1, column=1, end_line=1, end_column=1),
            message=(
                f"title must match the catalog for {document.path}; expected "
                f"{expected_title!r}, found {document.title!r}"
            ),
            suggestion="rewrite the frontmatter title to the canonical value",
        ),
    )
