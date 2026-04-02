from __future__ import annotations

from pathlib import Path

import pytest

from crypto_reconciliation.adapters.outputs.cointracking_api import CoinTrackingApiStubAdapter
from crypto_reconciliation.adapters.outputs.generic_http import GenericHttpOutputStubAdapter
from crypto_reconciliation.adapters.sources.blockchain.stub import BlockchainSourceStubAdapter
from crypto_reconciliation.adapters.sources.platform_api.stub import PlatformApiSourceStubAdapter
from crypto_reconciliation.infrastructure.ai import LocalStubModelGateway, NullModelGateway
from crypto_reconciliation.infrastructure.storage.sqlite_stub import SqliteStorageStub
from crypto_reconciliation.ports.ai import ReviewRequest


def test_ai_stubs_return_deterministic_reviews() -> None:
    request = ReviewRequest(task="review", subject="subject", context={"b": 2, "a": 1})

    null_response = NullModelGateway().review(request)
    stub_response = LocalStubModelGateway().review(request)

    assert null_response.provider == "null"
    assert stub_response.findings == ("a", "b")


def test_sqlite_storage_stub_describes_placeholder(tmp_path: Path) -> None:
    stub = SqliteStorageStub(database_path=tmp_path / "workspace.sqlite3")

    assert stub.describe()["status"] == "stub"


def test_output_stub_adapters_raise_not_implemented(tmp_path: Path) -> None:
    with pytest.raises(NotImplementedError):
        CoinTrackingApiStubAdapter().render((), tmp_path / "out.csv")
    with pytest.raises(NotImplementedError):
        GenericHttpOutputStubAdapter().render((), tmp_path / "out.csv")


def test_source_stub_adapters_raise_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        BlockchainSourceStubAdapter().normalize(None, Path())  # type: ignore[arg-type]
    with pytest.raises(NotImplementedError):
        PlatformApiSourceStubAdapter().normalize(None, Path())  # type: ignore[arg-type]
