"""GTrade report adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from crypto_reconciliation.adapters.sources.csv_support import matching_file_paths, read_csv_rows
from crypto_reconciliation.adapters.sources.intake_support import match_intake_by_path_or_header, no_intake_route
from crypto_reconciliation.adapters.sources.wallet_record_support import (
    AdapterIssueSpec,
    WalletRecordSpec,
    adapter_issue,
    wallet_record,
)
from crypto_reconciliation.domain.models import (
    AdapterCapability,
    AdapterManifest,
    FileInventoryEntry,
    IssueRecord,
    NormalizedTransaction,
    SourceProfile,
    TransactionCategory,
    WalletInventoryRecord,
)
from crypto_reconciliation.domain.types import AdapterId, AssetSymbol, JsonValue, TransactionId
from crypto_reconciliation.ports.adapters import NormalizationResult
from crypto_reconciliation.ports.intake_routing import IntakeFileFacts, IntakeRoute, IntakeRoutingRequest


class GTradeAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("gtrade"),
        display_name="GTrade",
        version="1.0.0",
        capabilities=frozenset(
            {AdapterCapability.NORMALIZE, AdapterCapability.WALLET_INVENTORY, AdapterCapability.INTAKE_ROUTE}
        ),
        description="Normalizes GTrade realized PnL reports and extracts trader aliases.",
    )

    def match(self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> int:
        del raw_dir
        if "gtrade" in source.lower():
            return 100
        if any(item.header[:3] == ("DATE", "PAIR", "ADDR") for item in inventory if item.header):
            return 100
        return 0

    def match_intake(self, relative_path: str, facts: IntakeFileFacts) -> int:
        return match_intake_by_path_or_header(
            relative_path,
            facts,
            path_hints=("gtrade",),
        )

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
            "mode_counts": {"date_only": rows_with_dates} if rows_with_dates else {},
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
        for path in matching_file_paths(raw_dir):
            for row in read_csv_rows(path):
                alias = (row.get("ADDR") or "").strip().lower()
                if not alias:
                    continue
                evidence.append(
                    wallet_record(
                        WalletRecordSpec(
                            source=source,
                            identifier_kind="address_alias",
                            identifier_value=alias,
                            network_scope="polygon",
                            controller="GTrade report",
                            account_label="",
                            evidence_kind="csv_row",
                            evidence_path=path.name,
                            confidence="medium",
                            note="The report exposes a truncated trader alias instead of a full on-chain address.",
                        )
                    )
                )
                issues.append(
                    adapter_issue(
                        AdapterIssueSpec(
                            source=source,
                            adapter_id=str(self.manifest.adapter_id),
                            issue_kind="partial_identifier_only",
                            message=(
                                "GTrade evidence exposes only a truncated address alias; keep companion explorer "
                                "evidence linked in the wallet inventory."
                            ),
                            wallet_id=f"address_alias:{alias}",
                            raw_file=path.name,
                        )
                    )
                )
                break
        if not evidence:
            issues.append(
                adapter_issue(
                    AdapterIssueSpec(
                        source=source,
                        adapter_id=str(self.manifest.adapter_id),
                        issue_kind="missing_identifier",
                        message="No address alias was found in the GTrade report.",
                    )
                )
            )
        return tuple(evidence), tuple(issues)

    def normalize(self, profile: SourceProfile, raw_dir: Path) -> NormalizationResult:
        transactions: list[NormalizedTransaction] = []
        issues: list[IssueRecord] = []
        wallet_inventory, _ = self.extract_wallet_inventory(str(profile.source), raw_dir, profile)
        for path in matching_file_paths(raw_dir):
            for index, row in enumerate(read_csv_rows(path), start=2):
                pnl = Decimal((row.get("PNL") or "0").strip())
                if pnl == Decimal("0"):
                    issues.append(
                        IssueRecord(
                            issue_id=f"gtrade:{path.name}:row:{index}",
                            source=str(profile.source),
                            adapter_id=str(self.manifest.adapter_id),
                            severity="medium",
                            kind="unsupported_row",
                            message=(
                                "GTrade report row lacks realized PnL and cannot be deterministically converted "
                                "into a normalized transaction without supporting explorer evidence."
                            ),
                            raw_file=path.name,
                            raw_row_ref=f"row:{index}",
                            status="needs_review",
                        )
                    )
                    continue
                category: TransactionCategory = "derivatives_profit" if pnl > 0 else "derivatives_loss"
                description = (row.get("DESCRIPTION") or "").strip()
                timestamp = _parse_report_date((row.get("DATE") or "").strip())
                transactions.append(
                    NormalizedTransaction(
                        transaction_id=TransactionId(f"gtrade:{path.name}:row:{index}"),
                        source=profile.source,
                        adapter_id=self.manifest.adapter_id,
                        account=str(profile.source),
                        wallet=str(profile.source),
                        timestamp=timestamp,
                        category=category,
                        description=description,
                        asset_in=AssetSymbol("DAI") if pnl > 0 else None,
                        amount_in=pnl if pnl > 0 else None,
                        asset_out=AssetSymbol("DAI") if pnl < 0 else None,
                        amount_out=abs(pnl) if pnl < 0 else None,
                        tx_hash=f"gtrade:{path.name}:row:{index}",
                        raw_file=path.name,
                        raw_row_ref=f"row:{index}",
                    )
                )
        return NormalizationResult(
            transactions=tuple(transactions),
            balances=(),
            issues=tuple(issues),
            reviews=(),
            wallet_inventory=wallet_inventory,
        )


def _parse_report_date(value: str) -> datetime:
    day, month, year = value.split("/")
    return datetime.fromisoformat(f"{year}-{month}-{day}T00:00:00+00:00").astimezone(UTC).replace(tzinfo=None)


ADAPTER = GTradeAdapter()
