from __future__ import annotations

from pathlib import Path

from tools.adapter_packs import load_adapter_packs, select_adapter_packs
from tools.scaffold_adapter import AdapterScaffoldSpec, scaffold_adapter


def test_load_adapter_packs_discovers_structured_csv_pack() -> None:
    packs = load_adapter_packs()

    assert [pack.id for pack in packs] == ["structured_csv/basic"]


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
            module_name="example_exchange",
            display_name="Example Exchange",
            description="Scaffolded source adapter.",
            version="0.1.0",
        ),
        force=False,
    )

    created_paths = {path.relative_to(repo_root) for path in created}
    assert created_paths == {
        Path("src/crypto_reconciliation/adapters/sources/example_exchange/__init__.py"),
        Path("src/crypto_reconciliation/adapters/sources/example_exchange/adapter.py"),
        Path("src/crypto_reconciliation/adapters/sources/example_exchange/tests/__init__.py"),
        Path("src/crypto_reconciliation/adapters/sources/example_exchange/tests/test_contract.py"),
        Path("src/crypto_reconciliation/adapters/sources/example_exchange/fixtures/.gitkeep"),
    }
    adapter_py = (
        repo_root / "src" / "crypto_reconciliation" / "adapters" / "sources" / "example_exchange" / "adapter.py"
    )
    assert "class ExampleExchangeSourceAdapter" in adapter_py.read_text(encoding="utf-8")
