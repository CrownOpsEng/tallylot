"""Ledger Live adapter."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from crypto_reconciliation.adapters.support import (
    match_intake_by_path_or_header,
    matching_file_paths,
    no_intake_route,
    passed_timezone_summary,
    read_csv_rows,
    wallet_identifier_kind,
    wallet_issue,
    wallet_record,
)
from crypto_reconciliation.adapters.support.drafts import (
    EconomicActivityDraft,
    classification,
    economic_leg,
    fee_leg,
    normalization_result_from_drafts,
)
from crypto_reconciliation.adapters.support.wallets import WalletIssueSpec, WalletRecordSpec
from crypto_reconciliation.domain.models import (
    AdapterCapability,
    AdapterManifest,
    FileInventoryEntry,
    IssueRecord,
    SourceProfile,
    WalletInventoryRecord,
)
from crypto_reconciliation.domain.types import AdapterId, JsonValue
from crypto_reconciliation.ports.adapters import NormalizationResult
from crypto_reconciliation.ports.intake_routing import IntakeFileFacts, IntakeRoute, IntakeRoutingRequest

HEADER_FIELDS = {"Account Name", "Account xpub", "Operation Date"}
SUPPORTED_OPERATION_GROUPS = frozenset({"IN+OUT", "IN+OUT+FEES"})


class LedgerLiveAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("ledger_live"),
        display_name="Ledger Live",
        version="1.0.0",
        capabilities=frozenset(
            {AdapterCapability.NORMALIZE, AdapterCapability.WALLET_INVENTORY, AdapterCapability.INTAKE_ROUTE}
        ),
        description="Normalizes Ledger Live operations and extracts wallet identifiers.",
    )

    def match(self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> int:
        del raw_dir
        if "ledger" in source.lower():
            return 100
        if any(HEADER_FIELDS.issubset(set(item.header)) for item in inventory if item.header):
            return 100
        return 0

    def match_intake(self, relative_path: str, facts: IntakeFileFacts) -> int:
        return match_intake_by_path_or_header(relative_path, facts, path_hints=("ledger",))

    def route_intake(self, request: IntakeRoutingRequest) -> IntakeRoute | None:
        return no_intake_route(request)

    def validate_profile_timezones(
        self,
        profile: SourceProfile,
    ) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
        return passed_timezone_summary(profile, mode="value_utc")

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
                        adapter_id=str(self.manifest.adapter_id),
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
                        adapter_id=str(self.manifest.adapter_id),
                        issue_kind="missing_identifier",
                        message="No account identifier was found in the Ledger Live operations exports.",
                    )
                )
            )
        return tuple(evidence), tuple(issues)

    def normalize(self, profile: SourceProfile, raw_dir: Path) -> NormalizationResult:
        drafts: list[EconomicActivityDraft] = []
        operations_by_hash: dict[str, list[tuple[str, dict[str, str]]]] = defaultdict(list)
        for path in matching_file_paths(raw_dir):
            for index, row in enumerate(read_csv_rows(path), start=2):
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
            fee_legs = (
                (fee_leg(asset=fee_asset.strip().upper(), amount=fee_amount),) if fee_amount > 0 and fee_asset else ()
            )
            drafts.append(
                EconomicActivityDraft(
                    activity_id=f"ledger_live:{raw_file}:{operation_hash}",
                    source=str(profile.source),
                    adapter_id="ledger_live",
                    account=account_label,
                    wallet=account_label,
                    timestamp=timestamp,
                    classification=classification(
                        economic_kind="asset_swap",
                        projection_type="Trade",
                        journal_intent="asset_exchange",
                        tax_treatment_code="capital_exchange",
                    ),
                    description=account_label,
                    raw_file=raw_file,
                    raw_row_ref=raw_row_ref,
                    tx_hash=operation_hash,
                    provider_operation_key="ledger_live_swap",
                    operation_group_id=operation_hash,
                    legs=(
                        economic_leg(
                            direction="in",
                            asset=(inbound.get("Currency Ticker") or "").strip().upper(),
                            amount=Decimal((inbound.get("Operation Amount") or "0").strip()),
                        ),
                        economic_leg(
                            direction="out",
                            asset=(outbound.get("Currency Ticker") or "").strip().upper(),
                            amount=Decimal((outbound.get("Operation Amount") or "0").strip()),
                        ),
                    ),
                    fee_legs=fee_legs,
                )
            )
        wallet_inventory, _ = self.extract_wallet_inventory(str(profile.source), raw_dir, profile)
        return normalization_result_from_drafts(
            drafts,
            wallet_inventory=wallet_inventory,
        )


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
