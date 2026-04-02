"""NEAR export adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from crypto_reconciliation.adapters.support import (
    IssueSpec,
    issue_record,
    match_intake_by_path_or_header,
    matching_file_paths,
    no_intake_route,
    passed_timezone_summary,
    read_csv_rows,
    wallet_record,
)
from crypto_reconciliation.adapters.support.drafts import (
    EconomicActivityDraft,
    classification,
    economic_leg,
    fee_leg,
    normalization_result_from_drafts,
)
from crypto_reconciliation.adapters.support.wallets import WalletRecordSpec
from crypto_reconciliation.domain.models import (
    AdapterCapability,
    AdapterManifest,
    FileInventoryEntry,
    IssueRecord,
    SourceProfile,
    WalletInventoryRecord,
)
from crypto_reconciliation.domain.types import AdapterId, JsonValue
from crypto_reconciliation.domain.value_objects import parse_decimal
from crypto_reconciliation.ports.adapters import NormalizationResult
from crypto_reconciliation.ports.intake_routing import IntakeFileFacts, IntakeRoute, IntakeRoutingRequest

SUPPORTED_METHODS = frozenset({"transfer", "deposit_and_stake"})


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
        return passed_timezone_summary(profile, mode="naive")

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
        drafts: list[EconomicActivityDraft] = []
        issues: list[IssueRecord] = []
        wallet_inventory, _ = self.extract_wallet_inventory(str(profile.source), raw_dir, profile)
        for path in matching_file_paths(raw_dir, pattern="*_transactions.csv"):
            for index, row in enumerate(read_csv_rows(path), start=2):
                raw_row_ref = f"row:{index}"
                timestamp = _parse_timestamp(_row_value(row, "Time", "Block Time"))
                tx_hash = _row_value(row, "Txn Hash")
                method = _row_value(row, "Method").lower()
                amount = parse_decimal(_row_value(row, "Deposit Value"))
                fee = parse_decimal(_row_value(row, "Txn Fee", default="0")) or Decimal("0")
                if timestamp is None:
                    issues.append(
                        _row_issue(
                            profile,
                            path.name,
                            raw_row_ref,
                            issue_id_suffix="invalid_timestamp",
                            message="NEAR transaction row is missing a supported block timestamp.",
                        )
                    )
                    continue
                if amount is None or amount <= Decimal("0"):
                    issues.append(
                        _row_issue(
                            profile,
                            path.name,
                            raw_row_ref,
                            issue_id_suffix="invalid_amount",
                            message="NEAR transaction row is missing a positive deposit value.",
                        )
                    )
                    continue
                if method == "transfer":
                    net_amount = amount - fee
                    if net_amount <= Decimal("0"):
                        issues.append(
                            _row_issue(
                                profile,
                                path.name,
                                raw_row_ref,
                                issue_id_suffix="non_positive_net_transfer",
                                message="NEAR transfer row has a non-positive net amount after fees.",
                            )
                        )
                        continue
                    drafts.append(
                        EconomicActivityDraft(
                            activity_id=f"near:{path.name}:{raw_row_ref}",
                            source=str(profile.source),
                            adapter_id="near",
                            account=str(profile.source),
                            wallet=str(profile.source),
                            timestamp=timestamp,
                            classification=classification(
                                normalized_category="deposit",
                                economic_kind="chain_transfer_in",
                                projection_type="Deposit",
                                journal_intent="funding_inflow",
                                tax_treatment_code="non_taxable_transfer_in",
                            ),
                            description=f"Transfer into {profile.source} - {tx_hash}",
                            raw_file=path.name,
                            raw_row_ref=raw_row_ref,
                            tx_hash=tx_hash,
                            provider_operation_key=method,
                            legs=(economic_leg(direction="in", asset="NEAR", amount=net_amount),),
                        )
                    )
                elif method == "deposit_and_stake":
                    description = f"Stake NEAR - {tx_hash}"
                    fee_legs = (fee_leg(asset="NEAR", amount=fee),) if fee > Decimal("0") else ()
                    drafts.append(
                        EconomicActivityDraft(
                            activity_id=f"near:{path.name}:{raw_row_ref}:wallet",
                            source=str(profile.source),
                            adapter_id="near",
                            account=str(profile.source),
                            wallet=str(profile.source),
                            timestamp=timestamp,
                            classification=classification(
                                normalized_category="withdrawal",
                                economic_kind="staking_transfer_out",
                                projection_type="Withdrawal",
                                journal_intent="funding_outflow",
                                tax_treatment_code="non_taxable_transfer_out",
                            ),
                            description=description,
                            raw_file=path.name,
                            raw_row_ref=raw_row_ref,
                            tx_hash=tx_hash,
                            provider_operation_key=method,
                            legs=(economic_leg(direction="out", asset="NEAR", amount=amount),),
                            fee_legs=fee_legs,
                        )
                    )
                    staking_source = f"{profile.source} - Staking"
                    drafts.append(
                        EconomicActivityDraft(
                            activity_id=f"near:{path.name}:{raw_row_ref}:staking",
                            source=staking_source,
                            adapter_id="near",
                            account=staking_source,
                            wallet=staking_source,
                            timestamp=timestamp,
                            classification=classification(
                                normalized_category="deposit",
                                economic_kind="staking_transfer_in",
                                projection_type="Deposit",
                                journal_intent="funding_inflow",
                                tax_treatment_code="non_taxable_transfer_in",
                            ),
                            description=description,
                            raw_file=path.name,
                            raw_row_ref=raw_row_ref,
                            tx_hash=tx_hash,
                            provider_operation_key=method,
                            legs=(economic_leg(direction="in", asset="NEAR", amount=amount),),
                        )
                    )
                else:
                    issues.append(
                        _row_issue(
                            profile,
                            path.name,
                            raw_row_ref,
                            issue_id_suffix=f"unsupported:{method or 'unknown'}",
                            message=f"Unsupported NEAR transaction method: {method or '<missing>'}",
                        )
                    )
        return normalization_result_from_drafts(
            drafts,
            issues=issues,
            wallet_inventory=wallet_inventory,
        )


def _row_value(row: dict[str, str], key: str, fallback: str = "", *, default: str = "") -> str:
    value = row.get(key, "")
    if value:
        return value.strip()
    if fallback:
        fallback_value = row.get(fallback, "")
        if fallback_value:
            return fallback_value.strip()
    return default


def _row_issue(
    profile: SourceProfile,
    raw_file: str,
    raw_row_ref: str,
    *,
    issue_id_suffix: str,
    message: str,
) -> IssueRecord:
    return issue_record(
        IssueSpec(
            issue_id=f"near:{raw_file}:{raw_row_ref}:{issue_id_suffix}",
            source=str(profile.source),
            adapter_id="near",
            kind="unsupported_row",
            message=message,
            raw_file=raw_file,
            raw_row_ref=raw_row_ref,
        )
    )


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC).replace(tzinfo=None)
    except ValueError:
        return None


ADAPTER = NearAdapter()
