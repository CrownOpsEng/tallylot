from __future__ import annotations

import json
from pathlib import Path

from repo_support import paths as repo_paths
from tools.adapter_packs import _load_adapter_packs, select_adapter_packs
from tools.scaffold_adapter import _AdapterScaffoldSpec, _build_argument_parser, _scaffold_adapter


def test_load_adapter_packs_discovers_structured_csv_pack() -> None:
    packs = _load_adapter_packs()

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


def test_load_adapter_packs_uses_active_repo_root_by_default(tmp_path: Path) -> None:
    pack_root = tmp_path / "tests" / "fixtures" / "adapter_packs" / "example" / "basic"
    (pack_root / "raw").mkdir(parents=True)
    (pack_root / "expected").mkdir()
    (pack_root / "pack.json").write_text(
        '{"adapter":"example","source":"Example","expected_adapter":"example","capabilities":["normalize"]}\n',
        encoding="utf-8",
    )

    with repo_paths.override_repo_root(tmp_path):
        packs = _load_adapter_packs()

    assert len(packs) == 1
    assert packs[0].id == "example/basic"


def test_scaffold_parser_uses_active_repo_root_by_default(tmp_path: Path) -> None:
    with repo_paths.override_repo_root(tmp_path):
        args = _build_argument_parser().parse_args(
            [
                "source",
                "platforms/example_exchange",
                "Example Exchange",
            ]
        )

    assert args.repo_root is None


def test_scaffold_adapter_creates_package_layout(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "pyrightconfig.json").write_text(
        """\
{
  "extends": "./pyrightconfig.tests.json",
  "include": ["src", "tests", "tools", "conftest.py"]
}
""",
        encoding="utf-8",
    )
    created = _scaffold_adapter(
        spec=_AdapterScaffoldSpec(
            repo_root=repo_root,
            kind="source",
            module_name="platforms/example_exchange",
            display_name="Example Exchange",
            description="Scaffolded source adapter.",
            version="0.1.0",
        ),
        force=False,
    )
    pyright_config = json.loads((repo_root / "pyrightconfig.tests.json").read_text(encoding="utf-8"))

    created_paths = {path.relative_to(repo_root) for path in created}
    assert created_paths == {
        Path("src/tallylot/adapters/sources/platforms/example_exchange/__init__.py"),
        Path("src/tallylot/adapters/sources/platforms/example_exchange/adapter.py"),
        Path("src/tallylot/adapters/sources/platforms/example_exchange/translation.py"),
        Path("src/tallylot/adapters/sources/platforms/example_exchange/tests/__init__.py"),
        Path("src/tallylot/adapters/sources/platforms/example_exchange/tests/test_contract.py"),
        Path("src/tallylot/adapters/sources/platforms/example_exchange/fixtures/.gitkeep"),
    }
    adapter_py = (
        repo_root / "src" / "tallylot" / "adapters" / "sources" / "platforms" / "example_exchange" / "adapter.py"
    )
    translation_py = (
        repo_root / "src" / "tallylot" / "adapters" / "sources" / "platforms" / "example_exchange" / "translation.py"
    )
    assert "class ExampleExchangeSourceAdapter" in adapter_py.read_text(encoding="utf-8")
    assert "translate_source_batches" in adapter_py.read_text(encoding="utf-8")
    assert "FILE_TRANSLATION_RULES" in translation_py.read_text(encoding="utf-8")
    assert {
        environment["root"]
        for environment in pyright_config["executionEnvironments"]
        if environment.get("reportPrivateUsage") is False
    } == {
        "tests",
        "src/tallylot/adapters/sources/platforms/example_exchange/tests",
    }


def test_scaffold_adapter_requires_source_category_namespace(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"

    try:
        _scaffold_adapter(
            spec=_AdapterScaffoldSpec(
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
