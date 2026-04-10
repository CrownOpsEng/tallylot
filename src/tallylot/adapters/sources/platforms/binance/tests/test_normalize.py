from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from tallylot.adapters.sources.platforms.binance.adapter import _BinanceAdapter
from tallylot.adapters.support.drafts import compile_activity_drafts
from tallylot.application.evidence.statement_extraction import (
    StatementExtractionService,
)
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.transactions import (
    AccountingIntentHint,
    EconomicKind,
    ProjectionHint,
    TaxTreatmentHint,
)
from tallylot.ports.evidence import (
    StatementDocumentBalanceRow,
    StatementDocumentParseResult,
)
from tallylot.ports.source_profiles import FileInventoryEntry
from tests.support.services import FakeSourceRegistry, build_source_profile


def test_binance_adapter_handles_supported_and_review_required_rows(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path
    (raw_dir / "Binance-Spot-Trade-History-202603230406(UTC--6)_abcd.csv").write_text(
        "Time,Pair,Side,Price,Executed,Amount,Fee\n"
        "23-09-20 18:20:55,ALGOUSDT,SELL,0.0997,103ALGO,10.2691USDT,0.00003593BNB\n",
        encoding="utf-8",
    )
    (raw_dir / "Binance-Deposit-History-202603230411(UTC--6)_abcd.csv").write_text(
        "Time,Coin,Network,Amount,Address,TXID,Status\n23-05-06 23:05:55,USDT,MATIC,125.564991,addr,tx-dep,Completed\n",
        encoding="utf-8",
    )
    (raw_dir / "Binance-Withdraw-History-202603230412(UTC--6)_abcd.csv").write_text(
        "Time,Coin,Network,Amount,Fee,Address,TXID,Status\n"
        "23-09-20 22:25:57,HNT,SOL,12.013,0.11,addr,tx-wd,Completed\n",
        encoding="utf-8",
    )
    (raw_dir / "Binance-Transaction-History-202603230400(UTC--6)_abcd.csv").write_text(
        "User ID,Time,Account,Operation,Coin,Change,Remark\n"
        "1,23-08-06 02:34:03,Spot,ETH 2.0 Staking Rewards,BETH,0.00000599,\n"
        "1,23-09-20 18:46:46,Spot,Small Assets Exchange BNB,ETH,-0.00005643,ETH to BNB\n"
        "1,23-09-20 18:46:46,Spot,Small Assets Exchange BNB,BNB,0.00041767,ETH to BNB\n"
        "1,23-09-20 18:17:41,USD-M Futures,Transfer Between Spot Account and UM Futures Account,USDT,-43.90477684,\n"
        "1,23-09-20 18:17:41,Spot,Transfer Between Spot Account and UM Futures Account,USDT,43.90477684,\n"
        "1,21-05-11 00:44:33,Spot,Binance Convert,ETH,0.03158115,\n",
        encoding="utf-8",
    )

    result = _BinanceAdapter().translate(
        build_source_profile(
            adapter_id="binance", raw_dir=str(raw_dir), source="Binance"
        ),
        raw_dir,
    )
    facts = compile_activity_drafts(result.drafts)

    assert len(facts) == 5
    assert len(result.issues) == 3
    projection_hints = {row.projection_hint for row in facts}
    assert ProjectionHint.TRADE in projection_hints
    assert ProjectionHint.DEPOSIT in projection_hints
    assert ProjectionHint.WITHDRAWAL in projection_hints
    assert ProjectionHint.STAKING in projection_hints
    economic_kinds = {row.economic_kind for row in facts}
    assert EconomicKind.STAKING_REWARD in economic_kinds
    assert AccountingIntentHint.INCOME_RECOGNITION in {
        row.accounting_intent_hint for row in facts
    }
    assert TaxTreatmentHint.STAKING_INCOME in {row.tax_treatment_hint for row in facts}
    assert any(
        "Transfer Between Spot Account and UM Futures Account" in row.message
        for row in result.issues
    )


def test_binance_convert_date_updated_covers_transaction_history_one_second_skew(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path
    (
        raw_dir / "Binance-Convert-Order-History-202603230441(UTC--6)_abcd.csv"
    ).write_text(
        "Time,Wallet,Pair,Type,Sell,Buy,Price,Inverse Price,Date Updated,Status\n"
        "21-05-11 00:44:32,SPOT,ETHBUSD,Instant,124.60184573 BUSD,0.03158115 ETH,x,x,21-05-11 00:44:33,Successful\n",
        encoding="utf-8",
    )
    (raw_dir / "Binance-Transaction-History-202603230400(UTC--6)_abcd.csv").write_text(
        "User ID,Time,Account,Operation,Coin,Change,Remark\n1,21-05-11 00:44:33,Spot,Binance Convert,ETH,0.03158115,\n",
        encoding="utf-8",
    )

    result = _BinanceAdapter().translate(
        build_source_profile(
            adapter_id="binance", raw_dir=str(raw_dir), source="Binance"
        ),
        raw_dir,
    )

    assert len(compile_activity_drafts(result.drafts)) == 1
    assert len(result.issues) == 0


def test_binance_transaction_history_skips_p2p_rows_when_c2c_history_exists(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path
    (raw_dir / "Binance-C2C-Order-History-202603230441(UTC--6)_abcd.csv").write_text(
        "Order Number,Created Time,Order Type,Asset,Quantity,Total Price,Fiat Type,Counterparty,Status\n"
        "123,23-09-20 19:48:03,SELL,USDT,891,891,CAD,merchant,Completed\n",
        encoding="utf-8",
    )
    (raw_dir / "Binance-Transaction-History-202603230400(UTC--6)_abcd.csv").write_text(
        "User ID,Time,Account,Operation,Coin,Change,Remark\n"
        "1,23-09-20 19:48:03,Funding,P2P Trading,USDT,-891,P2P - 123\n",
        encoding="utf-8",
    )

    result = _BinanceAdapter().translate(
        build_source_profile(
            adapter_id="binance", raw_dir=str(raw_dir), source="Binance"
        ),
        raw_dir,
    )
    facts = compile_activity_drafts(result.drafts)

    assert len(facts) == 1
    assert facts[0].economic_kind == EconomicKind.P2P_TRADE
    assert facts[0].projection_hint == ProjectionHint.TRADE
    assert facts[0].accounting_intent_hint == AccountingIntentHint.ASSET_EXCHANGE
    assert facts[0].tax_treatment_hint == TaxTreatmentHint.CAPITAL_EXCHANGE
    assert len(result.issues) == 0


def test_binance_adapter_reads_nested_bundle_paths(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    bundle_dir = raw_dir / "bundle_a"
    bundle_dir.mkdir(parents=True)
    (bundle_dir / "Binance-C2C-Order-History-202603230441(UTC--6)_abcd.csv").write_text(
        "Order Number,Created Time,Order Type,Asset,Quantity,Total Price,Fiat Type,Counterparty,Status\n"
        "123,23-09-20 19:48:03,SELL,USDT,891,891,CAD,merchant,Completed\n",
        encoding="utf-8",
    )
    (
        bundle_dir / "Binance-Transaction-History-202603230400(UTC--6)_abcd.csv"
    ).write_text(
        "User ID,Time,Account,Operation,Coin,Change,Remark\n"
        "1,23-09-20 19:48:03,Funding,P2P Trading,USDT,-891,P2P - 123\n",
        encoding="utf-8",
    )

    result = _BinanceAdapter().translate(
        build_source_profile(
            adapter_id="binance", raw_dir=str(raw_dir), source="Binance"
        ),
        raw_dir,
    )
    facts = compile_activity_drafts(result.drafts)

    assert len(facts) == 1
    assert facts[0].economic_kind == EconomicKind.P2P_TRADE
    assert facts[0].projection_hint == ProjectionHint.TRADE
    assert facts[0].accounting_intent_hint == AccountingIntentHint.ASSET_EXCHANGE
    assert facts[0].tax_treatment_hint == TaxTreatmentHint.CAPITAL_EXCHANGE
    assert not result.issues


def test_binance_translation_priority_is_not_path_order_dependent(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    transaction_dir = raw_dir / "a_transaction"
    convert_dir = raw_dir / "z_convert"
    transaction_dir.mkdir(parents=True)
    convert_dir.mkdir(parents=True)
    (
        convert_dir / "Binance-Convert-Order-History-202603230441(UTC--6)_abcd.csv"
    ).write_text(
        "Time,Wallet,Pair,Type,Sell,Buy,Price,Inverse Price,Date Updated,Status\n"
        "21-05-11 00:44:32,SPOT,ETHBUSD,Instant,124.60184573 BUSD,0.03158115 ETH,x,x,21-05-11 00:44:33,Successful\n",
        encoding="utf-8",
    )
    (
        transaction_dir / "Binance-Transaction-History-202603230400(UTC--6)_abcd.csv"
    ).write_text(
        "User ID,Time,Account,Operation,Coin,Change,Remark\n1,21-05-11 00:44:33,Spot,Binance Convert,ETH,0.03158115,\n",
        encoding="utf-8",
    )

    result = _BinanceAdapter().translate(
        build_source_profile(
            adapter_id="binance", raw_dir=str(raw_dir), source="Binance"
        ),
        raw_dir,
    )

    assert len(compile_activity_drafts(result.drafts)) == 1
    assert not result.issues


def test_binance_adapter_surfaces_unmatched_export_files(tmp_path: Path) -> None:
    raw_dir = tmp_path
    (raw_dir / "Binance-Unknown-History-202603230441(UTC--6)_abcd.csv").write_text(
        "Header\nvalue\n",
        encoding="utf-8",
    )

    result = _BinanceAdapter().translate(
        build_source_profile(
            adapter_id="binance", raw_dir=str(raw_dir), source="Binance"
        ),
        raw_dir,
    )

    assert not compile_activity_drafts(result.drafts)
    assert len(result.issues) == 1
    assert result.issues[0].kind == "unsupported_file"


def test_binance_statement_service_emits_latest_balance_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "older.pdf").write_bytes(b"older")
    (raw_dir / "latest.pdf").write_bytes(b"latest")

    older_as_of = datetime(2026, 2, 1, tzinfo=UTC)
    latest_as_of = datetime(2026, 3, 23, tzinfo=UTC)

    def fake_parse_statement_document(
        path: Path, text: str
    ) -> StatementDocumentParseResult:
        del text
        if path.name == "older.pdf":
            return StatementDocumentParseResult(
                pdf_file=path.name,
                recognized=True,
                statement_as_of_at=older_as_of,
                rows=(
                    StatementDocumentBalanceRow(
                        source="Binance",
                        account="Binance",
                        wallet="Spot",
                        balance_kind="available",
                        asset="USDT",
                        quantity=Decimal("1"),
                        as_of_at=older_as_of,
                        as_of_precision=TemporalPrecision.DATE,
                        pdf_file=path.name,
                        raw_row_ref="Spot Top 10 Holdings",
                    ),
                ),
            )
        return StatementDocumentParseResult(
            pdf_file=path.name,
            recognized=True,
            statement_as_of_at=latest_as_of,
            rows=(
                StatementDocumentBalanceRow(
                    source="Binance",
                    account="Binance",
                    wallet="Funding",
                    balance_kind="available",
                    asset="USDT",
                    quantity=Decimal("0.009526"),
                    as_of_at=latest_as_of,
                    as_of_precision=TemporalPrecision.DATE,
                    pdf_file=path.name,
                    raw_row_ref="Funding Top 10 Holdings",
                    notes="Statement-backed quantity aggregated from Binance holdings sections.",
                ),
                StatementDocumentBalanceRow(
                    source="Binance",
                    account="Binance",
                    wallet="Spot",
                    balance_kind="available",
                    asset="USDT",
                    quantity=Decimal("0.000340"),
                    as_of_at=latest_as_of,
                    as_of_precision=TemporalPrecision.DATE,
                    pdf_file=path.name,
                    raw_row_ref="Spot Top 10 Holdings",
                    notes="Statement-backed quantity aggregated from Binance holdings sections.",
                ),
                StatementDocumentBalanceRow(
                    source="Binance",
                    account="Binance",
                    wallet="Spot",
                    balance_kind="available",
                    asset="SOLO",
                    quantity=Decimal("0.920099"),
                    as_of_at=latest_as_of,
                    as_of_precision=TemporalPrecision.DATE,
                    pdf_file=path.name,
                    raw_row_ref="Spot Top 10 Holdings",
                    notes="Statement-backed quantity aggregated from Binance holdings sections.",
                ),
            ),
        )

    def fake_extract_pdf_text(path: Path) -> str:
        del path
        return "statement"

    def fake_match_statement_document(path: Path, text: str) -> int:
        del path, text
        return 100

    monkeypatch.setattr(
        "tallylot.application.evidence.statement_extraction.service._extract_pdf_text",
        fake_extract_pdf_text,
    )
    monkeypatch.setattr(
        "tallylot.adapters.sources.platforms.binance.adapter._parse_statement_document",
        fake_parse_statement_document,
    )
    monkeypatch.setattr(
        "tallylot.adapters.sources.platforms.binance.adapter._match_statement_document",
        fake_match_statement_document,
    )

    result = StatementExtractionService(
        FakeSourceRegistry((_BinanceAdapter(),))
    ).extract_source_balance_evidence(
        build_source_profile(
            adapter_id="binance",
            raw_dir=str(raw_dir),
            source="Binance",
            file_inventory=(
                FileInventoryEntry(
                    relative_path="older.pdf",
                    suffix=".pdf",
                    size_bytes=5,
                    sha256="older",
                    source_path=str(raw_dir / "older.pdf"),
                    capture_uid="capture-1",
                    source="Binance",
                    evidence_role="statement_source",
                    originality_class="upstream_original",
                ),
                FileInventoryEntry(
                    relative_path="latest.pdf",
                    suffix=".pdf",
                    size_bytes=6,
                    sha256="latest",
                    source_path=str(raw_dir / "latest.pdf"),
                    capture_uid="capture-1",
                    source="Binance",
                    evidence_role="statement_source",
                    originality_class="upstream_original",
                ),
            ),
        ),
        raw_dir,
    )

    evidence_rows = [row.to_row() for row in result.balance_evidence]

    assert evidence_rows == [
        {
            "source": "Binance",
            "location_id": "binance",
            "instrument_id": "symbol:SOLO@binance",
            "quantity": "0.920099",
            "as_of_at": "2026-03-23",
            "as_of_precision": "date",
            "balance_kind": "available",
            "capture_uid": "capture-1",
            "relative_path": "latest.pdf",
            "archive_member_path": "",
            "locator_kind": "raw_file",
            "anchor": "Spot Top 10 Holdings",
            "notes": "Statement-backed quantity aggregated from Binance holdings sections.",
        },
        {
            "source": "Binance",
            "location_id": "binance",
            "instrument_id": "symbol:USDT@binance",
            "quantity": "0.009866",
            "as_of_at": "2026-03-23",
            "as_of_precision": "date",
            "balance_kind": "available",
            "capture_uid": "capture-1",
            "relative_path": "latest.pdf",
            "archive_member_path": "",
            "locator_kind": "raw_file",
            "anchor": "Funding Top 10 Holdings + Spot Top 10 Holdings",
            "notes": "Statement-backed quantity aggregated from Binance holdings sections.",
        },
    ]
