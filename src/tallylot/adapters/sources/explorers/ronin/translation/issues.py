"""Ronin explorer translation issue helpers."""

from __future__ import annotations

from tallylot.adapters.support import IssueSpec, issue_record
from tallylot.adapters.support.drafts import EconomicActivityDraft, LegKind
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.ports.source_profiles import SourceProfile

from .rows import RoninFeeResolution


def supported_fee_reviews(
    fee_resolution: RoninFeeResolution,
    *,
    draft_count: int,
) -> tuple[NormalizationReviewRecord, ...]:
    if draft_count == 0 or fee_resolution.review is None:
        return ()
    return (fee_resolution.review,)


def row_issue(
    profile: SourceProfile,
    raw_file: str,
    raw_row_ref: str,
    issue_id_suffix: str,
    message: str,
) -> IssueRecord:
    return issue_record(
        IssueSpec(
            issue_id=f"ronin:{raw_file}:{raw_row_ref}:{issue_id_suffix}",
            source=str(profile.source),
            adapter_id="ronin",
            kind="unsupported_row",
            message=message,
            raw_file=raw_file,
            raw_row_ref=raw_row_ref,
        )
    )


def symbol_identity_issues(
    profile: SourceProfile,
    drafts: tuple[EconomicActivityDraft, ...] | list[EconomicActivityDraft],
) -> tuple[IssueRecord, ...]:
    issues: list[IssueRecord] = []
    for draft in drafts:
        for leg in draft.legs:
            if leg.kind is not LegKind.PRIMARY:
                continue
            claims = leg.instrument_identity_claims
            if (
                len(claims) == 1
                and claims[0].scheme == "symbol"
                and claims[0].venue == "ronin"
                and claims[0].value != "RON"
            ):
                issues.append(
                    issue_record(
                        IssueSpec(
                            issue_id=(
                                f"ronin:{draft.raw_file}:{draft.raw_row_ref}:"
                                "instrument_identity_blocked"
                            ),
                            source=str(profile.source),
                            adapter_id="ronin",
                            severity="medium",
                            kind="instrument_identity_blocked",
                            message=(
                                "Ronin token rows without immutable contract identity "
                                "keep a symbol-only instrument id and cannot "
                                "participate in historical API-backed balance lookup."
                            ),
                            raw_file=draft.raw_file,
                            raw_row_ref=draft.raw_row_ref,
                        )
                    )
                )
                break
    return tuple(issues)
