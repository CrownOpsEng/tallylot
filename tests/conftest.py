from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "06_scripts"
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

@pytest.fixture
def fixture_root() -> Path:
    return FIXTURE_ROOT


@pytest.fixture
def copy_fixture_tree(tmp_path: Path, fixture_root: Path):
    def _copy(relative_path: str, *, destination_name: str | None = None) -> Path:
        source = fixture_root / relative_path
        if not source.exists():
            raise FileNotFoundError(f"Fixture path does not exist: {source}")
        target = tmp_path / (destination_name or source.name)
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        return target

    return _copy


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        path = Path(str(item.fspath))
        if "tests/e2e" in path.as_posix():
            item.add_marker(pytest.mark.e2e)
