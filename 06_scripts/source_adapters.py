#!/usr/bin/env python3

"""Adapter registry for universal source profiling and normalization."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone, tzinfo
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Sequence
import csv
import json
import re
from zoneinfo import ZoneInfo

from coinbase_common import (
    coinbase_balance_rows_from_text,
    csv_dict_rows,
    normalize_coinbase_transactions,
    retail_csv_rows,
)
from normalization_common import attach_fee_to_event, attach_fee_to_event_list
from pdf_balance_extract import binance_balance_rows_from_text, shakepay_balance_rows_from_text
from pipeline_common import CANONICAL_BALANCE_HEADERS, CANONICAL_EVENT_HEADERS, EXCEPTION_HEADERS, SourceProfile, source_slug
from script_common import (
    decimal_or_zero,
    decimal_text,
    extract_pdf_text,
    parse_datetime_to_utc_naive,
    read_cointracking_rows,
    read_csv_rows,
    source_timezone_from_filename,
)
from wallet_inventory_common import (
    EVM_ADDRESS_PATTERN,
    WALLET_EVIDENCE_HEADERS,
    dedupe_rows,
    infer_identifier_kind,
    normalize_identifier,
    wallet_evidence_row,
    wallet_issue_row,
)


DECISION_HEADERS = (
    "manifest_fingerprint",
    "event_id",
    "resolution_status",
    "resolution_note",
)

BINANCE_NUMBER_ASSET_PATTERN = re.compile(r"^\s*([-+]?[0-9]+(?:\.[0-9]+)?)\s*([A-Z0-9]+)\s*$")
BINANCE_TRADE_ID_PATTERN = re.compile(r"TradeID\s*-\s*(?P<trade_id>[A-Za-z0-9_-]+)")
BINANCE_SMALL_ASSET_PATTERN = re.compile(r"^(?P<asset>[A-Z0-9]+)\s+to\s+BNB$", re.IGNORECASE)
BINANCE_TIME_FORMATS = ("%y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S")
BASELINE_CUTOFF_TIMESTAMP = datetime(2023, 8, 5, 8, 34, 4)
WEALTHSIMPLE_TIME_FORMATS = ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S")
LEDGER_LIVE_TIME_FORMATS = ("%Y-%m-%dT%H:%M:%S.%fZ",)
CRYPTO_COM_TIME_FORMATS = ("%Y-%m-%d %H:%M:%S",)
SHAKEPAY_TIME_FORMATS = ("%Y-%m-%d %H:%M:%S",)
NEAR_TIME_FORMATS = ("%Y-%m-%d %H:%M:%S",)
SHAKEPAY_SOURCE_TIMEZONE = ZoneInfo("America/Toronto")


@dataclass(frozen=True)
class AdapterNormalizationResult:
    canonical_events: list[dict[str, str]]
    canonical_balances: list[dict[str, str]]
    exceptions: list[dict[str, str]]


@dataclass(frozen=True)
class TimezonePolicy:
    name: str
    allowed_modes: frozenset[str]
    expected_timezone: str
    note: str


STRICT_EXPLICIT_UTC_POLICY = TimezonePolicy(
    name="explicit_utc",
    allowed_modes=frozenset({"header_utc", "value_utc"}),
    expected_timezone="UTC",
    note="Source exports must declare UTC in the header or encoded timestamp values.",
)

EXPLICIT_OR_OFFSET_POLICY = TimezonePolicy(
    name="explicit_or_filename_offset",
    allowed_modes=frozenset({"header_utc", "value_utc", "filename_offset"}),
    expected_timezone="UTC or exported filename offset",
    note="Source exports must either declare UTC in the file itself or embed the export offset in the filename.",
)

SHAKEPAY_SOURCE_LOCAL_POLICY = TimezonePolicy(
    name="source_local_toronto",
    allowed_modes=frozenset({"naive"}),
    expected_timezone=SHAKEPAY_SOURCE_TIMEZONE.key,
    note="Shakepay CSV summaries are normalized using the source-local Canada/Eastern account time.",
)

WEALTHSIMPLE_DATE_ONLY_POLICY = TimezonePolicy(
    name="date_only",
    allowed_modes=frozenset({"date_only"}),
    expected_timezone="date-only",
    note="Wealthsimple activities exports are treated as date-only records and matched with a full-day tolerance.",
)

ASSUMED_UTC_NAIVE_POLICY = TimezonePolicy(
    name="assumed_utc_naive",
    allowed_modes=frozenset({"naive"}),
    expected_timezone="UTC",
    note="This export family emits naive timestamps and the adapter treats them as UTC based on the platform export.",
)

GTRADE_DATE_ONLY_POLICY = TimezonePolicy(
    name="date_only",
    allowed_modes=frozenset({"date_only"}),
    expected_timezone="date-only",
    note="The GTrade report only publishes trade dates, not times.",
)


def default_exception_row(
    *,
    manifest_fingerprint: str,
    source: str,
    adapter: str,
    event_id: str,
    raw_file: str,
    raw_row_ref: str,
    exception_kind: str,
    message: str,
    resolution_status: str = "",
    resolution_note: str = "",
) -> dict[str, str]:
    return {
        "manifest_fingerprint": manifest_fingerprint,
        "event_id": event_id,
        "source": source,
        "adapter": adapter,
        "raw_file": raw_file,
        "raw_row_ref": raw_row_ref,
        "exception_kind": exception_kind,
        "message": message,
        "status": "needs_review",
        "resolution_status": resolution_status,
        "resolution_note": resolution_note,
    }


def timezone_issue_row(row: dict[str, str], issue_kind: str, message: str) -> dict[str, str]:
    return {
        "filename": row.get("filename", ""),
        "family": row.get("family", ""),
        "date_field": row.get("date_field", ""),
        "timestamp_resolution": row.get("timestamp_resolution", ""),
        "timezone_mode": row.get("timezone_mode", ""),
        "timezone_value": row.get("timezone_value", ""),
        "issue_kind": issue_kind,
        "message": message,
    }


def summarize_timezone_validation(
    *,
    profile: SourceProfile,
    policy_for_row,
) -> tuple[dict[str, object], list[dict[str, str]]]:
    issues: list[dict[str, str]] = []
    mode_counts: Counter[str] = Counter()
    rows_with_dates = 0

    for row in profile.file_inventory:
        if not row.get("date_field"):
            continue
        rows_with_dates += 1
        timezone_mode = row.get("timezone_mode", "")
        mode_counts[timezone_mode or "blank"] += 1
        if row.get("timezone_conflict") == "yes":
            issues.append(
                timezone_issue_row(
                    row,
                    "timezone_conflict",
                    "Conflicting timezone hints were detected for the same file.",
                )
            )
            continue
        policy = policy_for_row(row)
        if policy is None:
            if timezone_mode in {"", "naive", "date_only", "source_timezone"}:
                issues.append(
                    timezone_issue_row(
                        row,
                        "timezone_unresolved",
                        "No adapter timezone policy covers this dated file.",
                    )
                )
            continue
        if timezone_mode not in policy.allowed_modes:
            issues.append(
                timezone_issue_row(
                    row,
                    "unexpected_timezone_mode",
                    (
                        f"Observed timezone mode {timezone_mode or 'blank'} is not allowed by "
                        f"{policy.name}; expected {policy.expected_timezone}. {policy.note}"
                    ),
                )
            )

    summary = {
        "status": "passed" if not issues else "failed",
        "issue_count": len(issues),
        "rows_with_dates": rows_with_dates,
        "mode_counts": dict(sorted(mode_counts.items())),
    }
    return summary, issues


def ct_row_to_canonical_event(row: dict[str, str], adapter_name: str, source_name: str) -> dict[str, str]:
    return {
        "event_id": row["Tx-ID"] or f"{adapter_name}:{row['raw_file']}:{row['raw_row_ref']}",
        "source": source_name,
        "adapter": adapter_name,
        "account": row["Exchange"],
        "wallet": row["Exchange"],
        "raw_file": row["raw_source"],
        "raw_row_ref": row["raw_ref"],
        "timestamp": row["Date"],
        "event_kind": row["Type"],
        "asset_in": row["Buy Cur."],
        "amount_in": row["Buy"],
        "asset_out": row["Sell Cur."],
        "amount_out": row["Sell"],
        "fee_asset": row["Fee Cur."],
        "fee_amount": row["Fee"],
        "tx_hash": row["Tx-ID"],
        "description": row["Comment"],
        "confidence": "high",
        "status": "mapped",
        "render_type": row["Type"],
        "render_exchange": row["Exchange"],
        "render_group": row["Group"],
        "render_comment": row["Comment"],
        "render_comment_mode": row["comment_mode"],
        "render_tx_id": row["Tx-ID"],
        "render_tx_id_mode": row["tx_id_mode"],
        "render_allowed_types": row["allowed_types"],
        "render_match_window_seconds": row["match_window_seconds"],
        "render_fee_tolerance": row["fee_tolerance"],
        "render_notes": row["notes"],
    }


def load_exception_decisions(path: Path | None, manifest_fingerprint: str) -> dict[str, dict[str, str]]:
    if path is None or not path.exists():
        return {}
    rows = read_cointracking_rows(path) if path.suffix.lower() == ".csv" and path.name.endswith("_ct.csv") else []
    if rows:
        return {}

    decisions: dict[str, dict[str, str]] = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("manifest_fingerprint") != manifest_fingerprint:
                continue
            event_id = row.get("event_id", "")
            if not event_id:
                continue
            decisions[event_id] = {
                "resolution_status": row.get("resolution_status", ""),
                "resolution_note": row.get("resolution_note", ""),
            }
    return decisions


def decisions_fingerprint(decisions: dict[str, dict[str, str]]) -> str:
    payload = [
        {
            "event_id": event_id,
            "resolution_status": values.get("resolution_status", ""),
            "resolution_note": values.get("resolution_note", ""),
        }
        for event_id, values in sorted(decisions.items())
    ]
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def normalized_timestamp(value: str, formats: Sequence[str], *, source_timezone: tzinfo | None = None) -> str:
    return parse_datetime_to_utc_naive(value.strip(), formats, source_timezone=source_timezone).strftime("%Y-%m-%d %H:%M:%S")


def event_id_for(adapter: str, raw_file: str, raw_row_ref: str) -> str:
    return f"{adapter}:{raw_file}:{raw_row_ref}"


def canonical_event(
    *,
    event_id: str,
    source: str,
    adapter: str,
    account: str,
    wallet: str,
    raw_file: str,
    raw_row_ref: str,
    timestamp: str,
    event_kind: str,
    description: str,
    amount_in: str = "",
    asset_in: str = "",
    amount_out: str = "",
    asset_out: str = "",
    fee_amount: str = "",
    fee_asset: str = "",
    tx_hash: str = "",
    render_group: str = "",
    render_notes: str = "",
    render_match_window_seconds: str = "0",
    render_fee_tolerance: str = "0.00000000",
    render_comment_mode: str = "exact",
    render_tx_id_mode: str = "exact",
    render_allowed_types: str | None = None,
) -> dict[str, str]:
    return {
        "event_id": event_id,
        "source": source,
        "adapter": adapter,
        "account": account,
        "wallet": wallet,
        "raw_file": raw_file,
        "raw_row_ref": raw_row_ref,
        "timestamp": timestamp,
        "event_kind": event_kind,
        "asset_in": asset_in,
        "amount_in": amount_in,
        "asset_out": asset_out,
        "amount_out": amount_out,
        "fee_asset": fee_asset,
        "fee_amount": fee_amount,
        "tx_hash": tx_hash,
        "description": description,
        "confidence": "high",
        "status": "mapped",
        "render_type": event_kind,
        "render_exchange": source,
        "render_group": render_group,
        "render_comment": description,
        "render_comment_mode": render_comment_mode,
        "render_tx_id": tx_hash,
        "render_tx_id_mode": render_tx_id_mode if tx_hash else "ignore",
        "render_allowed_types": render_allowed_types or event_kind,
        "render_match_window_seconds": render_match_window_seconds,
        "render_fee_tolerance": render_fee_tolerance,
        "render_notes": render_notes,
    }


def maybe_append_exception(
    exceptions: list[dict[str, str]],
    decisions: dict[str, dict[str, str]],
    *,
    manifest_fingerprint: str,
    source: str,
    adapter: str,
    event_id: str,
    raw_file: str,
    raw_row_ref: str,
    exception_kind: str,
    message: str,
) -> None:
    decision = decisions.get(event_id, {})
    exception = default_exception_row(
        manifest_fingerprint=manifest_fingerprint,
        source=source,
        adapter=adapter,
        event_id=event_id,
        raw_file=raw_file,
        raw_row_ref=raw_row_ref,
        exception_kind=exception_kind,
        message=message,
        resolution_status=decision.get("resolution_status", ""),
        resolution_note=decision.get("resolution_note", ""),
    )
    if exception["resolution_status"] != "accepted":
        exceptions.append(exception)


def parse_number_asset(text: str) -> tuple[str, str]:
    match = BINANCE_NUMBER_ASSET_PATTERN.match(text.strip())
    if match is None:
        raise ValueError(f"Unable to parse amount/asset value: {text!r}")
    amount = decimal_text(decimal_or_zero(match.group(1)))
    asset = match.group(2).upper()
    return amount, asset


def extract_trade_id(text: str) -> str:
    match = BINANCE_TRADE_ID_PATTERN.search(text)
    return match.group("trade_id") if match is not None else ""


def sum_changes(rows: Iterable[dict[str, str]]) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = defaultdict(Decimal)
    for row in rows:
        totals[row["Coin"].upper()] += decimal_or_zero(row["Change"])
    return totals


def tx_hash_or_event_id(event_id: str, raw_hash: str) -> str:
    return raw_hash.strip() or event_id


def raw_hash_description(prefix: str, raw_hash: str, fallback: str) -> str:
    hash_text = raw_hash.strip()
    return f"{prefix} - {hash_text}" if hash_text else fallback


def sum_decimal_strings(values: Iterable[str]) -> Decimal:
    total = Decimal("0")
    for value in values:
        total += decimal_or_zero(value)
    return total


def source_staked_label(source: str) -> str:
    return f"{source} - Staking" if not source.endswith("Staking") else source


def build_balance_row(
    *,
    source: str,
    account: str,
    wallet: str,
    balance_kind: str,
    asset: str,
    quantity: str = "",
    staked_quantity: str = "",
    value_amount: str = "",
    value_currency: str = "",
    price_amount: str = "",
    price_currency: str = "",
    as_of: str = "",
    pdf_file: str = "",
    notes: str = "",
) -> dict[str, str]:
    return {
        "source": source,
        "account": account,
        "wallet": wallet,
        "balance_kind": balance_kind,
        "asset": asset,
        "quantity": quantity,
        "staked_quantity": staked_quantity,
        "value_amount": value_amount,
        "value_currency": value_currency,
        "price_amount": price_amount,
        "price_currency": price_currency,
        "as_of": as_of,
        "pdf_file": pdf_file,
        "notes": notes,
    }


def profile_paths(
    raw_dir: Path,
    profile: SourceProfile,
    *,
    families: set[str] | None = None,
    suffixes: set[str] | None = None,
    predicate=None,
) -> list[Path]:
    paths: list[Path] = []
    for row in profile.file_inventory:
        if families is not None and row.get("family") not in families:
            continue
        if suffixes is not None and row.get("suffix") not in suffixes:
            continue
        path = raw_dir / row["filename"]
        if predicate is not None and not predicate(path, row):
            continue
        if path.exists() and path.is_file():
            paths.append(path)
    return sorted(paths)


def profile_has_row(
    profile: SourceProfile,
    *,
    families: set[str] | None = None,
    filename_contains: str | None = None,
    header_contains: str | None = None,
) -> bool:
    for row in profile.file_inventory:
        if families is not None and row.get("family") not in families:
            continue
        if filename_contains is not None and filename_contains.lower() not in row.get("filename", "").lower():
            continue
        if header_contains is not None and header_contains.lower() not in row.get("header_preview", "").lower():
            continue
        return True
    return False


class SourceAdapter:
    name = "base"
    aliases: tuple[str, ...] = ()
    supported = False

    def matches_source(self, source_name: str) -> bool:
        slug = source_slug(source_name)
        alias_slugs = {source_slug(alias) for alias in self.aliases}
        return slug == self.name or slug in alias_slugs

    def matches_profile(self, profile: SourceProfile) -> bool:
        return False

    def matches(self, source: str, profile: SourceProfile | None = None) -> bool:
        if profile is not None and self.matches_profile(profile):
            return True
        return self.matches_source(source)

    def timezone_policy_for_row(self, row: dict[str, str]) -> TimezonePolicy | None:
        if not row.get("date_field"):
            return None
        return STRICT_EXPLICIT_UTC_POLICY

    def validate_profile_timezones(self, profile: SourceProfile) -> tuple[dict[str, object], list[dict[str, str]]]:
        return summarize_timezone_validation(profile=profile, policy_for_row=self.timezone_policy_for_row)

    def extract_wallet_identifiers(
        self,
        source: str,
        raw_dir: Path,
        profile: SourceProfile,
    ) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        return [], []

    def normalize(
        self,
        raw_dir: Path,
        profile: SourceProfile,
        *,
        exception_decisions: dict[str, dict[str, str]],
    ) -> AdapterNormalizationResult:
        exception = default_exception_row(
            manifest_fingerprint=profile.manifest_fingerprint,
            source=profile.source,
            adapter=self.name,
            event_id=f"{self.name}:adapter_not_implemented",
            raw_file="",
            raw_row_ref="",
            exception_kind="adapter_not_implemented",
            message=f"No deterministic normalization adapter has been implemented for {profile.source}.",
            resolution_status=exception_decisions.get(f"{self.name}:adapter_not_implemented", {}).get("resolution_status", ""),
            resolution_note=exception_decisions.get(f"{self.name}:adapter_not_implemented", {}).get("resolution_note", ""),
        )
        exceptions = [] if exception["resolution_status"] == "accepted" else [exception]
        return AdapterNormalizationResult(canonical_events=[], canonical_balances=[], exceptions=exceptions)


class MetamaskAppAdapter(SourceAdapter):
    name = "metamask_app"
    aliases = ("metamask app", "app-metamask")
    supported = False

    def matches_profile(self, profile: SourceProfile) -> bool:
        return any(row.get("filename") == "MetaMask state logs.json" for row in profile.file_inventory)

    def extract_wallet_identifiers(
        self,
        source: str,
        raw_dir: Path,
        profile: SourceProfile,
    ) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        state_path = raw_dir / "MetaMask state logs.json"
        if not state_path.exists():
            return [], [
                wallet_issue_row(
                    source=source,
                    raw_dir=raw_dir,
                    wallet_id="",
                    issue_kind="missing_identifier",
                    message="MetaMask state logs were not found.",
                )
            ]

        payload = json.loads(state_path.read_text(encoding="utf-8"))
        metamask = payload.get("metamask", {})
        evidence: list[dict[str, str]] = []
        issues: list[dict[str, str]] = []
        internal_accounts = (((metamask.get("internalAccounts") or {}).get("accounts")) or {})
        for account in internal_accounts.values():
            identifier_value = (account.get("address") or "").strip()
            if not identifier_value:
                continue
            metadata = account.get("metadata") or {}
            keyring = metadata.get("keyring") or {}
            evidence.append(
                wallet_evidence_row(
                    source=source,
                    raw_dir=raw_dir,
                    identifier_value=identifier_value,
                    network_scope="ethereum",
                    controller=f"MetaMask {keyring.get('type', '').strip()}".strip(),
                    account_label=(metadata.get("name") or "").strip(),
                    evidence_kind="app_state",
                    evidence_path=state_path,
                    confidence="high",
                )
            )

        identities = metamask.get("identities") or {}
        for identifier_value, identity in identities.items():
            kind = infer_identifier_kind(identifier_value)
            normalized_identifier = normalize_identifier(kind, identifier_value)
            if any(row["normalized_identifier"] == normalized_identifier for row in evidence):
                continue
            network_scope = {
                "btc_address": "bitcoin",
                "tron_address": "tron",
                "solana_address": "solana",
                "evm_address": "ethereum",
            }.get(kind, "")
            evidence.append(
                wallet_evidence_row(
                    source=source,
                    raw_dir=raw_dir,
                    identifier_value=identifier_value,
                    network_scope=network_scope,
                    controller="MetaMask app",
                    account_label=(identity.get("name") or "").strip(),
                    evidence_kind="app_state",
                    evidence_path=state_path,
                    confidence="medium",
                    note="Discovered from the MetaMask identity map rather than a chain-scoped export.",
                    identifier_kind=kind,
                )
            )

        if not evidence:
            issues.append(
                wallet_issue_row(
                    source=source,
                    raw_dir=raw_dir,
                    wallet_id="",
                    issue_kind="missing_identifier",
                    message="No wallet identifiers could be extracted from the MetaMask app state.",
                    evidence_path=state_path,
                )
            )
        return dedupe_rows(evidence, key_fields=WALLET_EVIDENCE_HEADERS), issues


class CoinbaseAdapter(SourceAdapter):
    name = "coinbase"
    aliases = ("coinbase",)
    supported = True

    def matches_profile(self, profile: SourceProfile) -> bool:
        return profile_has_row(profile, filename_contains="statement - all time") or profile_has_row(
            profile,
            filename_contains="coinbase pro - statement",
        )

    def timezone_policy_for_row(self, row: dict[str, str]) -> TimezonePolicy | None:
        if not row.get("date_field"):
            return None
        return STRICT_EXPLICIT_UTC_POLICY

    def normalize(
        self,
        raw_dir: Path,
        profile: SourceProfile,
        *,
        exception_decisions: dict[str, dict[str, str]],
    ) -> AdapterNormalizationResult:
        retail_candidates = profile_paths(
            raw_dir,
            profile,
            families={"custodial_all_time_csv"},
            suffixes={".csv"},
            predicate=lambda path, _: "statement - all time" in path.name.lower(),
        )
        retail_path = retail_candidates[-1] if retail_candidates else None
        pro_statement_paths = profile_paths(
            raw_dir,
            profile,
            families={"transfer_statement_csv"},
            suffixes={".csv"},
            predicate=lambda path, _: "coinbase pro - statement" in path.name.lower(),
        )
        pro_fill_paths = profile_paths(
            raw_dir,
            profile,
            families={"fills_csv"},
            suffixes={".csv"},
            predicate=lambda path, _: "coinbase pro - fills" in path.name.lower(),
        )
        pdf_paths = profile_paths(raw_dir, profile, families={"statement_balance_pdf"}, suffixes={".pdf"})

        exceptions: list[dict[str, str]] = []
        if retail_path is None:
            maybe_append_exception(
                exceptions,
                exception_decisions,
                manifest_fingerprint=profile.manifest_fingerprint,
                source=profile.source,
                adapter=self.name,
                event_id="coinbase:missing_retail_csv",
                raw_file="",
                raw_row_ref="",
                exception_kind="missing_required_input",
                message="Coinbase retail all-time CSV is required for deterministic normalization.",
            )
            return AdapterNormalizationResult(canonical_events=[], canonical_balances=[], exceptions=exceptions)

        normalized_rows = normalize_coinbase_transactions(
            retail_csv_rows(retail_path),
            [dict(row, _file=path.name) for path in pro_statement_paths for row in csv_dict_rows(path, "Coinbase Pro statement CSV")],
            [dict(row, _file=path.name) for path in pro_fill_paths for row in csv_dict_rows(path, "Coinbase Pro fills CSV")],
            retail_source=retail_path,
        )

        events = [ct_row_to_canonical_event(row, self.name, profile.source) for row in normalized_rows]
        balances: list[dict[str, str]] = []
        for pdf_path in pdf_paths:
            balances.extend(coinbase_balance_rows_from_text(extract_pdf_text(pdf_path), pdf_path.name))
        return AdapterNormalizationResult(canonical_events=events, canonical_balances=balances, exceptions=exceptions)


class WealthsimpleAdapter(SourceAdapter):
    name = "wealthsimple"
    aliases = ("wealthsimple", "wealthsimple crypto")
    supported = True

    def matches_profile(self, profile: SourceProfile) -> bool:
        return profile_has_row(profile, filename_contains="activities-export")

    def timezone_policy_for_row(self, row: dict[str, str]) -> TimezonePolicy | None:
        if not row.get("date_field"):
            return None
        return WEALTHSIMPLE_DATE_ONLY_POLICY

    def normalize(
        self,
        raw_dir: Path,
        profile: SourceProfile,
        *,
        exception_decisions: dict[str, dict[str, str]],
    ) -> AdapterNormalizationResult:
        activity_paths = profile_paths(
            raw_dir,
            profile,
            families={"broker_activity_csv"},
            suffixes={".csv"},
            predicate=lambda path, _: path.name.lower().startswith("activities-export"),
        )
        exceptions: list[dict[str, str]] = []
        if not activity_paths:
            maybe_append_exception(
                exceptions,
                exception_decisions,
                manifest_fingerprint=profile.manifest_fingerprint,
                source=profile.source,
                adapter=self.name,
                event_id="wealthsimple:missing_activities_export",
                raw_file="",
                raw_row_ref="",
                exception_kind="missing_required_input",
                message="Wealthsimple activities export CSV is required for deterministic crypto normalization.",
            )
            return AdapterNormalizationResult(canonical_events=[], canonical_balances=[], exceptions=exceptions)

        events: list[dict[str, str]] = []
        for path in activity_paths:
            for index, row in enumerate(read_csv_rows(path), start=2):
                if not any((value or "").strip() for value in row.values()):
                    continue
                transaction_date = (row.get("transaction_date") or "").strip()
                if not transaction_date or transaction_date.lower().startswith("as of "):
                    continue
                if (row.get("account_type") or "").strip().lower() != "crypto":
                    continue
                timestamp_source = (row.get("settlement_date") or "").strip() or transaction_date
                timestamp = normalized_timestamp(timestamp_source, WEALTHSIMPLE_TIME_FORMATS)
                raw_row_ref = f"row:{index}"
                event_id = event_id_for(self.name, path.name, raw_row_ref)
                activity_type = (row.get("activity_type") or "").strip()
                activity_sub_type = (row.get("activity_sub_type") or "").strip()
                description = f"{activity_type}:{activity_sub_type or 'base'}"
                account = (row.get("account_id") or "").strip() or "Wealthsimple Crypto"
                quantity = decimal_or_zero(row.get("quantity"))
                currency = (row.get("currency") or "").strip().upper()
                symbol = (row.get("symbol") or "").strip().upper()
                commission = decimal_or_zero(row.get("commission"))
                net_cash = decimal_or_zero(row.get("net_cash_amount"))

                if activity_type == "Trade" and symbol and currency:
                    if activity_sub_type == "BUY":
                        events.append(
                            canonical_event(
                                event_id=event_id,
                                source=profile.source,
                                adapter=self.name,
                                account=account,
                                wallet=account,
                                raw_file=path.name,
                                raw_row_ref=raw_row_ref,
                                timestamp=timestamp,
                                event_kind="Trade",
                                description="Wealthsimple Crypto buy",
                                amount_in=decimal_text(abs(quantity)),
                                asset_in=symbol,
                                amount_out=decimal_text(abs(net_cash)),
                                asset_out=currency,
                                fee_amount=decimal_text(commission),
                                fee_asset=currency,
                                render_match_window_seconds="86399",
                                render_notes=description,
                            )
                        )
                        continue
                    if activity_sub_type == "SELL":
                        events.append(
                            canonical_event(
                                event_id=event_id,
                                source=profile.source,
                                adapter=self.name,
                                account=account,
                                wallet=account,
                                raw_file=path.name,
                                raw_row_ref=raw_row_ref,
                                timestamp=timestamp,
                                event_kind="Trade",
                                description="Wealthsimple Crypto sell",
                                amount_in=decimal_text(abs(net_cash)),
                                asset_in=currency,
                                amount_out=decimal_text(abs(quantity)),
                                asset_out=symbol,
                                fee_amount=decimal_text(commission),
                                fee_asset=currency,
                                render_match_window_seconds="86399",
                                render_notes=description,
                            )
                        )
                        continue

                if activity_type == "MoneyMovement" and currency:
                    if quantity >= 0:
                        events.append(
                            canonical_event(
                                event_id=event_id,
                                source=profile.source,
                                adapter=self.name,
                                account=account,
                                wallet=account,
                                raw_file=path.name,
                                raw_row_ref=raw_row_ref,
                                timestamp=timestamp,
                                event_kind="Deposit",
                                description=f"Wealthsimple money movement {activity_sub_type or 'credit'}",
                                amount_in=decimal_text(abs(quantity)),
                                asset_in=currency,
                                render_match_window_seconds="86399",
                                render_notes=description,
                            )
                        )
                    else:
                        events.append(
                            canonical_event(
                                event_id=event_id,
                                source=profile.source,
                                adapter=self.name,
                                account=account,
                                wallet=account,
                                raw_file=path.name,
                                raw_row_ref=raw_row_ref,
                                timestamp=timestamp,
                                event_kind="Withdrawal",
                                description=f"Wealthsimple money movement {activity_sub_type or 'debit'}",
                                amount_out=decimal_text(abs(quantity)),
                                asset_out=currency,
                                render_match_window_seconds="86399",
                                render_notes=description,
                            )
                        )
                    continue

                maybe_append_exception(
                    exceptions,
                    exception_decisions,
                    manifest_fingerprint=profile.manifest_fingerprint,
                    source=profile.source,
                    adapter=self.name,
                    event_id=event_id,
                    raw_file=path.name,
                    raw_row_ref=raw_row_ref,
                    exception_kind="unsupported_row",
                    message=f"Unsupported Wealthsimple crypto activity: {activity_type}/{activity_sub_type}",
                )

        return AdapterNormalizationResult(canonical_events=events, canonical_balances=[], exceptions=exceptions)


class BinanceAdapter(SourceAdapter):
    name = "binance"
    aliases = ("binance",)
    supported = True

    def matches_profile(self, profile: SourceProfile) -> bool:
        return any(row.get("filename", "").lower().startswith("binance") for row in profile.file_inventory)

    def timezone_policy_for_row(self, row: dict[str, str]) -> TimezonePolicy | None:
        if not row.get("date_field"):
            return None
        header_preview = (row.get("header_preview") or "").lower()
        if "utc_time" in header_preview:
            return STRICT_EXPLICIT_UTC_POLICY
        return EXPLICIT_OR_OFFSET_POLICY

    _trade_operations = {
        "Buy",
        "Sell",
        "Fee",
        "Transaction Buy",
        "Transaction Spend",
        "Transaction Fee",
        "Transaction Revenue",
        "Transaction Sold",
        "Transaction Related",
        "Binance Convert",
        "Small Assets Exchange BNB",
        "ETH 2.0 Staking",
        "Token Swap - Redenomination/Rebranding",
        "BETH to WBETH Wrapping",
    }
    _historical_only_ignored_operations = {
        "Isolated Margin Loan",
        "Isolated Margin Repayment",
        "Launchpool Subscription/Redemption",
        "Staking Purchase",
        "Staking Redemption",
        "Simple Earn Flexible Subscription",
        "Simple Earn Flexible Redemption",
        "Transfer Between Main Account/Futures and Margin Account",
        "Transfer Between Main and Funding Wallet",
        "Transfer Between UM Futures and Funding Account",
        "Transfer Between Spot Account and UM Futures Account",
        "Transfer Between Futures Contract Accounts",
        "Send/Recieve",
        "P2P Trading",
        "BNB Fee Deduction",
    }
    _income_type_by_operation = {
        "Staking Rewards": "Staking",
        "ETH 2.0 Staking Rewards": "Staking",
        "Simple Earn Flexible Interest": "Interest Income",
        "Launchpool Airdrop - User Claim Distribution": "Interest Income",
        "Airdrop Assets": "Airdrop",
        "Token Swap - Distribution": "Reward / Bonus",
    }

    def normalize(
        self,
        raw_dir: Path,
        profile: SourceProfile,
        *,
        exception_decisions: dict[str, dict[str, str]],
    ) -> AdapterNormalizationResult:
        events: list[dict[str, str]] = []
        exceptions: list[dict[str, str]] = []
        balances: list[dict[str, str]] = []
        covered_timestamps: set[str] = set()
        has_c2c_history = any(path.name.startswith("Binance-C2C-Order-History-") for path in raw_dir.glob("*.csv"))

        for pdf_path in sorted(raw_dir.glob("AccountStatementPeriod_*.pdf")):
            balances.extend(binance_balance_rows_from_text(extract_pdf_text(pdf_path), pdf_path.name))

        for path in sorted(raw_dir.glob("*.csv")):
            name = path.name
            if name.startswith("Binance-Spot-Trade-History-"):
                events.extend(self._spot_trade_events(path, profile.source))
                covered_timestamps.update(self._timestamps_for_file(path, "Time", status_field=None, allowed_statuses=None))
            elif name.startswith("Binance-Convert-Order-History-"):
                events.extend(self._convert_order_events(path, profile.source))
                covered_timestamps.update(self._convert_covered_timestamps(path))
            elif name.startswith("Binance-Deposit-History-"):
                events.extend(self._deposit_history_events(path, profile.source))
                covered_timestamps.update(self._timestamps_for_file(path, "Time", status_field="Status", allowed_statuses={"Completed"}))
            elif name.startswith("Binance-Withdraw-History-"):
                events.extend(self._withdraw_history_events(path, profile.source))
                covered_timestamps.update(self._timestamps_for_file(path, "Time", status_field="Status", allowed_statuses={"Completed"}))
            elif name.startswith("Binance-Fiat-Buy-History-"):
                events.extend(self._fiat_buy_history_events(path, profile.source))
                covered_timestamps.update(self._timestamps_for_file(path, "Time", status_field="Status", allowed_statuses={"Successful"}))
            elif name.startswith("Binance-Fiat-Sell-History-"):
                events.extend(self._fiat_sell_history_events(path, profile.source))
                covered_timestamps.update(self._timestamps_for_file(path, "Time", status_field="Status", allowed_statuses={"Successful"}))
            elif name.startswith("Binance-C2C-Order-History-"):
                events.extend(self._c2c_order_events(path, profile.source))
                covered_timestamps.update(self._timestamps_for_file(path, "Created Time", status_field="Status", allowed_statuses={"Completed"}))
            elif name.startswith("Binance-Transaction-History-") or re.match(r"^Binance Transactions \d{4}\.csv$", name):
                events.extend(
                    self._transaction_history_events(
                        path,
                        profile,
                        exception_decisions=exception_decisions,
                        covered_timestamps=covered_timestamps,
                        has_c2c_history=has_c2c_history,
                        exceptions=exceptions,
                    )
                )

        return AdapterNormalizationResult(canonical_events=events, canonical_balances=balances, exceptions=exceptions)

    def _timestamps_for_file(
        self,
        path: Path,
        field: str,
        *,
        status_field: str | None,
        allowed_statuses: set[str] | None,
    ) -> set[str]:
        timestamps: set[str] = set()
        for row in read_csv_rows(path):
            values = [str(value).strip() for value in row.values() if value not in (None, "")]
            if values == ["No data matches the criteria."] or not any(values):
                continue
            if status_field is not None and allowed_statuses is not None:
                if (row.get(status_field) or "").strip() not in allowed_statuses:
                    continue
            timestamp = (row.get(field) or "").strip()
            if timestamp:
                timestamps.add(timestamp)
        return timestamps

    def _convert_covered_timestamps(self, path: Path) -> set[str]:
        timestamps = self._timestamps_for_file(path, "Time", status_field="Status", allowed_statuses={"Successful"})
        timestamps.update(self._timestamps_for_file(path, "Date Updated", status_field="Status", allowed_statuses={"Successful"}))
        return timestamps

    def _spot_trade_events(self, path: Path, source: str) -> list[dict[str, str]]:
        events: list[dict[str, str]] = []
        for index, row in enumerate(read_csv_rows(path), start=2):
            if not any((value or "").strip() for value in row.values()):
                continue
            executed_amount, executed_asset = parse_number_asset(row["Executed"])
            quote_amount, quote_asset = parse_number_asset(row["Amount"])
            fee_amount, fee_asset = parse_number_asset(row["Fee"])
            timestamp = normalized_timestamp(
                row["Time"],
                BINANCE_TIME_FORMATS,
                source_timezone=source_timezone_from_filename(path.name),
            )
            side = (row.get("Side") or "").strip().upper()
            raw_row_ref = f"row:{index}"
            event_id = event_id_for(self.name, path.name, raw_row_ref)
            if side == "BUY":
                amount_in, asset_in = executed_amount, executed_asset
                amount_out, asset_out = quote_amount, quote_asset
            else:
                amount_in, asset_in = quote_amount, quote_asset
                amount_out, asset_out = executed_amount, executed_asset
            events.append(
                canonical_event(
                    event_id=event_id,
                    source=source,
                    adapter=self.name,
                    account="Spot",
                    wallet="Spot",
                    raw_file=path.name,
                    raw_row_ref=raw_row_ref,
                    timestamp=timestamp,
                    event_kind="Trade",
                    description=f"Binance spot {side.lower()} {row['Pair']}",
                    amount_in=amount_in,
                    asset_in=asset_in,
                    amount_out=amount_out,
                    asset_out=asset_out,
                    fee_amount=fee_amount,
                    fee_asset=fee_asset,
                    render_group="Spot",
                    render_notes=row["Pair"],
                )
            )
        return events

    def _convert_order_events(self, path: Path, source: str) -> list[dict[str, str]]:
        events: list[dict[str, str]] = []
        for index, row in enumerate(read_csv_rows(path), start=2):
            if (row.get("Status") or "").strip() != "Successful":
                continue
            sell_amount, sell_asset = parse_number_asset(row["Sell"])
            buy_amount, buy_asset = parse_number_asset(row["Buy"])
            timestamp = normalized_timestamp(
                row["Time"],
                BINANCE_TIME_FORMATS,
                source_timezone=source_timezone_from_filename(path.name),
            )
            raw_row_ref = f"row:{index}"
            events.append(
                canonical_event(
                    event_id=event_id_for(self.name, path.name, raw_row_ref),
                    source=source,
                    adapter=self.name,
                    account=(row.get("Wallet") or "Spot").strip() or "Spot",
                    wallet=(row.get("Wallet") or "Spot").strip() or "Spot",
                    raw_file=path.name,
                    raw_row_ref=raw_row_ref,
                    timestamp=timestamp,
                    event_kind="Trade",
                    description=f"Binance convert {row['Pair']}",
                    amount_in=buy_amount,
                    asset_in=buy_asset,
                    amount_out=sell_amount,
                    asset_out=sell_asset,
                    render_group=(row.get("Wallet") or "Spot").strip().title() or "Spot",
                    render_notes="Binance Convert",
                )
            )
        return events

    def _deposit_history_events(self, path: Path, source: str) -> list[dict[str, str]]:
        events: list[dict[str, str]] = []
        for index, row in enumerate(read_csv_rows(path), start=2):
            if (row.get("Status") or "").strip() != "Completed":
                continue
            raw_row_ref = f"row:{index}"
            events.append(
                canonical_event(
                    event_id=event_id_for(self.name, path.name, raw_row_ref),
                    source=source,
                    adapter=self.name,
                    account="Binance",
                    wallet="Funding",
                    raw_file=path.name,
                    raw_row_ref=raw_row_ref,
                    timestamp=normalized_timestamp(
                        row["Time"],
                        BINANCE_TIME_FORMATS,
                        source_timezone=source_timezone_from_filename(path.name),
                    ),
                    event_kind="Deposit",
                    description=f"Binance deposit via {row['Network']}",
                    amount_in=decimal_text(decimal_or_zero(row["Amount"])),
                    asset_in=(row.get("Coin") or "").strip().upper(),
                    tx_hash=(row.get("TXID") or "").strip(),
                    render_group="Funding",
                    render_notes=row.get("Address", ""),
                )
            )
        return events

    def _withdraw_history_events(self, path: Path, source: str) -> list[dict[str, str]]:
        events: list[dict[str, str]] = []
        for index, row in enumerate(read_csv_rows(path), start=2):
            if (row.get("Status") or "").strip() != "Completed":
                continue
            asset = (row.get("Coin") or "").strip().upper()
            raw_row_ref = f"row:{index}"
            event = canonical_event(
                event_id=event_id_for(self.name, path.name, raw_row_ref),
                source=source,
                adapter=self.name,
                account="Binance",
                wallet="Funding",
                raw_file=path.name,
                raw_row_ref=raw_row_ref,
                timestamp=normalized_timestamp(
                    row["Time"],
                    BINANCE_TIME_FORMATS,
                    source_timezone=source_timezone_from_filename(path.name),
                ),
                event_kind="Withdrawal",
                description=f"Binance withdrawal via {row['Network']}",
                amount_out=decimal_text(decimal_or_zero(row["Amount"])),
                asset_out=asset,
                tx_hash=(row.get("TXID") or "").strip(),
                render_group="Funding",
                render_notes=row.get("Address", ""),
            )
            events.append(attach_fee_to_event(event, fee_amount=row.get("Fee", ""), fee_asset=asset))
        return events

    def _fiat_buy_history_events(self, path: Path, source: str) -> list[dict[str, str]]:
        events: list[dict[str, str]] = []
        for index, row in enumerate(read_csv_rows(path), start=2):
            if (row.get("Status") or "").strip() != "Successful":
                continue
            spend_amount, spend_asset = parse_number_asset(row["Spend Amount"])
            receive_amount, receive_asset = parse_number_asset(row["Receive Amount"])
            fee_amount, fee_asset = parse_number_asset(row["Fee"])
            raw_row_ref = f"row:{index}"
            events.append(
                canonical_event(
                    event_id=event_id_for(self.name, path.name, raw_row_ref),
                    source=source,
                    adapter=self.name,
                    account="Funding",
                    wallet="Funding",
                    raw_file=path.name,
                    raw_row_ref=raw_row_ref,
                    timestamp=normalized_timestamp(
                        row["Time"],
                        BINANCE_TIME_FORMATS,
                        source_timezone=source_timezone_from_filename(path.name),
                    ),
                    event_kind="Trade",
                    description=f"Binance fiat buy via {row['Method']}",
                    amount_in=receive_amount,
                    asset_in=receive_asset,
                    amount_out=spend_amount,
                    asset_out=spend_asset,
                    fee_amount=fee_amount,
                    fee_asset=fee_asset,
                    tx_hash=(row.get("Transaction ID") or "").strip(),
                    render_group="Funding",
                    render_notes=row.get("Price", ""),
                )
            )
        return events

    def _fiat_sell_history_events(self, path: Path, source: str) -> list[dict[str, str]]:
        events: list[dict[str, str]] = []
        for index, row in enumerate(read_csv_rows(path), start=2):
            values = [str(value).strip() for value in row.values() if value not in (None, "")]
            if values == ["No data matches the criteria."] or (row.get("Status") or "").strip() != "Successful":
                continue
            spend_amount, spend_asset = parse_number_asset(row["Spend Amount"])
            receive_amount, receive_asset = parse_number_asset(row["Receive Amount"])
            fee_amount, fee_asset = parse_number_asset(row["Fee"])
            raw_row_ref = f"row:{index}"
            events.append(
                canonical_event(
                    event_id=event_id_for(self.name, path.name, raw_row_ref),
                    source=source,
                    adapter=self.name,
                    account="Funding",
                    wallet="Funding",
                    raw_file=path.name,
                    raw_row_ref=raw_row_ref,
                    timestamp=normalized_timestamp(
                        row["Time"],
                        BINANCE_TIME_FORMATS,
                        source_timezone=source_timezone_from_filename(path.name),
                    ),
                    event_kind="Trade",
                    description=f"Binance fiat sell via {row['Method']}",
                    amount_in=receive_amount,
                    asset_in=receive_asset,
                    amount_out=spend_amount,
                    asset_out=spend_asset,
                    fee_amount=fee_amount,
                    fee_asset=fee_asset,
                    tx_hash=(row.get("Transaction ID") or "").strip(),
                    render_group="Funding",
                    render_notes=row.get("Price", ""),
                )
            )
        return events

    def _c2c_order_events(self, path: Path, source: str) -> list[dict[str, str]]:
        events: list[dict[str, str]] = []
        for index, row in enumerate(read_csv_rows(path), start=2):
            if (row.get("Status") or "").strip() != "Completed":
                continue
            raw_row_ref = f"row:{index}"
            order_type = (row.get("Order Type") or "").strip().lower()
            fiat_asset = (row.get("Fiat Type") or "").strip().upper()
            crypto_asset = (row.get("Asset") or "").strip().upper()
            fiat_amount = decimal_text(decimal_or_zero(row["Total Price"]))
            crypto_amount = decimal_text(decimal_or_zero(row["Quantity"]))
            amount_in, asset_in = (fiat_amount, fiat_asset) if order_type == "sell" else (crypto_amount, crypto_asset)
            amount_out, asset_out = (crypto_amount, crypto_asset) if order_type == "sell" else (fiat_amount, fiat_asset)
            events.append(
                canonical_event(
                    event_id=event_id_for(self.name, path.name, raw_row_ref),
                    source=source,
                    adapter=self.name,
                    account="Funding",
                    wallet="Funding",
                    raw_file=path.name,
                    raw_row_ref=raw_row_ref,
                    timestamp=normalized_timestamp(
                        row["Created Time"],
                        BINANCE_TIME_FORMATS,
                        source_timezone=source_timezone_from_filename(path.name),
                    ),
                    event_kind="Trade",
                    description=f"Binance P2P {order_type} {crypto_asset}/{fiat_asset}",
                    amount_in=amount_in,
                    asset_in=asset_in,
                    amount_out=amount_out,
                    asset_out=asset_out,
                    tx_hash=(row.get("Order Number") or "").strip(),
                    render_group="Funding",
                    render_notes=row.get("Counterparty", ""),
                )
            )
        return events

    def _transaction_history_events(
        self,
        path: Path,
        profile: SourceProfile,
        *,
        exception_decisions: dict[str, dict[str, str]],
        covered_timestamps: set[str],
        has_c2c_history: bool,
        exceptions: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        groups: dict[tuple[str, str], list[tuple[int, dict[str, str]]]] = defaultdict(list)
        for index, row in enumerate(read_csv_rows(path), start=2):
            if not any((value or "").strip() for value in row.values()):
                continue
            groups[((row.get("Time") or "").strip(), (row.get("Account") or "").strip())].append((index, row))

        events: list[dict[str, str]] = []
        for (timestamp_text, account), indexed_rows in sorted(groups.items()):
            if not timestamp_text:
                continue
            if timestamp_text in covered_timestamps:
                continue

            active_rows = list(indexed_rows)
            group_timestamp = parse_datetime_to_utc_naive(
                timestamp_text,
                BINANCE_TIME_FORMATS,
                source_timezone=timezone.utc,
            )
            if group_timestamp <= BASELINE_CUTOFF_TIMESTAMP:
                active_rows = [
                    (index, row)
                    for index, row in active_rows
                    if (row.get("Operation") or "").strip() not in self._historical_only_ignored_operations
                ]
            if not active_rows:
                continue

            filtered_rows = list(active_rows)
            operations = {(row.get("Operation") or "").strip() for _, row in filtered_rows}
            if operations & self._trade_operations and operations & {"Deposit", "Withdraw"}:
                filtered_rows = [
                    (index, row)
                    for index, row in filtered_rows
                    if (row.get("Operation") or "").strip() not in {"Deposit", "Withdraw"}
                ]
            active_rows = filtered_rows
            operations = {(row.get("Operation") or "").strip() for _, row in active_rows}
            if operations == {"P2P Trading"} and has_c2c_history:
                continue

            if operations <= self._income_type_by_operation.keys() | {"Distribution", "Realized Profit and Loss", "Funding Fee", "Asset Recovery", "Deposit", "Withdraw", "Fee"}:
                events.extend(self._single_row_events(path, profile.source, account, active_rows))
                continue

            if operations <= self._trade_operations:
                parsed = self._grouped_trade_events(
                    path,
                    profile,
                    account,
                    timestamp_text,
                    active_rows,
                    exception_decisions=exception_decisions,
                )
                events.extend(parsed[0])
                if parsed[1] is not None and parsed[1].get("resolution_status") != "accepted":
                    exceptions.append(parsed[1])
                continue

            raw_row_ref = f"group:{timestamp_text}:{account or 'unknown'}"
            event_id = event_id_for(self.name, path.name, raw_row_ref)
            maybe_append_exception(
                exceptions,
                exception_decisions,
                manifest_fingerprint=profile.manifest_fingerprint,
                source=profile.source,
                adapter=self.name,
                event_id=event_id,
                raw_file=path.name,
                raw_row_ref=raw_row_ref,
                exception_kind="unsupported_group",
                message=f"Unsupported Binance transaction-history operations: {', '.join(sorted(operations))}",
            )
        return events

    def _single_row_events(
        self,
        path: Path,
        source: str,
        account: str,
        indexed_rows: list[tuple[int, dict[str, str]]],
    ) -> list[dict[str, str]]:
        events: list[dict[str, str]] = []
        for index, row in indexed_rows:
            operation = (row.get("Operation") or "").strip()
            amount = decimal_text(abs(decimal_or_zero(row.get("Change"))))
            asset = (row.get("Coin") or "").strip().upper()
            timestamp = normalized_timestamp(
                row["Time"],
                BINANCE_TIME_FORMATS,
                source_timezone=timezone.utc,
            )
            raw_row_ref = f"row:{index}"
            event_id = event_id_for(self.name, path.name, raw_row_ref)
            description = row.get("Remark", "") or operation
            tx_hash = extract_trade_id(row.get("Remark", ""))

            if operation in self._income_type_by_operation:
                events.append(
                    canonical_event(
                        event_id=event_id,
                        source=source,
                        adapter=self.name,
                        account=account or "Spot",
                        wallet=account or "Spot",
                        raw_file=path.name,
                        raw_row_ref=raw_row_ref,
                        timestamp=timestamp,
                        event_kind=self._income_type_by_operation[operation],
                        description=description,
                        amount_in=amount,
                        asset_in=asset,
                        tx_hash=tx_hash,
                        render_group=account or "Spot",
                        render_notes=operation,
                    )
                )
            elif operation == "Deposit":
                events.append(
                    canonical_event(
                        event_id=event_id,
                        source=source,
                        adapter=self.name,
                        account=account or "Spot",
                        wallet=account or "Spot",
                        raw_file=path.name,
                        raw_row_ref=raw_row_ref,
                        timestamp=timestamp,
                        event_kind="Deposit",
                        description=description,
                        amount_in=amount,
                        asset_in=asset,
                        tx_hash=tx_hash,
                        render_group=account or "Spot",
                        render_notes=operation,
                    )
                )
            elif operation == "Withdraw":
                events.append(
                    canonical_event(
                        event_id=event_id,
                        source=source,
                        adapter=self.name,
                        account=account or "Spot",
                        wallet=account or "Spot",
                        raw_file=path.name,
                        raw_row_ref=raw_row_ref,
                        timestamp=timestamp,
                        event_kind="Withdrawal",
                        description=description,
                        amount_out=amount,
                        asset_out=asset,
                        tx_hash=tx_hash,
                        render_group=account or "Spot",
                        render_notes=operation,
                    )
                )
            elif operation == "Fee":
                events.append(
                    canonical_event(
                        event_id=event_id,
                        source=source,
                        adapter=self.name,
                        account=account or "Spot",
                        wallet=account or "Spot",
                        raw_file=path.name,
                        raw_row_ref=raw_row_ref,
                        timestamp=timestamp,
                        event_kind="Other Fee",
                        description=description,
                        amount_out=amount,
                        asset_out=asset,
                        tx_hash=tx_hash,
                        render_group=account or "Spot",
                        render_notes=operation,
                    )
                )
            elif operation == "Distribution":
                event_kind = "Airdrop" if "airdrop" in description.lower() else "Reward / Bonus"
                if decimal_or_zero(row.get("Change")) >= 0:
                    events.append(
                        canonical_event(
                            event_id=event_id,
                            source=source,
                            adapter=self.name,
                            account=account or "Spot",
                            wallet=account or "Spot",
                            raw_file=path.name,
                            raw_row_ref=raw_row_ref,
                            timestamp=timestamp,
                            event_kind=event_kind,
                            description=description,
                            amount_in=amount,
                            asset_in=asset,
                            render_group=account or "Spot",
                            render_notes=operation,
                        )
                    )
                else:
                    events.append(
                        canonical_event(
                            event_id=event_id,
                            source=source,
                            adapter=self.name,
                            account=account or "Spot",
                            wallet=account or "Spot",
                            raw_file=path.name,
                            raw_row_ref=raw_row_ref,
                            timestamp=timestamp,
                            event_kind="Other Expense",
                            description=description,
                            amount_out=amount,
                            asset_out=asset,
                            render_group=account or "Spot",
                            render_notes=operation,
                        )
                    )
            elif operation == "Asset Recovery":
                events.append(
                    canonical_event(
                        event_id=event_id,
                        source=source,
                        adapter=self.name,
                        account=account or "Spot",
                        wallet=account or "Spot",
                        raw_file=path.name,
                        raw_row_ref=raw_row_ref,
                        timestamp=timestamp,
                        event_kind="Other Expense",
                        description=description,
                        amount_out=amount,
                        asset_out=asset,
                        render_group=account or "Spot",
                        render_notes=operation,
                    )
                )
            elif operation in {"Realized Profit and Loss", "Funding Fee"}:
                event_kind = "Derivatives / Futures Profit" if decimal_or_zero(row.get("Change")) >= 0 else "Derivatives / Futures Loss"
                payload = {
                    "event_id": event_id,
                    "source": source,
                    "adapter": self.name,
                    "account": account or "USD-M Futures",
                    "wallet": account or "USD-M Futures",
                    "raw_file": path.name,
                    "raw_row_ref": raw_row_ref,
                    "timestamp": timestamp,
                    "event_kind": event_kind,
                    "description": description,
                    "render_group": account or "USD-M Futures",
                    "render_notes": operation,
                    "tx_hash": tx_hash,
                }
                if decimal_or_zero(row.get("Change")) >= 0:
                    payload.update({"amount_in": amount, "asset_in": asset})
                else:
                    payload.update({"amount_out": amount, "asset_out": asset})
                events.append(canonical_event(**payload))
        return events

    def _grouped_trade_events(
        self,
        path: Path,
        profile: SourceProfile,
        account: str,
        timestamp_text: str,
        indexed_rows: list[tuple[int, dict[str, str]]],
        *,
        exception_decisions: dict[str, dict[str, str]],
    ) -> tuple[list[dict[str, str]], dict[str, str] | None]:
        rows = [row for _, row in indexed_rows]
        operations = {(row.get("Operation") or "").strip() for row in rows}
        raw_row_ref = f"group:{timestamp_text}:{account or 'unknown'}"
        timestamp = normalized_timestamp(
            timestamp_text,
            BINANCE_TIME_FORMATS,
            source_timezone=timezone.utc,
        )

        if operations == {"Small Assets Exchange BNB"}:
            events, message = self._small_asset_exchange_events(path, profile.source, account, timestamp, indexed_rows)
            if message is None:
                return events, None
            event_id = event_id_for(self.name, path.name, raw_row_ref)
            return [], default_exception_row(
                manifest_fingerprint=profile.manifest_fingerprint,
                source=profile.source,
                adapter=self.name,
                event_id=event_id,
                raw_file=path.name,
                raw_row_ref=raw_row_ref,
                exception_kind="ambiguous_group",
                message=message,
                resolution_status=exception_decisions.get(event_id, {}).get("resolution_status", ""),
                resolution_note=exception_decisions.get(event_id, {}).get("resolution_note", ""),
            )

        fee_rows = [row for row in rows if (row.get("Operation") or "").strip() in {"Fee", "Transaction Fee"}]
        non_fee_rows = [row for row in rows if row not in fee_rows]
        positive = {asset: total for asset, total in sum_changes(non_fee_rows).items() if total > 0}
        negative = {asset: abs(total) for asset, total in sum_changes(non_fee_rows).items() if total < 0}
        fee_totals = {asset: abs(total) for asset, total in sum_changes(fee_rows).items() if total != 0}

        if not positive and not negative and len(fee_totals) == 1:
            fee_asset, fee_amount = next(iter(fee_totals.items()))
            event = canonical_event(
                event_id=event_id_for(self.name, path.name, raw_row_ref),
                source=profile.source,
                adapter=self.name,
                account=account or "Spot",
                wallet=account or "Spot",
                raw_file=path.name,
                raw_row_ref=raw_row_ref,
                timestamp=timestamp,
                event_kind="Other Fee",
                description=rows[0].get("Remark", "") or "Binance fee row",
                amount_out=decimal_text(fee_amount),
                asset_out=fee_asset,
                render_group=account or "Spot",
                render_notes=", ".join(sorted(operations)),
            )
            return [event], None

        if len(positive) == 1 and len(negative) == 1 and len(fee_totals) <= 1:
            asset_in, amount_in = next(iter(positive.items()))
            asset_out, amount_out = next(iter(negative.items()))
            trade_id = next((extract_trade_id(row.get("Remark", "")) for row in rows if extract_trade_id(row.get("Remark", ""))), "")
            event = canonical_event(
                event_id=event_id_for(self.name, path.name, raw_row_ref),
                source=profile.source,
                adapter=self.name,
                account=account or "Spot",
                wallet=account or "Spot",
                raw_file=path.name,
                raw_row_ref=raw_row_ref,
                timestamp=timestamp,
                event_kind="Trade",
                description=rows[0].get("Remark", "") or "Binance grouped trade",
                amount_in=decimal_text(amount_in),
                asset_in=asset_in,
                amount_out=decimal_text(amount_out),
                asset_out=asset_out,
                tx_hash=trade_id,
                render_group=account or "Spot",
                render_notes=", ".join(sorted(operations)),
            )
            if fee_totals:
                fee_asset, fee_total = next(iter(fee_totals.items()))
                event = attach_fee_to_event(event, fee_amount=fee_total, fee_asset=fee_asset)
            return [event], None

        event_id = event_id_for(self.name, path.name, raw_row_ref)
        decision = exception_decisions.get(event_id, {})
        return [], default_exception_row(
            manifest_fingerprint=profile.manifest_fingerprint,
            source=profile.source,
            adapter=self.name,
            event_id=event_id,
            raw_file=path.name,
            raw_row_ref=raw_row_ref,
            exception_kind="ambiguous_group",
            message=f"Unable to safely collapse Binance grouped rows with operations: {', '.join(sorted(operations))}",
            resolution_status=decision.get("resolution_status", ""),
            resolution_note=decision.get("resolution_note", ""),
        )

    def _small_asset_exchange_events(
        self,
        path: Path,
        source: str,
        account: str,
        timestamp: str,
        indexed_rows: list[tuple[int, dict[str, str]]],
    ) -> tuple[list[dict[str, str]], str | None]:
        buy_by_asset: dict[str, Decimal] = defaultdict(Decimal)
        sell_by_asset: dict[str, Decimal] = defaultdict(Decimal)
        raw_refs: dict[str, list[str]] = defaultdict(list)
        unresolved = False

        for index, row in indexed_rows:
            coin = (row.get("Coin") or "").strip().upper()
            change = decimal_or_zero(row.get("Change"))
            raw_refs[coin].append(f"row:{index}")
            remark_match = BINANCE_SMALL_ASSET_PATTERN.match((row.get("Remark") or "").strip())
            mapped_asset = (remark_match.group("asset") if remark_match is not None else coin).upper()
            if change < 0 and coin != "BNB":
                sell_by_asset[mapped_asset] += abs(change)
            elif change > 0 and coin == "BNB":
                buy_by_asset[mapped_asset] += change
            else:
                unresolved = True

        if unresolved or set(buy_by_asset) != set(sell_by_asset):
            return [], "Unable to safely pair Binance Small Assets Exchange rows into asset-specific BNB trades."

        events: list[dict[str, str]] = []
        for asset in sorted(sell_by_asset):
            raw_row_ref = f"small_assets:{asset}"
            events.append(
                canonical_event(
                    event_id=event_id_for(self.name, path.name, raw_row_ref),
                    source=source,
                    adapter=self.name,
                    account=account or "Spot",
                    wallet=account or "Spot",
                    raw_file=path.name,
                    raw_row_ref=";".join(sorted(raw_refs.get(asset, []))),
                    timestamp=timestamp,
                    event_kind="Trade",
                    description=f"Binance dust conversion {asset} to BNB",
                    amount_in=decimal_text(buy_by_asset[asset]),
                    asset_in="BNB",
                    amount_out=decimal_text(sell_by_asset[asset]),
                    asset_out=asset,
                    render_group=account or "Spot",
                    render_notes="Small Assets Exchange BNB",
                )
            )
        return events, None


class CryptoComAdapter(SourceAdapter):
    name = "crypto_com"
    aliases = ("crypto.com", "crypto com", "cryptocom")
    supported = True

    def matches_profile(self, profile: SourceProfile) -> bool:
        return profile_has_row(profile, header_contains="timestamp (utc)")

    def timezone_policy_for_row(self, row: dict[str, str]) -> TimezonePolicy | None:
        if not row.get("date_field"):
            return None
        return STRICT_EXPLICIT_UTC_POLICY

    def normalize(
        self,
        raw_dir: Path,
        profile: SourceProfile,
        *,
        exception_decisions: dict[str, dict[str, str]],
    ) -> AdapterNormalizationResult:
        cash_paths = profile_paths(
            raw_dir,
            profile,
            families={"custodial_transaction_csv"},
            suffixes={".csv"},
            predicate=lambda path, row: path.name.lower().startswith("cash_transactions_")
            and "timestamp (utc)" in row.get("header_preview", "").lower(),
        )
        crypto_paths = profile_paths(
            raw_dir,
            profile,
            families={"custodial_transaction_csv"},
            suffixes={".csv"},
            predicate=lambda path, row: path.name.lower().startswith("crypto_transactions_")
            and "timestamp (utc)" in row.get("header_preview", "").lower(),
        )
        exceptions: list[dict[str, str]] = []
        if not cash_paths and not crypto_paths:
            maybe_append_exception(
                exceptions,
                exception_decisions,
                manifest_fingerprint=profile.manifest_fingerprint,
                source=profile.source,
                adapter=self.name,
                event_id="crypto_com:missing_transaction_csvs",
                raw_file="",
                raw_row_ref="",
                exception_kind="missing_required_input",
                message="Crypto.com cash or crypto transaction CSV exports are required for normalization.",
            )
            return AdapterNormalizationResult(canonical_events=[], canonical_balances=[], exceptions=exceptions)

        events: list[dict[str, str]] = []
        for path in cash_paths:
            for index, row in enumerate(read_csv_rows(path), start=2):
                kind = (row.get("Transaction Kind") or "").strip().lower()
                if kind != "viban_deposit":
                    continue
                timestamp = normalized_timestamp(
                    row["Timestamp (UTC)"],
                    CRYPTO_COM_TIME_FORMATS,
                    source_timezone=timezone.utc,
                )
                raw_row_ref = f"row:{index}"
                event_id = event_id_for(self.name, path.name, raw_row_ref)
                events.append(
                    canonical_event(
                        event_id=event_id,
                        source=profile.source,
                        adapter=self.name,
                        account=profile.source,
                        wallet=profile.source,
                        raw_file=path.name,
                        raw_row_ref=raw_row_ref,
                        timestamp=timestamp,
                        event_kind="Deposit",
                        description=(row.get("Transaction Description") or "Crypto.com cash deposit").strip(),
                        amount_in=decimal_text(decimal_or_zero(row.get("Amount"))),
                        asset_in=(row.get("Currency") or "").strip().upper(),
                        tx_hash=(row.get("Transaction Hash") or "").strip(),
                        render_notes=kind,
                    )
                )

        for path in crypto_paths:
            for index, row in enumerate(read_csv_rows(path), start=2):
                kind = (row.get("Transaction Kind") or "").strip().lower()
                timestamp = normalized_timestamp(
                    row["Timestamp (UTC)"],
                    CRYPTO_COM_TIME_FORMATS,
                    source_timezone=timezone.utc,
                )
                raw_row_ref = f"row:{index}"
                event_id = event_id_for(self.name, path.name, raw_row_ref)
                description = (row.get("Transaction Description") or kind or "Crypto.com event").strip()
                tx_hash = tx_hash_or_event_id(event_id, row.get("Transaction Hash") or "")
                currency = (row.get("Currency") or "").strip().upper()
                to_currency = (row.get("To Currency") or "").strip().upper()
                amount = abs(decimal_or_zero(row.get("Amount")))
                to_amount = abs(decimal_or_zero(row.get("To Amount")))

                if kind == "viban_purchase" and currency and to_currency:
                    events.append(
                        canonical_event(
                            event_id=event_id,
                            source=profile.source,
                            adapter=self.name,
                            account=profile.source,
                            wallet=profile.source,
                            raw_file=path.name,
                            raw_row_ref=raw_row_ref,
                            timestamp=timestamp,
                            event_kind="Trade",
                            description=f"{currency} -> {to_currency}",
                            amount_in=decimal_text(to_amount),
                            asset_in=to_currency,
                            amount_out=decimal_text(amount),
                            asset_out=currency,
                            tx_hash=tx_hash,
                            render_notes=kind,
                        )
                    )
                    continue

                if kind == "crypto_withdrawal" and currency:
                    events.append(
                        canonical_event(
                            event_id=event_id,
                            source=profile.source,
                            adapter=self.name,
                            account=profile.source,
                            wallet=profile.source,
                            raw_file=path.name,
                            raw_row_ref=raw_row_ref,
                            timestamp=timestamp,
                            event_kind="Withdrawal",
                            description=description,
                            amount_out=decimal_text(amount),
                            asset_out=currency,
                            tx_hash=tx_hash,
                            render_notes=kind,
                        )
                    )
                    continue

                maybe_append_exception(
                    exceptions,
                    exception_decisions,
                    manifest_fingerprint=profile.manifest_fingerprint,
                    source=profile.source,
                    adapter=self.name,
                    event_id=event_id,
                    raw_file=path.name,
                    raw_row_ref=raw_row_ref,
                    exception_kind="unsupported_row",
                    message=f"Unsupported Crypto.com transaction kind: {kind or 'blank'}",
                )

        return AdapterNormalizationResult(canonical_events=events, canonical_balances=[], exceptions=exceptions)


class EvmExplorerAdapter(SourceAdapter):
    name = "evm_explorer"
    aliases = (
        "evm explorer",
        "bsc metamask wallet",
        "eth metamask wallet",
        "eth galagames wallet",
        "metamask - polygon",
    )
    supported = True

    def timezone_policy_for_row(self, row: dict[str, str]) -> TimezonePolicy | None:
        if not row.get("date_field"):
            return None
        return STRICT_EXPLICIT_UTC_POLICY

    _native_asset_by_scope = {
        "bsc": "BNB",
        "polygon": "MATIC",
        "eth": "ETH",
    }
    _token_symbol_overrides = {
        "0x7ddee176f665cd201f93eede625770e2fd911990": "GALA",
    }

    def matches_source(self, source_name: str) -> bool:
        if super().matches_source(source_name):
            return True
        slug = source_slug(source_name)
        return slug.startswith(("bsc_", "eth_", "polygon_"))

    def matches_profile(self, profile: SourceProfile) -> bool:
        return any(
            row.get("family") in {
                "explorer_transaction_csv",
                "explorer_token_transfer_csv",
                "explorer_internal_transaction_csv",
                "explorer_nft_transfer_csv",
            }
            for row in profile.file_inventory
        )

    def extract_wallet_identifiers(
        self,
        source: str,
        raw_dir: Path,
        profile: SourceProfile,
    ) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        evidence: list[dict[str, str]] = []
        issues: list[dict[str, str]] = []
        scope_key = self._scope_for_profile(profile)
        selected_paths = self._selected_paths(raw_dir, profile, scope_key)
        addresses = {
            match.group(0)
            for path in selected_paths
            for match in EVM_ADDRESS_PATTERN.finditer(path.name)
        }
        for address in sorted(addresses, key=str.lower):
            path = next(path for path in selected_paths if address.lower() in path.name.lower())
            evidence.append(
                wallet_evidence_row(
                    source=source,
                    raw_dir=raw_dir,
                    identifier_value=address,
                    network_scope=self._network_scope_for_key(scope_key),
                    controller="Explorer export",
                    account_label="",
                    evidence_kind="filename",
                    evidence_path=path,
                    confidence="high",
                )
            )

        if not evidence:
            issues.append(
                wallet_issue_row(
                    source=source,
                    raw_dir=raw_dir,
                    wallet_id="",
                    issue_kind="missing_identifier",
                    message="No EVM address could be extracted from the profiled explorer capture.",
                )
            )
        elif len({row["normalized_identifier"] for row in evidence}) > 1:
            issues.append(
                wallet_issue_row(
                    source=source,
                    raw_dir=raw_dir,
                    wallet_id="",
                    issue_kind="multiple_primary_identifiers",
                    message="The profiled explorer capture exposed more than one owned EVM address.",
                )
            )

        return dedupe_rows(evidence, key_fields=WALLET_EVIDENCE_HEADERS), issues

    def normalize(
        self,
        raw_dir: Path,
        profile: SourceProfile,
        *,
        exception_decisions: dict[str, dict[str, str]],
    ) -> AdapterNormalizationResult:
        scope_key = self._scope_for_profile(profile)
        selected_paths = self._selected_paths(raw_dir, profile, scope_key)
        exceptions: list[dict[str, str]] = []
        if not selected_paths:
            maybe_append_exception(
                exceptions,
                exception_decisions,
                manifest_fingerprint=profile.manifest_fingerprint,
                source=profile.source,
                adapter=self.name,
                event_id=f"{self.name}:{scope_key}:missing_scope_files",
                raw_file="",
                raw_row_ref="",
                exception_kind="missing_required_input",
                message=f"No explorer CSV files matched the {scope_key} scope for {profile.source}.",
            )
            return AdapterNormalizationResult(canonical_events=[], canonical_balances=[], exceptions=exceptions)

        owned_addresses = {
            match.group(0).lower()
            for path in selected_paths
            for match in re.finditer(r"0x[a-fA-F0-9]{40}", path.name)
        }
        native_asset = self._native_asset_by_scope[scope_key]
        grouped: dict[str, dict[str, list[tuple[Path, int, dict[str, str]]]]] = defaultdict(
            lambda: {"normal": [], "token": [], "internal": [], "nft": []}
        )
        for path in selected_paths:
            profile_row = next((row for row in profile.file_inventory if row.get("filename") == path.name), {})
            family = self._family_for_profile_row(profile_row)
            if family is None:
                continue
            for index, row in enumerate(read_csv_rows(path), start=2):
                tx_hash = (row.get("Transaction Hash") or "").strip()
                if not tx_hash:
                    continue
                grouped[tx_hash][family].append((path, index, row))

        events: list[dict[str, str]] = []
        for tx_hash, group in sorted(grouped.items(), key=lambda item: self._group_timestamp(item[1])):
            group_events, group_exception = self._group_events(
                profile,
                tx_hash,
                group,
                owned_addresses=owned_addresses,
                native_asset=native_asset,
                exception_decisions=exception_decisions,
            )
            events.extend(group_events)
            if group_exception is not None and group_exception.get("resolution_status") != "accepted":
                exceptions.append(group_exception)

        return AdapterNormalizationResult(canonical_events=events, canonical_balances=[], exceptions=exceptions)

    def _scope_for_profile(self, profile: SourceProfile) -> str:
        context_parts = [source_slug(profile.source)]
        context_parts.extend(source_slug(part) for part in profile.raw_dir.parts[-3:])
        context = " ".join(part for part in context_parts if part)
        if "polygon" in context:
            return "polygon"
        if "bsc" in context or "bnb" in context:
            return "bsc"
        return "eth"

    def _network_scope_for_key(self, scope_key: str) -> str:
        if scope_key == "eth":
            return "ethereum"
        return scope_key

    def _selected_paths(self, raw_dir: Path, profile: SourceProfile, scope_key: str) -> list[Path]:
        candidates = profile_paths(
            raw_dir,
            profile,
            families={
                "explorer_transaction_csv",
                "explorer_token_transfer_csv",
                "explorer_internal_transaction_csv",
                "explorer_nft_transfer_csv",
            },
            suffixes={".csv"},
            predicate=lambda path, row: self._family_for_profile_row(row) is not None,
        )
        if self._is_chain_scoped_capture(profile.raw_dir):
            return candidates
        scoped = [path for path in candidates if self._path_matches_scope(path, scope_key)]
        return scoped

    def _is_chain_scoped_capture(self, raw_dir: Path) -> bool:
        return any(source_slug(part).startswith(("bsc_", "eth_", "polygon_")) for part in raw_dir.parts)

    def _path_matches_scope(self, path: Path, scope_key: str) -> bool:
        lowered = path.name.lower()
        if scope_key == "polygon":
            return "polygon" in lowered
        if scope_key == "bsc":
            return "bsc" in lowered or "bnb" in lowered
        return "-eth" in lowered or "_eth" in lowered or " eth" in lowered or lowered.startswith("eth")

    def _family_for_profile_row(self, row: dict[str, str]) -> str | None:
        family = row.get("family", "")
        if family == "explorer_token_transfer_csv":
            return "token"
        if family == "explorer_internal_transaction_csv":
            return "internal"
        if family == "explorer_nft_transfer_csv":
            return "nft"
        if family == "explorer_transaction_csv":
            return "normal"
        return None

    def _group_timestamp(self, group: dict[str, list[tuple[Path, int, dict[str, str]]]]) -> str:
        timestamps = [
            (row.get("DateTime (UTC)") or "").strip()
            for family_rows in group.values()
            for _, _, row in family_rows
            if (row.get("DateTime (UTC)") or "").strip()
        ]
        return min(timestamps) if timestamps else ""

    def _group_events(
        self,
        profile: SourceProfile,
        tx_hash: str,
        group: dict[str, list[tuple[Path, int, dict[str, str]]]],
        *,
        owned_addresses: set[str],
        native_asset: str,
        exception_decisions: dict[str, dict[str, str]],
    ) -> tuple[list[dict[str, str]], dict[str, str] | None]:
        timestamp = normalized_timestamp(
            self._group_timestamp(group),
            ("%Y-%m-%d %H:%M:%S",),
            source_timezone=timezone.utc,
        )
        raw_file = self._group_raw_file(group)
        raw_row_ref = self._group_raw_ref(group)
        method = self._group_method(group)
        event_id = event_id_for(self.name, raw_file, tx_hash)
        fee_paid = self._group_fee_paid(group, owned_addresses)
        native_in, native_out = self._native_movements(group, native_asset)
        token_in, token_out, inbound_is_airdrop = self._token_movements(group["token"], owned_addresses)
        nft_in, nft_out, suspicious_nft_assets = self._nft_movements(group["nft"], owned_addresses)
        incoming = token_in + nft_in
        outgoing = token_out + nft_out
        has_token_history = bool(group["token"] or group["nft"])

        if not has_token_history and method.lower() in {"exact input", "swap exact eth for tokens", "swap exact tokens for eth", "execute"}:
            decision = exception_decisions.get(event_id, {})
            return [], default_exception_row(
                manifest_fingerprint=profile.manifest_fingerprint,
                source=profile.source,
                adapter=self.name,
                event_id=event_id,
                raw_file=raw_file,
                raw_row_ref=raw_row_ref,
                exception_kind="missing_required_input",
                message=f"{profile.source} needs token-transfer history to deterministically classify {method} tx {tx_hash}.",
                resolution_status=decision.get("resolution_status", ""),
                resolution_note=decision.get("resolution_note", ""),
            )

        if method.lower() in {"approve", "set delegate"}:
            if fee_paid <= 0:
                return [], None
            return [
                canonical_event(
                    event_id=event_id,
                    source=profile.source,
                    adapter=self.name,
                    account=profile.source,
                    wallet=profile.source,
                    raw_file=raw_file,
                    raw_row_ref=raw_row_ref,
                    timestamp=timestamp,
                    event_kind="Other Fee",
                    description=f"{method} - {tx_hash}",
                    amount_out=decimal_text(fee_paid),
                    asset_out=native_asset,
                    tx_hash=tx_hash,
                    render_notes="evm_fee_only",
                )
            ], None

        if method.lower().startswith("stake") and outgoing and not incoming:
            return self._stake_events(
                profile.source,
                raw_file,
                raw_row_ref,
                timestamp,
                tx_hash,
                outgoing[0],
                fee_paid,
                native_asset,
            ), None

        if method.lower().startswith("withdraw") and incoming and not outgoing:
            return self._unstake_events(
                profile.source,
                raw_file,
                raw_row_ref,
                timestamp,
                tx_hash,
                incoming[0],
                fee_paid,
                native_asset,
            ), None

        if "claim" in method.lower() and incoming and not outgoing:
            events = [
                canonical_event(
                    event_id=event_id,
                    source=profile.source,
                    adapter=self.name,
                    account=profile.source,
                    wallet=profile.source,
                    raw_file=raw_file,
                    raw_row_ref=raw_row_ref,
                    timestamp=timestamp,
                    event_kind="Staking",
                    description=f"{method} - {tx_hash}",
                    amount_in=decimal_text(incoming[0][1]),
                    asset_in=incoming[0][0],
                    tx_hash=tx_hash,
                    render_notes="evm_claim",
                )
            ]
            return attach_fee_to_event_list(events, fee_amount=fee_paid, fee_asset=native_asset), None

        if incoming and (outgoing or native_out > 0):
            asset_out, amount_out = outgoing[0] if outgoing else (native_asset, native_out)
            asset_in, amount_in = incoming[0]
            trade_event = canonical_event(
                event_id=event_id,
                source=profile.source,
                adapter=self.name,
                account=profile.source,
                wallet=profile.source,
                raw_file=raw_file,
                raw_row_ref=raw_row_ref,
                timestamp=timestamp,
                event_kind="Trade",
                description=f"{method} - {tx_hash}",
                amount_in=decimal_text(amount_in),
                asset_in=asset_in,
                amount_out=decimal_text(amount_out if asset_out != native_asset else amount_out - fee_paid if amount_out > fee_paid else amount_out),
                asset_out=asset_out,
                tx_hash=tx_hash,
                render_notes="evm_trade",
            )
            return [attach_fee_to_event(trade_event, fee_amount=fee_paid, fee_asset=native_asset)], None

        if suspicious_nft_assets and not incoming and not outgoing and native_in <= 0 and native_out <= 0:
            decision = exception_decisions.get(event_id, {})
            asset_list = ", ".join(suspicious_nft_assets)
            return [], default_exception_row(
                manifest_fingerprint=profile.manifest_fingerprint,
                source=profile.source,
                adapter=self.name,
                event_id=event_id,
                raw_file=raw_file,
                raw_row_ref=raw_row_ref,
                exception_kind="review_required",
                message=(
                    f"{profile.source} received suspicious NFT airdrop {asset_list} in tx {tx_hash}; "
                    "keep it in review instead of auto-importing it as an economic deposit."
                ),
                resolution_status=decision.get("resolution_status", ""),
                resolution_note=decision.get("resolution_note", ""),
            )

        if outgoing:
            asset_out, amount_out = outgoing[0]
            withdrawal_event = canonical_event(
                event_id=event_id,
                source=profile.source,
                adapter=self.name,
                account=profile.source,
                wallet=profile.source,
                raw_file=raw_file,
                raw_row_ref=raw_row_ref,
                timestamp=timestamp,
                event_kind="Withdrawal",
                description=f"{method or 'Transfer out'} - {tx_hash}",
                amount_out=decimal_text(amount_out),
                asset_out=asset_out,
                tx_hash=tx_hash,
                render_notes="evm_out",
            )
            return [attach_fee_to_event(withdrawal_event, fee_amount=fee_paid, fee_asset=native_asset)], None

        if native_out > 0:
            return [
                attach_fee_to_event(
                    canonical_event(
                        event_id=event_id,
                        source=profile.source,
                        adapter=self.name,
                        account=profile.source,
                        wallet=profile.source,
                        raw_file=raw_file,
                        raw_row_ref=raw_row_ref,
                        timestamp=timestamp,
                        event_kind="Withdrawal",
                        description=f"{method or 'Transfer out'} - {tx_hash}",
                        amount_out=decimal_text(native_out),
                        asset_out=native_asset,
                        tx_hash=tx_hash,
                        render_notes="evm_native_out",
                    ),
                    fee_amount=fee_paid,
                    fee_asset=native_asset,
                )
            ], None

        if incoming:
            asset_in, amount_in = incoming[0]
            event_kind = "Airdrop" if inbound_is_airdrop else "Deposit"
            return [
                attach_fee_to_event(
                    canonical_event(
                        event_id=event_id,
                        source=profile.source,
                        adapter=self.name,
                        account=profile.source,
                        wallet=profile.source,
                        raw_file=raw_file,
                        raw_row_ref=raw_row_ref,
                        timestamp=timestamp,
                        event_kind=event_kind,
                        description=f"{method or event_kind} - {tx_hash}",
                        amount_in=decimal_text(amount_in),
                        asset_in=asset_in,
                        tx_hash=tx_hash,
                        render_notes="evm_in",
                    ),
                    fee_amount=fee_paid,
                    fee_asset=native_asset,
                )
            ], None

        if native_in > 0:
            return [
                attach_fee_to_event(
                    canonical_event(
                        event_id=event_id,
                        source=profile.source,
                        adapter=self.name,
                        account=profile.source,
                        wallet=profile.source,
                        raw_file=raw_file,
                        raw_row_ref=raw_row_ref,
                        timestamp=timestamp,
                        event_kind="Deposit",
                        description=f"{method or 'Transfer in'} - {tx_hash}",
                        amount_in=decimal_text(native_in),
                        asset_in=native_asset,
                        tx_hash=tx_hash,
                        render_notes="evm_native_in",
                    ),
                    fee_amount=fee_paid,
                    fee_asset=native_asset,
                )
            ], None

        if fee_paid > 0:
            return [
                canonical_event(
                    event_id=event_id_for(self.name, raw_file, f"{tx_hash}:fee"),
                    source=profile.source,
                    adapter=self.name,
                    account=profile.source,
                    wallet=profile.source,
                    raw_file=raw_file,
                    raw_row_ref=raw_row_ref,
                    timestamp=timestamp,
                    event_kind="Other Fee",
                    description=f"{method or 'Explorer tx'} - {tx_hash}",
                    amount_out=decimal_text(fee_paid),
                    asset_out=native_asset,
                    tx_hash=tx_hash,
                    render_notes="evm_fee_only",
                )
            ], None
        return [], None

    def _group_raw_file(self, group: dict[str, list[tuple[Path, int, dict[str, str]]]]) -> str:
        for family_rows in group.values():
            if family_rows:
                return family_rows[0][0].name
        return ""

    def _group_raw_ref(self, group: dict[str, list[tuple[Path, int, dict[str, str]]]]) -> str:
        return ";".join(f"{path.name}:row:{index}" for family_rows in group.values() for path, index, _ in family_rows)

    def _group_method(self, group: dict[str, list[tuple[Path, int, dict[str, str]]]]) -> str:
        for _, _, row in group["normal"]:
            method = (row.get("Method") or "").strip()
            if method:
                return method
        for _, _, row in group["internal"]:
            row_type = (row.get("Type") or "").strip()
            if row_type:
                return row_type
        for _, _, row in group["token"]:
            return "Transfer"
        for _, _, row in group["nft"]:
            return (row.get("Method") or "").strip() or "NFT"
        return "Explorer tx"

    def _group_fee_paid(
        self,
        group: dict[str, list[tuple[Path, int, dict[str, str]]]],
        owned_addresses: set[str],
    ) -> Decimal:
        total = Decimal("0")
        for _, _, row in group["normal"]:
            from_owned = (row.get("From") or "").strip().lower() in owned_addresses
            if from_owned or decimal_or_zero(self._value_out(row)) > 0 or (row.get("ErrCode") or "").strip():
                total += decimal_or_zero(self._tx_fee(row))
        return total

    def _native_movements(
        self,
        group: dict[str, list[tuple[Path, int, dict[str, str]]]],
        native_asset: str,
    ) -> tuple[Decimal, Decimal]:
        native_in = Decimal("0")
        native_out = Decimal("0")
        for _, _, row in group["normal"]:
            native_in += decimal_or_zero(self._value_in(row))
            native_out += decimal_or_zero(self._value_out(row))
        for _, _, row in group["internal"]:
            native_in += decimal_or_zero(self._value_in(row))
            native_out += decimal_or_zero(self._value_out(row))
        return native_in, native_out

    def _token_movements(
        self,
        rows: list[tuple[Path, int, dict[str, str]]],
        owned_addresses: set[str],
    ) -> tuple[list[tuple[str, Decimal]], list[tuple[str, Decimal]], bool]:
        incoming: dict[str, Decimal] = defaultdict(Decimal)
        outgoing: dict[str, Decimal] = defaultdict(Decimal)
        inbound_is_airdrop = False
        for _, _, row in rows:
            symbol = self._token_symbol(row)
            amount = decimal_or_zero(row.get("TokenValue"))
            from_address = (row.get("From") or "").strip().lower()
            to_address = (row.get("To") or "").strip().lower()
            if to_address in owned_addresses and from_address not in owned_addresses:
                incoming[symbol] += amount
                inbound_is_airdrop = inbound_is_airdrop or self._is_airdrop_like_token(row)
            elif from_address in owned_addresses and to_address not in owned_addresses:
                outgoing[symbol] += amount
        return sorted(incoming.items()), sorted(outgoing.items()), inbound_is_airdrop

    def _nft_movements(
        self,
        rows: list[tuple[Path, int, dict[str, str]]],
        owned_addresses: set[str],
    ) -> tuple[list[tuple[str, Decimal]], list[tuple[str, Decimal]], list[str]]:
        incoming: dict[str, Decimal] = defaultdict(Decimal)
        outgoing: dict[str, Decimal] = defaultdict(Decimal)
        suspicious_incoming: set[str] = set()
        for _, _, row in rows:
            asset = (row.get("TokenName") or "").strip() or (row.get("Contract") or "").strip() or "NFT"
            quantity = decimal_or_zero(row.get("Quantity") or "1")
            from_address = (row.get("From") or "").strip().lower()
            to_address = (row.get("To") or "").strip().lower()
            if to_address in owned_addresses and from_address not in owned_addresses:
                if self._is_suspicious_nft(row):
                    suspicious_incoming.add(asset)
                else:
                    incoming[asset] += quantity
            elif from_address in owned_addresses and to_address not in owned_addresses:
                outgoing[asset] += quantity
        return sorted(incoming.items()), sorted(outgoing.items()), sorted(suspicious_incoming)

    def _token_symbol(self, row: dict[str, str]) -> str:
        contract = (row.get("ContractAddress") or "").strip().lower()
        if contract in self._token_symbol_overrides:
            return self._token_symbol_overrides[contract]
        symbol = (row.get("TokenSymbol") or "").strip()
        if symbol and "TOKEN*" not in symbol:
            return symbol.upper()
        token_name = (row.get("TokenName") or "").strip()
        if token_name and "TOKEN*" not in token_name:
            return token_name.upper()
        return (contract[-8:] or "TOKEN").upper()

    def _is_airdrop_like_token(self, row: dict[str, str]) -> bool:
        from_address = (row.get("From") or "").strip().lower()
        contract = (row.get("ContractAddress") or "").strip().lower()
        if contract in self._token_symbol_overrides and from_address != "0x0000000000000000000000000000000000000000":
            return False
        symbol = (row.get("TokenSymbol") or "").strip()
        token_name = (row.get("TokenName") or "").strip()
        return (
            from_address == "0x0000000000000000000000000000000000000000"
            or "." in symbol
            or "*" in symbol
            or ":" in token_name
        )

    def _is_suspicious_nft(self, row: dict[str, str]) -> bool:
        token_name = (row.get("TokenName") or "").strip()
        lowered = token_name.lower()
        return (
            lowered.startswith("$")
            or "token*" in lowered
            or " pass " in f" {lowered} "
            or lowered.endswith(" pass")
        )

    def _value_in(self, row: dict[str, str]) -> str:
        for key, value in row.items():
            if key.startswith("Value_IN("):
                return value
        return ""

    def _value_out(self, row: dict[str, str]) -> str:
        for key, value in row.items():
            if key.startswith("Value_OUT("):
                return value
        return ""

    def _tx_fee(self, row: dict[str, str]) -> str:
        for key, value in row.items():
            if key.startswith("TxnFee("):
                return value
        return ""

    def _stake_events(
        self,
        source: str,
        raw_file: str,
        raw_row_ref: str,
        timestamp: str,
        tx_hash: str,
        outgoing: tuple[str, Decimal],
        fee_paid: Decimal,
        native_asset: str,
    ) -> list[dict[str, str]]:
        asset, amount = outgoing
        staked_source = f"{source} Staked"
        events = [
            canonical_event(
                event_id=event_id_for(self.name, raw_file, f"{tx_hash}:stake_out"),
                source=source,
                adapter=self.name,
                account=source,
                wallet=source,
                raw_file=raw_file,
                raw_row_ref=raw_row_ref,
                timestamp=timestamp,
                event_kind="Withdrawal",
                description=f"Stake {asset} - {tx_hash}",
                amount_out=decimal_text(amount),
                asset_out=asset,
                tx_hash=tx_hash,
                render_notes="evm_stake_out",
            ),
            canonical_event(
                event_id=event_id_for(self.name, raw_file, f"{tx_hash}:stake_in"),
                source=staked_source,
                adapter=self.name,
                account=staked_source,
                wallet=staked_source,
                raw_file=raw_file,
                raw_row_ref=raw_row_ref,
                timestamp=timestamp,
                event_kind="Deposit",
                description=f"Stake {asset} - {tx_hash}",
                amount_in=decimal_text(amount),
                asset_in=asset,
                tx_hash=tx_hash,
                render_notes="evm_stake_in",
            ),
        ]
        return attach_fee_to_event_list(events, fee_amount=fee_paid, fee_asset=native_asset)

    def _unstake_events(
        self,
        source: str,
        raw_file: str,
        raw_row_ref: str,
        timestamp: str,
        tx_hash: str,
        incoming: tuple[str, Decimal],
        fee_paid: Decimal,
        native_asset: str,
    ) -> list[dict[str, str]]:
        asset, amount = incoming
        staked_source = f"{source} Staked"
        events = [
            canonical_event(
                event_id=event_id_for(self.name, raw_file, f"{tx_hash}:unstake_in"),
                source=source,
                adapter=self.name,
                account=source,
                wallet=source,
                raw_file=raw_file,
                raw_row_ref=raw_row_ref,
                timestamp=timestamp,
                event_kind="Deposit",
                description=f"Unstake {asset} - {tx_hash}",
                amount_in=decimal_text(amount),
                asset_in=asset,
                tx_hash=tx_hash,
                render_notes="evm_unstake_in",
            ),
            canonical_event(
                event_id=event_id_for(self.name, raw_file, f"{tx_hash}:unstake_out"),
                source=staked_source,
                adapter=self.name,
                account=staked_source,
                wallet=staked_source,
                raw_file=raw_file,
                raw_row_ref=raw_row_ref,
                timestamp=timestamp,
                event_kind="Withdrawal",
                description=f"Unstake {asset} - {tx_hash}",
                amount_out=decimal_text(amount),
                asset_out=asset,
                tx_hash=tx_hash,
                render_notes="evm_unstake_out",
            ),
        ]
        return attach_fee_to_event_list(events, fee_amount=fee_paid, fee_asset=native_asset)


class ShakepayAdapter(SourceAdapter):
    name = "shakepay"
    aliases = ("shakepay",)
    supported = True

    def matches_profile(self, profile: SourceProfile) -> bool:
        return profile_has_row(profile, header_contains="credit") and profile_has_row(profile, header_contains="debit")

    def timezone_policy_for_row(self, row: dict[str, str]) -> TimezonePolicy | None:
        if not row.get("date_field"):
            return None
        return SHAKEPAY_SOURCE_LOCAL_POLICY

    def normalize(
        self,
        raw_dir: Path,
        profile: SourceProfile,
        *,
        exception_decisions: dict[str, dict[str, str]],
    ) -> AdapterNormalizationResult:
        cash_paths = profile_paths(
            raw_dir,
            profile,
            families={"fiat_transaction_csv"},
            suffixes={".csv"},
            predicate=lambda path, row: "credit" in row.get("header_preview", "").lower(),
        )
        crypto_paths = profile_paths(
            raw_dir,
            profile,
            families={"custodial_transaction_csv"},
            suffixes={".csv"},
            predicate=lambda path, row: "amount credited" in row.get("header_preview", "").lower(),
        )
        pdf_paths = profile_paths(
            raw_dir,
            profile,
            families={"statement_balance_pdf"},
            suffixes={".pdf"},
            predicate=lambda path, _: "performance report" in path.name.lower(),
        )
        exceptions: list[dict[str, str]] = []
        if not cash_paths and not crypto_paths:
            maybe_append_exception(
                exceptions,
                exception_decisions,
                manifest_fingerprint=profile.manifest_fingerprint,
                source=profile.source,
                adapter=self.name,
                event_id="shakepay:missing_transaction_csvs",
                raw_file="",
                raw_row_ref="",
                exception_kind="missing_required_input",
                message="Shakepay cash or crypto transaction CSV exports are required for normalization.",
            )
            return AdapterNormalizationResult(canonical_events=[], canonical_balances=[], exceptions=exceptions)

        events: list[dict[str, str]] = []
        balances: list[dict[str, str]] = []
        for pdf_path in pdf_paths:
            balances.extend(shakepay_balance_rows_from_text(extract_pdf_text(pdf_path), pdf_path.name))

        for path in crypto_paths:
            for index, row in enumerate(read_csv_rows(path), start=2):
                event = self._crypto_event(path, profile.source, index, row)
                if event is not None:
                    events.append(event)

        for path in cash_paths:
            for index, row in enumerate(read_csv_rows(path), start=2):
                event = self._cash_event(path, profile.source, index, row)
                if event is not None:
                    events.append(event)

        return AdapterNormalizationResult(canonical_events=events, canonical_balances=balances, exceptions=exceptions)

    def _crypto_event(self, path: Path, source: str, index: int, row: dict[str, str]) -> dict[str, str] | None:
        event_type = (row.get("Type") or "").strip()
        raw_row_ref = f"row:{index}"
        event_id = event_id_for(self.name, path.name, raw_row_ref)
        timestamp = normalized_timestamp(
            row["Date"],
            SHAKEPAY_TIME_FORMATS,
            source_timezone=SHAKEPAY_SOURCE_TIMEZONE,
        )
        description = (row.get("Description") or event_type or "Shakepay").strip()

        if event_type == "Reward":
            return canonical_event(
                event_id=event_id,
                source=source,
                adapter=self.name,
                account=source,
                wallet=source,
                raw_file=path.name,
                raw_row_ref=raw_row_ref,
                timestamp=timestamp,
                event_kind="Reward / Bonus",
                description=description.lower(),
                amount_in=decimal_text(abs(decimal_or_zero(row.get("Amount Credited")))),
                asset_in=(row.get("Asset Credited") or "").strip().upper(),
                tx_hash=event_id,
                render_notes=event_type,
            )

        if event_type == "Buy":
            return canonical_event(
                event_id=event_id,
                source=source,
                adapter=self.name,
                account=source,
                wallet=source,
                raw_file=path.name,
                raw_row_ref=raw_row_ref,
                timestamp=timestamp,
                event_kind="Trade",
                description=description,
                amount_in=decimal_text(abs(decimal_or_zero(row.get("Amount Credited")))),
                asset_in=(row.get("Asset Credited") or "").strip().upper(),
                amount_out=decimal_text(abs(decimal_or_zero(row.get("Amount Debited")))),
                asset_out=(row.get("Asset Debited") or "").strip().upper(),
                tx_hash=event_id,
                render_notes=event_type,
            )

        if event_type == "Sell":
            return canonical_event(
                event_id=event_id,
                source=source,
                adapter=self.name,
                account=source,
                wallet=source,
                raw_file=path.name,
                raw_row_ref=raw_row_ref,
                timestamp=timestamp,
                event_kind="Trade",
                description=description,
                amount_in=decimal_text(abs(decimal_or_zero(row.get("Amount Credited")))),
                asset_in=(row.get("Asset Credited") or "").strip().upper(),
                amount_out=decimal_text(abs(decimal_or_zero(row.get("Amount Debited")))),
                asset_out=(row.get("Asset Debited") or "").strip().upper(),
                tx_hash=event_id,
                render_notes=event_type,
            )

        if event_type == "Receive":
            return canonical_event(
                event_id=event_id,
                source=source,
                adapter=self.name,
                account=source,
                wallet=source,
                raw_file=path.name,
                raw_row_ref=raw_row_ref,
                timestamp=timestamp,
                event_kind="Deposit",
                description=description,
                amount_in=decimal_text(abs(decimal_or_zero(row.get("Amount Credited")))),
                asset_in=(row.get("Asset Credited") or "").strip().upper(),
                tx_hash=event_id,
                render_notes=event_type,
            )

        if event_type == "Send":
            return canonical_event(
                event_id=event_id,
                source=source,
                adapter=self.name,
                account=source,
                wallet=source,
                raw_file=path.name,
                raw_row_ref=raw_row_ref,
                timestamp=timestamp,
                event_kind="Withdrawal",
                description=description,
                amount_out=decimal_text(abs(decimal_or_zero(row.get("Amount Debited")))),
                asset_out=(row.get("Asset Debited") or "").strip().upper(),
                tx_hash=event_id,
                render_notes=event_type,
            )
        return None

    def _cash_event(self, path: Path, source: str, index: int, row: dict[str, str]) -> dict[str, str] | None:
        event_type = (row.get("Type") or "").strip()
        raw_row_ref = f"row:{index}"
        event_id = event_id_for(self.name, path.name, raw_row_ref)
        timestamp = normalized_timestamp(
            row["Date"],
            SHAKEPAY_TIME_FORMATS,
            source_timezone=SHAKEPAY_SOURCE_TIMEZONE,
        )
        description = (row.get("Description") or event_type or "Shakepay cash").strip()
        credit = abs(decimal_or_zero(row.get("Credit")))
        debit = abs(decimal_or_zero(row.get("Debit")))

        if event_type in {"Buy", "Sell"}:
            return None

        if event_type in {"Interac e-Transfer", "Receive"} and credit > 0:
            return canonical_event(
                event_id=event_id,
                source=source,
                adapter=self.name,
                account=source,
                wallet=source,
                raw_file=path.name,
                raw_row_ref=raw_row_ref,
                timestamp=timestamp,
                event_kind="Deposit",
                description=description,
                amount_in=decimal_text(credit),
                asset_in="CAD",
                tx_hash=event_id,
                render_notes=event_type,
            )

        if event_type in {"Card purchase", "Bill payment", "Other"} and debit > 0:
            return canonical_event(
                event_id=event_id,
                source=source,
                adapter=self.name,
                account=source,
                wallet=source,
                raw_file=path.name,
                raw_row_ref=raw_row_ref,
                timestamp=timestamp,
                event_kind="Expense (non taxable)",
                description=description,
                amount_out=decimal_text(debit),
                asset_out="CAD",
                tx_hash=event_id,
                render_notes=event_type,
            )

        if event_type == "Send" and debit > 0:
            return canonical_event(
                event_id=event_id,
                source=source,
                adapter=self.name,
                account=source,
                wallet=source,
                raw_file=path.name,
                raw_row_ref=raw_row_ref,
                timestamp=timestamp,
                event_kind="Withdrawal",
                description=description,
                amount_out=decimal_text(debit),
                asset_out="CAD",
                tx_hash=event_id,
                render_notes=event_type,
            )

        if event_type == "Reward" and credit > 0:
            return canonical_event(
                event_id=event_id,
                source=source,
                adapter=self.name,
                account=source,
                wallet=source,
                raw_file=path.name,
                raw_row_ref=raw_row_ref,
                timestamp=timestamp,
                event_kind="Reward / Bonus",
                description=description,
                amount_in=decimal_text(credit),
                asset_in="CAD",
                tx_hash=event_id,
                render_notes=event_type,
            )

        return None


class LedgerLiveAdapter(SourceAdapter):
    name = "ledger_live"
    aliases = ("ledger live", "ada ledger", "ledger-live-main")
    supported = True

    def matches_source(self, source_name: str) -> bool:
        return super().matches_source(source_name) or source_slug(source_name).startswith("ledger_live")

    def matches_profile(self, profile: SourceProfile) -> bool:
        return profile_has_row(profile, families={"wallet_operation_csv"}, header_contains="account xpub")

    def extract_wallet_identifiers(
        self,
        source: str,
        raw_dir: Path,
        profile: SourceProfile,
    ) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        evidence: list[dict[str, str]] = []
        issues: list[dict[str, str]] = []
        account_identifiers: dict[str, set[str]] = defaultdict(set)
        for path in profile_paths(raw_dir, profile, families={"wallet_operation_csv"}, suffixes={".csv"}):
            for row in read_csv_rows(path):
                account_label = (row.get("Account Name") or "").strip()
                identifier_value = (row.get("Account xpub") or "").strip()
                if not identifier_value:
                    continue
                account_identifiers[account_label].add(identifier_value)
                evidence.append(
                    wallet_evidence_row(
                        source=source,
                        raw_dir=raw_dir,
                        identifier_value=identifier_value,
                        network_scope=self._wallet_network_scope(identifier_value, account_label, row),
                        controller="Ledger Live",
                        account_label=account_label,
                        evidence_kind="csv_row",
                        evidence_path=path,
                        confidence="high",
                    )
                )

        for account_label, identifiers in sorted(account_identifiers.items()):
            if len(identifiers) > 1:
                issues.append(
                    wallet_issue_row(
                        source=source,
                        raw_dir=raw_dir,
                        wallet_id="",
                        issue_kind="account_identifier_conflict",
                        message=f"Ledger Live account {account_label or 'blank'} maps to multiple identifiers.",
                    )
                )

        if not evidence:
            issues.append(
                wallet_issue_row(
                    source=source,
                    raw_dir=raw_dir,
                    wallet_id="",
                    issue_kind="missing_identifier",
                    message="No account identifier was found in the Ledger Live operations exports.",
                )
            )

        return dedupe_rows(evidence, key_fields=WALLET_EVIDENCE_HEADERS), issues

    def timezone_policy_for_row(self, row: dict[str, str]) -> TimezonePolicy | None:
        if not row.get("date_field"):
            return None
        return STRICT_EXPLICIT_UTC_POLICY

    def normalize(
        self,
        raw_dir: Path,
        profile: SourceProfile,
        *,
        exception_decisions: dict[str, dict[str, str]],
    ) -> AdapterNormalizationResult:
        paths = profile_paths(raw_dir, profile, families={"wallet_operation_csv"}, suffixes={".csv"})
        exceptions: list[dict[str, str]] = []
        if not paths:
            maybe_append_exception(
                exceptions,
                exception_decisions,
                manifest_fingerprint=profile.manifest_fingerprint,
                source=profile.source,
                adapter=self.name,
                event_id="ledger_live:missing_operations_csv",
                raw_file="",
                raw_row_ref="",
                exception_kind="missing_required_input",
                message="Ledger Live operations CSV export is required for normalization.",
            )
            return AdapterNormalizationResult(canonical_events=[], canonical_balances=[], exceptions=exceptions)

        grouped_rows: dict[tuple[str, str], list[tuple[Path, int, dict[str, str]]]] = defaultdict(list)
        for path in paths:
            for index, row in enumerate(read_csv_rows(path), start=2):
                if (row.get("Status") or "Confirmed").strip() not in {"", "Confirmed"}:
                    continue
                operation_hash = (row.get("Operation Hash") or "").strip()
                if not operation_hash:
                    continue
                account_name = (row.get("Account Name") or "").strip() or profile.source
                grouped_rows[(account_name, operation_hash)].append((path, index, row))

        events: list[dict[str, str]] = []
        for (account_name, operation_hash), indexed_rows in sorted(grouped_rows.items()):
            events.extend(self._group_events(profile.source, account_name, operation_hash, indexed_rows))

        return AdapterNormalizationResult(canonical_events=events, canonical_balances=[], exceptions=exceptions)

    def _group_events(
        self,
        source: str,
        account_name: str,
        operation_hash: str,
        indexed_rows: list[tuple[Path, int, dict[str, str]]],
    ) -> list[dict[str, str]]:
        timestamp = normalized_timestamp(indexed_rows[0][2]["Operation Date"], LEDGER_LIVE_TIME_FORMATS)
        by_type: dict[str, list[tuple[Path, int, dict[str, str]]]] = defaultdict(list)
        for item in indexed_rows:
            by_type[(item[2].get("Operation Type") or "").strip().upper()].append(item)

        if by_type.get("DELEGATE"):
            by_type.pop("OUT", None)

        in_assets = defaultdict(Decimal)
        out_assets = defaultdict(Decimal)
        fee_assets = defaultdict(Decimal)
        for _, _, row in by_type.get("IN", []):
            in_assets[(row.get("Currency Ticker") or "").strip().upper()] += decimal_or_zero(row.get("Operation Amount"))
        for _, _, row in by_type.get("OUT", []):
            out_assets[(row.get("Currency Ticker") or "").strip().upper()] += decimal_or_zero(row.get("Operation Amount"))
        for _, _, row in by_type.get("FEES", []):
            fee_assets[(row.get("Currency Ticker") or "").strip().upper()] += decimal_or_zero(row.get("Operation Amount"))

        events: list[dict[str, str]] = []
        if len(in_assets) == 1 and len(out_assets) == 1:
            asset_in, amount_in = next(iter(in_assets.items()))
            asset_out, amount_out = next(iter(out_assets.items()))
            fee_asset = ""
            fee_amount = ""
            if len(fee_assets) == 1:
                fee_asset, fee_total = next(iter(fee_assets.items()))
                fee_amount = decimal_text(fee_total)
            event_id = event_id_for(self.name, indexed_rows[0][0].name, operation_hash)
            events.append(
                canonical_event(
                    event_id=event_id,
                    source=source,
                    adapter=self.name,
                    account=account_name,
                    wallet=account_name,
                    raw_file=indexed_rows[0][0].name,
                    raw_row_ref=";".join(f"{path.name}:row:{index}" for path, index, _ in indexed_rows),
                    timestamp=timestamp,
                    event_kind="Trade",
                    description=account_name,
                    amount_in=decimal_text(amount_in),
                    asset_in=asset_in,
                    amount_out=decimal_text(amount_out),
                    asset_out=asset_out,
                    fee_amount=fee_amount,
                    fee_asset=fee_asset,
                    tx_hash=operation_hash,
                    render_notes="ledger_live_grouped_trade",
                )
            )
            return events

        for path, index, row in by_type.get("IN", []):
            raw_row_ref = f"row:{index}"
            event_id = event_id_for(self.name, path.name, raw_row_ref)
            asset = (row.get("Currency Ticker") or "").strip().upper()
            events.append(
                canonical_event(
                    event_id=event_id,
                    source=source,
                    adapter=self.name,
                    account=account_name,
                    wallet=account_name,
                    raw_file=path.name,
                    raw_row_ref=raw_row_ref,
                    timestamp=normalized_timestamp(row["Operation Date"], LEDGER_LIVE_TIME_FORMATS),
                    event_kind="Deposit",
                    description=account_name,
                    amount_in=decimal_text(decimal_or_zero(row.get("Operation Amount"))),
                    asset_in=asset,
                    tx_hash=f"IN-{operation_hash}",
                    render_notes="ledger_live_in",
                )
            )

        for path, index, row in by_type.get("OUT", []):
            raw_row_ref = f"row:{index}"
            event_id = event_id_for(self.name, path.name, raw_row_ref)
            asset = (row.get("Currency Ticker") or "").strip().upper()
            events.append(
                canonical_event(
                    event_id=event_id,
                    source=source,
                    adapter=self.name,
                    account=account_name,
                    wallet=account_name,
                    raw_file=path.name,
                    raw_row_ref=raw_row_ref,
                    timestamp=normalized_timestamp(row["Operation Date"], LEDGER_LIVE_TIME_FORMATS),
                    event_kind="Withdrawal",
                    description=account_name,
                    amount_out=decimal_text(decimal_or_zero(row.get("Operation Amount"))),
                    asset_out=asset,
                    fee_amount=decimal_text(decimal_or_zero(row.get("Operation Fees"))),
                    fee_asset=asset if decimal_or_zero(row.get("Operation Fees")) else "",
                    tx_hash=f"OUT-{operation_hash}",
                    render_notes="ledger_live_out",
                )
            )

        for path, index, row in by_type.get("DELEGATE", []):
            raw_row_ref = f"row:{index}"
            event_id = event_id_for(self.name, path.name, raw_row_ref)
            asset = (row.get("Currency Ticker") or "").strip().upper()
            events.append(
                canonical_event(
                    event_id=event_id,
                    source=source,
                    adapter=self.name,
                    account=account_name,
                    wallet=account_name,
                    raw_file=path.name,
                    raw_row_ref=raw_row_ref,
                    timestamp=normalized_timestamp(row["Operation Date"], LEDGER_LIVE_TIME_FORMATS),
                    event_kind="Expense (non taxable)",
                    description=f"{asset} Staking Deposit - {operation_hash}",
                    amount_out=decimal_text(decimal_or_zero(row.get("Operation Amount"))),
                    asset_out=asset,
                    fee_amount=decimal_text(decimal_or_zero(row.get("Operation Fees"))),
                    fee_asset=asset if decimal_or_zero(row.get("Operation Fees")) else "",
                    render_notes="ledger_live_delegate",
                )
            )

        for path, index, row in by_type.get("FEES", []):
            raw_row_ref = f"row:{index}"
            event_id = event_id_for(self.name, path.name, raw_row_ref)
            asset = (row.get("Currency Ticker") or "").strip().upper()
            events.append(
                canonical_event(
                    event_id=event_id,
                    source=source,
                    adapter=self.name,
                    account=account_name,
                    wallet=account_name,
                    raw_file=path.name,
                    raw_row_ref=raw_row_ref,
                    timestamp=normalized_timestamp(row["Operation Date"], LEDGER_LIVE_TIME_FORMATS),
                    event_kind="Other Fee",
                    description=f"{account_name} network fee",
                    amount_out=decimal_text(decimal_or_zero(row.get("Operation Amount"))),
                    asset_out=asset,
                    tx_hash=f"FEE-{operation_hash}",
                    render_notes="ledger_live_fee",
                )
            )
        return events

    def _wallet_network_scope(self, identifier_value: str, account_label: str, row: dict[str, str]) -> str:
        kind = infer_identifier_kind(identifier_value)
        if kind == "btc_xpub":
            return "bitcoin"
        if kind == "cardano_account_key":
            return "cardano"
        if kind == "evm_address":
            ticker = (row.get("Currency Ticker") or "").strip().upper()
            if ticker == "ETH":
                return "ethereum"
        account = account_label.lower()
        if "ethereum" in account or account.startswith("eth"):
            return "ethereum"
        if "bitcoin" in account or account.startswith("btc"):
            return "bitcoin"
        if "cardano" in account or "ada" in account:
            return "cardano"
        return ""


class NearAdapter(SourceAdapter):
    name = "near"
    aliases = ("near", "near wallet", "near wallet - staking", "near-main")
    supported = True

    def matches_source(self, source_name: str) -> bool:
        return super().matches_source(source_name) or source_slug(source_name).startswith("near")

    def matches_profile(self, profile: SourceProfile) -> bool:
        return any(
            row.get("family") in {"near_transaction_csv", "near_ft_transaction_csv", "near_nft_transaction_csv", "near_receipt_csv"}
            for row in profile.file_inventory
        )

    def timezone_policy_for_row(self, row: dict[str, str]) -> TimezonePolicy | None:
        if not row.get("date_field"):
            return None
        return ASSUMED_UTC_NAIVE_POLICY

    def extract_wallet_identifiers(
        self,
        source: str,
        raw_dir: Path,
        profile: SourceProfile,
    ) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        evidence = [
            wallet_evidence_row(
                source=source,
                raw_dir=raw_dir,
                identifier_value=identifier_value,
                network_scope="near",
                controller="NearBlocks export",
                account_label="",
                evidence_kind="filename",
                evidence_path=path,
                confidence="high",
            )
            for identifier_value, path in self._owned_account_paths(profile, raw_dir)
        ]
        issues: list[dict[str, str]] = []
        if not evidence:
            issues.append(
                wallet_issue_row(
                    source=source,
                    raw_dir=raw_dir,
                    wallet_id="",
                    issue_kind="missing_identifier",
                    message="No NEAR account identifier was found in the profiled capture.",
                )
            )
        return dedupe_rows(evidence, key_fields=WALLET_EVIDENCE_HEADERS), issues

    def normalize(
        self,
        raw_dir: Path,
        profile: SourceProfile,
        *,
        exception_decisions: dict[str, dict[str, str]],
    ) -> AdapterNormalizationResult:
        tx_paths = profile_paths(raw_dir, profile, families={"near_transaction_csv"}, suffixes={".csv"})
        ft_paths = profile_paths(raw_dir, profile, families={"near_ft_transaction_csv"}, suffixes={".csv"})
        nft_paths = profile_paths(raw_dir, profile, families={"near_nft_transaction_csv"}, suffixes={".csv"})
        exceptions: list[dict[str, str]] = []
        if not tx_paths and not ft_paths and not nft_paths:
            maybe_append_exception(
                exceptions,
                exception_decisions,
                manifest_fingerprint=profile.manifest_fingerprint,
                source=profile.source,
                adapter=self.name,
                event_id="near:missing_export_csvs",
                raw_file="",
                raw_row_ref="",
                exception_kind="missing_required_input",
                message="NEAR transaction or token export CSVs are required for normalization.",
            )
            return AdapterNormalizationResult(canonical_events=[], canonical_balances=[], exceptions=exceptions)

        events: list[dict[str, str]] = []
        owned_accounts = self._owned_accounts(profile, raw_dir)
        seen_tx_hashes: set[str] = set()
        for path in tx_paths:
            for index, row in enumerate(read_csv_rows(path), start=2):
                tx_hash = (row.get("Txn Hash") or "").strip()
                if not tx_hash or tx_hash in seen_tx_hashes or (row.get("Status") or "").strip() != "Success":
                    continue
                seen_tx_hashes.add(tx_hash)
                method = (row.get("Method") or "").strip()
                if method == "TRANSFER" and (row.get("To") or "").strip().lower() in owned_accounts:
                    events.append(self._near_deposit_event(path, profile.source, index, row))
                    continue
                if method == "deposit_and_stake":
                    events.extend(self._near_stake_events(path, profile.source, index, row))
                    continue

        for path in ft_paths:
            for index, row in enumerate(read_csv_rows(path), start=2):
                if (row.get("Status") or "").strip() != "Success" or (row.get("Direction") or "").strip() != "In":
                    continue
                raw_row_ref = f"row:{index}"
                event_id = event_id_for(self.name, path.name, raw_row_ref)
                token = (row.get("Token") or "").strip()
                event_kind = "Airdrop" if "airdrop" in ((row.get("Contract") or "") + " " + token).lower() else "Deposit"
                events.append(
                    canonical_event(
                        event_id=event_id,
                        source=profile.source,
                        adapter=self.name,
                        account=profile.source,
                        wallet=profile.source,
                        raw_file=path.name,
                        raw_row_ref=raw_row_ref,
                        timestamp=normalized_timestamp(
                            row["Time"],
                            NEAR_TIME_FORMATS,
                            source_timezone=timezone.utc,
                        ),
                        event_kind=event_kind,
                        description=token,
                        amount_in=decimal_text(decimal_or_zero(row.get("Quantity"))),
                        asset_in=token,
                        tx_hash=(row.get("Txn Hash") or "").strip(),
                        render_notes=(row.get("Contract") or "").strip(),
                    )
                )

        for path in nft_paths:
            for index, row in enumerate(read_csv_rows(path), start=2):
                if (row.get("Status") or "").strip() != "Success" or (row.get("Direction") or "").strip() != "In":
                    continue
                raw_row_ref = f"row:{index}"
                event_id = event_id_for(self.name, path.name, raw_row_ref)
                token_name = (row.get("Token") or "").strip()
                contract = (row.get("Contract") or "").strip()
                events.append(
                    canonical_event(
                        event_id=event_id,
                        source=profile.source,
                        adapter=self.name,
                        account=profile.source,
                        wallet=profile.source,
                        raw_file=path.name,
                        raw_row_ref=raw_row_ref,
                        timestamp=normalized_timestamp(
                            row["Time"],
                            NEAR_TIME_FORMATS,
                            source_timezone=timezone.utc,
                        ),
                        event_kind="Airdrop",
                        description=token_name or contract or "NEAR NFT mint",
                        amount_in="1.00000000",
                        asset_in=token_name or contract or "NEAR NFT",
                        tx_hash=(row.get("Txn Hash") or "").strip(),
                        render_notes=f"token_id={(row.get('Token ID') or '').strip()}",
                    )
                )

        return AdapterNormalizationResult(canonical_events=events, canonical_balances=[], exceptions=exceptions)

    def _owned_accounts(self, profile: SourceProfile, raw_dir: Path) -> set[str]:
        return {identifier_value for identifier_value, _ in self._owned_account_paths(profile, raw_dir)}

    def _owned_account_paths(self, profile: SourceProfile, raw_dir: Path) -> list[tuple[str, Path]]:
        account_paths: dict[str, Path] = {}
        for row in profile.file_inventory:
            filename = row.get("filename", "")
            for match in re.finditer(r"[a-f0-9]{64}", filename.lower()):
                account_paths.setdefault(match.group(0), raw_dir / filename)
        if account_paths:
            return sorted(account_paths.items())
        for path in profile_paths(raw_dir, profile, families={"near_transaction_csv", "near_receipt_csv"}, suffixes={".csv"}):
            for row in read_csv_rows(path):
                for field in ("To", "Affected", "Involved"):
                    value = (row.get(field) or "").strip().lower()
                    if re.fullmatch(r"[a-f0-9]{64}", value):
                        account_paths.setdefault(value, path)
        return sorted(account_paths.items())

    def _near_deposit_event(self, path: Path, source: str, index: int, row: dict[str, str]) -> dict[str, str]:
        raw_row_ref = f"row:{index}"
        event_id = event_id_for(self.name, path.name, raw_row_ref)
        deposit_value = decimal_or_zero(row.get("Deposit Value"))
        tx_fee = decimal_or_zero(row.get("Txn Fee"))
        return canonical_event(
            event_id=event_id,
            source=source,
            adapter=self.name,
            account=source,
            wallet=source,
            raw_file=path.name,
            raw_row_ref=raw_row_ref,
            timestamp=normalized_timestamp(
                row["Time"],
                NEAR_TIME_FORMATS,
                source_timezone=timezone.utc,
            ),
            event_kind="Deposit",
            description=raw_hash_description(f"Transfer into {source}", row.get("Txn Hash") or "", f"Transfer into {source}"),
            amount_in=decimal_text(deposit_value - tx_fee),
            asset_in="NEAR",
            tx_hash=(row.get("Txn Hash") or "").strip(),
            render_notes="near_transfer_in",
        )

    def _near_stake_events(self, path: Path, source: str, index: int, row: dict[str, str]) -> list[dict[str, str]]:
        raw_row_ref = f"row:{index}"
        timestamp = normalized_timestamp(
            row["Time"],
            NEAR_TIME_FORMATS,
            source_timezone=timezone.utc,
        )
        tx_hash = (row.get("Txn Hash") or "").strip()
        deposit_value = decimal_or_zero(row.get("Deposit Value"))
        tx_fee = decimal_or_zero(row.get("Txn Fee"))
        description = f"Stake NEAR - {tx_hash}" if tx_hash else "Stake NEAR"
        return [
            canonical_event(
                event_id=event_id_for(self.name, path.name, f"{raw_row_ref}:wallet"),
                source=source,
                adapter=self.name,
                account=source,
                wallet=source,
                raw_file=path.name,
                raw_row_ref=raw_row_ref,
                timestamp=timestamp,
                event_kind="Withdrawal",
                description=description,
                amount_out=decimal_text(deposit_value + tx_fee),
                asset_out="NEAR",
                fee_amount=decimal_text(tx_fee),
                fee_asset="NEAR",
                tx_hash=tx_hash,
                render_notes="near_stake_out",
            ),
            canonical_event(
                event_id=event_id_for(self.name, path.name, f"{raw_row_ref}:staking"),
                source=source_staked_label(source),
                adapter=self.name,
                account=source_staked_label(source),
                wallet=source_staked_label(source),
                raw_file=path.name,
                raw_row_ref=raw_row_ref,
                timestamp=timestamp,
                event_kind="Deposit",
                description=description,
                amount_in=decimal_text(deposit_value),
                asset_in="NEAR",
                tx_hash=tx_hash,
                render_notes="near_stake_in",
            ),
        ]


class GTradeAdapter(SourceAdapter):
    name = "gtrade"
    aliases = ("gtrade", "gtrade 1ct")
    supported = True

    def matches_profile(self, profile: SourceProfile) -> bool:
        return profile_has_row(profile, families={"derivatives_report_csv"})

    def timezone_policy_for_row(self, row: dict[str, str]) -> TimezonePolicy | None:
        if not row.get("date_field"):
            return None
        return GTRADE_DATE_ONLY_POLICY

    def extract_wallet_identifiers(
        self,
        source: str,
        raw_dir: Path,
        profile: SourceProfile,
    ) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        evidence: list[dict[str, str]] = []
        aliases: set[str] = set()
        for path in profile_paths(raw_dir, profile, families={"derivatives_report_csv"}, suffixes={".csv"}):
            for row in read_csv_rows(path):
                alias = (row.get("ADDR") or "").strip()
                if not alias:
                    continue
                aliases.add(alias)
                evidence.append(
                    wallet_evidence_row(
                        source=source,
                        raw_dir=raw_dir,
                        identifier_value=alias,
                        network_scope="polygon",
                        controller="GTrade report",
                        account_label="",
                        evidence_kind="csv_row",
                        evidence_path=path,
                        confidence="medium",
                        note="The report exposes a truncated trader alias instead of a full on-chain address.",
                        identifier_kind="address_alias",
                    )
                )

        issues: list[dict[str, str]] = []
        if aliases:
            issues.append(
                wallet_issue_row(
                    source=source,
                    raw_dir=raw_dir,
                    wallet_id="address_alias:" + min(alias.lower() for alias in aliases),
                    issue_kind="partial_identifier_only",
                    message="GTrade evidence exposes only a truncated address alias; keep companion explorer evidence linked in the canonical wallet inventory.",
                    evidence_path=next(iter(profile_paths(raw_dir, profile, families={"derivatives_report_csv"}, suffixes={".csv"})), None),
                )
            )
        else:
            issues.append(
                wallet_issue_row(
                    source=source,
                    raw_dir=raw_dir,
                    wallet_id="",
                    issue_kind="missing_identifier",
                    message="No address alias was found in the GTrade report.",
                )
            )

        return dedupe_rows(evidence, key_fields=WALLET_EVIDENCE_HEADERS), issues

    def normalize(
        self,
        raw_dir: Path,
        profile: SourceProfile,
        *,
        exception_decisions: dict[str, dict[str, str]],
    ) -> AdapterNormalizationResult:
        report_paths = profile_paths(raw_dir, profile, families={"derivatives_report_csv"}, suffixes={".csv"})
        exceptions: list[dict[str, str]] = []
        if not report_paths:
            maybe_append_exception(
                exceptions,
                exception_decisions,
                manifest_fingerprint=profile.manifest_fingerprint,
                source=profile.source,
                adapter=self.name,
                event_id="gtrade:missing_report_csv",
                raw_file="",
                raw_row_ref="",
                exception_kind="missing_required_input",
                message="GTrade trading-history CSV is required for normalization.",
            )
            return AdapterNormalizationResult(canonical_events=[], canonical_balances=[], exceptions=exceptions)

        events: list[dict[str, str]] = []
        for path in report_paths:
            for index, row in enumerate(read_csv_rows(path), start=2):
                raw_row_ref = f"row:{index}"
                event_id = event_id_for(self.name, path.name, raw_row_ref)
                timestamp = normalized_timestamp(f"{row['DATE']} 00:00:00", ("%d/%m/%Y %H:%M:%S",))
                pnl = decimal_or_zero(row.get("PNL"))
                description = (row.get("DESCRIPTION") or "").strip()
                if pnl != 0:
                    event_kind = "Derivatives / Futures Profit" if pnl > 0 else "Derivatives / Futures Loss"
                    payload = {
                        "event_id": event_id,
                        "source": profile.source,
                        "adapter": self.name,
                        "account": profile.source,
                        "wallet": profile.source,
                        "raw_file": path.name,
                        "raw_row_ref": raw_row_ref,
                        "timestamp": timestamp,
                        "event_kind": event_kind,
                        "description": description,
                        "tx_hash": event_id,
                        "render_match_window_seconds": "86399",
                        "render_notes": f"{row.get('PAIR', '')}:{row.get('TYPE', '')}:{row.get('DIR', '')}",
                    }
                    if pnl > 0:
                        payload.update({"amount_in": decimal_text(abs(pnl)), "asset_in": "DAI"})
                    else:
                        payload.update({"amount_out": decimal_text(abs(pnl)), "asset_out": "DAI"})
                    events.append(canonical_event(**payload))
                    continue

                maybe_append_exception(
                    exceptions,
                    exception_decisions,
                    manifest_fingerprint=profile.manifest_fingerprint,
                    source=profile.source,
                    adapter=self.name,
                    event_id=event_id,
                    raw_file=path.name,
                    raw_row_ref=raw_row_ref,
                    exception_kind="unsupported_row",
                    message="GTrade report row lacks realized PnL and cannot be deterministically converted into a CoinTracking transaction without supporting explorer evidence.",
                )

        return AdapterNormalizationResult(canonical_events=events, canonical_balances=[], exceptions=exceptions)


ADAPTERS: tuple[SourceAdapter, ...] = (
    MetamaskAppAdapter(),
    CoinbaseAdapter(),
    WealthsimpleAdapter(),
    BinanceAdapter(),
    CryptoComAdapter(),
    EvmExplorerAdapter(),
    ShakepayAdapter(),
    LedgerLiveAdapter(),
    NearAdapter(),
    GTradeAdapter(),
)


def get_adapter(source: str, profile: SourceProfile | None = None) -> SourceAdapter:
    if profile is not None:
        profile_matches = [adapter for adapter in ADAPTERS if adapter.matches_profile(profile)]
        if len(profile_matches) == 1:
            return profile_matches[0]
        for adapter in profile_matches:
            if adapter.matches_source(source):
                return adapter
        if profile_matches:
            return profile_matches[0]
    for adapter in ADAPTERS:
        if adapter.matches_source(source):
            return adapter
    fallback = SourceAdapter()
    fallback.name = "generic"
    fallback.aliases = ()
    return fallback


def available_adapter_rows() -> list[dict[str, str]]:
    return [
        {
            "adapter": adapter.name,
            "supported": "yes" if adapter.supported else "no",
            "aliases": ", ".join(adapter.aliases),
        }
        for adapter in ADAPTERS
    ]
