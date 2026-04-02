"""EVM explorer transaction translation rules."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from crypto_reconciliation.adapters.support import IssueSpec, issue_record, matching_file_paths, read_csv_rows
from crypto_reconciliation.adapters.support.drafts import EconomicActivityDraft, classification, economic_leg
from crypto_reconciliation.domain.models import IssueRecord, SourceProfile


def translate_transactions(
    profile: SourceProfile,
    raw_dir: Path,
    *,
    owned_addresses: set[str],
) -> tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...]]:
    issues: list[IssueRecord] = []
    drafts: list[EconomicActivityDraft] = []
    suspicious_hashes = _suspicious_nft_hashes(raw_dir, owned_addresses)
    for path in matching_file_paths(raw_dir):
        if "nft" in path.name.lower():
            continue
        for index, row in enumerate(read_csv_rows(path), start=2):
            tx_hash = (row.get("Transaction Hash") or "").strip()
            if not tx_hash:
                continue
            if tx_hash in suspicious_hashes:
                issues.append(
                    issue_record(
                        IssueSpec(
                            source=str(profile.source),
                            adapter_id="evm_explorer",
                            issue_id=f"evm_explorer:{path.name}:{tx_hash}",
                            severity="medium",
                            kind="review_required",
                            message=(
                                f"{profile.source} received suspicious NFT airdrop "
                                f"{suspicious_hashes[tx_hash]} in tx {tx_hash}; keep it in review instead of "
                                "auto-importing it as an economic deposit."
                            ),
                            raw_file=path.name,
                            raw_row_ref=f"{path.name}:row:{index};{suspicious_hashes[tx_hash + ':ref']}",
                            status="needs_review",
                        )
                    )
                )
                continue
            amount_in = Decimal((row.get("Value_IN(BNB)") or "0").strip())
            if amount_in <= Decimal("0"):
                continue
            drafts.append(
                EconomicActivityDraft(
                    activity_id=f"evm_explorer:{path.name}:{tx_hash}",
                    source=str(profile.source),
                    adapter_id="evm_explorer",
                    account=str(profile.source),
                    wallet=str(profile.source),
                    timestamp=_parse_utc_timestamp((row.get("DateTime (UTC)") or "").strip()),
                    classification=classification(
                        economic_kind="chain_transfer_in",
                        projection_type="Deposit",
                        journal_intent="funding_inflow",
                        tax_treatment_code="non_taxable_transfer_in",
                    ),
                    description=f"Transfer - {tx_hash}",
                    raw_file=path.name,
                    raw_row_ref=f"{path.name}:row:{index}",
                    tx_hash=tx_hash,
                    provider_operation_key="explorer_transfer_in",
                    legs=(economic_leg(direction="in", asset="BNB", amount=amount_in),),
                )
            )
    return tuple(drafts), tuple(issues)


def _suspicious_nft_hashes(raw_dir: Path, owned_addresses: set[str]) -> dict[str, str]:
    suspicious: dict[str, str] = {}
    for path in matching_file_paths(raw_dir, pattern="*nft*.csv"):
        for index, row in enumerate(read_csv_rows(path), start=2):
            to_address = (row.get("To") or "").strip().lower()
            token_name = (row.get("TokenName") or "").strip()
            tx_hash = (row.get("Transaction Hash") or "").strip()
            if to_address not in owned_addresses or not token_name.startswith("$"):
                continue
            suspicious[tx_hash] = token_name
            suspicious[f"{tx_hash}:ref"] = f"{path.name}:row:{index}"
    return suspicious


def _parse_utc_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(f"{value}+00:00").astimezone(UTC).replace(tzinfo=None)
