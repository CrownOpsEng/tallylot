from __future__ import annotations

from . import forward_contracts_support as support
from ._common import build_rule


def _target_reader_clause_invalid(clause: str, authoritative_terms: set[str]) -> bool:
    connector = " reading " if " reading " in clause else " from "
    if connector not in clause:
        return True
    capability = support.canonical_text_value(clause.split(connector, 1)[0]).casefold()
    if capability in support.BRIDGE_MATRIX_TARGET_READER_PLACEHOLDER_CAPABILITIES:
        return True
    if support.placeholder_text(clause):
        return True
    target_terms = set(support.extract_backticked_tokens(clause.split(connector, 1)[1]))
    if "owning target product" in clause.split(connector, 1)[1]:
        target_terms.add("owning target product")
    return not (target_terms & authoritative_terms)


FORWARD_CONTRACTS_MATRIX_RULES = (
    build_rule(
        "forward_contracts.bridge_cutover_matrix_rows_match_declared_inventory",
        "docs/concepts/bridge-to-target-mapping.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError("bridge cutover matrix row inventory drifted")
            )
            for condition in (
                tuple(
                    support.canonical_text_value(row["Current bridge surface"])
                    for row in support.bridge_matrix_rows()
                )
                != support.EXPECTED_MATRIX_ROWS,
            )
            if condition
        ]
        + [
            (_ for _ in ()).throw(
                AssertionError("canonical current-reader inventory drifted")
            )
            for condition in support.reader_inventory_checks()
            if condition
        ],
    ),
    build_rule(
        "forward_contracts.bridge_cutover_matrix_rows_are_complete_and_non_placeholder",
        "docs/concepts/bridge-to-target-mapping.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(
                    f"bridge row is incomplete or uses placeholder gate text: {row['Current bridge surface']}"
                )
            )
            for row in support.bridge_matrix_rows()
            if any(
                not row[column]
                for column in support.BRIDGE_MATRIX_REQUIRED_NONEMPTY_COLUMNS
            )
            or support.placeholder_text(row["Cutover gate"])
            or support.placeholder_text(row["Retirement gate"])
        ],
    ),
    build_rule(
        "forward_contracts.bridge_cutover_matrix_current_reader_labels_are_canonical",
        "docs/concepts/bridge-to-target-mapping.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(
                    f"current readers must use canonical backticked inventory labels for {row['Current bridge surface']}"
                )
            )
            for row in support.bridge_matrix_rows()
            for clause in support.split_matrix_clauses(row["Current readers"])
            if not clause.startswith("`")
            or not clause.endswith("`")
            or support.canonical_text_value(clause)
            not in frozenset(support.reader_inventory())
        ],
    ),
    build_rule(
        "forward_contracts.bridge_cutover_matrix_target_readers_name_capability_and_authority",
        "docs/concepts/bridge-to-target-mapping.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(
                    f"target readers do not name a concrete capability and authoritative product for {row['Current bridge surface']}"
                )
            )
            for row in support.bridge_matrix_rows()
            if (
                not (
                    authoritative_terms := (
                        set(
                            support.extract_backticked_tokens(
                                row["Target authoritative product(s)"]
                            )
                        )
                        | (
                            {"owning target product"}
                            if "owning target product"
                            in row["Target authoritative product(s)"]
                            else set[str]()
                        )
                    )
                )
                or any(
                    _target_reader_clause_invalid(clause, authoritative_terms)
                    for clause in support.split_matrix_clauses(
                        row["Target readers after cutover"]
                    )
                )
            )
        ],
    ),
    build_rule(
        "forward_contracts.bridge_cutover_matrix_compatibility_shapes_and_surface_names_are_canonical",
        "docs/concepts/bridge-to-target-mapping.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError(
                    f"compatibility shape or surface naming drifted in matrix row {row['Current bridge surface']}"
                )
            )
            for row in support.bridge_matrix_rows()
            if any(
                fragment in cell.casefold()
                for cell in row.values()
                for fragment in support.BRIDGE_MATRIX_BANNED_FRAGMENTS
            )
            or any(
                support.canonical_text_value(cell).casefold()
                not in support.BRIDGE_MATRIX_ALLOWED_SHAPES
                for cell in (
                    row["Derived compatibility view"],
                    row["Derived compatibility sidecar"],
                )
                if "compatibility" in support.canonical_text_value(cell).casefold()
            )
        ],
    ),
)
