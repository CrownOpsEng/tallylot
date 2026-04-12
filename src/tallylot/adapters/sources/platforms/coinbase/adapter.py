"""Coinbase retail export adapter entry point."""

from __future__ import annotations

from pathlib import Path

from tallylot.adapters.support import (
    match_intake_by_path_or_header,
    no_intake_route,
    passed_timezone_summary,
)
from tallylot.adapters.support.drafts import symbol_claim
from tallylot.domain.instruments import InstrumentIdentityClaim, InstrumentKind
from tallylot.domain.issues import IssueRecord
from tallylot.domain.types import AdapterId, JsonValue
from tallylot.ports.adapter_contracts import AdapterCapability, AdapterManifest
from tallylot.ports.evidence import (
    LocationInventoryRecord,
    StatementDocumentBalanceRow,
    StatementDocumentParseResult,
)
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
from tallylot.ports.translation_inputs import (
    TranslationInputCandidate,
    TranslationInputPlan,
)

from .matching import RETAIL_HEADER, match_coinbase_inventory
from .normalization import (
    describe_translation_inputs,
    translate_coinbase_exports,
    translate_selected_inputs,
)
from .pdf_balances import match_statement_document as _match_statement_document
from .pdf_balances import parse_statement_document as _parse_statement_document


class _CoinbaseAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("coinbase"),
        display_name="Coinbase",
        version="1.0.0",
        capabilities=frozenset(
            {AdapterCapability.SOURCE_TRANSLATE, AdapterCapability.INTAKE_ROUTE}
        ),
        description="Normalizes Coinbase retail all-time exports.",
    )

    def match(
        self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]
    ) -> int:
        return match_coinbase_inventory(source, raw_dir, inventory)

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
                family_id="retail_export",
            )
            for item in inventory
            if {
                "portfolio",
                "type",
                "time",
                "amount",
                "balance",
                "amount/balance unit",
            }.issubset({field.lower() for field in item.header})
        )

    def match_intake(self, relative_path: str, facts: IntakeFileFacts) -> int:
        return match_intake_by_path_or_header(
            relative_path,
            facts,
            path_hints=("coinbase",),
            header_hints=(
                "portfolio,type,time,amount,balance,amount/balance unit",
                ",".join(RETAIL_HEADER).lower(),
            ),
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

    def match_statement_document(self, pdf_path: Path, text: str) -> int:
        return _match_statement_document(pdf_path, text)

    def parse_statement_document(
        self, pdf_path: Path, text: str
    ) -> StatementDocumentParseResult:
        return _parse_statement_document(pdf_path, text)

    def resolve_statement_instrument_claims(
        self, row: StatementDocumentBalanceRow
    ) -> tuple[InstrumentIdentityClaim, ...]:
        kind_hint = (
            InstrumentKind.FIAT
            if row.asset.strip().upper() in {"CAD", "USD"}
            else InstrumentKind.CRYPTO
        )
        return (symbol_claim(row.asset, venue="coinbase", kind_hint=kind_hint),)

    def translate(
        self, profile: SourceProfile, raw_dir: Path
    ) -> SourceTranslationBatch:
        return translate_coinbase_exports(profile, raw_dir)

    def describe_translation_inputs(
        self, profile: SourceProfile, raw_dir: Path
    ) -> tuple[TranslationInputCandidate, ...]:
        return describe_translation_inputs(profile, raw_dir)

    def translate_selected_inputs(
        self,
        profile: SourceProfile,
        raw_dir: Path,
        plan: TranslationInputPlan,
    ) -> SourceTranslationBatch:
        return translate_selected_inputs(profile, raw_dir, plan)


ADAPTER = _CoinbaseAdapter()
