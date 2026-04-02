from __future__ import annotations

from pathlib import Path

import pytest

from tallylot.adapters.outputs.cointracking_api import ADAPTER as COINTRACKING_API_ADAPTER
from tallylot.adapters.outputs.generic_http import ADAPTER as GENERIC_HTTP_ADAPTER
from tallylot.adapters.sources.stubs.blockchain import ADAPTER as BLOCKCHAIN_STUB_ADAPTER
from tallylot.adapters.sources.stubs.platform_api import ADAPTER as PLATFORM_API_STUB_ADAPTER
from tallylot.domain.types import AdapterId, SourceId
from tallylot.infrastructure.ai import LocalStubModelGateway, NullModelGateway
from tallylot.infrastructure.storage.sqlite_stub import SqliteStorageStub
from tallylot.ports.ai import ReviewRequest
from tallylot.ports.source_profiles import SourceProfile


def _stub_profile() -> SourceProfile:
    return SourceProfile(
        source=SourceId("stub"),
        raw_dir="/tmp/raw",
        adapter_id=AdapterId("stub"),
        manifest_fingerprint="fixture",
        file_inventory=(),
        supported=False,
    )


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
        COINTRACKING_API_ADAPTER.render((), tmp_path / "out.csv")
    with pytest.raises(NotImplementedError):
        GENERIC_HTTP_ADAPTER.render((), tmp_path / "out.csv")


def test_source_stub_adapters_raise_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        BLOCKCHAIN_STUB_ADAPTER.translate(_stub_profile(), Path())
    with pytest.raises(NotImplementedError):
        PLATFORM_API_STUB_ADAPTER.translate(_stub_profile(), Path())
