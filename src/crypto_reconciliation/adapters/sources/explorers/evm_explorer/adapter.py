"""EVM explorer adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from crypto_reconciliation.adapters.support import (
    EVM_ADDRESS_PATTERN,
    IssueSpec,
    issue_record,
    match_intake_by_path_or_header,
    matching_file_paths,
    no_intake_route,
    passed_timezone_summary,
    read_csv_rows,
    wallet_issue,
    wallet_record,
)
from crypto_reconciliation.adapters.support.drafts import (
    EconomicActivityDraft,
    classification,
    economic_leg,
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

TRANSACTION_HEADER_FIELDS = {"Transaction Hash", "DateTime (UTC)"}


class EvmExplorerAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("evm_explorer"),
        display_name="EVM Explorer",
        version="1.0.0",
        capabilities=frozenset(
            {AdapterCapability.NORMALIZE, AdapterCapability.WALLET_INVENTORY, AdapterCapability.INTAKE_ROUTE}
        ),
        description="Normalizes EVM explorer exports and extracts owned EVM addresses.",
    )

    def match(self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> int:
        del raw_dir
        lower_source = source.lower()
        if "explorer" in lower_source or any(chain in lower_source for chain in ("bsc", "ethereum", "polygon", "arb")):
            return 100
        if any(TRANSACTION_HEADER_FIELDS.issubset(set(item.header)) for item in inventory if item.header):
            return 75
        if any("explorer" in item.relative_path.lower() for item in inventory):
            return 75
        return 0

    def match_intake(self, relative_path: str, facts: IntakeFileFacts) -> int:
        return match_intake_by_path_or_header(
            relative_path,
            facts,
            path_hints=("etherscan", "arbiscan", "polygonscan", "bsc", "evm"),
        )

    def route_intake(self, request: IntakeRoutingRequest) -> IntakeRoute | None:
        return no_intake_route(request)

    def validate_profile_timezones(
        self,
        profile: SourceProfile,
    ) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
        return passed_timezone_summary(profile, mode="header_utc")

    def extract_wallet_inventory(
        self,
        source: str,
        raw_dir: Path,
        profile: SourceProfile,
    ) -> tuple[tuple[WalletInventoryRecord, ...], tuple[IssueRecord, ...]]:
        del profile
        addresses = sorted(_owned_addresses(raw_dir))
        issues: list[IssueRecord] = []
        if not addresses:
            return (), (
                wallet_issue(
                    WalletIssueSpec(
                        source=source,
                        adapter_id=str(self.manifest.adapter_id),
                        issue_kind="missing_identifier",
                        message="No EVM address could be extracted from the profiled explorer capture.",
                    )
                ),
            )
        if len(addresses) > 1:
            issues.append(
                wallet_issue(
                    WalletIssueSpec(
                        source=source,
                        adapter_id=str(self.manifest.adapter_id),
                        issue_kind="multiple_primary_identifiers",
                        message="The profiled explorer capture exposed more than one owned EVM address.",
                    )
                )
            )
        evidence = tuple(
            wallet_record(
                WalletRecordSpec(
                    source=source,
                    identifier_kind="evm_address",
                    identifier_value=address,
                    network_scope=_network_scope(source),
                    controller="Explorer export",
                    account_label="",
                    evidence_kind="filename",
                    evidence_path=_evidence_filename(raw_dir, address),
                    confidence="high",
                )
            )
            for address in addresses
        )
        return evidence, tuple(issues)

    def normalize(self, profile: SourceProfile, raw_dir: Path) -> NormalizationResult:
        issues: list[IssueRecord] = []
        drafts: list[EconomicActivityDraft] = []
        wallet_inventory, wallet_issues = self.extract_wallet_inventory(str(profile.source), raw_dir, profile)
        owned_addresses = _owned_addresses(raw_dir)
        suspicious_hashes = _suspicious_nft_hashes(raw_dir, owned_addresses)
        for path in matching_file_paths(raw_dir):
            if "nft" in path.name.lower():
                continue
            for index, row in enumerate(read_csv_rows(path), start=2):
                tx_hash = (row.get("Transaction Hash") or "").strip()
                if not tx_hash:
                    continue
                if tx_hash in suspicious_hashes:
                    issues.append(
                        issue_record(
                            IssueSpec(
                                source=str(profile.source),
                                adapter_id=str(self.manifest.adapter_id),
                                issue_id=f"evm_explorer:{path.name}:{tx_hash}",
                                severity="medium",
                                kind="review_required",
                                message=(
                                    f"{profile.source} received suspicious NFT airdrop "
                                    f"{suspicious_hashes[tx_hash]} in tx {tx_hash}; keep it in review instead of "
                                    "auto-importing it as an economic deposit."
                                ),
                                raw_file=path.name,
                                raw_row_ref=f"{path.name}:row:{index};{suspicious_hashes[tx_hash + ':ref']}",
                                status="needs_review",
                            )
                        )
                    )
                    continue
                amount_in = Decimal((row.get("Value_IN(BNB)") or "0").strip())
                if amount_in <= Decimal("0"):
                    continue
                timestamp = _parse_utc_timestamp((row.get("DateTime (UTC)") or "").strip())
                drafts.append(
                    EconomicActivityDraft(
                        activity_id=f"evm_explorer:{path.name}:{tx_hash}",
                        source=str(profile.source),
                        adapter_id="evm_explorer",
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
                        description=f"Transfer - {tx_hash}",
                        raw_file=path.name,
                        raw_row_ref=f"{path.name}:row:{index}",
                        tx_hash=tx_hash,
                        provider_operation_key="explorer_transfer_in",
                        legs=(economic_leg(direction="in", asset="BNB", amount=amount_in),),
                    )
                )
        return normalization_result_from_drafts(
            drafts,
            issues=(*issues, *wallet_issues),
            wallet_inventory=wallet_inventory,
        )


def _owned_addresses(raw_dir: Path) -> set[str]:
    addresses: set[str] = set()
    for path in matching_file_paths(raw_dir):
        for match in EVM_ADDRESS_PATTERN.finditer(path.name):
            addresses.add(match.group(0).lower())
    if addresses:
        return addresses
    for path in matching_file_paths(raw_dir):
        rows = read_csv_rows(path)
        to_addresses = {
            (row.get("To") or "").strip().lower()
            for row in rows
            if EVM_ADDRESS_PATTERN.fullmatch((row.get("To") or "").strip())
        }
        if len(to_addresses) == 1:
            return to_addresses
    return set()


def _network_scope(source: str) -> str:
    lower_source = source.lower()
    if "bsc" in lower_source:
        return "bsc"
    if "polygon" in lower_source:
        return "polygon"
    if "arb" in lower_source:
        return "arbitrum"
    return "ethereum"


def _evidence_filename(raw_dir: Path, address: str) -> str:
    for path in matching_file_paths(raw_dir):
        if address in path.name.lower():
            return path.name
    first = matching_file_paths(raw_dir)
    return first[0].name if first else ""


def _suspicious_nft_hashes(raw_dir: Path, owned_addresses: set[str]) -> dict[str, str]:
    suspicious: dict[str, str] = {}
    for path in matching_file_paths(raw_dir, pattern="*nft*.csv"):
        for index, row in enumerate(read_csv_rows(path), start=2):
            to_address = (row.get("To") or "").strip().lower()
            token_name = (row.get("TokenName") or "").strip()
            tx_hash = (row.get("Transaction Hash") or "").strip()
            if to_address not in owned_addresses or not token_name.startswith("$"):
                continue
            suspicious[tx_hash] = token_name
            suspicious[f"{tx_hash}:ref"] = f"{path.name}:row:{index}"
    return suspicious


def _parse_utc_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(f"{value}+00:00").astimezone(UTC).replace(tzinfo=None)


ADAPTER = EvmExplorerAdapter()
