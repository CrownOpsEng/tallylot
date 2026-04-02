#!/usr/bin/env python3

"""Shared archive inspection and extraction helpers for intake."""

from __future__ import annotations

import hashlib
import tarfile
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Callable


def sanitize_archive_member_path(name: str) -> Path | None:
    parts = [part for part in PurePosixPath(name).parts if part not in {"", "."}]
    if not parts or any(part == ".." for part in parts):
        return None
    return Path(*parts)


def iter_archive_member_bytes(path: Path) -> list[tuple[str, bytes]]:
    members: list[tuple[str, bytes]] = []
    try:
        if path.suffix.lower() == ".zip":
            with zipfile.ZipFile(path) as handle:
                for member in handle.infolist():
                    if member.is_dir() or not member.filename:
                        continue
                    safe_path = sanitize_archive_member_path(member.filename)
                    if safe_path is None:
                        continue
                    members.append((str(safe_path), handle.read(member)))
        elif path.name.lower().endswith((".tar.gz", ".tgz", ".tar")):
            with tarfile.open(path) as handle:
                for member in handle.getmembers():
                    if not member.isfile() or not member.name:
                        continue
                    safe_path = sanitize_archive_member_path(member.name)
                    if safe_path is None:
                        continue
                    extracted = handle.extractfile(member)
                    if extracted is None:
                        continue
                    members.append((str(safe_path), extracted.read()))
    except (OSError, zipfile.BadZipFile, tarfile.TarError):
        return []
    return members


def inspect_archive_members(path: Path, inspect_file: Callable[[Path], dict[str, str]]) -> list[dict[str, str]]:
    members: list[dict[str, str]] = []
    for member_name, data in iter_archive_member_bytes(path):
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_path = Path(tmp_dir) / Path(member_name).name
            temp_path.write_bytes(data)
            inspection_row = inspect_file(temp_path)
        members.append(
            {
                "member_name": member_name,
                "sha256": hashlib.sha256(data).hexdigest(),
                "size_bytes": str(len(data)),
                **inspection_row,
            }
        )
    return members


def summarize_archive_members(
    path: Path,
    inspect_file: Callable[[Path], dict[str, str]],
) -> dict[str, str]:
    members = inspect_archive_members(path, inspect_file)
    preview = " | ".join(member["member_name"] for member in members[:8])
    families = sorted({member.get("family", "") for member in members if member.get("family")})
    source_candidates: set[str] = set()
    for member in members:
        family = member.get("family", "")
        member_name = member.get("member_name", "").lower()
        if "cointracking" in member_name or family.startswith("cointracking_"):
            source_candidates.add("CoinTracking")
        elif "kucoin" in member_name:
            source_candidates.add("Kucoin Main")
        elif "wealthsimple" in member_name or family == "broker_activity_csv":
            source_candidates.add("WealthSimple")
        elif (
            "binance" in member_name
            or family.startswith("binance_margin_")
            or family in {
                "convert_order_csv",
                "deposit_history_csv",
                "withdrawal_history_csv",
                "p2p_order_csv",
                "fiat_buy_csv",
                "fiat_exchange_csv",
                "futures_transaction_csv",
                "custodial_transaction_csv",
            }
        ):
            source_candidates.add("Binance")
    crypto_detected = "yes" if source_candidates else "no"
    archive_detected_source = next(iter(source_candidates)) if len(source_candidates) == 1 else ""
    status = "identified" if archive_detected_source else ("review" if members else "unsupported")
    findings = []
    if families:
        findings.append(f"families={','.join(families[:6])}")
    if preview:
        findings.append(f"members={preview}")
    return {
        "archive_member_count": str(len(members)),
        "archive_member_preview": preview,
        "archive_member_families": ";".join(families),
        "archive_detected_source": archive_detected_source,
        "archive_contains_crypto_records": crypto_detected,
        "archive_inspection_status": status,
        "archive_findings": " | ".join(findings),
    }


def read_archive_member_bytes(path: Path, member_name: str) -> bytes:
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as handle:
            return handle.read(member_name)
    with tarfile.open(path) as handle:
        member = handle.getmember(member_name)
        extracted = handle.extractfile(member)
        if extracted is None:
            raise FileNotFoundError(f"Could not extract archive member {member_name!r} from {path}")
        return extracted.read()
