"""Location inventory aggregation rules."""

from __future__ import annotations

from collections import defaultdict

from tallylot.domain.captures import provenance_locator_from_row


def summarize_location_inventory(
    evidence_rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    identifier_kinds_by_identifier: dict[str, set[str]] = defaultdict(set)
    issue_rows: list[dict[str, str]] = []

    for row in evidence_rows:
        grouped[row["location_id"]].append(row)
        identifier_kinds_by_identifier[row["normalized_identifier"]].add(
            row["identifier_kind"]
        )
        evidence_path = _evidence_path(row)
        if not evidence_path:
            issue_rows.append(
                {
                    "source": row["source"],
                    "capture_uid": row["capture_uid"],
                    "location_id": row["location_id"],
                    "issue_kind": "missing_evidence_path",
                    "message": "Location evidence rows must retain a source-relative evidence path.",
                    "evidence_path": "",
                }
            )

    inventory_rows: list[dict[str, str]] = []
    for location_id, rows in sorted(grouped.items()):
        primary = rows[0]
        identifier_kind = primary["identifier_kind"]
        status = (
            "needs_linked_evidence" if identifier_kind == "address_alias" else "ready"
        )
        notes = sorted({row["note"] for row in rows if row["note"]})
        inventory_rows.append(
            {
                "location_id": location_id,
                "location_kind": primary["location_kind"],
                "location_label": primary["location_label"],
                "parent_location_id": primary["parent_location_id"],
                "location_path": primary["location_path"],
                "identifier_kind": identifier_kind,
                "normalized_identifier": primary["normalized_identifier"],
                "display_identifier": primary["display_identifier"],
                "network_scopes": "; ".join(
                    sorted(
                        {row["network_scope"] for row in rows if row["network_scope"]}
                    )
                ),
                "source_labels": "; ".join(
                    sorted({row["source"] for row in rows if row["source"]})
                ),
                "controller_labels": "; ".join(
                    sorted({row["controller"] for row in rows if row["controller"]})
                ),
                "parent_location_labels": "; ".join(
                    sorted(
                        {
                            row["parent_location_label"]
                            for row in rows
                            if row["parent_location_label"]
                        }
                    )
                ),
                "evidence_count": str(len(rows)),
                "primary_evidence_path": _evidence_path(primary),
                "status": status,
                "notes": "; ".join(notes),
            }
        )

    for normalized_identifier, identifier_kinds in sorted(
        identifier_kinds_by_identifier.items()
    ):
        if len(identifier_kinds) <= 1:
            continue
        issue_rows.append(
            {
                "source": "",
                "capture_uid": "",
                "location_id": "",
                "issue_kind": "identifier_kind_conflict",
                "message": (
                    "The same identifier was classified under multiple kinds: "
                    + ", ".join(sorted(identifier_kinds))
                ),
                "evidence_path": normalized_identifier,
            }
        )

    return inventory_rows, issue_rows


def _evidence_path(row: dict[str, str]) -> str:
    evidence_locator = provenance_locator_from_row(row, prefix="evidence")
    if evidence_locator is None:
        return ""
    return evidence_locator.to_reference_ref()
