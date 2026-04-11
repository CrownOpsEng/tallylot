"""EVM explorer token transfer translation rules."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from tallylot.adapters.sources.explorers.evm_explorer.drafts import (
    EvmDraftContext,
    draft_transfer,
    location_id_from_identifier,
)
from tallylot.adapters.sources.explorers.evm_explorer.issues import (
    row_issue,
    token_identity_issue,
)
from tallylot.adapters.sources.explorers.evm_explorer.models import (
    EvmTranslationContext,
)
from tallylot.adapters.sources.explorers.evm_explorer.parsing import parse_utc_timestamp
from tallylot.adapters.support import (
    EVM_ADDRESS_PATTERN,
    evm_erc20_asset_claim,
    read_csv_rows,
)
from tallylot.adapters.support.drafts import (
    ActivitySemantics,
    EconomicActivityDraft,
    symbol_claim,
)
from tallylot.domain.issues import IssueRecord
from tallylot.domain.transactions import (
    AccountingIntentHint,
    EconomicKind,
    ProjectionHint,
    TaxTreatmentHint,
)
from tallylot.domain.value_objects import parse_decimal
from tallylot.ports.source_profiles import SourceProfile


def translate_token_transfers(
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
        timestamp = parse_utc_timestamp(timestamp_text)
        if (
            not tx_hash
            or timestamp is None
            or amount is None
            or amount <= Decimal("0")
            or not symbol
        ):
            issues.append(
                row_issue(
                    profile,
                    path.name,
                    index,
                    "invalid_row",
                    "EVM explorer token row is invalid.",
                )
            )
            continue
        if tx_hash in context.blocked_tx_hashes:
            continue
        unsupported_method = context.unsupported_methods.get(tx_hash)
        if unsupported_method:
            issues.append(
                row_issue(
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
        contract_address = (row.get("ContractAddress") or "").strip().lower()
        if EVM_ADDRESS_PATTERN.fullmatch(contract_address):
            token_claim = evm_erc20_asset_claim(
                context.network_scope,
                contract_address,
                display_name=symbol,
            )
        else:
            token_claim = symbol_claim(symbol, venue="evm_explorer")
        if (
            to_address in context.owned_addresses
            and from_address not in context.owned_addresses
        ):
            if not EVM_ADDRESS_PATTERN.fullmatch(contract_address):
                issues.append(token_identity_issue(profile, path.name, index=index))
            drafts.append(
                draft_transfer(
                    profile,
                    EvmDraftContext(
                        path_name=path.name,
                        row_index=index,
                        tx_hash=tx_hash,
                        timestamp=timestamp,
                        location_id=location_id_from_identifier(
                            "evm_address",
                            to_address,
                            network_scope=context.network_scope,
                        ),
                        quantity=amount,
                        instrument=token_claim,
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
        if (
            from_address in context.owned_addresses
            and to_address not in context.owned_addresses
        ):
            if not EVM_ADDRESS_PATTERN.fullmatch(contract_address):
                issues.append(token_identity_issue(profile, path.name, index=index))
            drafts.append(
                draft_transfer(
                    profile,
                    EvmDraftContext(
                        path_name=path.name,
                        row_index=index,
                        tx_hash=tx_hash,
                        timestamp=timestamp,
                        location_id=location_id_from_identifier(
                            "evm_address",
                            from_address,
                            network_scope=context.network_scope,
                        ),
                        quantity=-amount,
                        instrument=token_claim,
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
            row_issue(
                profile,
                path.name,
                index,
                "unsupported_shape",
                "EVM explorer token row does not match a supported simple transfer shape.",
            )
        )
    return tuple(drafts), tuple(issues)
