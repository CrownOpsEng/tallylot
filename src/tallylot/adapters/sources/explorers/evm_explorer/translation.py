"""EVM explorer translation rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from tallylot.adapters.sources.explorers.evm_explorer.families import (
    classified_csv_paths,
    native_symbol_for_header,
)
from tallylot.adapters.support import (
    IssueSpec,
    canonical_location_id_from_identifier,
    issue_record,
    read_csv_header,
    read_csv_rows,
)
from tallylot.adapters.support.drafts import (
    SINGLE_PRIMARY_ACTIVITY_POLICY,
    ActivitySemantics,
    EconomicActivityDraft,
    LegKind,
    economic_leg,
    symbol_claim,
)
from tallylot.domain.issues import IssueRecord
from tallylot.domain.transactions import AccountingIntentHint, EconomicKind, ProjectionHint, TaxTreatmentHint
from tallylot.domain.types import LocationId
from tallylot.domain.value_objects import parse_decimal
from tallylot.ports.source_profiles import SourceProfile


@dataclass(frozen=True)
class EvmTranslationContext:
    owned_addresses: set[str]
    network_scope: str
    blocked_tx_hashes: set[str]
    unsupported_methods: dict[str, str]


@dataclass(frozen=True)
class EvmDraftContext:
    path_name: str
    row_index: int
    tx_hash: str
    timestamp: datetime
    location_id: LocationId
    quantity: Decimal
    symbol: str


def translate_transactions(
    profile: SourceProfile,
    raw_dir: Path,
    *,
    owned_addresses: set[str],
    network_scope: str,
) -> tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...]]:
    drafts: list[EconomicActivityDraft] = []
    issues: list[IssueRecord] = []
    context = EvmTranslationContext(
        owned_addresses=owned_addresses,
        network_scope=network_scope,
        blocked_tx_hashes=_blocked_nft_tx_hashes(raw_dir),
        unsupported_methods=_unsupported_native_methods(raw_dir),
    )
    for path, family_id in classified_csv_paths(raw_dir):
        if family_id == "native_transfers":
            path_drafts, path_issues = _translate_native_transfers(
                profile,
                path,
                context,
            )
        elif family_id == "token_transfers":
            path_drafts, path_issues = _translate_token_transfers(
                profile,
                path,
                context,
            )
        elif family_id == "internal_transfers":
            path_drafts, path_issues = (), _unsupported_internal_transfer_issues(profile, path)
        elif family_id == "nft_transfers":
            path_drafts, path_issues = (), _nft_transfer_issues(profile, path, owned_addresses=owned_addresses)
        else:
            path_drafts, path_issues = (), ()
        drafts.extend(path_drafts)
        issues.extend(path_issues)
    return tuple(drafts), tuple(issues)


def _translate_native_transfers(
    profile: SourceProfile,
    path: Path,
    context: EvmTranslationContext,
) -> tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...]]:
    drafts: list[EconomicActivityDraft] = []
    issues: list[IssueRecord] = []
    symbol = native_symbol_for_header(read_csv_header(path)) or context.network_scope.upper()
    for index, row in enumerate(read_csv_rows(path), start=2):
        tx_hash = (row.get("Transaction Hash") or "").strip()
        timestamp_text = (row.get("DateTime (UTC)") or "").strip()
        method = (row.get("Method") or "").strip().lower()
        to_address = (row.get("To") or "").strip().lower()
        from_address = (row.get("From") or "").strip().lower()
        amount_in = _parse_amount(row, "Value_IN")
        amount_out = _parse_amount(row, "Value_OUT")
        timestamp = _parse_utc_timestamp(timestamp_text)
        if not tx_hash or timestamp is None:
            issues.append(
                _row_issue(
                    profile,
                    path.name,
                    index,
                    "invalid_row",
                    "EVM explorer row is missing tx hash or timestamp.",
                )
            )
            continue
        if tx_hash in context.blocked_tx_hashes:
            continue
        if amount_in <= Decimal("0") and amount_out <= Decimal("0"):
            continue
        if method not in {"", "transfer"}:
            issues.append(
                _row_issue(
                    profile,
                    path.name,
                    index,
                    f"unsupported_method:{method}",
                    f"Unsupported EVM explorer native method: {method}",
                )
            )
            continue
        if amount_in > Decimal("0") and amount_out == Decimal("0") and to_address in context.owned_addresses:
            drafts.append(
                _draft(
                    profile,
                    EvmDraftContext(
                        path_name=path.name,
                        row_index=index,
                        tx_hash=tx_hash,
                        timestamp=timestamp,
                        location_id=canonical_location_id_from_identifier(
                            "evm_address",
                            to_address,
                            network_scope=context.network_scope,
                        ),
                        quantity=amount_in,
                        symbol=symbol,
                    ),
                    ActivitySemantics(
                        economic_kind=EconomicKind.CHAIN_TRANSFER_IN,
                        projection_hint=ProjectionHint.DEPOSIT,
                        accounting_intent_hint=AccountingIntentHint.FUNDING_INFLOW,
                        tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN,
                    ),
                )
            )
            continue
        if amount_out > Decimal("0") and amount_in == Decimal("0") and from_address in context.owned_addresses:
            drafts.append(
                _draft(
                    profile,
                    EvmDraftContext(
                        path_name=path.name,
                        row_index=index,
                        tx_hash=tx_hash,
                        timestamp=timestamp,
                        location_id=canonical_location_id_from_identifier(
                            "evm_address",
                            from_address,
                            network_scope=context.network_scope,
                        ),
                        quantity=-amount_out,
                        symbol=symbol,
                    ),
                    ActivitySemantics(
                        economic_kind=EconomicKind.ASSET_WITHDRAWAL,
                        projection_hint=ProjectionHint.WITHDRAWAL,
                        accounting_intent_hint=AccountingIntentHint.FUNDING_OUTFLOW,
                        tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_OUT,
                    ),
                )
            )
            continue
        issues.append(
            _row_issue(
                profile,
                path.name,
                index,
                "unsupported_shape",
                "EVM explorer native row does not match a supported simple transfer shape.",
            )
        )
    return tuple(drafts), tuple(issues)


def _translate_token_transfers(
    profile: SourceProfile,
    path: Path,
    context: EvmTranslationContext,
) -> tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...]]:
    drafts: list[EconomicActivityDraft] = []
    issues: list[IssueRecord] = []
    for index, row in enumerate(read_csv_rows(path), start=2):
        tx_hash = (row.get("Transaction Hash") or "").strip()
        timestamp_text = (row.get("DateTime (UTC)") or "").strip()
        from_address = (row.get("From") or "").strip().lower()
        to_address = (row.get("To") or "").strip().lower()
        symbol = (row.get("TokenSymbol") or "").strip().upper()
        amount = parse_decimal((row.get("TokenValue") or "").replace(",", "").strip())
        timestamp = _parse_utc_timestamp(timestamp_text)
        if not tx_hash or timestamp is None or amount is None or amount <= Decimal("0") or not symbol:
            issues.append(_row_issue(profile, path.name, index, "invalid_row", "EVM explorer token row is invalid."))
            continue
        if tx_hash in context.blocked_tx_hashes:
            continue
        unsupported_method = context.unsupported_methods.get(tx_hash)
        if unsupported_method:
            issues.append(
                _row_issue(
                    profile,
                    path.name,
                    index,
                    f"unsupported_related_method:{unsupported_method}",
                    (
                        "EVM explorer token transfer is linked to an unsupported contract-call transaction "
                        f"method: {unsupported_method}"
                    ),
                )
            )
            continue
        if to_address in context.owned_addresses and from_address not in context.owned_addresses:
            drafts.append(
                _draft(
                    profile,
                    EvmDraftContext(
                        path_name=path.name,
                        row_index=index,
                        tx_hash=tx_hash,
                        timestamp=timestamp,
                        location_id=canonical_location_id_from_identifier(
                            "evm_address",
                            to_address,
                            network_scope=context.network_scope,
                        ),
                        quantity=amount,
                        symbol=symbol,
                    ),
                    ActivitySemantics(
                        economic_kind=EconomicKind.CHAIN_TRANSFER_IN,
                        projection_hint=ProjectionHint.DEPOSIT,
                        accounting_intent_hint=AccountingIntentHint.FUNDING_INFLOW,
                        tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_IN,
                    ),
                )
            )
            continue
        if from_address in context.owned_addresses and to_address not in context.owned_addresses:
            drafts.append(
                _draft(
                    profile,
                    EvmDraftContext(
                        path_name=path.name,
                        row_index=index,
                        tx_hash=tx_hash,
                        timestamp=timestamp,
                        location_id=canonical_location_id_from_identifier(
                            "evm_address",
                            from_address,
                            network_scope=context.network_scope,
                        ),
                        quantity=-amount,
                        symbol=symbol,
                    ),
                    ActivitySemantics(
                        economic_kind=EconomicKind.ASSET_WITHDRAWAL,
                        projection_hint=ProjectionHint.WITHDRAWAL,
                        accounting_intent_hint=AccountingIntentHint.FUNDING_OUTFLOW,
                        tax_treatment_hint=TaxTreatmentHint.NON_TAXABLE_TRANSFER_OUT,
                    ),
                )
            )
            continue
        issues.append(
            _row_issue(
                profile,
                path.name,
                index,
                "unsupported_shape",
                "EVM explorer token row does not match a supported simple transfer shape.",
            )
        )
    return tuple(drafts), tuple(issues)


def _unsupported_internal_transfer_issues(profile: SourceProfile, path: Path) -> tuple[IssueRecord, ...]:
    return tuple(
        _row_issue(
            profile,
            path.name,
            index,
            "unsupported_internal_trace",
            "Internal trace rows are present but are not normalized automatically because they may double-count swaps.",
        )
        for index, _ in enumerate(read_csv_rows(path), start=2)
    )


def _nft_transfer_issues(
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
            _row_issue(
                profile,
                path.name,
                index,
                "unsupported_nft_activity",
                "NFT transfer rows are present but are not normalized automatically in this phase.",
            )
        )
    return tuple(issues)


def _unsupported_native_methods(raw_dir: Path) -> dict[str, str]:
    methods: dict[str, str] = {}
    for path, family_id in classified_csv_paths(raw_dir):
        if family_id != "native_transfers":
            continue
        for row in read_csv_rows(path):
            tx_hash = (row.get("Transaction Hash") or "").strip()
            method = (row.get("Method") or "").strip().lower()
            if not tx_hash or method in {"", "transfer"}:
                continue
            methods[tx_hash] = method
    return methods


def _blocked_nft_tx_hashes(raw_dir: Path) -> set[str]:
    blocked: set[str] = set()
    for path, family_id in classified_csv_paths(raw_dir):
        if family_id != "nft_transfers":
            continue
        for row in read_csv_rows(path):
            tx_hash = (row.get("Transaction Hash") or "").strip()
            if tx_hash:
                blocked.add(tx_hash)
    return blocked


def _draft(
    profile: SourceProfile,
    draft_context: EvmDraftContext,
    semantics: ActivitySemantics,
) -> EconomicActivityDraft:
    return EconomicActivityDraft(
        activity_id=f"evm_explorer:{draft_context.path_name}:{draft_context.tx_hash}",
        source=str(profile.source),
        adapter_id="evm_explorer",
        location_id=draft_context.location_id,
        timestamp=draft_context.timestamp,
        classification=semantics.to_classification(),
        leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
        description=f"Transfer - {draft_context.tx_hash}",
        raw_file=draft_context.path_name,
        raw_row_ref=f"row:{draft_context.row_index}",
        tx_hash=draft_context.tx_hash,
        provider_operation_key="explorer_transfer",
        legs=(
            economic_leg(
                leg_id="primary",
                kind=LegKind.PRIMARY,
                quantity=draft_context.quantity,
                instrument=symbol_claim(draft_context.symbol, venue="evm_explorer"),
            ),
        ),
    )


def _row_issue(
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


def _parse_amount(row: dict[str, str], prefix: str) -> Decimal:
    value = next((text for field, text in row.items() if field.startswith(f"{prefix}(")), "")
    parsed = parse_decimal(value.replace(",", "").strip())
    return parsed or Decimal("0")


def _parse_utc_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(f"{value}+00:00").astimezone(UTC)
    except ValueError:
        return None
