from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from tallylot.application.evidence.evidence_sets.builder import _statement_records
from tallylot.application.evidence.statement_extraction import (
    CollectedStatementDocument,
    StatementDocumentCollectionResult,
)
from tallylot.domain.captures import ProvenanceLocator
from tallylot.domain.evidence import (
    EvidenceMemberStatus,
    EvidenceSelectionBasis,
)
from tallylot.domain.issues import IssueRecord
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import CaptureUid
from tallylot.ports.evidence import (
    StatementDocumentBalanceRow,
    StatementDocumentParseResult,
)
from tallylot.ports.source_profiles import FileInventoryEntry
from tests.support.services import build_source_profile


def test_statement_records_use_contract_observation_keys() -> None:
    latest_document = _collected_statement_document(
        relative_path="latest.pdf",
        statement_as_of_at=datetime(2026, 3, 23, tzinfo=UTC),
        member_status=EvidenceMemberStatus.SELECTED,
        selected=True,
        rows=(
            StatementDocumentBalanceRow(
                source="coinbase",
                account="Main",
                wallet="Wallet",
                balance_kind="asset_balance",
                asset="BTC",
                quantity=Decimal("1.25"),
                as_of_at=datetime(2026, 3, 23, tzinfo=UTC),
                as_of_precision=TemporalPrecision.TIMESTAMP,
                pdf_file="latest.pdf",
                raw_row_ref="row-1",
            ),
        ),
    )
    older_document = _collected_statement_document(
        relative_path="older.pdf",
        statement_as_of_at=datetime(2026, 2, 23, tzinfo=UTC),
        member_status=EvidenceMemberStatus.SUPERSEDED,
        selected=False,
    )

    selections, _, observations = _statement_records(
        profile=build_source_profile(adapter_id="coinbase", source="coinbase"),
        capture_uid="capture-1",
        capture_manifest_fingerprint="manifest-1",
        documents=StatementDocumentCollectionResult(
            collected_documents=(latest_document, older_document),
            issues=(),
            reviews=(),
        ),
    )

    selection_lookup = {selection.key: selection for selection in selections}

    assert selection_lookup[("statement_document", "latest.pdf", "")].basis is (
        EvidenceSelectionBasis.FRESHNESS
    )
    assert selection_lookup[("statement_document", "older.pdf", "")].basis is (
        EvidenceSelectionBasis.FRESHNESS
    )
    assert [observation.record.key for observation in observations] == [
        ("document",),
        ("row-1",),
    ]


def test_statement_records_preserve_blocking_gap_refs_for_missing_dates() -> None:
    issue = IssueRecord(
        issue_id="coinbase:statement.pdf:statement_document_missing_as_of",
        source="coinbase",
        adapter_id="coinbase",
        severity="high",
        kind="statement_document_missing_as_of",
        message="missing statement date",
        raw_file="statement.pdf",
        raw_provenance=ProvenanceLocator(
            capture_uid=CaptureUid("capture-1"),
            relative_path="statement.pdf",
            locator_kind="raw_file",
        ),
    )

    selections, _, observations = _statement_records(
        profile=build_source_profile(adapter_id="coinbase", source="coinbase"),
        capture_uid="capture-1",
        capture_manifest_fingerprint="manifest-1",
        documents=StatementDocumentCollectionResult(
            collected_documents=(
                _collected_statement_document(
                    relative_path="statement.pdf",
                    statement_as_of_at=None,
                    member_status=EvidenceMemberStatus.BLOCKED,
                    selected=False,
                ),
            ),
            issues=(issue,),
            reviews=(),
        ),
    )

    assert not observations
    assert selections == (
        type(selections[0])(
            evidence_set_id="",
            selection_id="",
            key=("statement_document", "statement.pdf", ""),
            fingerprint="",
            basis=EvidenceSelectionBasis.UPSTREAM_GAP,
            blocking_gap_refs=(issue.issue_id,),
        ),
    )


def _collected_statement_document(
    *,
    relative_path: str,
    statement_as_of_at: datetime | None,
    member_status: EvidenceMemberStatus,
    selected: bool,
    rows: tuple[StatementDocumentBalanceRow, ...] = (),
) -> CollectedStatementDocument:
    return CollectedStatementDocument(
        entry=FileInventoryEntry(
            relative_path=relative_path,
            suffix=".pdf",
            size_bytes=1,
            sha256=f"sha256:{relative_path}",
        ),
        parsed=StatementDocumentParseResult(
            pdf_file=relative_path,
            recognized=True,
            statement_as_of_at=statement_as_of_at,
            rows=rows,
        ),
        locator=(relative_path, ""),
        member_status=member_status,
        selected=selected,
        statement_as_of_precision=(
            TemporalPrecision.TIMESTAMP if statement_as_of_at is not None else None
        ),
        document_effective_precision=None,
    )
