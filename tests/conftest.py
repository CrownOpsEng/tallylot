from __future__ import annotations

from pathlib import Path

import pytest
from pytest import Item

from crypto_reconciliation.infrastructure.serialization import FilesystemArtifactStore

MARKERS_BY_TEST_DIR = {
    "unit": "unit",
    "contract": "contract",
    "e2e": "e2e",
}


@pytest.fixture
def structured_source_dir() -> Path:
    return Path(__file__).parent / "fixtures" / "structured_csv_source" / "raw"


@pytest.fixture
def baseline_export_dir() -> Path:
    return Path(__file__).parent / "fixtures" / "baseline_exports"


@pytest.fixture
def verification_previous_dir() -> Path:
    return Path(__file__).parent / "fixtures" / "verification" / "previous"


@pytest.fixture
def verification_current_dir() -> Path:
    return Path(__file__).parent / "fixtures" / "verification" / "current"


@pytest.fixture
def artifact_store() -> FilesystemArtifactStore:
    return FilesystemArtifactStore()


def pytest_collection_modifyitems(items: list[Item]) -> None:
    for item in items:
        marker = _marker_for_test_path(item.path)
        if marker is not None:
            item.add_marker(marker)


def _marker_for_test_path(path: Path) -> str | None:
    for part in path.parts:
        marker = MARKERS_BY_TEST_DIR.get(part)
        if marker is not None:
            return marker
    return None
