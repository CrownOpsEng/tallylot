"""Module loading helpers for adapter discovery."""

from __future__ import annotations

import importlib
import importlib.util
import pkgutil
from types import ModuleType

DISCOVERABLE_MODULE_NAMES = ("adapter", "stub")
IGNORED_DISCOVERY_PARTS = frozenset({"tests", "fixtures", "__pycache__"})


def iter_discoverable_modules(package_name: str) -> tuple[ModuleType, ...]:
    package = importlib.import_module(package_name)
    modules: list[ModuleType] = []
    for package_info in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
        if is_ignored_discovery_name(package_info.name):
            continue
        if package_info.ispkg:
            modules.extend(iter_adapter_package_modules(package_info.name))
            continue
        modules.append(importlib.import_module(package_info.name))
    return tuple(modules)


def iter_adapter_package_modules(package_name: str) -> tuple[ModuleType, ...]:
    package = importlib.import_module(package_name)
    modules: list[ModuleType] = []
    for module_name in DISCOVERABLE_MODULE_NAMES:
        qualified_name = f"{package_name}.{module_name}"
        if importlib.util.find_spec(qualified_name) is None:
            continue
        modules.append(importlib.import_module(qualified_name))
    if modules:
        return tuple(modules)

    for package_info in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
        if is_ignored_discovery_name(package_info.name):
            continue
        if package_info.ispkg:
            modules.extend(iter_adapter_package_modules(package_info.name))
            continue
        modules.append(importlib.import_module(package_info.name))
    return tuple(modules)


def is_ignored_discovery_name(module_name: str) -> bool:
    parts = module_name.split(".")
    return any(
        part in IGNORED_DISCOVERY_PARTS or part.startswith(("test_", "_"))
        for part in parts
    )
