"""Shakepay export adapter."""

from __future__ import annotations

from pathlib import Path

from tallylot.adapters.sources.platforms.shakepay.pdf_balances import (
    match_statement_document as _match_statement_document,
    parse_statement_document as _parse_statement_document,
)
from tallylot.adapters.sources.platforms.shakepay.translation import translate_row
from tallylot.adapters.support import (
    collect_csv_row_results,
    match_intake_by_path_or_header,
    no_intake_route,
    passed_timezone_summary,
    skip_files_outside_profile_families,
)
from tallylot.adapters.support.drafts import (
    TranslationBatchDrafts,
    symbol_claim,
    translation_batch_from_drafts,
)
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


class _ShakepayAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("shakepay"),
        display_name="Shakepay",
        version="1.0.0",
        capabilities=frozenset(
            {AdapterCapability.SOURCE_TRANSLATE, AdapterCapability.INTAKE_ROUTE}
        ),
        description="Normalizes Shakepay cash and crypto export summaries.",
    )

    def match(
        self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]
    ) -> int:
        del raw_dir
        if "shakepay" in source.lower():
            return 100
        if any(
            "crypto_transactions_summary.csv" in item.relative_path
            for item in inventory
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
        claims: list[FileFamilyClaim] = []
        for item in inventory:
            lower_path = item.relative_path.lower()
            if "crypto_transactions_summary.csv" in lower_path:
                claims.append(
                    FileFamilyClaim(
                        relative_path=item.relative_path,
                        adapter_id=self.manifest.adapter_id,
                        family_id="crypto_summary",
                    )
                )
            elif "cash_transactions_summary.csv" in lower_path:
                claims.append(
                    FileFamilyClaim(
                        relative_path=item.relative_path,
                        adapter_id=self.manifest.adapter_id,
                        family_id="cash_summary",
                    )
                )
        return tuple(claims)

    def match_intake(self, relative_path: str, facts: IntakeFileFacts) -> int:
        return match_intake_by_path_or_header(
            relative_path,
            facts,
            path_hints=(
                "shakepay",
                "crypto_transactions_summary.csv",
                "cash_transactions_summary.csv",
            ),
        )

    def route_intake(self, request: IntakeRoutingRequest) -> IntakeRoute | None:
        return no_intake_route(request)

    def validate_profile_timezones(
        self,
        profile: SourceProfile,
    ) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
        return passed_timezone_summary(profile, mode="america_toronto")

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

    def translate(
        self, profile: SourceProfile, raw_dir: Path
    ) -> SourceTranslationBatch:
        drafts, issues = collect_csv_row_results(
            raw_dir,
            lambda row_context: translate_row(profile, row_context),
            skip_file=skip_files_outside_profile_families(
                raw_dir,
                profile,
                family_ids=("cash_summary", "crypto_summary"),
            ),
        )
        return translation_batch_from_drafts(
            TranslationBatchDrafts(drafts=drafts, issues=issues)
        )

    def resolve_statement_instrument_claims(
        self, row: StatementDocumentBalanceRow
    ) -> tuple[InstrumentIdentityClaim, ...]:
        return (_shakepay_instrument_claim(row.asset),)


ADAPTER = _ShakepayAdapter()


def _shakepay_instrument_claim(symbol: str) -> InstrumentIdentityClaim:
    upper_symbol = symbol.strip().upper()
    kind_hint = (
        InstrumentKind.FIAT if upper_symbol in {"CAD", "USD"} else InstrumentKind.CRYPTO
    )
    return symbol_claim(upper_symbol, venue="shakepay", kind_hint=kind_hint)
