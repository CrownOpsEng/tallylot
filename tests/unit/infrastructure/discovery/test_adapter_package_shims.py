from __future__ import annotations

import ast
from pathlib import Path

from repo_support.paths import repo_root


def _adapter_package_roots() -> tuple[Path, ...]:
    adapter_root = repo_root() / "src" / "tallylot" / "adapters"
    package_roots = {
        path.parent
        for path in adapter_root.rglob("*.py")
        if path.name in {"adapter.py", "stub.py"} and "tests" not in path.parts
    }
    return tuple(sorted(package_roots))


def test_adapter_package_init_files_are_docstring_only() -> None:
    for package_root in _adapter_package_roots():
        package_init = package_root / "__init__.py"
        module = ast.parse(
            package_init.read_text(encoding="utf-8"), filename=str(package_init)
        )
        assert ast.get_docstring(module) is not None, package_init

        executable_statements = (
            module.body[1:] if ast.get_docstring(module) is not None else module.body
        )
        assert not executable_statements, package_init
