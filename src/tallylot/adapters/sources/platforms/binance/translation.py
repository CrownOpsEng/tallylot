"""Binance file-family translation rules."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import cast

from tallylot.adapters.support import (
    FileTranslationContext,
    FileTranslationRule,
    translate_file_families,
)
from tallylot.adapters.support.drafts import (
    TranslationBatchDrafts,
    translation_batch_from_drafts,
)
from tallylot.adapters.support.drafts.models import EconomicActivityDraft
from tallylot.domain.issues import IssueRecord
from tallylot.ports.source_profiles import SourceProfile
from tallylot.ports.source_translation import SourceTranslationBatch

from .funding_history import normalize_deposit_rows as _normalize_deposit_rows
from .funding_history import normalize_withdraw_rows as _normalize_withdraw_rows
from .order_history import normalize_c2c_order_rows as _normalize_c2c_order_rows
from .order_history import normalize_convert_order_rows as _normalize_convert_order_rows
from .spot_trades import normalize_spot_rows as _normalize_spot_rows
from .transaction_history import (
    normalize_transaction_rows as _normalize_transaction_rows,
)


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
        cast(set[datetime], convert_match_times)
        if isinstance(convert_match_times, set)
        else None
    )
    resolved_p2p_match_times = (
        cast(set[datetime], p2p_match_times)
        if isinstance(p2p_match_times, set)
        else None
    )
    drafts, issues = _normalize_transaction_rows(
        context.profile,
        context.path,
        convert_match_times=(
            frozenset(resolved_convert_match_times)
            if resolved_convert_match_times is not None
            else None
        ),
        p2p_match_times=frozenset(resolved_p2p_match_times)
        if resolved_p2p_match_times is not None
        else None,
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
        matches_path=lambda path: path.name.startswith(
            "Binance-Convert-Order-History-"
        ),
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


def translate_binance_exports(
    profile: SourceProfile, raw_dir: Path
) -> SourceTranslationBatch:
    translation = translate_file_families(
        raw_dir,
        profile=profile,
        rules=BINANCE_FILE_TRANSLATION_RULES,
        state={"convert_match_times": set(), "p2p_match_times": set()},
    )
    return translation_batch_from_drafts(
        TranslationBatchDrafts(drafts=translation.drafts, issues=translation.issues)
    )
