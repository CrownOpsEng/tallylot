"""Wallet inventory aggregation rules."""

from __future__ import annotations

from collections import defaultdict


def summarize_wallet_inventory(
    evidence_rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    identifier_kinds_by_identifier: dict[str, set[str]] = defaultdict(set)
    issue_rows: list[dict[str, str]] = []

    for row in evidence_rows:
        grouped[row["wallet_id"]].append(row)
        identifier_kinds_by_identifier[row["normalized_identifier"]].add(row["identifier_kind"])
        if not row["evidence_path"]:
            issue_rows.append(
                {
                    "source": row["source"],
                    "capture_path": row["capture_path"],
                    "wallet_id": row["wallet_id"],
                    "issue_kind": "missing_evidence_path",
                    "message": "Wallet evidence rows must retain a source-relative evidence path.",
                    "evidence_path": "",
                }
            )

    inventory_rows: list[dict[str, str]] = []
    for wallet_id, rows in sorted(grouped.items()):
        primary = rows[0]
        identifier_kind = primary["identifier_kind"]
        status = "needs_linked_evidence" if identifier_kind == "address_alias" else "ready"
        notes = sorted({row["note"] for row in rows if row["note"]})
        inventory_rows.append(
            {
                "wallet_id": wallet_id,
                "identifier_kind": identifier_kind,
                "normalized_identifier": primary["normalized_identifier"],
                "display_identifier": primary["display_identifier"],
                "network_scopes": "; ".join(sorted({row["network_scope"] for row in rows if row["network_scope"]})),
                "source_labels": "; ".join(sorted({row["source"] for row in rows if row["source"]})),
                "controller_labels": "; ".join(sorted({row["controller"] for row in rows if row["controller"]})),
                "account_labels": "; ".join(sorted({row["account_label"] for row in rows if row["account_label"]})),
                "evidence_count": str(len(rows)),
                "primary_evidence_path": primary["evidence_path"],
                "status": status,
                "notes": "; ".join(notes),
            }
        )

    for normalized_identifier, identifier_kinds in sorted(identifier_kinds_by_identifier.items()):
        if len(identifier_kinds) <= 1:
            continue
        issue_rows.append(
            {
                "source": "",
                "capture_path": "",
                "wallet_id": "",
                "issue_kind": "identifier_kind_conflict",
                "message": (
                    "The same identifier was classified under multiple kinds: " + ", ".join(sorted(identifier_kinds))
                ),
                "evidence_path": normalized_identifier,
            }
        )

    return inventory_rows, issue_rows
