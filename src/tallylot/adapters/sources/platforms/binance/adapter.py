"""Binance export adapter entry point."""

from __future__ import annotations

from pathlib import Path

from tallylot.adapters.support import (
    TimezoneReviewPolicy,
    match_intake_by_path_or_header,
    no_intake_route,
    reviewed_timezone_summary,
)
from tallylot.domain.issues import IssueRecord
from tallylot.domain.types import AdapterId, JsonValue
from tallylot.ports.adapter_contracts import AdapterCapability, AdapterManifest
from tallylot.ports.evidence import LocationInventoryRecord
from tallylot.ports.intake_routing import IntakeFileFacts, IntakeRoute, IntakeRoutingRequest
from tallylot.ports.source_profiles import FileFamilyClaim, FileInventoryEntry, SourceProfile
from tallylot.ports.source_translation import SourceTranslationBatch

from .matching import (
    C2C_HEADER,
    CONVERT_HEADER,
    DEPOSIT_HEADER,
    SPOT_HEADER,
    TRANSACTION_HEADER,
    WITHDRAW_HEADER,
    match_binance_inventory,
)
from .pdf_balances import extract_pdf_balances as _extract_pdf_balances
from .pdf_balances import match_pdf_statement as _match_pdf_statement
from .translation import translate_binance_exports


class _BinanceAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("binance"),
        display_name="Binance",
        version="1.0.0",
        capabilities=frozenset({AdapterCapability.SOURCE_TRANSLATE, AdapterCapability.INTAKE_ROUTE}),
        description="Normalizes Binance deposit, withdrawal, spot, and transaction-history exports.",
    )

    def match(self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> int:
        del raw_dir
        return match_binance_inventory(source, inventory)

    def classify_profile_families(
        self,
        source: str,
        raw_dir: Path,
        inventory: tuple[FileInventoryEntry, ...],
    ) -> tuple[FileFamilyClaim, ...]:
        del source, raw_dir
        family_headers: dict[tuple[str, ...], str] = {
            SPOT_HEADER: "spot_trade_history",
            DEPOSIT_HEADER: "deposit_history",
            WITHDRAW_HEADER: "withdraw_history",
            CONVERT_HEADER: "convert_order_history",
            C2C_HEADER: "c2c_order_history",
            TRANSACTION_HEADER: "transaction_history",
        }
        claims: list[FileFamilyClaim] = []
        for item in inventory:
            family_id = family_headers.get(item.header, "")
            if not family_id:
                continue
            claims.append(
                FileFamilyClaim(
                    relative_path=item.relative_path,
                    adapter_id=self.manifest.adapter_id,
                    family_id=family_id,
                )
            )
        return tuple(claims)

    def match_intake(self, relative_path: str, facts: IntakeFileFacts) -> int:
        return match_intake_by_path_or_header(
            relative_path,
            facts,
            path_hints=("binance",),
            header_hints=(
                "pair,coin,date,amount,type,status",
                "pair,coin,amount,time,interest type",
                "date(utc),pair,side,price,executed,amount,fee",
            ),
        )

    def route_intake(self, request: IntakeRoutingRequest) -> IntakeRoute | None:
        return no_intake_route(request)

    def validate_profile_timezones(
        self,
        profile: SourceProfile,
    ) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
        return reviewed_timezone_summary(
            profile,
            policy=TimezoneReviewPolicy(
                adapter_id=str(self.manifest.adapter_id),
                mode="naive",
                message="Binance exports with dated rows must include a filename offset before normalization.",
            ),
        )

    def extract_location_inventory(
        self,
        source: str,
        raw_dir: Path,
        profile: SourceProfile,
    ) -> tuple[tuple[LocationInventoryRecord, ...], tuple[IssueRecord, ...]]:
        del source, raw_dir, profile
        return (), ()

    def match_pdf_statement(self, pdf_path: Path, text: str) -> int:
        return _match_pdf_statement(pdf_path, text)

    def extract_pdf_balances(self, pdf_path: Path, text: str) -> list[dict[str, str]]:
        return _extract_pdf_balances(text, pdf_path.name)

    def translate(self, profile: SourceProfile, raw_dir: Path) -> SourceTranslationBatch:
        return translate_binance_exports(profile, raw_dir)


ADAPTER = _BinanceAdapter()
