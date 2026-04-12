"""Balance reference matching and hydration."""

from __future__ import annotations

from collections import defaultdict

from tallylot.domain.balances import (
    BalanceProviderRequest,
    BalanceReference,
    BalanceTarget,
)
from tallylot.domain.balances.matching import balance_target_match_key
from tallylot.domain.issues import IssueRecord
from tallylot.domain.value_objects import format_temporal_value
from tallylot.ports.balance_providers import (
    BalanceProviderPort,
    BalanceProviderRegistryPort,
)
from tallylot.ports.evidence import EvidenceRepositoryPort


class BalanceReferenceResolver:
    def __init__(
        self,
        *,
        evidence: EvidenceRepositoryPort,
        providers: BalanceProviderRegistryPort | None = None,
    ) -> None:
        self._evidence = evidence
        self._providers = providers

    def resolve(
        self,
        *,
        existing_references: tuple[BalanceReference, ...],
        targets: tuple[BalanceTarget, ...],
        hydrate_missing: bool,
    ) -> tuple[tuple[BalanceReference, ...], tuple[IssueRecord, ...]]:
        references_by_target: dict[object, list[BalanceReference]] = defaultdict(list)
        for reference in existing_references:
            references_by_target[balance_target_match_key(reference.target)].append(
                reference
            )
        matched: list[BalanceReference] = []
        unresolved: list[BalanceTarget] = []
        for target in targets:
            matching = tuple(
                references_by_target.get(balance_target_match_key(target), ())
            )
            if matching:
                matched.extend(matching)
            else:
                unresolved.append(target)
        if not hydrate_missing or not unresolved or self._providers is None:
            return tuple(matched), tuple(
                _missing_reference_issue(
                    target,
                    existing_references=existing_references,
                )
                for target in unresolved
            )
        hydrated, hydration_issues = self._hydrate(tuple(unresolved))
        return tuple((*matched, *hydrated)), hydration_issues

    def _hydrate(
        self,
        targets: tuple[BalanceTarget, ...],
    ) -> tuple[tuple[BalanceReference, ...], tuple[IssueRecord, ...]]:
        if self._providers is None:
            return (), tuple(_missing_reference_issue(target) for target in targets)
        provider_groups: dict[BalanceProviderPort, list[BalanceProviderRequest]] = (
            defaultdict(list)
        )
        unsupported_targets: list[BalanceTarget] = []
        for target in targets:
            request = BalanceProviderRequest(target=target)
            provider = self._providers.provider_for_requests((request,))
            if provider is None:
                unsupported_targets.append(target)
                continue
            provider_groups[provider].append(request)
        references: list[BalanceReference] = []
        issues: list[IssueRecord] = [
            *(
                _missing_reference_issue(target, kind="unsupported_balance_provider")
                for target in unsupported_targets
            )
        ]
        for provider, requests in provider_groups.items():
            for result in provider.fetch_references(tuple(requests)):
                if result.reference is not None:
                    references.append(result.reference)
                    continue
                issues.append(
                    IssueRecord(
                        issue_id=":".join(
                            (
                                str(result.target.source),
                                str(result.target.location_id),
                                str(result.target.instrument_id),
                                result.target.balance_kind,
                                result.issue_kind or "balance_reference_unresolved",
                            )
                        ),
                        source=str(result.target.source),
                        adapter_id="balances",
                        severity="high",
                        kind=result.issue_kind or "balance_reference_unresolved",
                        message=result.issue_message
                        or "Balance reference could not be resolved.",
                        context_timestamp=format_temporal_value(
                            result.target.target_at,
                            precision=result.target.target_precision,
                            label="balance provider unresolved target_at",
                        ),
                        raw_file="",
                    )
                )
        return tuple(references), tuple(issues)


def _missing_reference_issue(
    target: BalanceTarget,
    *,
    existing_references: tuple[BalanceReference, ...] = (),
    kind: str = "missing_balance_reference",
) -> IssueRecord:
    nearest_reference = _nearest_reference(target, existing_references)
    message = "No balance reference satisfied the requested target."
    if nearest_reference is not None:
        target_at = format_temporal_value(
            nearest_reference.target.target_at,
            precision=nearest_reference.target.target_precision,
            label="nearest balance reference target_at",
        )
        message = (
            "No balance reference satisfied the requested target. "
            f"Closest available {nearest_reference.reference_kind.value.replace('_', ' ')} "
            "reference target_at is "
            f"{target_at}."
        )
    return IssueRecord(
        issue_id=":".join(
            (
                str(target.source),
                str(target.location_id),
                str(target.instrument_id),
                target.balance_kind,
                kind,
            )
        ),
        source=str(target.source),
        adapter_id="balances",
        severity="high",
        kind=kind,
        message=message,
        context_timestamp=format_temporal_value(
            target.target_at,
            precision=target.target_precision,
            label="missing balance reference target_at",
        ),
        raw_file="",
    )


def _nearest_reference(
    target: BalanceTarget,
    references: tuple[BalanceReference, ...],
) -> BalanceReference | None:
    matching = tuple(
        reference
        for reference in references
        if (
            reference.target.source == target.source
            and reference.target.location_id == target.location_id
            and str(reference.target.instrument_id) == str(target.instrument_id)
            and reference.target.balance_kind == target.balance_kind
        )
    )
    if not matching:
        return None
    return min(
        matching,
        key=lambda reference: abs(
            (reference.target.target_at - target.target_at).total_seconds()
        ),
    )
