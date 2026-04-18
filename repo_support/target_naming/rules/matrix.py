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
    findings.extend(_required_inventory_findings(document, table.rows, spec))
    for row in table.rows:
        findings.extend(_required_cell_findings(document, row, spec))
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


def _required_inventory_findings(
    document: DocumentModel,
    rows: tuple[TableRow, ...],
    spec: MatrixSpec,
) -> tuple[NamingFinding, ...]:
    actual_rows = tuple(
        _canonical_matrix_value(row.cells[0].text) if row.cells else "" for row in rows
    )
    if actual_rows == spec.required_rows:
        return ()
    mismatch_index = next(
        (
            index
            for index, pair in enumerate(
                zip(actual_rows, spec.required_rows, strict=False)
            )
            if pair[0] != pair[1]
        ),
        None,
    )
    if mismatch_index is None:
        mismatch_index = min(len(rows), max(len(spec.required_rows) - 1, 0))
    span = (
        rows[mismatch_index].cells[0].span
        if rows and mismatch_index < len(rows) and rows[mismatch_index].cells
        else _line_one_span()
    )
    return (
        build_finding(
            rule_id="matrix.rows.required_inventory",
            document=document,
            span=span,
            message=(
                "matrix rows must match the required inventory and order; "
                f"expected {spec.required_rows!r}, found {actual_rows!r}"
            ),
            suggestion="rewrite the bridge cutover rows to the catalog-declared inventory and order",
        ),
    )


def _required_cell_findings(
    document: DocumentModel,
    row: TableRow,
    spec: MatrixSpec,
) -> tuple[NamingFinding, ...]:
    findings: list[NamingFinding] = []
    column_index = {column: index for index, column in enumerate(spec.required_columns)}
    surface_name = _canonical_matrix_value(row.cells[0].text) if row.cells else "row"
    for column in spec.required_nonempty_columns:
        index = column_index[column]
        if index >= len(row.cells) or not _canonical_matrix_value(
            row.cells[index].text
        ):
            span = (
                row.cells[min(index, len(row.cells) - 1)].span
                if row.cells
                else _line_one_span()
            )
            findings.append(
                build_finding(
                    rule_id="matrix.rows.required_cell",
                    document=document,
                    span=span,
                    message=(f"matrix row {surface_name!r} must populate {column!r}"),
                    suggestion="fill every required reader and gate cell in the cutover matrix",
                )
            )
    return tuple(findings)


def _canonical_matrix_value(text: str) -> str:
    return text.replace("`", "").strip()


def _line_one_span() -> SourceSpan:
    return SourceSpan(line=1, column=1, end_line=1, end_column=1)
