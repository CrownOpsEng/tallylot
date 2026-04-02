"""GTrade report adapter."""

from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.adapters.sources.platforms.gtrade.translation import translate_transactions
from crypto_reconciliation.adapters.support import (
    match_intake_by_path_or_header,
    matching_file_paths,
    no_intake_route,
    passed_timezone_summary,
    read_csv_header,
    read_csv_rows,
    wallet_issue,
    wallet_record,
)
from crypto_reconciliation.adapters.support.drafts import translation_batch_from_drafts
from crypto_reconciliation.adapters.support.wallets import WalletIssueSpec, WalletRecordSpec
from crypto_reconciliation.domain.issues import IssueRecord
from crypto_reconciliation.domain.types import AdapterId, JsonValue
from crypto_reconciliation.ports.adapter_contracts import AdapterCapability, AdapterManifest
from crypto_reconciliation.ports.evidence import WalletInventoryRecord
from crypto_reconciliation.ports.intake_routing import IntakeFileFacts, IntakeRoute, IntakeRoutingRequest
from crypto_reconciliation.ports.source_profiles import FileInventoryEntry, SourceProfile
from crypto_reconciliation.ports.source_translation import SourceTranslationBatch


class GTradeAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("gtrade"),
        display_name="GTrade",
        version="1.0.0",
        capabilities=frozenset(
            {AdapterCapability.SOURCE_TRANSLATE, AdapterCapability.WALLET_INVENTORY, AdapterCapability.INTAKE_ROUTE}
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

    def translate(self, profile: SourceProfile, raw_dir: Path) -> SourceTranslationBatch:
        wallet_inventory, _ = self.extract_wallet_inventory(str(profile.source), raw_dir, profile)
        drafts, issues = translate_transactions(profile, raw_dir)
        return translation_batch_from_drafts(
            drafts,
            issues=issues,
            wallet_inventory=wallet_inventory,
        )


def _skip_unrecognized_csv(path: Path) -> bool:
    header = read_csv_header(path)
    return header[:3] != ("DATE", "PAIR", "ADDR")


ADAPTER = GTradeAdapter()
