"""GTrade report adapter."""

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
    read_csv_header,
    read_csv_rows,
    wallet_issue,
    wallet_record,
)
from crypto_reconciliation.adapters.support.drafts import (
    ActivityClassification,
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
        return match_intake_by_path_or_header(relative_path, facts, path_hints=("gtrade",))

    def route_intake(self, request: IntakeRoutingRequest) -> IntakeRoute | None:
        return no_intake_route(request)

    def validate_profile_timezones(
        self,
        profile: SourceProfile,
    ) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
        return passed_timezone_summary(profile, mode="date_only")

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
            if _skip_unrecognized_csv(path):
                continue
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
                    wallet_issue(
                        WalletIssueSpec(
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
                wallet_issue(
                    WalletIssueSpec(
                        source=source,
                        adapter_id=str(self.manifest.adapter_id),
                        issue_kind="missing_identifier",
                        message="No address alias was found in the GTrade report.",
                    )
                )
            )
        return tuple(evidence), tuple(issues)

    def normalize(self, profile: SourceProfile, raw_dir: Path) -> NormalizationResult:
        drafts: list[EconomicActivityDraft] = []
        issues: list[IssueRecord] = []
        wallet_inventory, _ = self.extract_wallet_inventory(str(profile.source), raw_dir, profile)
        for path in matching_file_paths(raw_dir):
            if _skip_unrecognized_csv(path):
                continue
            for index, row in enumerate(read_csv_rows(path), start=2):
                pnl = _parse_decimal((row.get("PNL") or "").strip())
                if pnl is None:
                    issues.append(
                        issue_record(
                            IssueSpec(
                                source=str(profile.source),
                                adapter_id=str(self.manifest.adapter_id),
                                issue_id=f"gtrade:{path.name}:row:{index}:invalid_pnl",
                                severity="medium",
                                kind="unsupported_row",
                                message="GTrade row is missing a supported realized PnL value.",
                                raw_file=path.name,
                                raw_row_ref=f"row:{index}",
                                status="needs_review",
                            )
                        )
                    )
                    continue
                if pnl == Decimal("0"):
                    issues.append(
                        issue_record(
                            IssueSpec(
                                source=str(profile.source),
                                adapter_id=str(self.manifest.adapter_id),
                                issue_id=f"gtrade:{path.name}:row:{index}",
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
                    )
                    continue
                description = (row.get("DESCRIPTION") or "").strip()
                timestamp = _parse_report_date((row.get("DATE") or "").strip())
                if timestamp is None:
                    issues.append(
                        issue_record(
                            IssueSpec(
                                source=str(profile.source),
                                adapter_id=str(self.manifest.adapter_id),
                                issue_id=f"gtrade:{path.name}:row:{index}:invalid_date",
                                severity="medium",
                                kind="unsupported_row",
                                message="GTrade row is missing a supported report date.",
                                raw_file=path.name,
                                raw_row_ref=f"row:{index}",
                                status="needs_review",
                            )
                        )
                    )
                    continue
                drafts.append(
                    EconomicActivityDraft(
                        activity_id=f"gtrade:{path.name}:row:{index}",
                        source=str(profile.source),
                        adapter_id="gtrade",
                        account=str(profile.source),
                        wallet=str(profile.source),
                        timestamp=timestamp,
                        classification=_classification_for_pnl(pnl),
                        description=description,
                        raw_file=path.name,
                        raw_row_ref=f"row:{index}",
                        tx_hash=f"gtrade:{path.name}:row:{index}",
                        provider_operation_key="realized_pnl",
                        legs=(
                            (economic_leg(direction="in", asset="DAI", amount=pnl),)
                            if pnl > 0
                            else (economic_leg(direction="out", asset="DAI", amount=abs(pnl)),)
                        ),
                    )
                )
        return normalization_result_from_drafts(
            drafts,
            issues=issues,
            wallet_inventory=wallet_inventory,
        )


def _classification_for_pnl(pnl: Decimal) -> ActivityClassification:
    if pnl > 0:
        return classification(
            normalized_category="derivatives_profit",
            economic_kind="derivative_realized_profit",
            projection_type="Derivatives / Futures Profit",
            journal_intent="income_recognition",
            tax_treatment_code="derivative_realized_gain",
        )
    return classification(
        normalized_category="derivatives_loss",
        economic_kind="derivative_realized_loss",
        projection_type="Derivatives / Futures Loss",
        journal_intent="expense_recognition",
        tax_treatment_code="derivative_realized_loss",
    )


def _skip_unrecognized_csv(path: Path) -> bool:
    header = read_csv_header(path)
    return header[:3] != ("DATE", "PAIR", "ADDR")


def _parse_decimal(value: str) -> Decimal | None:
    if not value:
        return None
    try:
        return Decimal(value)
    except ArithmeticError:
        return None


def _parse_report_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        day, month, year = value.split("/")
        return datetime.fromisoformat(f"{year}-{month}-{day}T00:00:00+00:00").astimezone(UTC).replace(tzinfo=None)
    except ValueError:
        return None


ADAPTER = GTradeAdapter()
