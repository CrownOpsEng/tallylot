"""NEAR export adapter."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from crypto_reconciliation.adapters.sources.intake_support import match_intake_by_path_or_header, no_intake_route
from crypto_reconciliation.adapters.sources.wallet_record_support import WalletRecordSpec, wallet_record
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
from crypto_reconciliation.ports.intake_routing import IntakeFileFacts, IntakeRoute, IntakeRoutingRequest


class NearAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("near"),
        display_name="NEAR",
        version="1.0.0",
        capabilities=frozenset(
            {AdapterCapability.NORMALIZE, AdapterCapability.WALLET_INVENTORY, AdapterCapability.INTAKE_ROUTE}
        ),
        description="Normalizes NEAR transaction exports and extracts wallet identifiers.",
    )

    def match(self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> int:
        del raw_dir
        if "near" in source.lower():
            return 100
        if any(item.relative_path.endswith("_transactions.csv") for item in inventory):
            return 100
        return 0

    def match_intake(self, relative_path: str, facts: IntakeFileFacts) -> int:
        return match_intake_by_path_or_header(relative_path, facts, path_hints=("near",))

    def route_intake(self, request: IntakeRoutingRequest) -> IntakeRoute | None:
        return no_intake_route(request)

    def validate_profile_timezones(
        self,
        profile: SourceProfile,
    ) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
        rows_with_dates = sum(1 for item in profile.file_inventory if item.date_field)
        return {
            "status": "passed",
            "issue_count": 0,
            "rows_with_dates": rows_with_dates,
            "mode_counts": {"naive": rows_with_dates} if rows_with_dates else {},
        }, ()

    def extract_wallet_inventory(
        self,
        source: str,
        raw_dir: Path,
        profile: SourceProfile,
    ) -> tuple[tuple[WalletInventoryRecord, ...], tuple[IssueRecord, ...]]:
        del profile
        evidence: list[WalletInventoryRecord] = []
        for path in sorted(raw_dir.glob("*_transactions.csv")):
            identifier = path.name.removesuffix("_transactions.csv")
            evidence.append(
                wallet_record(
                    WalletRecordSpec(
                        source=source,
                        identifier_kind="near_account",
                        identifier_value=identifier,
                        network_scope="near",
                        controller="NearBlocks export",
                        account_label="",
                        evidence_kind="filename",
                        evidence_path=path.name,
                        confidence="high",
                    )
                )
            )
        return tuple(evidence), ()

    def normalize(self, profile: SourceProfile, raw_dir: Path) -> NormalizationResult:
        events: list[CanonicalEvent] = []
        wallet_inventory, _ = self.extract_wallet_inventory(str(profile.source), raw_dir, profile)
        for path in sorted(raw_dir.glob("*_transactions.csv")):
            for index, row in enumerate(_read_rows(path), start=2):
                timestamp = _parse_timestamp(_row_value(row, "Time", "Block Time"))
                tx_hash = _row_value(row, "Txn Hash")
                method = _row_value(row, "Method").lower()
                amount = Decimal(_row_value(row, "Deposit Value"))
                fee = Decimal(_row_value(row, "Txn Fee", default="0"))
                raw_row_ref = f"row:{index}"
                if method == "transfer":
                    events.append(
                        CanonicalEvent(
                            event_id=EventId(f"near:{path.name}:{raw_row_ref}"),
                            source=profile.source,
                            adapter_id=self.manifest.adapter_id,
                            account=str(profile.source),
                            wallet=str(profile.source),
                            timestamp=timestamp,
                            event_kind="Deposit",
                            description=f"Transfer into {profile.source} - {tx_hash}",
                            asset_in=AssetSymbol("NEAR"),
                            amount_in=amount - fee,
                            tx_hash=tx_hash,
                            raw_file=path.name,
                            raw_row_ref=raw_row_ref,
                        )
                    )
                elif method == "deposit_and_stake":
                    description = f"Stake NEAR - {tx_hash}"
                    events.append(
                        CanonicalEvent(
                            event_id=EventId(f"near:{path.name}:{raw_row_ref}:wallet"),
                            source=profile.source,
                            adapter_id=self.manifest.adapter_id,
                            account=str(profile.source),
                            wallet=str(profile.source),
                            timestamp=timestamp,
                            event_kind="Withdrawal",
                            description=description,
                            asset_out=AssetSymbol("NEAR"),
                            amount_out=amount,
                            fee_asset=AssetSymbol("NEAR"),
                            fee_amount=fee,
                            tx_hash=tx_hash,
                            raw_file=path.name,
                            raw_row_ref=raw_row_ref,
                        )
                    )
                    staking_source = f"{profile.source} - Staking"
                    events.append(
                        CanonicalEvent(
                            event_id=EventId(f"near:{path.name}:{raw_row_ref}:staking"),
                            source=SourceId(staking_source),
                            adapter_id=self.manifest.adapter_id,
                            account=staking_source,
                            wallet=staking_source,
                            timestamp=timestamp,
                            event_kind="Deposit",
                            description=description,
                            asset_in=AssetSymbol("NEAR"),
                            amount_in=amount,
                            tx_hash=tx_hash,
                            raw_file=path.name,
                            raw_row_ref=raw_row_ref,
                        )
                    )
        return NormalizationResult(
            canonical_events=tuple(events),
            canonical_balances=(),
            issues=(),
            reviews=(),
            wallet_inventory=wallet_inventory,
        )


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _row_value(row: dict[str, str], key: str, fallback: str = "", *, default: str = "") -> str:
    value = row.get(key, "")
    if value:
        return value.strip()
    if fallback:
        fallback_value = row.get(fallback, "")
        if fallback_value:
            return fallback_value.strip()
    return default


def _parse_timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC).replace(tzinfo=None)


ADAPTER = NearAdapter()
