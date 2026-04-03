from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest

from tallylot.domain.types import AdapterId
from tallylot.infrastructure.discovery.adapters import modules, registry
from tallylot.ports.adapter_contracts import AdapterCapability, AdapterManifest


class AdapterModule(ModuleType):
    ADAPTER: object | None = None  # pylint: disable=invalid-name


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

    def fake_iter_discoverable_modules(package_name: str) -> tuple[ModuleType, ...]:
        del package_name
        return (cast(ModuleType, module),)

    monkeypatch.setattr(registry, "iter_discoverable_modules", fake_iter_discoverable_modules)

    with pytest.raises(
        ValueError,
        match="must declare intake route, source translation, or wallet inventory capability",
    ):
        registry.collect_source_adapters("fixture.sources")


def test_output_adapter_discovery_rejects_duplicate_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    source_module = AdapterModule("fixture.source")
    output_module = AdapterModule("fixture.output")

    class SourceAdapterFixture:
        manifest = AdapterManifest(
            adapter_id=AdapterId("shared_adapter"),
            display_name="Shared Source",
            version="1.0.0",
            capabilities=frozenset({AdapterCapability.SOURCE_TRANSLATE}),
        )

        def match(self, source: str, raw_dir: object, inventory: tuple[object, ...]) -> int:
            del source, raw_dir, inventory
            return 100

        def match_intake(self, relative_path: str, facts: object) -> int:
            del relative_path, facts
            return 0

        def route_intake(self, request: object) -> object | None:
            del request
            return None

        def validate_profile_timezones(self, profile: object) -> tuple[dict[str, object], tuple[object, ...]]:
            del profile
            return {}, ()

        def extract_wallet_inventory(
            self,
            source: str,
            raw_dir: object,
            profile: object,
        ) -> tuple[tuple[object, ...], tuple[object, ...]]:
            del source, raw_dir, profile
            return (), ()

        def translate(self, profile: object, raw_dir: object) -> object:
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

    def fake_collect_source_adapters(package_name: str) -> tuple[SourceAdapterFixture, ...]:
        del package_name
        return (cast(SourceAdapterFixture, source_module.ADAPTER),)

    def fake_collect_output_adapters(package_name: str) -> tuple[OutputAdapterFixture, ...]:
        del package_name
        return (cast(OutputAdapterFixture, output_module.ADAPTER),)

    monkeypatch.setattr(registry, "collect_source_adapters", fake_collect_source_adapters)
    monkeypatch.setattr(registry, "collect_output_adapters", fake_collect_output_adapters)

    with pytest.raises(ValueError, match="duplicate adapter_id"):
        registry.build_registry()


def test_iter_modules_supports_package_style_adapters_without_loading_tests(
    tmp_path: Path,
) -> None:
    package_root = tmp_path / "fixture_adapters"
    package_root.mkdir()
    (package_root / "__init__.py").write_text("", encoding="utf-8")
    (package_root / "flat_adapter.py").write_text("ADAPTER = object()\n", encoding="utf-8")
    categorized = package_root / "platforms"
    categorized.mkdir()
    (categorized / "__init__.py").write_text("", encoding="utf-8")
    packaged = categorized / "packaged_adapter"
    packaged.mkdir()
    (packaged / "__init__.py").write_text("", encoding="utf-8")
    (packaged / "adapter.py").write_text("ADAPTER = object()\n", encoding="utf-8")
    (packaged / "tests.py").write_text("raise RuntimeError('should not import tests')\n", encoding="utf-8")
    (package_root / "_helper.py").write_text("raise RuntimeError('should not import helpers')\n", encoding="utf-8")

    sys.path.insert(0, str(tmp_path))
    importlib.invalidate_caches()
    sys.modules.pop("fixture_adapters", None)
    sys.modules.pop("fixture_adapters.flat_adapter", None)
    sys.modules.pop("fixture_adapters.platforms", None)
    sys.modules.pop("fixture_adapters.platforms.packaged_adapter", None)
    sys.modules.pop("fixture_adapters.platforms.packaged_adapter.adapter", None)
    sys.modules.pop("fixture_adapters.platforms.packaged_adapter.tests", None)

    discovered = modules.iter_discoverable_modules("fixture_adapters")

    assert {module.__name__ for module in discovered} == {
        "fixture_adapters.flat_adapter",
        "fixture_adapters.platforms.packaged_adapter.adapter",
    }
    sys.path.pop(0)


def test_adapter_registry_reports_unknown_ids() -> None:
    empty_registry = registry.AdapterRegistry(source_adapters=(), output_adapters=())

    with pytest.raises(KeyError, match="unknown source adapter: missing"):
        empty_registry.source_adapter("missing")

    with pytest.raises(KeyError, match="unknown output adapter: missing"):
        empty_registry.output_adapter("missing")
