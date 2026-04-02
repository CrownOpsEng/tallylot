from __future__ import annotations

from pathlib import Path

from tools.adapter_packs import load_adapter_packs, select_adapter_packs
from tools.scaffold_adapter import AdapterScaffoldSpec, scaffold_adapter


def test_load_adapter_packs_discovers_structured_csv_pack() -> None:
    packs = load_adapter_packs()

    pack_ids = {pack.id for pack in packs}

    assert "structured_csv/basic" in pack_ids
    assert "coinbase/retail_buy_renamed" in pack_ids
    assert "evm_wallet/wallets" in pack_ids


def test_select_adapter_packs_rejects_unknown_id() -> None:
    try:
        select_adapter_packs(selected_ids=("missing/pack",))
    except ValueError as exc:
        assert "missing/pack" in str(exc)
    else:
        raise AssertionError("expected missing pack selection to fail")


def test_scaffold_adapter_creates_package_layout(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    created = scaffold_adapter(
        spec=AdapterScaffoldSpec(
            repo_root=repo_root,
            kind="source",
            module_name="platforms/example_exchange",
            display_name="Example Exchange",
            description="Scaffolded source adapter.",
            version="0.1.0",
        ),
        force=False,
    )

    created_paths = {path.relative_to(repo_root) for path in created}
    assert created_paths == {
        Path("src/crypto_reconciliation/adapters/sources/platforms/example_exchange/__init__.py"),
        Path("src/crypto_reconciliation/adapters/sources/platforms/example_exchange/adapter.py"),
        Path("src/crypto_reconciliation/adapters/sources/platforms/example_exchange/translation.py"),
        Path("src/crypto_reconciliation/adapters/sources/platforms/example_exchange/tests/__init__.py"),
        Path("src/crypto_reconciliation/adapters/sources/platforms/example_exchange/tests/test_contract.py"),
        Path("src/crypto_reconciliation/adapters/sources/platforms/example_exchange/fixtures/.gitkeep"),
    }
    adapter_py = (
        repo_root
        / "src"
        / "crypto_reconciliation"
        / "adapters"
        / "sources"
        / "platforms"
        / "example_exchange"
        / "adapter.py"
    )
    translation_py = (
        repo_root
        / "src"
        / "crypto_reconciliation"
        / "adapters"
        / "sources"
        / "platforms"
        / "example_exchange"
        / "translation.py"
    )
    assert "class ExampleExchangeSourceAdapter" in adapter_py.read_text(encoding="utf-8")
    assert "normalize_source_drafts" in adapter_py.read_text(encoding="utf-8")
    assert "FILE_TRANSLATION_RULES" in translation_py.read_text(encoding="utf-8")


def test_scaffold_adapter_requires_source_category_namespace(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"

    try:
        scaffold_adapter(
            spec=AdapterScaffoldSpec(
                repo_root=repo_root,
                kind="source",
                module_name="example_exchange",
                display_name="Example Exchange",
                description="Scaffolded source adapter.",
                version="0.1.0",
            ),
            force=False,
        )
    except ValueError as exc:
        assert "category namespace" in str(exc)
    else:
        raise AssertionError("expected uncategorized source scaffold to fail")
