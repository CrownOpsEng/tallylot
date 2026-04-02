from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.application.dtos import BaselineValidateRequest
from crypto_reconciliation.application.services.baseline import (
    BaselineValidationService,
    _cad_flow_by_type,
    _exchange_reconciliation,
    _find_export,
    _source_activity,
)
from crypto_reconciliation.infrastructure.serialization.filesystem import FilesystemArtifactStore


def test_exchange_reconciliation_includes_exchange_only_assets() -> None:
    rows = _exchange_reconciliation(
        current_rows=[
            {
                "Ticker": "BTC",
                "Amount": "1.0",
            }
        ],
        exchange_rows=[
            {
                "Amount": "1.0",
                "Currency": "BTC",
            },
            {
                "Amount": "5.0",
                "Currency": "ETH",
            },
        ],
    )

    assert rows == [
        {
            "ticker": "BTC",
            "current_balance_amount": "1.0",
            "exchange_balance_amount": "1.0",
            "delta": "0.0",
            "status": "matched",
        },
        {
            "ticker": "ETH",
            "current_balance_amount": "0",
            "exchange_balance_amount": "5.0",
            "delta": "-5.0",
            "status": "drift",
        },
    ]


def test_source_activity_includes_balance_only_sources() -> None:
    rows = _source_activity(
        trade_rows=[
            {
                "Exchange": "Coinbase",
                "Date": "2023-08-05 08:34:04",
            }
        ],
        exchange_rows=[
            {
                "Exchange": "Coinbase",
            },
            {
                "Exchange": "Binance",
            },
        ],
    )

    assert rows == [
        {
            "source": "Binance",
            "first_timestamp": "",
            "last_timestamp": "",
            "transaction_count": "0",
            "has_balance_rows": "yes",
        },
        {
            "source": "Coinbase",
            "first_timestamp": "2023-08-05 08:34:04",
            "last_timestamp": "2023-08-05 08:34:04",
            "transaction_count": "1",
            "has_balance_rows": "yes",
        },
    ]


def test_cad_flow_by_type_treats_blank_numeric_values_as_zero() -> None:
    rows = _cad_flow_by_type(
        trade_rows=[
            {
                "Type": "Trade",
                "Buy": "",
                "Cur.": "CAD",
                "Sell": "10.0",
                "Cur..1": "CAD",
                "Fee": "",
                "Cur..2": "CAD",
            }
        ]
    )

    assert rows == [
        {
            "type": "Trade",
            "cad_bought": "0",
            "cad_sold": "10.0",
            "cad_fees": "0",
            "net_cad": "-10.0",
        }
    ]


def test_find_export_rejects_ambiguous_matches(tmp_path: Path) -> None:
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    (export_dir / "Trade Table A.csv").write_text("x\n", encoding="utf-8")
    (export_dir / "Trade Table B.csv").write_text("x\n", encoding="utf-8")

    try:
        _find_export(export_dir, "Trade Table")
    except FileNotFoundError as exc:
        assert "exactly one export" in str(exc)
    else:
        raise AssertionError("expected ambiguous baseline export lookup to fail")


def test_baseline_validation_service_writes_relocation_safe_artifacts(
    baseline_export_dir: Path,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "baseline"

    response = BaselineValidationService(FilesystemArtifactStore()).execute(
        BaselineValidateRequest(export_dir=baseline_export_dir, output_dir=output_dir)
    )

    reconciliation_rows = FilesystemArtifactStore().read_rows(output_dir / "baseline_exchange_reconciliation.csv")

    assert response.asset_count >= 1
    assert output_dir.joinpath("baseline_summary.json").exists()
    assert any(row["ticker"] == "CAD" for row in reconciliation_rows)
