"""Binance export adapter entry point."""

from __future__ import annotations

import re
from pathlib import Path

from tallylot.adapters.support import (
    TimezoneReviewPolicy,
    match_intake_by_path_or_header,
    reviewed_timezone_summary,
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

from .matching import (
    C2C_HEADER,
    CONVERT_HEADER,
    DEPOSIT_HEADER,
    SPOT_HEADER,
    TRANSACTION_HEADER,
    WITHDRAW_HEADER,
    match_binance_inventory,
)
from .pdf_balances import match_statement_document as _match_statement_document
from .statement_evidence import parse_statement_document as _parse_statement_document
from .translation import translate_binance_exports

_RAW_WORKBOOK_PATTERNS = (
    re.compile(
        r"^binance(?:-| )order history(?: report)? \d{4}\.(?:xlsx|xls)$", re.IGNORECASE
    ),
    re.compile(
        r"^binance(?:-| )withdrawal history report \d{4}\.(?:xlsx|xls)$", re.IGNORECASE
    ),
)


class _BinanceAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("binance"),
        display_name="Binance",
        version="1.0.0",
        capabilities=frozenset(
            {AdapterCapability.SOURCE_TRANSLATE, AdapterCapability.INTAKE_ROUTE}
        ),
        description="Normalizes Binance deposit, withdrawal, spot, and transaction-history exports.",
    )

    def match(
        self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]
    ) -> int:
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
        if not _is_raw_binance_workbook(request.relative_path):
            return None
        return IntakeRoute(
            category="source_raw",
            role="source_export",
            source_folder="binance",
            capture_label=request.incoming_dir.name,
            action="extract_copy" if request.archive_member_path else "copy",
            target_path=_raw_workbook_target_path(request),
        )

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

    def match_statement_document(self, pdf_path: Path, text: str) -> int:
        return _match_statement_document(pdf_path, text)

    def parse_statement_document(
        self, pdf_path: Path, text: str
    ) -> StatementDocumentParseResult:
        return _parse_statement_document(pdf_path, text)

    def translate(
        self, profile: SourceProfile, raw_dir: Path
    ) -> SourceTranslationBatch:
        return translate_binance_exports(profile, raw_dir)

    def resolve_statement_instrument_claims(
        self, row: StatementDocumentBalanceRow
    ) -> tuple[InstrumentIdentityClaim, ...]:
        return (
            symbol_claim(
                row.asset,
                venue="binance",
                kind_hint=InstrumentKind.CRYPTO,
            ),
        )


ADAPTER = _BinanceAdapter()


def _is_raw_binance_workbook(relative_path: str) -> bool:
    filename = Path(relative_path).name
    return any(pattern.match(filename) for pattern in _RAW_WORKBOOK_PATTERNS)


def _raw_workbook_target_path(request: IntakeRoutingRequest) -> Path:
    capture_root = (
        request.workspace_root
        / "evidence"
        / "raw"
        / "source"
        / "binance"
        / request.incoming_dir.name
    )
    if request.archive_member_path:
        archive_stem = Path(request.archive_source_path).stem
        return (
            capture_root / archive_stem / "contents" / Path(request.archive_member_path)
        )
    return capture_root / Path(request.relative_path)
