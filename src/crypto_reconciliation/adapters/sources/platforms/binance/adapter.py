"""Binance export adapter entry point."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import cast

from crypto_reconciliation.adapters.support import (
    FileTranslationContext,
    FileTranslationRule,
    TimezoneReviewPolicy,
    match_intake_by_path_or_header,
    no_intake_route,
    reviewed_timezone_summary,
    translate_file_families,
)
from crypto_reconciliation.adapters.support.drafts import normalization_result_from_drafts
from crypto_reconciliation.adapters.support.drafts.models import EconomicActivityDraft
from crypto_reconciliation.domain.models import (
    AdapterCapability,
    AdapterManifest,
    FileInventoryEntry,
    IssueRecord,
    SourceProfile,
    WalletInventoryRecord,
)
from crypto_reconciliation.domain.types import AdapterId, JsonValue
from crypto_reconciliation.ports.adapters import NormalizationResult
from crypto_reconciliation.ports.intake_routing import IntakeFileFacts, IntakeRoute, IntakeRoutingRequest

from .funding_history import normalize_deposit_rows as _normalize_deposit_rows
from .funding_history import normalize_withdraw_rows as _normalize_withdraw_rows
from .matching import match_binance_inventory
from .order_history import normalize_c2c_order_rows as _normalize_c2c_order_rows
from .order_history import normalize_convert_order_rows as _normalize_convert_order_rows
from .pdf_balances import extract_pdf_balances as _extract_pdf_balances
from .pdf_balances import match_pdf_statement as _match_pdf_statement
from .spot_trades import normalize_spot_rows as _normalize_spot_rows
from .transaction_history import normalize_transaction_rows as _normalize_transaction_rows


def _translate_spot_history(
    context: FileTranslationContext,
) -> tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...]]:
    return tuple(_normalize_spot_rows(context.profile, context.path)), ()


def _translate_deposit_history(
    context: FileTranslationContext,
) -> tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...]]:
    return tuple(_normalize_deposit_rows(context.profile, context.path)), ()


def _translate_withdraw_history(
    context: FileTranslationContext,
) -> tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...]]:
    return tuple(_normalize_withdraw_rows(context.profile, context.path)), ()


def _translate_convert_history(
    context: FileTranslationContext,
) -> tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...]]:
    drafts, matched_times = _normalize_convert_order_rows(context.profile, context.path)
    convert_match_times = _state_datetime_set(context, "convert_match_times")
    convert_match_times.update(matched_times)
    return tuple(drafts), ()


def _translate_c2c_history(
    context: FileTranslationContext,
) -> tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...]]:
    drafts, matched_times = _normalize_c2c_order_rows(context.profile, context.path)
    p2p_match_times = _state_datetime_set(context, "p2p_match_times")
    p2p_match_times.update(matched_times)
    return tuple(drafts), ()


def _translate_transaction_history(
    context: FileTranslationContext,
) -> tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...]]:
    convert_match_times = context.state.get("convert_match_times")
    p2p_match_times = context.state.get("p2p_match_times")
    resolved_convert_match_times = (
        cast(set[datetime], convert_match_times) if isinstance(convert_match_times, set) else None
    )
    resolved_p2p_match_times = cast(set[datetime], p2p_match_times) if isinstance(p2p_match_times, set) else None
    drafts, issues = _normalize_transaction_rows(
        context.profile,
        context.path,
        convert_match_times=(
            frozenset(resolved_convert_match_times) if resolved_convert_match_times is not None else None
        ),
        p2p_match_times=frozenset(resolved_p2p_match_times) if resolved_p2p_match_times is not None else None,
    )
    return tuple(drafts), tuple(issues)


def _state_datetime_set(context: FileTranslationContext, key: str) -> set[datetime]:
    value = context.state.get(key)
    if isinstance(value, set):
        return cast(set[datetime], value)
    typed_value: set[datetime] = set()
    context.state[key] = typed_value
    return typed_value


BINANCE_FILE_TRANSLATION_RULES = (
    FileTranslationRule(
        family="spot_trade_history",
        matches_path=lambda path: path.name.startswith("Binance-Spot-Trade-History-"),
        translate=_translate_spot_history,
        priority=20,
    ),
    FileTranslationRule(
        family="deposit_history",
        matches_path=lambda path: path.name.startswith("Binance-Deposit-History-"),
        translate=_translate_deposit_history,
        priority=20,
    ),
    FileTranslationRule(
        family="withdraw_history",
        matches_path=lambda path: path.name.startswith("Binance-Withdraw-History-"),
        translate=_translate_withdraw_history,
        priority=20,
    ),
    FileTranslationRule(
        family="convert_order_history",
        matches_path=lambda path: path.name.startswith("Binance-Convert-Order-History-"),
        translate=_translate_convert_history,
        priority=10,
    ),
    FileTranslationRule(
        family="c2c_order_history",
        matches_path=lambda path: path.name.startswith("Binance-C2C-Order-History-"),
        translate=_translate_c2c_history,
        priority=10,
    ),
    FileTranslationRule(
        family="transaction_history",
        matches_path=lambda path: path.name.startswith("Binance-Transaction-History-"),
        translate=_translate_transaction_history,
        priority=20,
    ),
)


class BinanceAdapter:
    manifest = AdapterManifest(
        adapter_id=AdapterId("binance"),
        display_name="Binance",
        version="1.0.0",
        capabilities=frozenset({AdapterCapability.NORMALIZE, AdapterCapability.INTAKE_ROUTE}),
        description="Normalizes Binance deposit, withdrawal, spot, and transaction-history exports.",
    )

    def match(self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> int:
        del raw_dir
        return match_binance_inventory(source, inventory)

    def match_intake(self, relative_path: str, facts: IntakeFileFacts) -> int:
        return match_intake_by_path_or_header(
            relative_path,
            facts,
            path_hints=("binance",),
            header_hints=(
                "pair,coin,date,amount,type,status",
                "pair,coin,amount,time,interest type",
                "date(utc),pair,side,price,executed,amount,fee",
            ),
        )

    def route_intake(self, request: IntakeRoutingRequest) -> IntakeRoute | None:
        return no_intake_route(request)

    def validate_profile_timezones(
        self,
        profile: SourceProfile,
    ) -> tuple[dict[str, JsonValue], tuple[IssueRecord, ...]]:
        return reviewed_timezone_summary(
            profile,
            policy=TimezoneReviewPolicy(
                adapter_id=str(self.manifest.adapter_id),
                mode="naive",
                message="Binance exports with dated rows must include a filename offset before normalization.",
            ),
        )

    def extract_wallet_inventory(
        self,
        source: str,
        raw_dir: Path,
        profile: SourceProfile,
    ) -> tuple[tuple[WalletInventoryRecord, ...], tuple[IssueRecord, ...]]:
        del source, raw_dir, profile
        return (), ()

    def match_pdf_statement(self, pdf_path: Path, text: str) -> int:
        return _match_pdf_statement(pdf_path, text)

    def extract_pdf_balances(self, pdf_path: Path, text: str) -> list[dict[str, str]]:
        return _extract_pdf_balances(text, pdf_path.name)

    def normalize(self, profile: SourceProfile, raw_dir: Path) -> NormalizationResult:
        translation = translate_file_families(
            raw_dir,
            profile=profile,
            rules=BINANCE_FILE_TRANSLATION_RULES,
            state={"convert_match_times": set(), "p2p_match_times": set()},
        )
        return normalization_result_from_drafts(
            translation.drafts,
            issues=translation.issues,
        )


ADAPTER = BinanceAdapter()
