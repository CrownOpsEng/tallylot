from __future__ import annotations

from pathlib import Path

import pytest


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
