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


REPO_DATA_TEST_NAMES = {
    "test_coinbase_adapter_normalizes_repo_exports",
    "test_wealthsimple_adapter_normalizes_repo_exports",
    "test_crypto_com_adapter_normalizes_repo_exports",
    "test_shakepay_adapter_normalizes_repo_exports",
    "test_ledger_live_adapter_normalizes_repo_exports",
    "test_near_adapter_normalizes_repo_exports",
    "test_binance_adapter_converts_filename_timezone_to_utc",
    "test_binance_adapter_surfaces_repo_transaction_history_transfer_and_p2p_gaps",
    "test_evm_explorer_adapter_normalizes_bsc_repo_exports",
    "test_evm_explorer_adapter_surfaces_polygon_review_rows_without_importing_them",
    "test_evm_explorer_adapter_surfaces_eth_gala_review_rows_without_importing_them",
    "test_gtrade_adapter_surfaces_report_limits_without_guessing",
    "test_build_source_profile_smoke_covers_major_sources",
    "test_timezone_validation_passes_for_repo_supported_sources",
    "test_normalize_source_uses_current_adapter_support_even_with_stale_profile_json",
    "test_profile_wallet_identifiers_extracts_ledger_live_accounts",
    "test_build_wallet_inventory_includes_gtrade_alias_issue",
    "test_refresh_wallet_inventory_writes_artifacts",
    "test_profile_wallet_identifiers_resolves_adapter_from_profile_without_hint",
}


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
            item.add_marker(pytest.mark.repo_data)
            item.add_marker(pytest.mark.slow)
            continue
        if item.name in REPO_DATA_TEST_NAMES:
            item.add_marker(pytest.mark.repo_data)
            item.add_marker(pytest.mark.slow)
