from __future__ import annotations

from . import contract_lock_support as support
from ._common import build_rule

CONTRACT_LOCK_MATRIX_RULES = (
    build_rule(
        "contract_lock.bridge_cutover_matrix_matches_declared_reader_inventory",
        "docs/concepts/bridge-to-target-mapping.md",
        lambda: [
            (_ for _ in ()).throw(
                AssertionError("canonical current-reader inventory drifted")
            )
            for condition in support.reader_inventory_checks()
            if condition
        ],
    ),
    build_rule(
        "contract_lock.bridge_cutover_matrix_rows_are_complete",
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
                AssertionError(
                    f"bridge row is incomplete or uses placeholder gate text: {row['Current bridge surface']}"
                )
            )
            for row in support.bridge_matrix_rows()
            if any(
                not row[column]
                for column in (
                    "Target authoritative product(s)",
                    "Derived compatibility view",
                    "Derived compatibility sidecar",
                    "Current readers",
                    "Target readers after cutover",
                    "Cutover gate",
                    "Retirement gate",
                )
            )
            or support.placeholder_text(row["Cutover gate"])
            or support.placeholder_text(row["Retirement gate"])
        ],
    ),
    build_rule(
        "contract_lock.bridge_cutover_matrix_target_readers_name_capability_and_authoritative_product",
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
                    support.canonical_text_value(
                        clause.split(" reading ", 1)[0]
                        if " reading " in clause
                        else clause.split(" from ", 1)[0]
                    ).casefold()
                    in frozenset(
                        item.casefold()
                        for item in support.BRIDGE_MATRIX_SPEC.target_reader_placeholder_capabilities
                    )
                    or support.placeholder_text(clause)
                    or not (
                        (
                            set(
                                support.extract_backticked_tokens(
                                    clause.split(" reading ", 1)[1]
                                    if " reading " in clause
                                    else clause.split(" from ", 1)[1]
                                )
                            )
                            | (
                                {"owning target product"}
                                if "owning target product"
                                in (
                                    clause.split(" reading ", 1)[1]
                                    if " reading " in clause
                                    else clause.split(" from ", 1)[1]
                                )
                                else set[str]()
                            )
                        )
                        & authoritative_terms
                    )
                    for clause in support.split_matrix_clauses(
                        row["Target readers after cutover"]
                    )
                )
            )
        ],
    ),
)
