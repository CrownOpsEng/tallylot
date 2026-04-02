from __future__ import annotations

from pathlib import Path


def test_source_adapter_packages_do_not_reexport_module_adapters() -> None:
    for package_init in sorted(Path("src/tallylot/adapters/sources").rglob("__init__.py")):
        if "/tests/" in package_init.as_posix():
            continue

        content = package_init.read_text(encoding="utf-8")

        assert "from .adapter import ADAPTER" not in content, package_init
        assert "from .stub import ADAPTER" not in content, package_init
