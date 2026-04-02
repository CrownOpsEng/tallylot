from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from repo_support.paths import repo_root

_ADAPTER_TEST_GLOB = "**/tests"
PYRIGHT_GENERATED_TEST_CONFIG_NAME = "pyrightconfig.tests.json"


def adapter_test_roots(*, root: Path | None = None) -> tuple[str, ...]:
    active_root = repo_root() if root is None else root.expanduser().resolve()
    adapter_root = active_root / "src" / "tallylot" / "adapters"
    if not adapter_root.is_dir():
        return ()
    return tuple(
        sorted(
            path.relative_to(active_root).as_posix()
            for path in adapter_root.glob(_ADAPTER_TEST_GLOB)
            if path.is_dir()
        )
    )


def _private_usage_environment(root: str) -> dict[str, object]:
    return {
        "root": root,
        "extraPaths": ["src", "."],
        "reportPrivateUsage": False,
    }


def _load_pyright_config(config_path: Path) -> dict[str, object]:
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{config_path} must contain a JSON object")
    return cast(dict[str, object], payload)


def expected_execution_environments(*, root: Path | None = None) -> list[dict[str, object]]:
    return [
        _private_usage_environment(path)
        for path in ("tests", *adapter_test_roots(root=root))
    ]


def sync_pyright_config(*, root: Path | None = None) -> bool:
    active_root = repo_root() if root is None else root.expanduser().resolve()
    config_path = active_root / PYRIGHT_GENERATED_TEST_CONFIG_NAME
    config = _load_pyright_config(config_path) if config_path.exists() else {}
    expected_environments = expected_execution_environments(root=active_root)
    if config.get("executionEnvironments") == expected_environments:
        return False
    config["executionEnvironments"] = expected_environments
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return True
