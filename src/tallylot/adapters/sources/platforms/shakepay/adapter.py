"""Shakepay export adapter."""

from __future__ import annotations

from pathlib import Path

from tallylot.adapters.sources.platforms.shakepay.statement_evidence import (
    parse_statement_pdf,
)
from tallylot.adapters.sources.platforms.shakepay.pdf_balances import (
    extract_pdf_balances as _extract_pdf_balances,
)
from tallylot.adapters.sources.platforms.shakepay.pdf_balances import (
    match_pdf_statement as _match_pdf_statement,
)
from tallylot.adapters.sources.platforms.shakepay.translation import translate_row
from tallylot.adapters.support import (
    IssueSpec,
    ReviewSpec,
    collect_csv_row_results,
    issue_record,
    location_id_from_parts,
    match_intake_by_path_or_header,
    no_intake_route,
    passed_timezone_summary,
    resolve_instrument_identity,
    review_record,
    skip_files_outside_profile_families,
)
from tallylot.adapters.support.drafts import symbol_claim, translation_batch_from_drafts
from tallylot.domain.captures import ProvenanceLocator
from tallylot.domain.instruments import InstrumentIdentityClaim, InstrumentKind
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.domain.reconciliation import BalanceEvidence
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

    def match_pdf_statement(self, pdf_path: Path, text: str) -> int:
        return _match_pdf_statement(pdf_path, text)

    def extract_pdf_balances(self, pdf_path: Path, text: str) -> list[dict[str, str]]:
        return _extract_pdf_balances(text, pdf_path.name)

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
            drafts,
            issues=issues,
        )

    def extract_statement_balance_evidence(
        self,
        profile: SourceProfile,
        raw_dir: Path,
    ) -> StatementBalanceEvidenceBatch:
        return _extract_statement_balance_evidence(profile, raw_dir)


ADAPTER = _ShakepayAdapter()


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
    for parsed in latest_statements:
        if not parsed.rows:
            issues.append(
                issue_record(
                    IssueSpec(
                        issue_id=f"{profile.source}:{parsed.pdf_file}:statement_evidence_missing",
                        source=str(profile.source),
                        adapter_id="shakepay",
                        severity="high",
                        kind="statement_evidence_missing",
                        message="Shakepay monthly statement was recognized but no balance rows were extracted.",
                        raw_file=parsed.pdf_file,
                    )
                )
            )
            continue
        for row in parsed.rows:
            resolved = resolve_instrument_identity(
                (_shakepay_instrument_claim(row.asset_symbol),)
            )
            if resolved is None:
                issues.append(
                    issue_record(
                        IssueSpec(
                            issue_id=(
                                f"{profile.source}:{parsed.pdf_file}:"
                                f"{row.asset_symbol}:instrument_identity_blocked"
                            ),
                            source=str(profile.source),
                            adapter_id="shakepay",
                            severity="high",
                            kind="instrument_identity_blocked",
                            message=(
                                "Shakepay statement evidence could not resolve "
                                f"instrument {row.asset_symbol}."
                            ),
                            raw_file=parsed.pdf_file,
                            raw_row_ref="page:1",
                        )
                    )
                )
                reviews.append(
                    review_record(
                        ReviewSpec(
                            review_id=(
                                f"{profile.source}:{parsed.pdf_file}:"
                                f"{row.asset_symbol}:instrument_identity_review"
                            ),
                            source=str(profile.source),
                            adapter_id="shakepay",
                            scope="balance_evidence",
                            kind="instrument_identity_review",
                            message=(
                                "Review required for Shakepay statement instrument "
                                f"{row.asset_symbol}."
                            ),
                            raw_file=parsed.pdf_file,
                            raw_row_ref="page:1",
                            field_name="asset_symbol",
                            original_value=row.asset_symbol,
                        )
                    )
                )
                continue
            evidence.append(
                BalanceEvidence(
                    source=profile.source,
                    location_id=location_id,
                    instrument_id=resolved.instrument.instrument_id,
                    quantity=row.quantity,
                    as_of_at=row.as_of_at,
                    as_of_precision=row.as_of_precision,
                    balance_kind="available",
                    provenance=ProvenanceLocator.from_reference_ref(row.evidence_ref),
                    notes=row.notes,
                )
            )
    return StatementBalanceEvidenceBatch(
        balance_evidence=tuple(evidence),
        issues=tuple(issues),
        reviews=tuple(reviews),
    )


def _shakepay_instrument_claim(symbol: str) -> InstrumentIdentityClaim:
    upper_symbol = symbol.strip().upper()
    kind_hint = (
        InstrumentKind.FIAT if upper_symbol in {"CAD", "USD"} else InstrumentKind.CRYPTO
    )
    return symbol_claim(upper_symbol, venue="shakepay", kind_hint=kind_hint)
