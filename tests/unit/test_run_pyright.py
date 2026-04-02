from __future__ import annotations

from pathlib import Path

from repo_support import paths as repo_paths
from tools.run_pyright import _adapter_test_roots, _pyright_config_payload


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
        assert _adapter_test_roots() == ("src/tallylot/adapters/sources/platforms/example/tests",)


def test_pyright_config_payload_appends_discovered_adapter_test_roots(tmp_path: Path) -> None:
    (tmp_path / "src" / "tallylot" / "adapters" / "sources" / "tests").mkdir(parents=True)
    (tmp_path / "pyrightconfig.json").write_text(
        """\
{
  "include": ["src", "tests", "tools", "conftest.py"],
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
        config = _pyright_config_payload()

    assert config["executionEnvironments"] == [
        {
            "root": "tests",
            "extraPaths": ["src", "."],
            "reportPrivateUsage": False,
        },
        {
            "root": "src/tallylot/adapters/sources/tests",
            "extraPaths": ["src", "."],
            "reportPrivateUsage": False,
        },
    ]
