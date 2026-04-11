from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

from tallylot.domain.captures import ProvenanceLocator
from tallylot.domain.checkpoints import BalanceSnapshot
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.reconciliation import BalanceEvidence
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import LocationId, SourceId
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.infrastructure.storage import FilesystemEvidenceRepository
from tests.support.skill_scripts import load_skill_main

if TYPE_CHECKING:
    import pytest


def test_reconciliation_balance_skill_runner_executes_runtime_workflows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_root = tmp_path / "normalized"
    analysis_root = tmp_path / "analysis"
    input_root.mkdir()
    (input_root / "clean-source").mkdir()
    (input_root / "issue-source").mkdir()
    as_of = datetime(2026, 3, 23, tzinfo=UTC)
    repository = FilesystemEvidenceRepository()

    repository.write_balance_snapshots(
        input_root / "clean-source" / "balances.csv",
        (
            BalanceSnapshot(
                source=SourceId("clean-source"),
                location_id=LocationId("clean-source"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("1.0"),
                as_of_at=as_of,
                as_of_precision=TemporalPrecision.DATE,
            ),
        ),
    )
    repository.write_balance_evidence(
        input_root / "clean-source" / "balance_evidence.csv",
        (
            BalanceEvidence(
                source=SourceId("clean-source"),
                location_id=LocationId("clean-source"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("1.0"),
                as_of_at=as_of,
                as_of_precision=TemporalPrecision.DATE,
                provenance=ProvenanceLocator.from_reference_ref("clean.csv"),
            ),
        ),
    )
    repository.write_balance_snapshots(
        input_root / "issue-source" / "balances.csv",
        (
            BalanceSnapshot(
                source=SourceId("issue-source"),
                location_id=LocationId("issue-source"),
                instrument_id=InstrumentId("ETH"),
                quantity=Decimal("2.0"),
                as_of_at=as_of,
                as_of_precision=TemporalPrecision.DATE,
            ),
        ),
    )
    repository.write_balance_evidence(
        input_root / "issue-source" / "balance_evidence.csv",
        (),
    )
    monkeypatch.chdir(tmp_path)
    main = load_skill_main(
        ".agents/skills/reconciliation-balance-operations/scripts/reconciliation_balance_operations.py"
    )

    exit_code = main(
        (
            "run",
            "--input-root",
            str(input_root),
            "--analysis-root",
            str(analysis_root),
        )
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
    payload = json.loads(captured.out)
    summary = json.loads(
        (analysis_root / "balance_reconciliation_summary.json").read_text(
            encoding="utf-8"
        )
    )
    blocker_rows = FilesystemArtifactStore().read_rows(
        analysis_root / "balance_reconciliation_blockers.csv"
    )

    assert payload["summary_output_ref"] == str(
        analysis_root / "balance_reconciliation_summary.json"
    )
    assert summary["latest_portfolio_clean_date"] == ""
    assert summary["latest_portfolio_source_backed_date"] == ""
    assert summary["latest_clean_source_date"] == "2026-03-23"
    assert summary["latest_source_backed_date"] == "2026-03-23"
    assert summary["latest_observed_assertion_date"] == "2026-03-23"
    assert blocker_rows[0]["source"] == "issue-source"
