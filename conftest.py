from __future__ import annotations

from pathlib import Path

import pytest
from pytest import Item

from repo_support.paths import fixtures_root, src_root
from tallylot.infrastructure.serialization import FilesystemArtifactStore

MARKERS_BY_TEST_DIR = {
    "unit": "unit",
    "contract": "contract",
    "e2e": "e2e",
}


def _adapter_root() -> Path:
    return src_root() / "tallylot" / "adapters"


def _adapter_test_dirs() -> tuple[Path, ...]:
    return tuple(sorted(path.resolve() for path in _adapter_root().glob("**/tests")))


def _adapter_test_ancestors() -> frozenset[Path]:
    adapter_root = _adapter_root()
    return frozenset(
        {
            ancestor
            for test_dir in _adapter_test_dirs()
            for ancestor in (test_dir, *test_dir.parents)
            if ancestor.is_relative_to(adapter_root)
        }
    )


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
        if _coverage_is_disabled(item):
            _drop_no_cover_marker(item)


def pytest_ignore_collect(collection_path: Path) -> bool:
    path = collection_path.resolve()
    adapter_root = _adapter_root()
    if not path.is_relative_to(adapter_root):
        return False
    if path.is_dir():
        return path not in _adapter_test_ancestors()
    return not any(path.is_relative_to(test_dir) for test_dir in _adapter_test_dirs())


def _marker_for_test_path(path: Path) -> str | None:
    for part in path.parts:
        marker = MARKERS_BY_TEST_DIR.get(part)
        if marker is not None:
            return marker
    if any(path.is_relative_to(test_dir) for test_dir in _adapter_test_dirs()):
        return "unit"
    return None


def _coverage_is_disabled(item: Item) -> bool:
    return bool(getattr(item.config.option, "no_cov", False))


def _drop_no_cover_marker(item: Item) -> None:
    item.own_markers = [mark for mark in item.own_markers if mark.name != "no_cover"]
