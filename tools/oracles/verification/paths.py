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
        path = directory / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing required export {filename!r} in {directory}")
        if not path.is_file():
            raise FileNotFoundError(f"Required export is not a file: {path}")
        resolved[key] = path
    return resolved
