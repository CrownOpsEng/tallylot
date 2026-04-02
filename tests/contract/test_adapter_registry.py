from __future__ import annotations

from crypto_reconciliation.infrastructure.discovery import build_registry


def test_adapter_registry_discovers_expected_adapters() -> None:
    registry = build_registry()

    source_ids = {str(adapter.manifest.adapter_id) for adapter in registry.source_adapters}
    output_ids = {str(adapter.manifest.adapter_id) for adapter in registry.output_adapters}

    assert "structured_csv" in source_ids
    assert "coinbase" in source_ids
    assert "wealthsimple" in source_ids
    assert "binance" in source_ids
    assert "crypto_com" in source_ids
    assert "shakepay" in source_ids
    assert "ledger_live" in source_ids
    assert "near" in source_ids
    assert "gtrade" in source_ids
    assert "evm_explorer" in source_ids
    assert "evm_wallet" in source_ids
    assert "blockchain_stub" in source_ids
    assert "cointracking_portfolio" in source_ids
    assert "platform_api_stub" in source_ids
    assert "cointracking_csv" in output_ids
    assert "cointracking_api" in output_ids
