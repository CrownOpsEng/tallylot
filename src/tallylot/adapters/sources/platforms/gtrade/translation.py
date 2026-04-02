"""GTrade transaction translation rules."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from tallylot.adapters.support import (
    IssueSpec,
    issue_record,
    matching_file_paths,
    read_csv_header,
    read_csv_rows,
)
from tallylot.adapters.support.drafts import (
    SINGLE_PRIMARY_ACTIVITY_POLICY,
    ActivityClassification,
    EconomicActivityDraft,
    LegKind,
    classification,
    economic_leg,
)
from tallylot.domain.issues import IssueRecord
from tallylot.domain.transactions import EconomicKind, JournalIntent, ProjectionType, TaxTreatmentCode
from tallylot.ports.source_profiles import SourceProfile


def translate_transactions(
    profile: SourceProfile,
    raw_dir: Path,
) -> tuple[tuple[EconomicActivityDraft, ...], tuple[IssueRecord, ...]]:
    drafts: list[EconomicActivityDraft] = []
    issues: list[IssueRecord] = []
    for path in matching_file_paths(raw_dir):
        if _skip_unrecognized_csv(path):
            continue
        for index, row in enumerate(read_csv_rows(path), start=2):
            pnl = _parse_decimal((row.get("PNL") or "").strip())
            if pnl is None:
                issues.append(
                    issue_record(
                        IssueSpec(
                            source=str(profile.source),
                            adapter_id="gtrade",
                            issue_id=f"gtrade:{path.name}:row:{index}:invalid_pnl",
                            severity="medium",
                            kind="unsupported_row",
                            message="GTrade row is missing a supported realized PnL value.",
                            raw_file=path.name,
                            raw_row_ref=f"row:{index}",
                            status="needs_review",
                        )
                    )
                )
                continue
            if pnl == Decimal("0"):
                issues.append(
                    issue_record(
                        IssueSpec(
                            source=str(profile.source),
                            adapter_id="gtrade",
                            issue_id=f"gtrade:{path.name}:row:{index}",
                            severity="medium",
                            kind="unsupported_row",
                            message=(
                                "GTrade report row lacks realized PnL and cannot be deterministically converted "
                                "into a normalized transaction without supporting explorer evidence."
                            ),
                            raw_file=path.name,
                            raw_row_ref=f"row:{index}",
                            status="needs_review",
                        )
                    )
                )
                continue
            description = (row.get("DESCRIPTION") or "").strip()
            timestamp = _parse_report_date((row.get("DATE") or "").strip())
            if timestamp is None:
                issues.append(
                    issue_record(
                        IssueSpec(
                            source=str(profile.source),
                            adapter_id="gtrade",
                            issue_id=f"gtrade:{path.name}:row:{index}:invalid_date",
                            severity="medium",
                            kind="unsupported_row",
                            message="GTrade row is missing a supported report date.",
                            raw_file=path.name,
                            raw_row_ref=f"row:{index}",
                            status="needs_review",
                        )
                    )
                )
                continue
            drafts.append(
                EconomicActivityDraft(
                    activity_id=f"gtrade:{path.name}:row:{index}",
                    source=str(profile.source),
                    adapter_id="gtrade",
                    account=str(profile.source),
                    wallet=str(profile.source),
                    timestamp=timestamp,
                    classification=_classification_for_pnl(pnl),
                    leg_policy=SINGLE_PRIMARY_ACTIVITY_POLICY,
                    description=description,
                    raw_file=path.name,
                    raw_row_ref=f"row:{index}",
                    tx_hash=f"gtrade:{path.name}:row:{index}",
                    provider_operation_key="realized_pnl",
                    legs=(
                        (economic_leg(direction="in", kind=LegKind.PRIMARY, asset="DAI", amount=pnl),)
                        if pnl > 0
                        else (economic_leg(direction="out", kind=LegKind.PRIMARY, asset="DAI", amount=abs(pnl)),)
                    ),
                )
            )
    return tuple(drafts), tuple(issues)


def _classification_for_pnl(pnl: Decimal) -> ActivityClassification:
    if pnl > 0:
        return classification(
            economic_kind=EconomicKind.DERIVATIVE_REALIZED_PROFIT,
            projection_type=ProjectionType.DERIVATIVES_FUTURES_PROFIT,
            journal_intent=JournalIntent.INCOME_RECOGNITION,
            tax_treatment_code=TaxTreatmentCode.DERIVATIVE_REALIZED_GAIN,
        )
    return classification(
        economic_kind=EconomicKind.DERIVATIVE_REALIZED_LOSS,
        projection_type=ProjectionType.DERIVATIVES_FUTURES_LOSS,
        journal_intent=JournalIntent.EXPENSE_RECOGNITION,
        tax_treatment_code=TaxTreatmentCode.DERIVATIVE_REALIZED_LOSS,
    )


def _skip_unrecognized_csv(path: Path) -> bool:
    header = read_csv_header(path)
    return header[:3] != ("DATE", "PAIR", "ADDR")


def _parse_decimal(value: str) -> Decimal | None:
    if not value:
        return None
    try:
        return Decimal(value)
    except ArithmeticError:
        return None


def _parse_report_date(value: str) -> datetime | None:
    if not value:
        return None
    for date_format in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, date_format).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None
