from __future__ import annotations

from pathlib import Path

import pytest
from pytest import Item

from repo_support.paths import fixtures_root, src_root
from tallylot.infrastructure.serialization import FilesystemArtifactStore

ADAPTER_ROOT = src_root() / "tallylot" / "adapters"
ADAPTER_TEST_DIRS = tuple(sorted(path.resolve() for path in ADAPTER_ROOT.glob("**/tests")))
ADAPTER_TEST_ANCESTORS = frozenset(
    {
        ancestor
        for test_dir in ADAPTER_TEST_DIRS
        for ancestor in (test_dir, *test_dir.parents)
        if ancestor.is_relative_to(ADAPTER_ROOT)
    }
)
MARKERS_BY_TEST_DIR = {
    "unit": "unit",
    "contract": "contract",
    "e2e": "e2e",
}


@pytest.fixture
def structured_source_dir() -> Path:
    return fixtures_root() / "structured_csv_source" / "raw"


@pytest.fixture
def baseline_export_dir() -> Path:
    return fixtures_root() / "baseline_exports"


@pytest.fixture
def verification_previous_dir() -> Path:
    return fixtures_root() / "verification" / "previous"


@pytest.fixture
def verification_current_dir() -> Path:
    return fixtures_root() / "verification" / "current"


@pytest.fixture
def artifact_store() -> FilesystemArtifactStore:
    return FilesystemArtifactStore()


def pytest_collection_modifyitems(items: list[Item]) -> None:
    for item in items:
        marker = _marker_for_test_path(item.path)
        if marker is not None:
            item.add_marker(marker)


def pytest_ignore_collect(collection_path: Path) -> bool:
    path = collection_path.resolve()
    if not path.is_relative_to(ADAPTER_ROOT):
        return False
    if path.is_dir():
        return path not in ADAPTER_TEST_ANCESTORS
    return not any(path.is_relative_to(test_dir) for test_dir in ADAPTER_TEST_DIRS)


def _marker_for_test_path(path: Path) -> str | None:
    for part in path.parts:
        marker = MARKERS_BY_TEST_DIR.get(part)
        if marker is not None:
            return marker
    if any(path.is_relative_to(test_dir) for test_dir in ADAPTER_TEST_DIRS):
        return "unit"
    return None
