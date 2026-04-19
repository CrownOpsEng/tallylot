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
    findings.extend(_current_reader_inventory_findings(document, table.rows, spec))
    for row in table.rows:
        findings.extend(_required_cell_findings(document, row, spec))
        findings.extend(_current_reader_findings(document, row, spec))
        findings.extend(_authoritative_product_findings(document, row, spec))
        findings.extend(_target_reader_findings(document, row, spec))
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


def _current_reader_inventory_findings(
    document: DocumentModel,
    rows: tuple[TableRow, ...],
    spec: MatrixSpec,
) -> tuple[NamingFinding, ...]:
    if not spec.current_reader_inventory:
        return ()
    column_index = {column: index for index, column in enumerate(spec.required_columns)}
    readers_index = column_index["Current readers"]
    used_labels: set[str] = {
        _canonical_matrix_value(clause)
        for row in rows
        if readers_index < len(row.cells)
        for clause in _split_matrix_clauses(row.cells[readers_index].text)
    }
    expected_labels: set[str] = set(spec.current_reader_inventory)
    if used_labels == expected_labels:
        return ()
    span = (
        rows[0].cells[readers_index].span
        if rows and readers_index < len(rows[0].cells)
        else _line_one_span()
    )
    return (
        build_finding(
            rule_id="matrix.rows.current_readers.inventory",
            document=document,
            span=span,
            message=(
                "matrix current-reader labels must cover the canonical inventory; "
                f"expected {sorted(expected_labels)!r}, found {sorted(used_labels)!r}"
            ),
            suggestion=(
                "rewrite current-reader cells to the canonical inventory labels"
            ),
        ),
    )


def _current_reader_findings(
    document: DocumentModel,
    row: TableRow,
    spec: MatrixSpec,
) -> tuple[NamingFinding, ...]:
    if not spec.current_reader_inventory:
        return ()
    column_index = {column: index for index, column in enumerate(spec.required_columns)}
    readers_index = column_index["Current readers"]
    if readers_index >= len(row.cells):
        return ()
    cell = row.cells[readers_index]
    allowed_labels = frozenset(spec.current_reader_inventory)
    findings: list[NamingFinding] = []
    for clause in _split_matrix_clauses(cell.text):
        label = _canonical_matrix_value(clause)
        if not clause.startswith("`") or not clause.endswith("`"):
            findings.append(
                build_finding(
                    rule_id="matrix.rows.current_readers.canonical_label",
                    document=document,
                    span=cell.span,
                    message=(
                        f"matrix current-reader label {clause!r} must use the "
                        "canonical backticked inventory form"
                    ),
                    suggestion=(
                        "wrap each current-reader label in backticks and use the "
                        "canonical inventory label"
                    ),
                )
            )
            continue
        if label not in allowed_labels:
            findings.append(
                build_finding(
                    rule_id="matrix.rows.current_readers.canonical_label",
                    document=document,
                    span=cell.span,
                    message=(
                        f"matrix current-reader label {label!r} is not in the "
                        "canonical inventory"
                    ),
                    suggestion=(
                        "replace the label with one of the canonical current-reader "
                        "inventory entries"
                    ),
                )
            )
    return tuple(findings)


def _authoritative_product_findings(
    document: DocumentModel,
    row: TableRow,
    spec: MatrixSpec,
) -> tuple[NamingFinding, ...]:
    column_index = {column: index for index, column in enumerate(spec.required_columns)}
    authoritative_index = column_index["Target authoritative product(s)"]
    if authoritative_index >= len(row.cells):
        return ()
    cell = row.cells[authoritative_index]
    if not _canonical_matrix_value(cell.text):
        return ()
    if _target_reader_terms(cell.text):
        return ()
    return (
        build_finding(
            rule_id="matrix.rows.authoritative_products.canonical_owner",
            document=document,
            span=cell.span,
            message=(
                "target-authority cells must name machine-readable authoritative "
                "products"
            ),
            suggestion=(
                "use backticked authoritative product names or the explicit "
                "'owning target product' phrase"
            ),
        ),
    )


def _target_reader_findings(
    document: DocumentModel,
    row: TableRow,
    spec: MatrixSpec,
) -> tuple[NamingFinding, ...]:
    column_index = {column: index for index, column in enumerate(spec.required_columns)}
    target_readers_index = column_index["Target readers after cutover"]
    if target_readers_index >= len(row.cells):
        return ()
    authoritative_index = column_index["Target authoritative product(s)"]
    authoritative_terms: set[str] = (
        _target_reader_terms(row.cells[authoritative_index].text)
        if authoritative_index < len(row.cells)
        else set()
    )
    placeholder_capabilities = frozenset(
        item.casefold() for item in spec.target_reader_placeholder_capabilities
    )
    cell = row.cells[target_readers_index]
    findings: list[NamingFinding] = []
    for clause in _split_matrix_clauses(cell.text):
        connector = " reading " if " reading " in clause else " from "
        if connector not in clause:
            findings.append(
                build_finding(
                    rule_id="matrix.rows.target_readers.shape",
                    document=document,
                    span=cell.span,
                    message=(
                        f"target-reader clause {clause!r} must name a concrete "
                        "capability plus authoritative product"
                    ),
                    suggestion=(
                        "rewrite each target-reader clause using '<capability> "
                        "reading <authoritative product>' or '<capability> from "
                        "<authoritative product>'"
                    ),
                )
            )
            continue
        capability_text, target_text = clause.split(connector, 1)
        capability = _canonical_matrix_value(capability_text)
        if not capability:
            findings.append(
                build_finding(
                    rule_id="matrix.rows.target_readers.shape",
                    document=document,
                    span=cell.span,
                    message=(
                        f"target-reader clause {clause!r} is missing a concrete "
                        "capability"
                    ),
                    suggestion=(
                        "name the target capability before the authoritative "
                        "product reference"
                    ),
                )
            )
            continue
        if capability.casefold() in placeholder_capabilities:
            findings.append(
                build_finding(
                    rule_id="matrix.rows.target_readers.placeholder_capability",
                    document=document,
                    span=cell.span,
                    message=(
                        f"target-reader capability {capability!r} is still a "
                        "placeholder, not a concrete capability"
                    ),
                    suggestion=(
                        "replace the placeholder with the concrete post-cutover "
                        "capability name"
                    ),
                )
            )
        target_terms: set[str] = _target_reader_terms(target_text)
        if authoritative_terms and not target_terms.intersection(authoritative_terms):
            findings.append(
                build_finding(
                    rule_id="matrix.rows.target_readers.authoritative_product",
                    document=document,
                    span=cell.span,
                    message=(
                        f"target-reader clause {clause!r} must name the row's "
                        "authoritative product"
                    ),
                    suggestion=(
                        "reference the same authoritative product named in the "
                        "target-authority column"
                    ),
                )
            )
    return tuple(findings)


def _canonical_matrix_value(text: str) -> str:
    return text.replace("`", "").strip()


def _split_matrix_clauses(text: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in text.split(";") if part.strip())


def _extract_backticked_tokens(text: str) -> tuple[str, ...]:
    tokens: list[str] = []
    token: list[str] = []
    inside_token = False
    for character in text:
        if character == "`":
            if inside_token:
                tokens.append("".join(token))
                token = []
            inside_token = not inside_token
            continue
        if inside_token:
            token.append(character)
    return tuple(tokens)


def _target_reader_terms(text: str) -> set[str]:
    terms = set(_extract_backticked_tokens(text))
    if "owning target product" in text:
        terms.add("owning target product")
    return terms


def _line_one_span() -> SourceSpan:
    return SourceSpan(line=1, column=1, end_line=1, end_column=1)
