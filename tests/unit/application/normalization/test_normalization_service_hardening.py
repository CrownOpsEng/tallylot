from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import override

import pytest
from reportlab.pdfgen import canvas

from tallylot.adapters.support.drafts import symbol_claim
from tallylot.application.normalization import NormalizeRequest
from tallylot.application.resource_refs import to_resource_ref
from tallylot.domain.captures import ProvenanceLocator
from tallylot.domain.instruments import (
    InstrumentId,
    InstrumentIdentityClaim,
    InstrumentKind,
)
from tallylot.domain.reconciliation import BalanceEvidence
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.transactions import (
    SINGLE_PRIMARY_ACTIVITY_POLICY,
    AccountingIntentHint,
    EconomicKind,
    LegKind,
    ProjectionHint,
    TaxTreatmentHint,
)
from tallylot.domain.types import LocationId, SourceId
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.infrastructure.storage import FilesystemFactRepository
from tallylot.ports.captures import SOURCE_CAPTURE_HEADER
from tallylot.ports.evidence import (
    StatementDocumentBalanceRow,
    StatementDocumentParseResult,
)
from tallylot.ports.source_profiles import FileFamilyClaim
from tallylot.ports.source_translation import (
    EconomicActivityDraft,
    SourceTranslationBatch,
    classification,
    economic_leg,
)
from repo_support.capture_roots import materialize_capture_root
from tests.support.services import (
    FakeSourceRegistry,
    MatchingSourceAdapter,
    build_normalization_service,
    build_registry_backed_normalization_service,
)


def _make_pdf(path: Path, *lines: str) -> None:
    pdf = canvas.Canvas(str(path))
    y = 750
    for line in lines:
        pdf.drawString(72, y, line)
        y -= 15
    pdf.save()


def test_normalization_service_rejects_unsupported_adapters(tmp_path: Path) -> None:
    raw_dir = materialize_capture_root(tmp_path, source="fixture")
    registry = FakeSourceRegistry(
        source_adapters=(MatchingSourceAdapter("unsupported", supported=False),)
    )
    artifacts = FilesystemArtifactStore()
    service = build_registry_backed_normalization_service(
        registry=registry, artifacts=artifacts
    )

    with pytest.raises(ValueError, match="is not supported for normalization"):
        service.execute(
            NormalizeRequest(
                source="fixture",
                raw_capture_ref=to_resource_ref(raw_dir),
                normalized_output_ref=to_resource_ref(tmp_path / "normalized"),
            )
        )


def test_normalization_service_rejects_non_capture_roots(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    service = build_normalization_service(artifacts=FilesystemArtifactStore())

    with pytest.raises(ValueError, match="must contain capture.json"):
        service.execute(
            NormalizeRequest(
                source="fixture_source",
                raw_capture_ref=to_resource_ref(raw_dir),
                normalized_output_ref=to_resource_ref(tmp_path / "normalized"),
            )
        )


def test_normalization_service_rejects_mismatched_capture_metadata(
    tmp_path: Path,
) -> None:
    raw_dir = materialize_capture_root(tmp_path, source="fixture_source")
    (raw_dir / "capture.json").write_text(
        json.dumps(
            {
                "capture_uid": "01HV4A5H7VJH7M3Y5A6B7C8D9E",
                "source": "other_source",
                "capture_label": "2026-03-23T14-15-16Z",
                "intake_started_at": "2026-03-23 14:15:16",
                "intake_completed_at": "2026-03-23 14:15:16",
                "intake_method": "source_intake_apply",
                "incoming_ref": "incoming/other_source",
                "manifest_fingerprint": "manifest:fixture",
                "status": "captured",
                "notes": "",
            }
        ),
        encoding="utf-8",
    )
    service = build_normalization_service(artifacts=FilesystemArtifactStore())

    with pytest.raises(ValueError, match="does not match requested source"):
        service.execute(
            NormalizeRequest(
                source="fixture_source",
                raw_capture_ref=to_resource_ref(raw_dir),
                normalized_output_ref=to_resource_ref(tmp_path / "normalized"),
            )
        )


def test_structured_csv_normalization_surfaces_invalid_rows_as_issues(
    tmp_path: Path,
) -> None:
    raw_dir = materialize_capture_root(tmp_path, source="fixture_source")
    header = (
        "timestamp,category,asset_in,amount_in,asset_out,amount_out,"
        "charge_asset,charge_amount,charge_side,rebate_asset,rebate_amount,rebate_side,"
        "tx_hash,description,account,wallet\n"
    )
    (raw_dir / "transactions.csv").write_text(
        header
        + "2023-08-06 10:00:00,trade,BTC,1.0,CAD,10.0,CAD,0.1,out,,,,tx-1,BTC buy,Fixture,Primary\n"
        + "2023-08-07 15:00:00,reward,ETH,not-a-decimal,,,,,,,,,tx-2,ETH reward,Fixture,Primary\n",
        encoding="utf-8",
    )
    artifacts = FilesystemArtifactStore()
    service = build_normalization_service(artifacts=artifacts)
    output_dir = tmp_path / "normalized"

    response = service.execute(
        NormalizeRequest(
            source="fixture_source",
            raw_capture_ref=to_resource_ref(raw_dir),
            normalized_output_ref=to_resource_ref(output_dir),
        )
    )

    assert response.fact_count == 1
    assert response.issue_count == 1
    assert response.review_count == 1

    exception_rows = artifacts.read_rows(output_dir / "exceptions.csv")
    review_rows = artifacts.read_rows(output_dir / "normalization_reviews.csv")
    wallet_rows = artifacts.read_rows(output_dir / "location_inventory.csv")

    assert exception_rows[0]["kind"] == "invalid_decimal"
    assert [row["kind"] for row in review_rows] == ["timestamp_timezone_assumed_utc"]
    assert wallet_rows[0]["evidence_relative_path"] == "transactions.csv"
    assert (output_dir / "timezone_issues.csv").exists()


def test_normalization_service_adds_capture_context_to_location_inventory(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    capture_uid = "01HV4A5H7VJH7M3Y5A6B7C8D9E"
    capture_label = "2026-03-23T14-15-16Z"
    raw_dir = (
        workspace_root
        / "evidence"
        / "raw"
        / "source"
        / "fixture_source"
        / capture_label
    )
    raw_dir.mkdir(parents=True)
    (raw_dir / "capture.json").write_text(
        json.dumps(
            {
                "capture_uid": capture_uid,
                "source": "fixture_source",
                "capture_label": capture_label,
                "intake_started_at": "2026-03-23 14:15:16",
                "intake_completed_at": "2026-03-23 14:15:16",
                "intake_method": "source_intake_apply",
                "incoming_ref": "incoming/fixture_source",
                "manifest_fingerprint": "manifest:fixture",
                "status": "captured",
                "notes": "",
            }
        ),
        encoding="utf-8",
    )
    (raw_dir / "transactions.csv").write_text(
        "timestamp,category,asset_in,amount_in,asset_out,amount_out,"
        "charge_asset,charge_amount,charge_side,rebate_asset,rebate_amount,rebate_side,"
        "tx_hash,description,account,wallet\n"
        "2023-08-06 10:00:00,trade,BTC,1.0,CAD,10.0,,,,,,,tx-1,BTC buy,Fixture,Primary\n",
        encoding="utf-8",
    )
    artifacts = FilesystemArtifactStore()
    artifacts.write_rows(
        workspace_root / "analysis" / "inventory" / "source_captures.csv",
        SOURCE_CAPTURE_HEADER,
        (
            {
                "capture_uid": capture_uid,
                "source": "fixture_source",
                "capture_label": capture_label,
                "status": "captured",
                "intake_started_at": "2026-03-23 14:15:16",
                "intake_completed_at": "2026-03-23 14:15:16",
                "intake_method": "source_intake_apply",
                "incoming_ref": "incoming/fixture_source",
                "capture_root_ref": f"evidence/raw/source/fixture_source/{capture_label}",
                "manifest_fingerprint": "manifest:fixture",
                "file_count": "1",
                "observed_period_start": "2023-08-06",
                "observed_period_end": "2023-08-06",
                "observed_group_count": "1",
                "supersedes_capture_uid": "",
                "notes": "",
            },
        ),
    )
    output_dir = workspace_root / "working" / "normalized" / "captures" / capture_uid

    build_normalization_service(artifacts=artifacts).execute(
        NormalizeRequest(
            source="fixture_source",
            raw_capture_ref=to_resource_ref(raw_dir),
            normalized_output_ref=to_resource_ref(output_dir),
        )
    )

    wallet_rows = artifacts.read_rows(output_dir / "location_inventory.csv")
    capture_rows = artifacts.read_rows(
        workspace_root / "analysis" / "inventory" / "source_captures.csv"
    )

    assert wallet_rows[0]["capture_uid"] == capture_uid
    assert wallet_rows[0]["capture_label"] == capture_label
    assert (
        wallet_rows[0]["capture_root_ref"]
        == f"evidence/raw/source/fixture_source/{capture_label}"
    )
    assert capture_rows[-1]["status"] == "normalized"


def test_structured_csv_normalization_rejects_zero_amounts(tmp_path: Path) -> None:
    raw_dir = materialize_capture_root(tmp_path, source="fixture_source")
    header = (
        "timestamp,category,asset_in,amount_in,asset_out,amount_out,"
        "charge_asset,charge_amount,charge_side,rebate_asset,rebate_amount,rebate_side,"
        "tx_hash,description,account,wallet\n"
    )
    (raw_dir / "transactions.csv").write_text(
        header
        + "2023-08-06 10:00:00,trade,BTC,0,CAD,10.0,CAD,0.1,out,,,,tx-1,BTC buy,Fixture,Primary\n",
        encoding="utf-8",
    )
    artifacts = FilesystemArtifactStore()
    service = build_normalization_service(artifacts=artifacts)
    output_dir = tmp_path / "normalized"

    response = service.execute(
        NormalizeRequest(
            source="fixture_source",
            raw_capture_ref=to_resource_ref(raw_dir),
            normalized_output_ref=to_resource_ref(output_dir),
        )
    )

    assert response.fact_count == 0
    assert response.issue_count == 2
    assert response.review_count == 0

    exception_rows = artifacts.read_rows(output_dir / "exceptions.csv")
    review_rows = artifacts.read_rows(output_dir / "normalization_reviews.csv")

    assert [row["kind"] for row in exception_rows] == ["zero_amount", "no_valid_rows"]
    assert not review_rows


class IdentityBlockingAdapter(MatchingSourceAdapter):
    def __init__(self) -> None:
        super().__init__("identity_blocking", supported=True)

    @override
    def translate(self, profile: object, raw_dir: Path) -> SourceTranslationBatch:
        del profile, raw_dir
        return SourceTranslationBatch(
            drafts=(
                EconomicActivityDraft(
                    activity_id="txn-good",
                    source="fixture",
                    adapter_id="identity_blocking",
                    timestamp=datetime(2025, 1, 1, tzinfo=UTC),
                    location_id=LocationId("fixture:primary"),
                    classification=classification(
                        economic_kind=EconomicKind.SPOT_TRADE,
                        projection_hint=ProjectionHint.TRADE,
                        accounting_intent_hint=AccountingIntentHint.ASSET_EXCHANGE,
                        tax_treatment_hint=TaxTreatmentHint.CAPITAL_EXCHANGE,
                    ),
                    legs=(
                        economic_leg(
                            leg_id="primary_btc",
                            kind=LegKind.PRIMARY,
                            instrument="BTC",
                            quantity=Decimal("1"),
                        ),
                    ),
                    leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
                    provenance_refs=("prov:good",),
                ),
                EconomicActivityDraft(
                    activity_id="txn-blocked",
                    source="fixture",
                    adapter_id="identity_blocking",
                    timestamp=datetime(2025, 1, 2, tzinfo=UTC),
                    location_id=LocationId("fixture:primary"),
                    classification=classification(
                        economic_kind=EconomicKind.SPOT_TRADE,
                        projection_hint=ProjectionHint.TRADE,
                        accounting_intent_hint=AccountingIntentHint.ASSET_EXCHANGE,
                        tax_treatment_hint=TaxTreatmentHint.CAPITAL_EXCHANGE,
                    ),
                    legs=(
                        economic_leg(
                            leg_id="primary_btc",
                            kind=LegKind.PRIMARY,
                            instrument=(
                                InstrumentIdentityClaim(
                                    scheme="symbol", value="BTC", venue="venue-a"
                                ),
                                InstrumentIdentityClaim(
                                    scheme="symbol", value="BTC", venue="venue-b"
                                ),
                            ),
                            quantity=Decimal("1"),
                        ),
                    ),
                    leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
                    provenance_refs=("prov:blocked",),
                ),
            ),
            balance_evidence=(),
            issues=(),
            reviews=(),
            location_inventory=(),
        )


def test_normalization_service_excludes_annotations_for_blocked_identity_drafts(
    tmp_path: Path,
) -> None:
    raw_dir = materialize_capture_root(tmp_path, source="fixture")
    artifacts = FilesystemArtifactStore()
    service = build_registry_backed_normalization_service(
        registry=FakeSourceRegistry(source_adapters=(IdentityBlockingAdapter(),)),
        artifacts=artifacts,
    )
    output_dir = tmp_path / "normalized"

    response = service.execute(
        NormalizeRequest(
            source="fixture",
            raw_capture_ref=to_resource_ref(raw_dir),
            normalized_output_ref=to_resource_ref(output_dir),
        )
    )

    facts = FilesystemFactRepository().read_facts(output_dir / "facts.csv")
    fact_annotations = json.loads(
        (output_dir / "fact_annotations.json").read_text(encoding="utf-8")
    )
    issue_rows = artifacts.read_rows(output_dir / "exceptions.csv")
    review_rows = artifacts.read_rows(output_dir / "normalization_reviews.csv")

    assert response.fact_count == 1
    assert response.issue_count == 1
    assert response.review_count == 1
    assert [str(fact.fact_id) for fact in facts] == ["txn-good"]
    assert fact_annotations == [
        {
            "fact_id": "txn-good",
            "provenance_refs": ["prov:good"],
            "review_markers": [],
            "adapter_metadata": [],
        }
    ]
    assert [row["kind"] for row in issue_rows] == ["instrument_identity_blocked"]
    assert [row["kind"] for row in review_rows] == ["instrument_identity_review"]


def test_structured_csv_normalization_normalizes_signed_amounts(tmp_path: Path) -> None:
    raw_dir = materialize_capture_root(tmp_path, source="fixture_source")
    header = (
        "timestamp,category,asset_in,amount_in,asset_out,amount_out,"
        "charge_asset,charge_amount,charge_side,rebate_asset,rebate_amount,rebate_side,"
        "tx_hash,description,account,wallet\n"
    )
    (raw_dir / "transactions.csv").write_text(
        header
        + "2023-08-06 10:00:00,trade,BTC,1.5,CAD,-10.0,CAD,-0.1,out,,,,tx-1,BTC buy,Fixture,Primary\n",
        encoding="utf-8",
    )
    artifacts = FilesystemArtifactStore()
    service = build_normalization_service(artifacts=artifacts)
    output_dir = tmp_path / "normalized"

    response = service.execute(
        NormalizeRequest(
            source="fixture_source",
            raw_capture_ref=to_resource_ref(raw_dir),
            normalized_output_ref=to_resource_ref(output_dir),
        )
    )

    assert response.fact_count == 1
    assert response.issue_count == 0
    assert response.review_count == 3

    facts = FilesystemFactRepository().read_facts(output_dir / "facts.csv")
    fact_annotations = json.loads(
        (output_dir / "fact_annotations.json").read_text(encoding="utf-8")
    )
    review_rows = artifacts.read_rows(output_dir / "normalization_reviews.csv")
    summary = json.loads(
        (output_dir / "normalization_summary.json").read_text(encoding="utf-8")
    )

    assert facts[0].legs[0].quantity == Decimal("1.5")
    assert facts[0].legs[1].quantity == Decimal("-10")
    charge_legs = tuple(leg for leg in facts[0].legs if leg.kind is LegKind.CHARGE)
    assert charge_legs[0].quantity == Decimal("-0.1")
    assert fact_annotations == [
        {
            "fact_id": str(facts[0].fact_id),
            "provenance_refs": [],
            "review_markers": [],
            "adapter_metadata": [],
        }
    ]
    assert [row["kind"] for row in review_rows] == [
        "outbound_amount_sign_normalized",
        "outbound_amount_sign_normalized",
        "timestamp_timezone_assumed_utc",
    ]
    assert review_rows[0]["field_name"] == "amount_out"
    assert review_rows[0]["original_value"] == "-10.0"
    assert review_rows[0]["normalized_value"] == "10"
    assert review_rows[1]["field_name"] == "charge_amount"
    assert review_rows[1]["original_value"] == "-0.1"
    assert review_rows[1]["normalized_value"] == "0.1"
    assert summary["review_count"] == 3
    assert summary["review_summary"] == [
        {
            "scope": "dataset",
            "kind": "timestamp_timezone_assumed_utc",
            "count": 1,
            "field_names": [],
            "messages": [
                (
                    "Structured CSV timestamps are timezone-naive; normalization assigns UTC "
                    "and those timestamps should be validated against the source system."
                )
            ],
        },
        {
            "scope": "row",
            "kind": "outbound_amount_sign_normalized",
            "count": 2,
            "field_names": ["amount_out", "charge_amount"],
            "messages": [
                "amount_out was negative and was normalized to a positive outbound value.",
                "charge_amount was negative and was normalized to a positive outbound value.",
            ],
        },
    ]


def test_structured_csv_normalization_rejects_conflicting_inbound_signs(
    tmp_path: Path,
) -> None:
    raw_dir = materialize_capture_root(tmp_path, source="fixture_source")
    header = (
        "timestamp,category,asset_in,amount_in,asset_out,amount_out,"
        "charge_asset,charge_amount,charge_side,rebate_asset,rebate_amount,rebate_side,"
        "tx_hash,description,account,wallet\n"
    )
    (raw_dir / "transactions.csv").write_text(
        header
        + "2023-08-06 10:00:00,trade,BTC,-1.5,,,,,,,,,tx-1,BTC transfer,Fixture,Primary\n",
        encoding="utf-8",
    )
    artifacts = FilesystemArtifactStore()
    service = build_normalization_service(artifacts=artifacts)
    output_dir = tmp_path / "normalized"

    response = service.execute(
        NormalizeRequest(
            source="fixture_source",
            raw_capture_ref=to_resource_ref(raw_dir),
            normalized_output_ref=to_resource_ref(output_dir),
        )
    )

    assert response.fact_count == 0
    assert response.issue_count == 2
    assert response.review_count == 0

    exception_rows = artifacts.read_rows(output_dir / "exceptions.csv")
    review_rows = artifacts.read_rows(output_dir / "normalization_reviews.csv")

    assert [row["kind"] for row in exception_rows] == [
        "conflicting_amount_sign",
        "no_valid_rows",
    ]
    assert not review_rows


def test_normalization_service_rejects_output_inside_raw_tree(tmp_path: Path) -> None:
    raw_dir = materialize_capture_root(tmp_path, source="fixture_source")
    (raw_dir / "transactions.csv").write_text(
        (
            "timestamp,category,asset_in,amount_in,asset_out,amount_out,"
            "charge_asset,charge_amount,charge_side,rebate_asset,rebate_amount,rebate_side,"
            "tx_hash,description,account,wallet\n"
            "2023-08-06 10:00:00,trade,BTC,1.0,CAD,10.0,CAD,0.1,out,,,,tx-1,BTC buy,Fixture,Primary\n"
        ),
        encoding="utf-8",
    )
    service = build_normalization_service(artifacts=FilesystemArtifactStore())

    with pytest.raises(
        ValueError,
        match="normalization output directory must not be inside raw source directory",
    ):
        service.execute(
            NormalizeRequest(
                source="fixture_source",
                raw_capture_ref=to_resource_ref(raw_dir),
                normalized_output_ref=to_resource_ref(raw_dir / "normalized"),
            )
        )


class EvidenceSourceAdapter(MatchingSourceAdapter):
    @override
    def translate(self, profile: object, raw_dir: Path) -> SourceTranslationBatch:
        del profile, raw_dir
        return SourceTranslationBatch(
            drafts=(
                EconomicActivityDraft(
                    activity_id="txn-1",
                    source="fixture",
                    adapter_id="evidence_fixture",
                    timestamp=datetime(2023, 8, 6, 10, 0, 0, tzinfo=UTC),
                    location_id=LocationId("fixture:primary"),
                    classification=classification(
                        economic_kind=EconomicKind.CHAIN_TRANSFER_IN,
                        projection_hint=ProjectionHint.DEPOSIT,
                        accounting_intent_hint=AccountingIntentHint.FUNDING_INFLOW,
                        tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN,
                    ),
                    legs=(
                        economic_leg(
                            leg_id="primary_btc",
                            kind=LegKind.PRIMARY,
                            instrument="BTC",
                            quantity=Decimal("1.5"),
                        ),
                    ),
                    leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
                    tx_hash="tx-1",
                ),
            ),
            balance_evidence=(
                BalanceEvidence(
                    source=SourceId("fixture"),
                    location_id=LocationId("fixture:primary"),
                    instrument_id=InstrumentId("symbol:BTC"),
                    quantity=Decimal("2.5"),
                    as_of_at=datetime(2023, 8, 6, 12, 0, 0, tzinfo=UTC),
                    as_of_precision=TemporalPrecision.TIMESTAMP,
                    provenance=ProvenanceLocator.from_reference_ref("statement:page:1"),
                ),
            ),
            issues=(),
            reviews=(),
            location_inventory=(),
        )


class StatementEvidenceSourceAdapter(MatchingSourceAdapter):
    @override
    def translate(self, profile: object, raw_dir: Path) -> SourceTranslationBatch:
        del profile, raw_dir
        return SourceTranslationBatch(
            drafts=(),
            balance_evidence=(),
            issues=(),
            reviews=(),
            location_inventory=(),
        )

    def match_statement_document(self, pdf_path: Path, text: str) -> int:
        del pdf_path
        return 100 if "ETH 3.5" in text else 0

    def parse_statement_document(
        self, pdf_path: Path, text: str
    ) -> StatementDocumentParseResult:
        del text
        as_of_at = datetime(2023, 8, 6, 12, 0, 0, tzinfo=UTC)
        return StatementDocumentParseResult(
            pdf_file=pdf_path.name,
            recognized=True,
            statement_as_of_at=as_of_at,
            rows=(
                StatementDocumentBalanceRow(
                    source="fixture",
                    account="fixture",
                    wallet="primary",
                    balance_kind="available",
                    asset="ETH",
                    quantity=Decimal("3.5"),
                    as_of_at=as_of_at,
                    as_of_precision=TemporalPrecision.TIMESTAMP,
                    pdf_file=pdf_path.name,
                    raw_row_ref="page=1",
                ),
            ),
        )

    def resolve_statement_instrument_claims(
        self, row: StatementDocumentBalanceRow
    ) -> tuple[InstrumentIdentityClaim, ...]:
        return (
            symbol_claim(
                row.asset,
                kind_hint=InstrumentKind.CRYPTO,
            ),
        )


class EmptyFamilyTranslationAdapter(MatchingSourceAdapter):
    @override
    def classify_profile_families(
        self,
        source: str,
        raw_dir: Path,
        inventory: tuple[object, ...],
    ) -> tuple[FileFamilyClaim, ...]:
        del source, inventory
        return (
            FileFamilyClaim(
                relative_path=raw_dir.joinpath("capture.csv").name,
                adapter_id=self.manifest.adapter_id,
                family_id="recognized_export",
            ),
        )

    @override
    def translate(self, profile: object, raw_dir: Path) -> SourceTranslationBatch:
        del profile, raw_dir
        return SourceTranslationBatch(
            drafts=(), balance_evidence=(), issues=(), reviews=(), location_inventory=()
        )


def test_normalization_service_persists_balance_evidence_separately_from_derived_balances(
    tmp_path: Path,
) -> None:
    raw_dir = materialize_capture_root(tmp_path, source="fixture")
    registry = FakeSourceRegistry(
        source_adapters=(EvidenceSourceAdapter("evidence_fixture"),)
    )
    artifacts = FilesystemArtifactStore()
    service = build_registry_backed_normalization_service(
        registry=registry, artifacts=artifacts
    )
    output_dir = tmp_path / "normalized"

    response = service.execute(
        NormalizeRequest(
            source="fixture",
            raw_capture_ref=to_resource_ref(raw_dir),
            normalized_output_ref=to_resource_ref(output_dir),
        )
    )

    balance_rows = artifacts.read_rows(output_dir / "balances.csv")
    balance_evidence_rows = artifacts.read_rows(output_dir / "balance_evidence.csv")
    summary = json.loads(
        (output_dir / "normalization_summary.json").read_text(encoding="utf-8")
    )

    assert response.balance_count == 1
    assert balance_rows == [
        {
            "source": "fixture",
            "location_id": "fixture:primary",
            "instrument_id": "symbol:BTC",
            "quantity": "1.5",
            "as_of_at": "2023-08-06 10:00:00",
            "as_of_precision": "timestamp",
            "balance_kind": "available",
            "notes": "",
        }
    ]
    assert balance_evidence_rows == [
        {
            "source": "fixture",
            "location_id": "fixture:primary",
            "instrument_id": "symbol:BTC",
            "quantity": "2.5",
            "as_of_at": "2023-08-06 12:00:00",
            "as_of_precision": "timestamp",
            "balance_kind": "available",
            "capture_uid": "",
            "relative_path": "statement:page:1",
            "archive_member_path": "",
            "locator_kind": "raw_file",
            "anchor": "",
            "notes": "",
        }
    ]
    assert summary["balance_count"] == 1
    assert summary["balance_evidence_count"] == 1


def test_normalization_service_uses_shared_statement_extraction(tmp_path: Path) -> None:
    raw_dir = materialize_capture_root(tmp_path, source="fixture")
    _make_pdf(raw_dir / "statement.pdf", "ETH 3.5")
    registry = FakeSourceRegistry(
        source_adapters=(StatementEvidenceSourceAdapter("statement_fixture"),)
    )
    artifacts = FilesystemArtifactStore()
    service = build_registry_backed_normalization_service(
        registry=registry, artifacts=artifacts
    )
    output_dir = tmp_path / "normalized"

    response = service.execute(
        NormalizeRequest(
            source="fixture",
            raw_capture_ref=to_resource_ref(raw_dir),
            normalized_output_ref=to_resource_ref(output_dir),
        )
    )

    balance_evidence_rows = artifacts.read_rows(output_dir / "balance_evidence.csv")

    assert response.balance_count == 0
    assert balance_evidence_rows == [
        {
            "source": "fixture",
            "location_id": "fixture",
            "instrument_id": "symbol:ETH",
            "quantity": "3.5",
            "as_of_at": "2023-08-06 12:00:00",
            "as_of_precision": "timestamp",
            "balance_kind": "available",
            "capture_uid": "01HV4A5H7VJH7M3Y5A6B7C8D9E",
            "relative_path": "statement.pdf",
            "archive_member_path": "",
            "locator_kind": "raw_file",
            "anchor": "page=1",
            "notes": "",
        }
    ]


def test_normalization_service_blocks_mixed_capture_profiles(tmp_path: Path) -> None:
    raw_dir = materialize_capture_root(tmp_path, source="mixed-capture")
    (raw_dir / "transactions.csv").write_text(
        "timestamp,category,asset_in,amount_in,asset_out,amount_out,"
        "charge_asset,charge_amount,charge_side,rebate_asset,rebate_amount,rebate_side,"
        "tx_hash,description,account,wallet\n"
        "2023-08-06 10:00:00,trade,BTC,1.0,CAD,10.0,CAD,0.1,out,,,,tx-1,BTC buy,Fixture,Primary\n",
        encoding="utf-8",
    )
    (raw_dir / "wallet-state.json").write_text(
        json.dumps(
            {
                "wallet_state": {
                    "internalAccounts": {
                        "accounts": {
                            "one": {
                                "address": "0x1111111111111111111111111111111111111111",
                                "type": "eip155:eoa",
                                "scopes": ["eip155:1"],
                                "metadata": {"name": "Primary"},
                            }
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    service = build_normalization_service(artifacts=FilesystemArtifactStore())

    with pytest.raises(ValueError, match="blocking scan issues"):
        service.execute(
            NormalizeRequest(
                source="mixed-capture",
                raw_capture_ref=to_resource_ref(raw_dir),
                normalized_output_ref=to_resource_ref(tmp_path / "normalized"),
            )
        )


def test_normalization_service_surfaces_no_supported_activity_for_recognized_empty_translation(
    tmp_path: Path,
) -> None:
    raw_dir = materialize_capture_root(tmp_path, source="recognized-empty")
    (raw_dir / "capture.csv").write_text("header\n", encoding="utf-8")
    artifacts = FilesystemArtifactStore()
    service = build_registry_backed_normalization_service(
        registry=FakeSourceRegistry(
            source_adapters=(EmptyFamilyTranslationAdapter("recognized_empty"),)
        ),
        artifacts=artifacts,
    )
    output_dir = tmp_path / "normalized"

    response = service.execute(
        NormalizeRequest(
            source="recognized-empty",
            raw_capture_ref=to_resource_ref(raw_dir),
            normalized_output_ref=to_resource_ref(output_dir),
        )
    )

    issue_rows = artifacts.read_rows(output_dir / "exceptions.csv")

    assert response.fact_count == 0
    assert response.issue_count == 1
    assert [row["kind"] for row in issue_rows] == ["no_supported_activity"]


def test_normalization_service_persists_fact_annotations_for_filtered_drafts(
    tmp_path: Path,
) -> None:
    raw_dir = materialize_capture_root(tmp_path, source="fixture_source")
    header = (
        "timestamp,category,asset_in,amount_in,asset_out,amount_out,"
        "charge_asset,charge_amount,charge_side,rebate_asset,rebate_amount,rebate_side,"
        "tx_hash,description,account,wallet\n"
    )
    (raw_dir / "transactions.csv").write_text(
        header
        + "2023-08-04 10:00:00,trade,BTC,1.0,CAD,10.0,CAD,0.1,out,,,,tx-early,early,Fixture,Primary\n"
        + "2023-08-06 10:00:00,trade,ETH,2.0,CAD,20.0,CAD,0.2,out,,,,tx-keep,keep,Fixture,Primary\n",
        encoding="utf-8",
    )
    artifacts = FilesystemArtifactStore()
    service = build_normalization_service(artifacts=artifacts)
    output_dir = tmp_path / "normalized"

    service.execute(
        NormalizeRequest(
            source="fixture_source",
            raw_capture_ref=to_resource_ref(raw_dir),
            normalized_output_ref=to_resource_ref(output_dir),
            window_start="2023-08-05 08:34:05",
            window_end="2025-12-31 23:59:59",
        )
    )

    fact_rows = artifacts.read_rows(output_dir / "facts.csv")
    fact_annotations = json.loads(
        (output_dir / "fact_annotations.json").read_text(encoding="utf-8")
    )

    assert [row["fact_id"] for row in fact_rows] == ["fixture_source:3"]
    assert fact_annotations == [
        {
            "fact_id": fact_rows[0]["fact_id"],
            "provenance_refs": [],
            "review_markers": [],
            "adapter_metadata": [],
        }
    ]


def test_normalization_service_filters_row_reviews_outside_explicit_window(
    tmp_path: Path,
) -> None:
    raw_dir = materialize_capture_root(tmp_path, source="fixture_source")
    header = (
        "timestamp,category,asset_in,amount_in,asset_out,amount_out,"
        "charge_asset,charge_amount,charge_side,rebate_asset,rebate_amount,rebate_side,"
        "tx_hash,description,account,wallet\n"
    )
    (raw_dir / "transactions.csv").write_text(
        header
        + "2023-08-04 10:00:00,trade,BTC,1.0,CAD,-10.0,CAD,-0.1,out,,,,tx-early,early,Fixture,Primary\n"
        + "2023-08-06 10:00:00,trade,ETH,2.0,CAD,20.0,CAD,0.2,out,,,,tx-keep,keep,Fixture,Primary\n",
        encoding="utf-8",
    )
    artifacts = FilesystemArtifactStore()
    service = build_normalization_service(artifacts=artifacts)
    output_dir = tmp_path / "normalized"

    response = service.execute(
        NormalizeRequest(
            source="fixture_source",
            raw_capture_ref=to_resource_ref(raw_dir),
            normalized_output_ref=to_resource_ref(output_dir),
            window_start="2023-08-05 08:34:05",
            window_end="2025-12-31 23:59:59",
        )
    )

    review_rows = artifacts.read_rows(output_dir / "normalization_reviews.csv")
    summary = json.loads(
        (output_dir / "normalization_summary.json").read_text(encoding="utf-8")
    )

    assert response.review_count == 1
    assert [row["kind"] for row in review_rows] == ["timestamp_timezone_assumed_utc"]
    assert summary["review_count"] == 1
    assert summary["reviews_outside_normalization_window"] == 2
