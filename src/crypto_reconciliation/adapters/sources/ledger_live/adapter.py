"""Ledger Live adapter."""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from crypto_reconciliation.adapters.sources.wallet_record_support import (
    AdapterIssueSpec,
    WalletRecordSpec,
    adapter_issue,
    wallet_identifier_kind,
    wallet_record,
)
from crypto_reconciliation.domain.models import (
    AdapterCapability,
    AdapterManifest,
    CanonicalEvent,
    FileInventoryEntry,
    IssueRecord,
    SourceProfile,
    WalletInventoryRecord,
)
from crypto_reconciliation.domain.types import AdapterId, AssetSymbol, EventId, JsonValue, SourceId
from crypto_reconciliation.ports.adapters import NormalizationResult

HEADER_FIELDS = {"Account Name", "Account xpub", "Operation Date"}


class LedgerLiveAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("ledger_live"),
        display_name="Ledger Live",
        version="1.0.0",
        capabilities=frozenset({AdapterCapability.NORMALIZE, AdapterCapability.WALLET_INVENTORY}),
        description="Normalizes Ledger Live operations and extracts wallet identifiers.",
    )

    def match(self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> int:
        del raw_dir
        if "ledger" in source.lower():
            return 100
        if any(HEADER_FIELDS.issubset(set(item.header)) for item in inventory if item.header):
            return 100
        return 0

    def validate_profile_timezones(
        self,
        profile: SourceProfile,
    ) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
        rows_with_dates = sum(1 for item in profile.file_inventory if item.date_field)
        return {
            "status": "passed",
            "issue_count": 0,
            "rows_with_dates": rows_with_dates,
            "mode_counts": {"value_utc": rows_with_dates} if rows_with_dates else {},
        }, ()

    def extract_wallet_inventory(
        self,
        source: str,
        raw_dir: Path,
        profile: SourceProfile,
    ) -> tuple[tuple[WalletInventoryRecord, ...], tuple[IssueRecord, ...]]:
        del profile
        evidence: list[WalletInventoryRecord] = []
        issues: list[IssueRecord] = []
        identifiers_by_account: dict[str, set[str]] = defaultdict(set)
        for path in _csv_paths(raw_dir):
            for row in _read_rows(path):
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
                adapter_issue(
                    AdapterIssueSpec(
                        source=source,
                        adapter_id=str(self.manifest.adapter_id),
                        issue_kind="account_identifier_conflict",
                        message=f"Ledger Live account {account_label or 'blank'} maps to multiple identifiers.",
                    )
                )
            )
        if not evidence:
            issues.append(
                adapter_issue(
                    AdapterIssueSpec(
                        source=source,
                        adapter_id=str(self.manifest.adapter_id),
                        issue_kind="missing_identifier",
                        message="No account identifier was found in the Ledger Live operations exports.",
                    )
                )
            )
        return tuple(evidence), tuple(issues)

    def normalize(self, profile: SourceProfile, raw_dir: Path) -> NormalizationResult:
        events: list[CanonicalEvent] = []
        operations_by_hash: dict[str, list[tuple[str, dict[str, str]]]] = defaultdict(list)
        for path in _csv_paths(raw_dir):
            for index, row in enumerate(_read_rows(path), start=2):
                operation_hash = (row.get("Operation Hash") or row.get("Transaction ID") or "").strip()
                if not operation_hash:
                    continue
                operations_by_hash[operation_hash].append((f"{path.name}:row:{index}", row))

        for operation_hash, grouped_rows in sorted(operations_by_hash.items()):
            type_map = {row.get("Operation Type", "").strip().upper(): row for _, row in grouped_rows}
            inbound = type_map.get("IN")
            outbound = type_map.get("OUT")
            fee_row = type_map.get("FEES")
            if inbound is None or outbound is None:
                continue
            timestamp = _parse_timestamp((inbound.get("Operation Date") or "").strip())
            account_label = (inbound.get("Account Name") or "").strip()
            raw_file = grouped_rows[0][0].split(":row:", maxsplit=1)[0]
            raw_row_ref = ";".join(f"{raw_file}:{ref.split(':', maxsplit=1)[1]}" for ref, _ in grouped_rows)
            fee_amount = Decimal((fee_row or {}).get("Operation Amount") or "0")
            fee_asset = (fee_row or outbound).get("Currency Ticker") or ""
            events.append(
                CanonicalEvent(
                    event_id=EventId(f"ledger_live:{raw_file}:{operation_hash}"),
                    source=SourceId(str(profile.source)),
                    adapter_id=self.manifest.adapter_id,
                    account=account_label,
                    wallet=account_label,
                    timestamp=timestamp,
                    event_kind="Trade",
                    description=account_label,
                    asset_in=AssetSymbol((inbound.get("Currency Ticker") or "").strip().upper()),
                    amount_in=Decimal((inbound.get("Operation Amount") or "0").strip()),
                    asset_out=AssetSymbol((outbound.get("Currency Ticker") or "").strip().upper()),
                    amount_out=Decimal((outbound.get("Operation Amount") or "0").strip()),
                    fee_asset=AssetSymbol(fee_asset.strip().upper()) if fee_amount > 0 and fee_asset else None,
                    fee_amount=fee_amount if fee_amount > 0 else None,
                    tx_hash=operation_hash,
                    raw_file=raw_file,
                    raw_row_ref=raw_row_ref,
                    render_type="Trade",
                    render_exchange=str(profile.source),
                    render_comment=account_label,
                    render_comment_mode="exact",
                    render_tx_id=operation_hash,
                    render_tx_id_mode="exact",
                    render_allowed_types="Trade",
                    render_match_window_seconds="0",
                    render_fee_tolerance="0.00000000",
                    render_notes="ledger_live_grouped_trade",
                )
            )
        wallet_inventory, _ = self.extract_wallet_inventory(str(profile.source), raw_dir, profile)
        return NormalizationResult(
            canonical_events=tuple(events),
            canonical_balances=(),
            issues=(),
            reviews=(),
            wallet_inventory=wallet_inventory,
        )


def _csv_paths(raw_dir: Path) -> tuple[Path, ...]:
    return tuple(sorted(raw_dir.rglob("*.csv")))


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


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


def _parse_timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=UTC).replace(tzinfo=None)


ADAPTER = LedgerLiveAdapter()
