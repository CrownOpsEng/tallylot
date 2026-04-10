"""Binance export adapter entry point."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from tallylot.adapters.support import (
    IssueSpec,
    ReviewSpec,
    TimezoneReviewPolicy,
    issue_record,
    location_id_from_parts,
    match_intake_by_path_or_header,
    no_intake_route,
    resolve_instrument_identity,
    review_record,
    reviewed_timezone_summary,
)
from tallylot.adapters.support.drafts import symbol_claim
from tallylot.domain.instruments import InstrumentKind
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.domain.reconciliation import BalanceEvidence
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import AdapterId, JsonValue
from tallylot.ports.adapter_contracts import AdapterCapability, AdapterManifest
from tallylot.ports.evidence import (
    LocationInventoryRecord,
    StatementBalanceEvidenceBatch,
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
from .pdf_balances import extract_pdf_balances as _extract_pdf_balances
from .pdf_balances import match_pdf_statement as _match_pdf_statement
from .statement_evidence import parse_statement_pdf
from .translation import translate_binance_exports


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

    def translate(
        self, profile: SourceProfile, raw_dir: Path
    ) -> SourceTranslationBatch:
        return translate_binance_exports(profile, raw_dir)

    def extract_statement_balance_evidence(
        self,
        profile: SourceProfile,
        raw_dir: Path,
    ) -> StatementBalanceEvidenceBatch:
        return _extract_statement_balance_evidence(profile, raw_dir)


ADAPTER = _BinanceAdapter()


def _extract_statement_balance_evidence(
    profile: SourceProfile,
    raw_dir: Path,
) -> StatementBalanceEvidenceBatch:
    parsed_statements = tuple(
        parsed
        for pdf_path in sorted(raw_dir.rglob("*.pdf"))
        if (parsed := parse_statement_pdf(pdf_path)).recognized
    )
    if not parsed_statements:
        return StatementBalanceEvidenceBatch(balance_evidence=(), issues=(), reviews=())
    latest_as_of = max(
        parsed.as_of_at for parsed in parsed_statements if parsed.as_of_at is not None
    )
    latest_statements = tuple(
        parsed for parsed in parsed_statements if parsed.as_of_at == latest_as_of
    )
    evidence: list[BalanceEvidence] = []
    issues: list[IssueRecord] = []
    reviews: list[NormalizationReviewRecord] = []
    location_id = location_id_from_parts(str(profile.source))
    aggregated_rows: dict[str, tuple[Decimal, set[str], set[str]]] = {}
    for parsed in latest_statements:
        if not parsed.rows:
            issues.append(
                issue_record(
                    IssueSpec(
                        issue_id=f"{profile.source}:{parsed.pdf_file}:statement_evidence_missing",
                        source=str(profile.source),
                        adapter_id="binance",
                        severity="high",
                        kind="statement_evidence_missing",
                        message="Binance account statement was recognized but no holdings rows were extracted.",
                        raw_file=parsed.pdf_file,
                    )
                )
            )
            continue
        for row in parsed.rows:
            quantity, sections, files = aggregated_rows.get(
                row.asset_symbol, (Decimal("0"), set(), set())
            )
            aggregated_rows[row.asset_symbol] = (
                quantity + row.quantity,
                sections | {row.section},
                files | {parsed.pdf_file},
            )
    for asset_symbol, (quantity, sections, files) in sorted(aggregated_rows.items()):
        resolved = resolve_instrument_identity(
            (
                symbol_claim(
                    asset_symbol,
                    venue="binance",
                    kind_hint=InstrumentKind.CRYPTO,
                ),
            )
        )
        if resolved is None:
            issue_files = ",".join(sorted(files))
            issues.append(
                issue_record(
                    IssueSpec(
                        issue_id=f"{profile.source}:{asset_symbol}:instrument_identity_blocked",
                        source=str(profile.source),
                        adapter_id="binance",
                        severity="high",
                        kind="instrument_identity_blocked",
                        message=f"Binance statement evidence could not resolve instrument {asset_symbol}.",
                        raw_file=issue_files,
                    )
                )
            )
            reviews.append(
                review_record(
                    ReviewSpec(
                        review_id=f"{profile.source}:{asset_symbol}:instrument_identity_review",
                        source=str(profile.source),
                        adapter_id="binance",
                        scope="balance_evidence",
                        kind="instrument_identity_review",
                        message=f"Review required for Binance statement instrument {asset_symbol}.",
                        raw_file=issue_files,
                        field_name="asset_symbol",
                        original_value=asset_symbol,
                    )
                )
            )
            continue
        evidence.append(
            BalanceEvidence(
                source=profile.source,
                location_id=location_id,
                instrument_id=resolved.instrument.instrument_id,
                quantity=quantity,
                as_of_at=latest_as_of,
                as_of_precision=TemporalPrecision.DATE,
                balance_kind="available",
                evidence_ref=f"{','.join(sorted(files))}#{' + '.join(sorted(sections))}",
                notes="Statement-backed quantity aggregated from Binance holdings sections.",
            )
        )
    return StatementBalanceEvidenceBatch(
        balance_evidence=tuple(evidence),
        issues=tuple(issues),
        reviews=tuple(reviews),
    )
