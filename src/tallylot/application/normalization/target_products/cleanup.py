"""Owned cleanup helpers for target-product execution."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
import shutil

_ALLOWED_PRODUCT_REF_FILENAMES = {
    "evidence_sets": "evidence_set.json",
    "claim_sets": "claim_set.json",
    "economic_facts": "economic_facts.json",
    "reconciliation_states": "reconciliation_state.json",
    "checkpoints": "checkpoint.json",
}


def pruned_refs(
    *, prior_refs: tuple[str, ...], current_refs: tuple[str, ...]
) -> tuple[str, ...]:
    return tuple(sorted(set(prior_refs) - set(current_refs)))


def prune_product_roots(workspace_root: Path, refs: tuple[str, ...]) -> None:
    workspace_root_resolved = workspace_root.resolve()
    for ref in refs:
        root = _product_root_from_ref(workspace_root, workspace_root_resolved, ref)
        if root is not None:
            shutil.rmtree(root)


def prune_owned_paths(paths: tuple[Path, ...]) -> None:
    for path in paths:
        if path.is_file():
            path.unlink()


def _product_root_from_ref(
    workspace_root: Path,
    workspace_root_resolved: Path,
    ref: str,
) -> Path | None:
    relative_ref = PurePosixPath(ref)
    parts = relative_ref.parts
    family = parts[2] if len(parts) >= 3 else ""
    if (
        relative_ref.is_absolute()
        or ".." in relative_ref.parts
        or len(parts) != 5
        or parts[:2] != ("working", "products")
        or _ALLOWED_PRODUCT_REF_FILENAMES.get(family) != parts[-1]
    ):
        return None
    root = workspace_root.joinpath(*parts[:-1])
    resolved_root = root.resolve() if root.is_dir() and not root.is_symlink() else None
    if resolved_root is None or not resolved_root.is_relative_to(
        workspace_root_resolved
    ):
        return None
    return resolved_root
