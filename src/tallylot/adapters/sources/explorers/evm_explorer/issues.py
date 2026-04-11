"""EVM explorer translation issue helpers."""

from __future__ import annotations

from pathlib import Path

from tallylot.adapters.sources.explorers.evm_explorer.families import (
    classified_csv_paths,
)
from tallylot.adapters.support import IssueSpec, issue_record, read_csv_rows
from tallylot.domain.issues import IssueRecord
from tallylot.ports.source_profiles import SourceProfile


def row_issue(
    profile: SourceProfile,
    raw_file: str,
    row_index: int,
    issue_suffix: str,
    message: str,
) -> IssueRecord:
    return issue_record(
        IssueSpec(
            source=str(profile.source),
            adapter_id="evm_explorer",
            issue_id=f"evm_explorer:{raw_file}:row:{row_index}:{issue_suffix}",
            kind="unsupported_row",
            message=message,
            raw_file=raw_file,
            raw_row_ref=f"row:{row_index}",
        )
    )


def token_identity_issue(
    profile: SourceProfile, raw_file: str, *, index: int
) -> IssueRecord:
    return issue_record(
        IssueSpec(
            source=str(profile.source),
            adapter_id="evm_explorer",
            issue_id=f"evm_explorer:{raw_file}:row:{index}:instrument_identity_blocked",
            severity="high",
            kind="instrument_identity_blocked",
            message=(
                "EVM explorer token transfer rows without a valid contract address do not "
                "expose immutable contract identity; the normalized fact keeps a symbol-only "
                "instrument id and cannot participate in historical API-backed balance lookup."
            ),
            raw_file=raw_file,
            raw_row_ref=f"row:{index}",
        )
    )


def unsupported_internal_transfer_issues(
    profile: SourceProfile, path: Path
) -> tuple[IssueRecord, ...]:
    return tuple(
        row_issue(
            profile,
            path.name,
            index,
            "unsupported_internal_trace",
            "Internal trace rows are present but are not normalized automatically because they may double-count swaps.",
        )
        for index, _ in enumerate(read_csv_rows(path), start=2)
    )


def nft_transfer_issues(
    profile: SourceProfile,
    path: Path,
    *,
    owned_addresses: set[str],
) -> tuple[IssueRecord, ...]:
    issues: list[IssueRecord] = []
    for index, row in enumerate(read_csv_rows(path), start=2):
        token_name = (row.get("TokenName") or "").strip()
        to_address = (row.get("To") or "").strip().lower()
        tx_hash = (row.get("Transaction Hash") or "").strip()
        if token_name.startswith("$") and to_address in owned_addresses:
            issues.append(
                issue_record(
                    IssueSpec(
                        source=str(profile.source),
                        adapter_id="evm_explorer",
                        issue_id=f"evm_explorer:{path.name}:{tx_hash or index}:suspicious_airdrop",
                        severity="medium",
                        kind="review_required",
                        message=f"{profile.source} received suspicious NFT airdrop {token_name} in tx {tx_hash}.",
                        raw_file=path.name,
                        raw_row_ref=f"row:{index}",
                        status="needs_review",
                    )
                )
            )
            continue
        issues.append(
            row_issue(
                profile,
                path.name,
                index,
                "unsupported_nft_activity",
                "NFT transfer rows are present but are not normalized automatically in this phase.",
            )
        )
    return tuple(issues)


def blocked_nft_tx_hashes(raw_dir: Path) -> set[str]:
    blocked: set[str] = set()
    for path, family_id in classified_csv_paths(raw_dir):
        if family_id != "nft_transfers":
            continue
        for row in read_csv_rows(path):
            tx_hash = (row.get("Transaction Hash") or "").strip()
            if tx_hash:
                blocked.add(tx_hash)
    return blocked
