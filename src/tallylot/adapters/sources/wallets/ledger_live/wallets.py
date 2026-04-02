"""Ledger Live wallet inventory helpers."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from tallylot.adapters.support import (
    matching_file_paths,
    read_csv_rows,
    wallet_identifier_kind,
    wallet_issue,
    wallet_record,
)
from tallylot.adapters.support.wallets import WalletIssueSpec, WalletRecordSpec
from tallylot.domain.issues import IssueRecord
from tallylot.ports.evidence import WalletInventoryRecord

HEADER_FIELDS = {"Account Name", "Account xpub", "Operation Date"}


def extract_wallet_inventory(
    source: str,
    raw_dir: Path,
) -> tuple[tuple[WalletInventoryRecord, ...], tuple[IssueRecord, ...]]:
    evidence: list[WalletInventoryRecord] = []
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
                wallet_record(
                    WalletRecordSpec(
                        source=source,
                        identifier_kind=kind,
                        identifier_value=identifier_value,
                        network_scope=account_type or _network_scope_from_kind(kind),
                        controller="Ledger Live",
                        account_label=account_label,
                        evidence_kind="csv_row",
                        evidence_path=path.name,
                        confidence="high",
                    )
                )
            )
            identifiers_by_account[account_label].add(identifier_value)

    for account_label, identifiers in sorted(identifiers_by_account.items()):
        if len(identifiers) <= 1:
            continue
        issues.append(
            wallet_issue(
                WalletIssueSpec(
                    source=source,
                    adapter_id="ledger_live",
                    issue_kind="account_identifier_conflict",
                    message=f"Ledger Live account {account_label or 'blank'} maps to multiple identifiers.",
                )
            )
        )
    if not evidence:
        issues.append(
            wallet_issue(
                WalletIssueSpec(
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
    kind = wallet_identifier_kind(identifier_value)
    return kind if kind != "unknown" else "account_wallet"


def _network_scope_from_kind(identifier_kind: str) -> str:
    return {
        "btc_xpub": "bitcoin",
        "evm_address": "ethereum",
        "cardano_account_key": "cardano",
    }.get(identifier_kind, "")
