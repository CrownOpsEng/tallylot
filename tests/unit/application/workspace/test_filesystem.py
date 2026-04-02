from __future__ import annotations

from pathlib import Path

import pytest

from tallylot.application.workspace.filesystem import (
    ensure_directory,
    ensure_output_not_within_input_tree,
    iter_tree_files,
)


def test_ensure_directory_creates_nested_path_and_returns_it(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "reports"

    returned = ensure_directory(path)

    assert returned == path
    assert path.is_dir()


def test_ensure_output_not_within_input_tree_rejects_nested_outputs(tmp_path: Path) -> None:
    input_root = tmp_path / "raw"
    output_path = input_root / "normalized" / "facts.csv"
    input_root.mkdir()

    with pytest.raises(ValueError, match="must not be inside raw source directory"):
        ensure_output_not_within_input_tree(
            input_root,
            output_path,
            input_label="raw source directory",
            output_label="normalization output",
        )


def test_iter_tree_files_sorts_results_and_honors_exclusions(tmp_path: Path) -> None:
    root = tmp_path / "normalized"
    excluded = root / "aggregate" / "wallet_inventory.csv"
    included_a = root / "b" / "wallet_inventory.csv"
    included_b = root / "a" / "facts.csv"
    for path in (excluded, included_a, included_b):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture\n", encoding="utf-8")

    paths = iter_tree_files(root, exclude_paths=(excluded,))

    assert paths == (included_b, included_a)
