from __future__ import annotations

import importlib.util
from collections.abc import Callable, Sequence
from pathlib import Path
from types import ModuleType
from typing import cast

from repo_support.paths import repo_root


def load_skill_main(relative_path: str) -> Callable[[Sequence[str] | None], int]:
    script_path = repo_root() / relative_path
    if script_path.is_file() is False:
        raise FileNotFoundError(f"missing repo skill script: {script_path}")
    module = _load_script_module(script_path)
    main = getattr(module, "main", None)
    if not callable(main):
        raise AttributeError(
            f"skill script does not expose a callable main: {script_path}"
        )
    return cast(Callable[[Sequence[str] | None], int], main)


def _load_script_module(script_path: Path) -> ModuleType:
    module_name = "_tallylot_test_skill_" + "_".join(script_path.parts[-5:])
    module_name = module_name.replace("-", "_").replace(".", "_")
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load repo skill script: {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
