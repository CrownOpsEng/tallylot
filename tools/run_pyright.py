from __future__ import annotations

import json
import subprocess
import tempfile
from collections.abc import Sequence
from typing import cast

from repo_support.paths import repo_root, src_root
from tools.uv_environment import repo_uv_environment

_CONFIG_FILE_NAME = "pyrightconfig.json"
_ADAPTER_TEST_GLOB = "**/tests"


def _adapter_test_roots() -> tuple[str, ...]:
    adapter_root = src_root() / "tallylot" / "adapters"
    return tuple(
        sorted(
            path.relative_to(repo_root()).as_posix()
            for path in adapter_root.glob(_ADAPTER_TEST_GLOB)
            if path.is_dir()
        )
    )


def _load_pyright_config() -> dict[str, object]:
    payload = json.loads((repo_root() / _CONFIG_FILE_NAME).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{_CONFIG_FILE_NAME} must contain a JSON object")
    return cast(dict[str, object], payload)


def _private_usage_environment(root: str) -> dict[str, object]:
    return {
        "root": root,
        "extraPaths": ["src", "."],
        "reportPrivateUsage": False,
    }


def _known_environment_roots(environments: list[object]) -> frozenset[str]:
    roots: set[str] = set()
    for entry in environments:
        if not isinstance(entry, dict):
            continue
        environment = cast(dict[object, object], entry)
        root = environment.get("root")
        if isinstance(root, str):
            roots.add(root)
    return frozenset(roots)


def _pyright_config_payload() -> dict[str, object]:
    config = _load_pyright_config()
    environments = config.get("executionEnvironments", [])
    if not isinstance(environments, list):
        raise ValueError(f"{_CONFIG_FILE_NAME} executionEnvironments must be a list")

    typed_environments = cast(list[object], environments)
    merged_environments: list[object] = [*typed_environments]
    known_roots = _known_environment_roots(typed_environments)
    merged_environments.extend(
        _private_usage_environment(path)
        for path in _adapter_test_roots()
        if path not in known_roots
    )
    config["executionEnvironments"] = merged_environments
    return config


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        prefix=".pyrightconfig.",
        suffix=".json",
        dir=repo_root(),
    ) as config_file:
        json.dump(_pyright_config_payload(), config_file, indent=2)
        config_file.write("\n")
        config_file.flush()
        result = subprocess.run(
            ("uv", "run", "pyright", "--project", config_file.name),
            check=False,
            env=repo_uv_environment(),
        )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
