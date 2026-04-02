from __future__ import annotations

from pathlib import Path

from repo_support import paths as repo_paths
from repo_support.pyright_config import adapter_test_roots, sync_pyright_config


def test_adapter_test_roots_are_discovered_from_globbed_adapter_packages(tmp_path: Path) -> None:
    adapter_tests = (
        tmp_path
        / "src"
        / "tallylot"
        / "adapters"
        / "sources"
        / "platforms"
        / "example"
        / "tests"
    )
    adapter_tests.mkdir(parents=True)

    with repo_paths.override_repo_root(tmp_path):
        assert adapter_test_roots() == ("src/tallylot/adapters/sources/platforms/example/tests",)


def test_sync_pyright_config_appends_discovered_adapter_test_roots(tmp_path: Path) -> None:
    (tmp_path / "src" / "tallylot" / "adapters" / "sources" / "tests").mkdir(parents=True)
    config_path = tmp_path / "pyrightconfig.tests.json"
    config_path.write_text(
        """\
{
  "executionEnvironments": [
    {
      "root": "tests",
      "extraPaths": ["src", "."],
      "reportPrivateUsage": false
    }
  ]
}
""",
        encoding="utf-8",
    )

    with repo_paths.override_repo_root(tmp_path):
        assert sync_pyright_config() is True

    assert (
        config_path.read_text(encoding="utf-8")
        == """\
{
  "executionEnvironments": [
    {
      "root": "tests",
      "extraPaths": [
        "src",
        "."
      ],
      "reportPrivateUsage": false
    },
    {
      "root": "src/tallylot/adapters/sources/tests",
      "extraPaths": [
        "src",
        "."
      ],
      "reportPrivateUsage": false
    }
  ]
}
"""
    )
