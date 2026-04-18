from __future__ import annotations

from ..catalog import MatrixSpec, TargetNamingCatalog
from ..model import DocumentModel, NamingFinding, SourceSpan, TableRow
from ._common import build_finding, find_phrase_column


def matrix_findings(
    document: DocumentModel,
    catalog: TargetNamingCatalog,
) -> tuple[NamingFinding, ...]:
    spec = next(
        (item for item in catalog.matrix_specs if item.path == document.path), None
    )
    if spec is None:
        return ()
    if not document.tables:
        return (
            build_finding(
                rule_id="matrix.columns.canonical",
                document=document,
                span=document.headings[0].span
                if document.headings
                else _line_one_span(),
                message="governed migration matrix is missing",
                suggestion="restore the canonical bridge-to-target matrix",
            ),
        )
    table = document.tables[0]
    findings: list[NamingFinding] = []
    actual_header = tuple(cell.text for cell in table.header.cells)
    if actual_header != spec.required_columns:
        findings.append(
            build_finding(
                rule_id="matrix.columns.canonical",
                document=document,
                span=table.header.span,
                message=(
                    f"matrix columns must match {spec.required_columns!r}, "
                    f"found {actual_header!r}"
                ),
                suggestion="rewrite the matrix header to the canonical column set",
            )
        )
    for row in table.rows:
        for cell in row.cells:
            lowered = cell.normalized_text
            for fragment in spec.banned_fragments:
                column = find_phrase_column(
                    lowered, fragment.casefold(), case_sensitive=True
                )
                if column is None:
                    continue
                findings.append(
                    build_finding(
                        rule_id="matrix.rows.stable_surface_names",
                        document=document,
                        span=cell.span,
                        message=f"matrix cell uses banned fragment {fragment!r}",
                        suggestion=(
                            "replace pseudo-family or workflow-path wording with a "
                            "stable surface, file, view, or sidecar name"
                        ),
                    )
                )
        findings.extend(_shape_column_findings(document, row, spec))
    return tuple(findings)


def _shape_column_findings(
    document: DocumentModel,
    row: TableRow,
    spec: MatrixSpec,
) -> tuple[NamingFinding, ...]:
    findings: list[NamingFinding] = []
    for cell in row.cells[2:4]:
        lowered = cell.normalized_text
        if lowered == "none":
            continue
        if "compatibility" in lowered and not any(
            noun in lowered
            for noun in (item.casefold() for item in spec.allowed_shape_nouns)
        ):
            findings.append(
                build_finding(
                    rule_id="matrix.rows.canonical_shapes",
                    document=document,
                    span=cell.span,
                    message="matrix cell uses a non-canonical compatibility shape noun",
                    suggestion="use only compatibility view, compatibility sidecar, or none",
                )
            )
    return tuple(findings)


def _line_one_span() -> SourceSpan:
    return SourceSpan(line=1, column=1, end_line=1, end_column=1)
