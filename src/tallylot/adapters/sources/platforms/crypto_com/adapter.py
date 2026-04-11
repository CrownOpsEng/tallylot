"""Crypto.com transaction export adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from tallylot.adapters.support import (
    CsvRowContext,
    IssueSpec,
    collect_csv_row_results,
    location_id_from_parts,
    issue_record,
    match_intake_by_path_or_header,
    no_intake_route,
    passed_timezone_summary,
    read_csv_header,
    skip_files_outside_profile_families,
)
from tallylot.adapters.support.drafts import (
    SINGLE_PRIMARY_ACTIVITY_POLICY,
    TWO_SIDED_PRIMARY_EXCHANGE_POLICY,
    EconomicActivityDraft,
    LegKind,
    classification,
    economic_leg,
    symbol_claim,
    translation_batch_from_drafts,
)
from tallylot.domain.issues import IssueRecord
from tallylot.domain.transactions import (
    AccountingIntentHint,
    EconomicKind,
    ProjectionHint,
    TaxTreatmentHint,
)
from tallylot.domain.types import AdapterId, JsonValue
from tallylot.domain.value_objects import parse_decimal
from tallylot.ports.adapter_contracts import AdapterCapability, AdapterManifest
from tallylot.ports.evidence import LocationInventoryRecord
from tallylot.ports.intake_routing import (
    IntakeFileFacts,
    IntakeRoute,
    IntakeRoutingRequest,
)
from tallylot.ports.source_profiles import (
    FileFamilyClaim,
    FileInventoryEntry,
    SourceProfile,
)
from tallylot.ports.source_translation import SourceTranslationBatch

HEADER_FIELDS = {
    "Timestamp (UTC)",
    "Transaction Description",
    "Currency",
    "Amount",
    "To Currency",
    "To Amount",
    "Transaction Kind",
}
SUPPORTED_TRANSACTION_KINDS = frozenset(
    {"viban_deposit", "viban_purchase", "crypto_withdrawal"}
)


class _CryptoComAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("crypto_com"),
        display_name="Crypto.com",
        version="1.0.0",
        capabilities=frozenset(
            {AdapterCapability.SOURCE_TRANSLATE, AdapterCapability.INTAKE_ROUTE}
        ),
        description="Normalizes Crypto.com transaction exports.",
    )

    def match(
        self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]
    ) -> int:
        del raw_dir
        if "crypto.com" in source.lower() or "crypto_com" in source.lower():
            return 100
        if any(
            HEADER_FIELDS.issubset(set(item.header))
            for item in inventory
            if item.header
        ):
            return 100
        return 0

    def classify_profile_families(
        self,
        source: str,
        raw_dir: Path,
        inventory: tuple[FileInventoryEntry, ...],
    ) -> tuple[FileFamilyClaim, ...]:
        del source, raw_dir
        return tuple(
            FileFamilyClaim(
                relative_path=item.relative_path,
                adapter_id=self.manifest.adapter_id,
                family_id="transaction_export",
            )
            for item in inventory
            if item.header and HEADER_FIELDS.issubset(set(item.header))
        )

    def match_intake(self, relative_path: str, facts: IntakeFileFacts) -> int:
        return match_intake_by_path_or_header(
            relative_path,
            facts,
            path_hints=("crypto.com", "crypto_com"),
        )

    def route_intake(self, request: IntakeRoutingRequest) -> IntakeRoute | None:
        return no_intake_route(request)

    def validate_profile_timezones(
        self,
        profile: SourceProfile,
    ) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
        return passed_timezone_summary(profile, mode="value_utc")

    def extract_location_inventory(
        self,
        source: str,
        raw_dir: Path,
        profile: SourceProfile,
    ) -> tuple[tuple[LocationInventoryRecord, ...], tuple[IssueRecord, ...]]:
        del source, raw_dir, profile
        return (), ()

    def translate(
        self, profile: SourceProfile, raw_dir: Path
    ) -> SourceTranslationBatch:
        drafts, issues = collect_csv_row_results(
            raw_dir,
            lambda row_context: _normalize_row(profile, row_context),
            skip_file=skip_files_outside_profile_families(
                raw_dir,
                profile,
                family_ids=("transaction_export",),
                extra_skip=_skip_unrecognized_csv,
            ),
        )
        return translation_batch_from_drafts(
            drafts,
            issues=issues,
        )


def _normalize_row(
    profile: SourceProfile,
    row_context: CsvRowContext,
) -> EconomicActivityDraft | IssueRecord:
    row = row_context.row
    timestamp = _parse_timestamp((row.get("Timestamp (UTC)") or "").strip())
    transaction_id = f"crypto_com:{row_context.raw_file}:{row_context.raw_row_ref}"
    if timestamp is None:
        return issue_record(
            IssueSpec(
                source=str(profile.source),
                adapter_id="crypto_com",
                issue_id=f"{transaction_id}:invalid_timestamp",
                kind="unsupported_row",
                message="Crypto.com row is missing a supported UTC timestamp.",
                raw_file=row_context.raw_file,
                raw_row_ref=row_context.raw_row_ref,
            )
        )
    description = (row.get("Transaction Description") or "").strip()
    kind = (row.get("Transaction Kind") or "").strip()
    tx_hash = (row.get("Transaction Hash") or "").strip()
    currency = (row.get("Currency") or "").strip().upper()
    amount = parse_decimal((row.get("Amount") or "").strip())
    to_currency = (row.get("To Currency") or "").strip().upper()
    to_amount = parse_decimal((row.get("To Amount") or "").strip())
    if kind == "viban_deposit" and amount is not None and amount > Decimal("0"):
        return EconomicActivityDraft(
            activity_id=transaction_id,
            source=str(profile.source),
            adapter_id="crypto_com",
            location_id=location_id_from_parts(str(profile.source)),
            timestamp=timestamp,
            classification=classification(
                economic_kind=EconomicKind.FIAT_DEPOSIT,
                projection_hint=ProjectionHint.DEPOSIT,
                accounting_intent_hint=AccountingIntentHint.FUNDING_INFLOW,
                tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN,
            ),
            leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
            description=description,
            raw_file=row_context.raw_file,
            raw_row_ref=row_context.raw_row_ref,
            tx_hash=tx_hash,
            provider_operation_key=kind,
            legs=(
                economic_leg(
                    leg_id="primary_in",
                    kind=LegKind.PRIMARY,
                    quantity=amount,
                    instrument=symbol_claim(currency, venue="crypto_com"),
                ),
            ),
        )
    if (
        kind == "viban_purchase"
        and amount is not None
        and amount < Decimal("0")
        and to_amount is not None
    ):
        return EconomicActivityDraft(
            activity_id=transaction_id,
            source=str(profile.source),
            adapter_id="crypto_com",
            location_id=location_id_from_parts(str(profile.source)),
            timestamp=timestamp,
            classification=classification(
                economic_kind=EconomicKind.SPOT_TRADE,
                projection_hint=ProjectionHint.TRADE,
                accounting_intent_hint=AccountingIntentHint.ASSET_EXCHANGE,
                tax_treatment_hint=TaxTreatmentHint.CAPITAL_EXCHANGE,
            ),
            leg_policy=TWO_SIDED_PRIMARY_EXCHANGE_POLICY,
            description=f"{currency} -> {to_currency}",
            raw_file=row_context.raw_file,
            raw_row_ref=row_context.raw_row_ref,
            tx_hash=tx_hash,
            provider_operation_key=kind,
            legs=(
                economic_leg(
                    leg_id="primary_in",
                    kind=LegKind.PRIMARY,
                    quantity=to_amount,
                    instrument=symbol_claim(to_currency, venue="crypto_com"),
                ),
                economic_leg(
                    leg_id="primary_out",
                    kind=LegKind.PRIMARY,
                    quantity=-abs(amount),
                    instrument=symbol_claim(currency, venue="crypto_com"),
                ),
            ),
        )
    if kind == "crypto_withdrawal" and amount is not None and amount < Decimal("0"):
        return EconomicActivityDraft(
            activity_id=transaction_id,
            source=str(profile.source),
            adapter_id="crypto_com",
            location_id=location_id_from_parts(str(profile.source)),
            timestamp=timestamp,
            classification=classification(
                economic_kind=EconomicKind.ASSET_WITHDRAWAL,
                projection_hint=ProjectionHint.WITHDRAWAL,
                accounting_intent_hint=AccountingIntentHint.FUNDING_OUTFLOW,
                tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_OUT,
            ),
            leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
            description=description,
            raw_file=row_context.raw_file,
            raw_row_ref=row_context.raw_row_ref,
            tx_hash=tx_hash,
            provider_operation_key=kind,
            legs=(
                economic_leg(
                    leg_id="primary_out",
                    kind=LegKind.PRIMARY,
                    quantity=-abs(amount),
                    instrument=symbol_claim(currency, venue="crypto_com"),
                ),
            ),
        )
    return issue_record(
        IssueSpec(
            source=str(profile.source),
            adapter_id="crypto_com",
            issue_id=transaction_id,
            kind="unsupported_row",
            message=f"Unsupported Crypto.com transaction kind: {kind}",
            raw_file=row_context.raw_file,
            raw_row_ref=row_context.raw_row_ref,
        )
    )


def _skip_unrecognized_csv(path: Path) -> bool:
    return not HEADER_FIELDS.issubset(set(read_csv_header(path)))


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    except ValueError:
        return None


ADAPTER = _CryptoComAdapter()
