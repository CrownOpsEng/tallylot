from __future__ import annotations

from pathlib import Path

from repo_support import paths as repo_paths


def test_repo_support_paths_default_to_repo_checkout() -> None:
    root = repo_paths.repo_root()

    assert (root / "pyproject.toml").exists()
    assert repo_paths.src_root() == root / "src"
    assert repo_paths.tests_root() == root / "tests"
    assert repo_paths.fixtures_root() == root / "tests" / "fixtures"
    assert repo_paths.adapter_packs_root() == root / "tests" / "fixtures" / "adapter_packs"
    assert repo_paths.docs_root() == root / "docs"
    assert repo_paths.agents_root() == root / "agents"
    assert repo_paths.claude_commands_root() == root / ".claude" / "commands"
    assert repo_paths.vscode_settings_path() == root / ".vscode" / "settings.json"


def test_override_repo_root_rebinds_derived_paths(tmp_path: Path) -> None:
    with repo_paths.override_repo_root(tmp_path):
        assert repo_paths.repo_root() == tmp_path.resolve()
        assert repo_paths.adapter_packs_root() == tmp_path.resolve() / "tests" / "fixtures" / "adapter_packs"
        assert repo_paths.relative_repo_path(tmp_path / "docs" / "README.md") == "docs/README.md"

    assert repo_paths.repo_root() != tmp_path.resolve()


def test_display_repo_path_falls_back_for_non_repo_paths(tmp_path: Path) -> None:
    assert repo_paths.display_repo_path(tmp_path / "outside.txt") == str(tmp_path / "outside.txt")
