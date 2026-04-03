"""Required export validation for verification comparison."""

from __future__ import annotations

from pathlib import Path

REQUIRED_FILES = {
    "validate_transactions": "Validate Transactions.csv",
    "missing_transactions": "Missing Transactions.csv",
    "duplicate_transactions": "Duplicate Transactions.csv",
    "current_balance": "Current Balance.csv",
    "balance_by_exchange": "Balance by Exchange.csv",
}


def required_verification_paths(directory: Path) -> dict[str, Path]:
    if not directory.exists():
        raise FileNotFoundError(f"verification directory does not exist: {directory}")
    if not directory.is_dir():
        raise NotADirectoryError(f"verification path is not a directory: {directory}")
    resolved: dict[str, Path] = {}
    for key, filename in REQUIRED_FILES.items():
        path = _resolve_required_export(directory, filename)
        resolved[key] = path
    return resolved


def _resolve_required_export(directory: Path, filename: str) -> Path:
    exact = directory / filename
    if exact.exists():
        if not exact.is_file():
            raise FileNotFoundError(f"Required export is not a file: {exact}")
        return exact

    stem = Path(filename).stem
    matches = sorted(
        path for path in directory.iterdir() if path.is_file() and path.suffix.lower() == ".csv" and stem in path.stem
    )
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        match_list = ", ".join(path.name for path in matches)
        raise FileNotFoundError(f"Ambiguous export matches for {filename!r} in {directory}: {match_list}")
    raise FileNotFoundError(f"Missing required export {filename!r} in {directory}")
