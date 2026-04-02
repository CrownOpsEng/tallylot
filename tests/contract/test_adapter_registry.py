from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest

from crypto_reconciliation.domain.models import AdapterCapability, AdapterManifest
from crypto_reconciliation.domain.types import AdapterId
from crypto_reconciliation.infrastructure.discovery import adapters as discovery_adapters
from crypto_reconciliation.infrastructure.discovery import build_registry


class AdapterModule(ModuleType):
    ADAPTER: object | None = None  # pylint: disable=invalid-name


def test_adapter_registry_discovers_expected_adapters() -> None:
    registry = build_registry()

    source_ids = {str(adapter.manifest.adapter_id) for adapter in registry.source_adapters}
    output_ids = {str(adapter.manifest.adapter_id) for adapter in registry.output_adapters}

    assert "structured_csv" in source_ids
    assert "blockchain_stub" in source_ids
    assert "platform_api_stub" in source_ids
    assert "cointracking_csv" in output_ids
    assert "cointracking_api" in output_ids


def test_source_adapter_discovery_rejects_invalid_contracts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = AdapterModule("fixture.invalid_source")

    class InvalidSourceAdapter:
        manifest = AdapterManifest(
            adapter_id=AdapterId("invalid_source"),
            display_name="Invalid Source",
            version="0.0.0",
            capabilities=frozenset({AdapterCapability.OUTPUT_RENDER}),
        )

        def render(self) -> None:
            return None

    module.ADAPTER = InvalidSourceAdapter()  # pylint: disable=invalid-name

    def fake_iter_modules(package_name: str) -> tuple[ModuleType, ...]:
        if package_name.endswith(".sources"):
            return (cast(ModuleType, module),)
        return ()

    monkeypatch.setattr(discovery_adapters, "_iter_discoverable_modules", fake_iter_modules)

    with pytest.raises(ValueError, match="must declare normalize capability"):
        discovery_adapters.build_registry()


def test_output_adapter_discovery_rejects_duplicate_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    source_module = AdapterModule("fixture.source")
    output_module = AdapterModule("fixture.output")

    class SourceAdapterFixture:
        manifest = AdapterManifest(
            adapter_id=AdapterId("shared_adapter"),
            display_name="Shared Source",
            version="1.0.0",
            capabilities=frozenset({AdapterCapability.NORMALIZE}),
        )

        def match(self, source: str, raw_dir: object, inventory: tuple[object, ...]) -> int:
            del source, raw_dir, inventory
            return 100

        def normalize(self, profile: object, raw_dir: object) -> object:
            del profile, raw_dir
            raise NotImplementedError

    class OutputAdapterFixture:
        manifest = AdapterManifest(
            adapter_id=AdapterId("shared_adapter"),
            display_name="Shared Output",
            version="1.0.0",
            capabilities=frozenset({AdapterCapability.OUTPUT_RENDER}),
        )

        def render(self, events: tuple[object, ...], output_path: object) -> object:
            del events, output_path
            raise NotImplementedError

    source_module.ADAPTER = SourceAdapterFixture()  # pylint: disable=invalid-name
    output_module.ADAPTER = OutputAdapterFixture()  # pylint: disable=invalid-name

    def fake_iter_modules(package_name: str) -> tuple[ModuleType, ...]:
        if package_name.endswith(".sources"):
            return (cast(ModuleType, source_module),)
        return (cast(ModuleType, output_module),)

    monkeypatch.setattr(discovery_adapters, "_iter_discoverable_modules", fake_iter_modules)

    with pytest.raises(ValueError, match="duplicate adapter_id"):
        discovery_adapters.build_registry()


def test_iter_modules_supports_package_style_adapters_without_loading_tests(
    tmp_path: Path,
) -> None:
    package_root = tmp_path / "fixture_adapters"
    package_root.mkdir()
    (package_root / "__init__.py").write_text("", encoding="utf-8")
    (package_root / "flat_adapter.py").write_text("ADAPTER = object()\n", encoding="utf-8")
    packaged = package_root / "packaged_adapter"
    packaged.mkdir()
    (packaged / "__init__.py").write_text("", encoding="utf-8")
    (packaged / "adapter.py").write_text("ADAPTER = object()\n", encoding="utf-8")
    (packaged / "tests.py").write_text("raise RuntimeError('should not import tests')\n", encoding="utf-8")
    (package_root / "_helper.py").write_text("raise RuntimeError('should not import helpers')\n", encoding="utf-8")

    sys.path.insert(0, str(tmp_path))
    importlib.invalidate_caches()
    sys.modules.pop("fixture_adapters", None)
    sys.modules.pop("fixture_adapters.flat_adapter", None)
    sys.modules.pop("fixture_adapters.packaged_adapter", None)
    sys.modules.pop("fixture_adapters.packaged_adapter.adapter", None)
    sys.modules.pop("fixture_adapters.packaged_adapter.tests", None)

    modules = discovery_adapters._iter_discoverable_modules("fixture_adapters")

    assert {module.__name__ for module in modules} == {
        "fixture_adapters.flat_adapter",
        "fixture_adapters.packaged_adapter.adapter",
    }
    sys.path.pop(0)
