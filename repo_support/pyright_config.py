from __future__ import annotations

import json
import os
from pathlib import Path
from typing import cast

from repo_support.paths import repo_root

_ADAPTER_TEST_GLOB = "**/tests"
PYRIGHT_GENERATED_TEST_CONFIG_NAME = "pyrightconfig.tests.json"
PYRIGHT_LOCAL_CONFIG_NAME = ".pyrightconfig.local.json"


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


def expected_execution_environments(
    *, root: Path | None = None
) -> list[dict[str, object]]:
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


def _project_environment_root() -> Path:
    configured = os.environ.get("VIRTUAL_ENV") or os.environ.get(
        "UV_PROJECT_ENVIRONMENT"
    )
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.home() / ".venvs" / "tallylot-py312").resolve()


def ensure_pyright_local_config(*, root: Path | None = None) -> bool:
    active_root = repo_root() if root is None else root.expanduser().resolve()
    local_config_path = active_root / PYRIGHT_LOCAL_CONFIG_NAME
    root_config = _load_pyright_config(active_root / "pyrightconfig.json")
    generated_test_config = _load_pyright_config(
        active_root / PYRIGHT_GENERATED_TEST_CONFIG_NAME
    )
    root_config.pop("extends", None)
    project_environment = _project_environment_root()
    merged_config = {
        **generated_test_config,
        **root_config,
        "venvPath": str(project_environment.parent),
        "venv": project_environment.name,
    }
    new_payload = json.dumps(merged_config, indent=2) + "\n"
    existing_payload = (
        local_config_path.read_text(encoding="utf-8")
        if local_config_path.exists()
        else None
    )
    if existing_payload == new_payload:
        return False
    local_config_path.write_text(new_payload, encoding="utf-8")
    return True
