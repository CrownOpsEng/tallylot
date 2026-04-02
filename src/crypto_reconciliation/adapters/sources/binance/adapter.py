"""Binance export adapter entry point."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import cast

from crypto_reconciliation.adapters.sources.intake_support import match_intake_by_path_or_header, no_intake_route
from crypto_reconciliation.domain.models import (
    AdapterCapability,
    AdapterManifest,
    CanonicalEvent,
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
        issues = tuple(
            IssueRecord(
                issue_id=f"binance:{item.relative_path}:timezone",
                source=str(profile.source),
                adapter_id=str(self.manifest.adapter_id),
                severity="high",
                kind="timezone_review_required",
                message="Binance exports with dated rows must include a filename offset before normalization.",
                raw_file=item.relative_path,
            )
            for item in profile.file_inventory
            if item.date_field and item.timezone_mode == "naive"
        )
        rows_with_dates = sum(1 for item in profile.file_inventory if item.date_field)
        mode_counts: dict[str, int] = {}
        for item in profile.file_inventory:
            if not item.date_field:
                continue
            mode_key = item.timezone_mode or "unknown"
            mode_counts[mode_key] = mode_counts.get(mode_key, 0) + 1
        mode_counts_json = cast(dict[str, JsonValue], dict(mode_counts))
        return {
            "status": "needs_review" if issues else "passed",
            "issue_count": len(issues),
            "rows_with_dates": rows_with_dates,
            "mode_counts": mode_counts_json,
        }, issues

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
        events: list[CanonicalEvent] = []
        issues: list[IssueRecord] = []
        convert_match_times: set[datetime] = set()
        p2p_match_times: set[datetime] = set()
        for path in sorted(raw_dir.rglob("*.csv")):
            if path.name.startswith("Binance-Spot-Trade-History-"):
                events.extend(_normalize_spot_rows(profile, path))
            elif path.name.startswith("Binance-Deposit-History-"):
                events.extend(_normalize_deposit_rows(profile, path))
            elif path.name.startswith("Binance-Withdraw-History-"):
                events.extend(_normalize_withdraw_rows(profile, path))
            elif path.name.startswith("Binance-Convert-Order-History-"):
                convert_events, matched_times = _normalize_convert_order_rows(profile, path)
                events.extend(convert_events)
                convert_match_times.update(matched_times)
            elif path.name.startswith("Binance-C2C-Order-History-"):
                c2c_events, matched_times = _normalize_c2c_order_rows(profile, path)
                events.extend(c2c_events)
                p2p_match_times.update(matched_times)
            elif path.name.startswith("Binance-Transaction-History-"):
                parsed_events, parsed_issues = _normalize_transaction_rows(
                    profile,
                    path,
                    convert_match_times=frozenset(convert_match_times),
                    p2p_match_times=frozenset(p2p_match_times),
                )
                events.extend(parsed_events)
                issues.extend(parsed_issues)
        return NormalizationResult(
            canonical_events=tuple(events),
            canonical_balances=(),
            issues=tuple(issues),
            reviews=(),
            wallet_inventory=(),
        )


ADAPTER = BinanceAdapter()
