"""Ledger Live location inventory helpers."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from tallylot.adapters.support import (
    location_id_from_parts,
    location_identifier_kind,
    location_issue,
    location_record,
    matching_file_paths,
    read_csv_rows,
)
from tallylot.adapters.support.locations import LocationIssueSpec, LocationRecordSpec
from tallylot.domain.captures import ProvenanceLocator
from tallylot.domain.issues import IssueRecord
from tallylot.domain.locations import LocationKind
from tallylot.ports.evidence import LocationInventoryRecord

HEADER_FIELDS = {"Account Name", "Account xpub", "Operation Date"}


def extract_location_inventory(
    source: str,
    raw_dir: Path,
) -> tuple[tuple[LocationInventoryRecord, ...], tuple[IssueRecord, ...]]:
    evidence: list[LocationInventoryRecord] = []
    issues: list[IssueRecord] = []
    identifiers_by_account: dict[str, set[str]] = defaultdict(set)
    for path in matching_file_paths(raw_dir):
        for row in read_csv_rows(path):
            account_label = (row.get("Account Name") or "").strip()
            identifier_value = (row.get("Account xpub") or "").strip()
            account_type = (row.get("Account Type") or "").strip().lower()
            if not identifier_value:
                continue
            kind = _ledger_identifier_kind(identifier_value, account_type)
            evidence.append(
                location_record(
                    LocationRecordSpec(
                        source=source,
                        location_id=location_id_from_parts(
                            source, account_label or identifier_value
                        ),
                        location_kind=LocationKind.ACCOUNT,
                        location_label=account_label or identifier_value,
                        identifier_kind=kind,
                        identifier_value=identifier_value,
                        network_scope=account_type or _network_scope_from_kind(kind),
                        controller="Ledger Live",
                        evidence_kind="csv_row",
                        evidence_provenance=ProvenanceLocator.from_reference_ref(
                            path.name
                        ),
                        confidence="high",
                    )
                )
            )
            identifiers_by_account[account_label].add(identifier_value)

    for account_label, identifiers in sorted(identifiers_by_account.items()):
        if len(identifiers) <= 1:
            continue
        issues.append(
            location_issue(
                LocationIssueSpec(
                    source=source,
                    adapter_id="ledger_live",
                    issue_kind="account_identifier_conflict",
                    message=f"Ledger Live account {account_label or 'blank'} maps to multiple identifiers.",
                )
            )
        )
    if not evidence:
        issues.append(
            location_issue(
                LocationIssueSpec(
                    source=source,
                    adapter_id="ledger_live",
                    issue_kind="missing_identifier",
                    message="No account identifier was found in the Ledger Live operations exports.",
                )
            )
        )
    return tuple(evidence), tuple(issues)


def _ledger_identifier_kind(identifier_value: str, account_type: str) -> str:
    if account_type == "bitcoin":
        return "btc_xpub"
    if account_type == "cardano":
        return "cardano_account_key"
    kind = location_identifier_kind(identifier_value)
    return kind if kind != "unknown" else "account_wallet"


def _network_scope_from_kind(identifier_kind: str) -> str:
    return {
        "btc_xpub": "bitcoin",
        "evm_address": "ethereum",
        "cardano_account_key": "cardano",
    }.get(identifier_kind, "")
