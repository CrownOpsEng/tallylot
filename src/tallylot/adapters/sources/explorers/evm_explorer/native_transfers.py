"""EVM explorer native transfer translation rules."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from tallylot.adapters.sources.explorers.evm_explorer.drafts import (
    EvmDraftContext,
    draft_transfer,
    location_id_from_identifier,
)
from tallylot.adapters.sources.explorers.evm_explorer.families import (
    classified_csv_paths,
    native_symbol_for_header,
)
from tallylot.adapters.sources.explorers.evm_explorer.issues import row_issue
from tallylot.adapters.sources.explorers.evm_explorer.models import (
    EvmTranslationContext,
)
from tallylot.adapters.sources.explorers.evm_explorer.parsing import (
    parse_amount,
    parse_utc_timestamp,
)
from tallylot.adapters.support import (
    evm_native_asset_claim,
    read_csv_header,
    read_csv_rows,
)
from tallylot.adapters.support.drafts import ActivitySemantics, EconomicActivityDraft
from tallylot.domain.issues import IssueRecord
from tallylot.domain.transactions import (
    AccountingIntentHint,
    EconomicKind,
    ProjectionHint,
    TaxTreatmentHint,
)
from tallylot.ports.source_profiles import SourceProfile


def translate_native_transfers(
    profile: SourceProfile,
    path: Path,
    context: EvmTranslationContext,
) -> tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...]]:
    drafts: list[EconomicActivityDraft] = []
    issues: list[IssueRecord] = []
    symbol = (
        native_symbol_for_header(read_csv_header(path)) or context.network_scope.upper()
    )
    for index, row in enumerate(read_csv_rows(path), start=2):
        tx_hash = (row.get("Transaction Hash") or "").strip()
        timestamp_text = (row.get("DateTime (UTC)") or "").strip()
        method = (row.get("Method") or "").strip().lower()
        to_address = (row.get("To") or "").strip().lower()
        from_address = (row.get("From") or "").strip().lower()
        amount_in = parse_amount(row, "Value_IN")
        amount_out = parse_amount(row, "Value_OUT")
        timestamp = parse_utc_timestamp(timestamp_text)
        if not tx_hash or timestamp is None:
            issues.append(
                row_issue(
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
                row_issue(
                    profile,
                    path.name,
                    index,
                    f"unsupported_method:{method}",
                    f"Unsupported EVM explorer native method: {method}",
                )
            )
            continue
        if (
            amount_in > Decimal("0")
            and amount_out == Decimal("0")
            and to_address in context.owned_addresses
        ):
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
                        quantity=amount_in,
                        instrument=evm_native_asset_claim(
                            context.network_scope,
                            display_name=symbol,
                        ),
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
            amount_out > Decimal("0")
            and amount_in == Decimal("0")
            and from_address in context.owned_addresses
        ):
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
                        quantity=-amount_out,
                        instrument=evm_native_asset_claim(
                            context.network_scope,
                            display_name=symbol,
                        ),
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
                "EVM explorer native row does not match a supported simple transfer shape.",
            )
        )
    return tuple(drafts), tuple(issues)


def unsupported_native_methods(raw_dir: Path) -> dict[str, str]:
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
