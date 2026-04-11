"""Cross-source balance corroboration sidecar outputs."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from tallylot.domain.balances import BalanceSnapshot
from tallylot.domain.issues import IssueRecord
from tallylot.domain.types import JsonValue
from tallylot.domain.value_objects import format_decimal, format_temporal_value
from tallylot.ports.artifacts import ArtifactStorePort
from tallylot.ports.evidence import EvidenceRepositoryPort

from .records import CrossSourceAssertionRecord
from .sources import BalanceSourceDir


@dataclass(frozen=True)
class CrossSourceCorroborationResult:
    assertions: tuple[CrossSourceAssertionRecord, ...]
    issues: tuple[IssueRecord, ...]

    def summary_payload(self) -> dict[str, JsonValue]:
        status_counts = Counter(assertion.status for assertion in self.assertions)
        ambiguous_count = sum(
            1
            for issue in self.issues
            if issue.kind == "cross_source_ambiguous_identity"
        )
        skipped_count = sum(
            1
            for issue in self.issues
            if issue.kind
            in {
                "cross_source_low_confidence_identity",
                "cross_source_ambiguous_identity",
            }
        )
        return {
            "assertion_count": len(self.assertions),
            "issue_count": len(self.issues),
            "matched_count": status_counts.get("matched", 0),
            "drift_count": status_counts.get("drift", 0),
            "missing_left_count": status_counts.get("missing_left", 0),
            "missing_right_count": status_counts.get("missing_right", 0),
            "ambiguous_count": ambiguous_count,
            "skipped_count": skipped_count,
        }


@dataclass(frozen=True)
class _IdentityRecord:
    source: str
    location_id: str
    normalized_identifier: str
    network_scope: str
    confidence: str


@dataclass(frozen=True)
class _JoinKey:
    instrument_id: str
    balance_kind: str
    target_at: object
    target_precision: object


@dataclass(frozen=True)
class _CrossSourceIssueContext:
    source: str
    normalized_identifier: str
    network_scope: str


@dataclass(frozen=True)
class _ComparablePair:
    normalized_identifier: str
    network_scope: str
    join_key: _JoinKey
    left_source: str
    left_identity: _IdentityRecord
    left_snapshot: BalanceSnapshot | None
    right_source: str
    right_identity: _IdentityRecord
    right_snapshot: BalanceSnapshot | None


def build_cross_source_corroboration(
    source_dirs: tuple[BalanceSourceDir, ...],
    *,
    evidence: EvidenceRepositoryPort,
    artifacts: ArtifactStorePort,
) -> CrossSourceCorroborationResult:
    snapshots_by_source = {
        source_dir.name: _read_snapshots(evidence, source_dir)
        for source_dir in source_dirs
    }
    inventory_by_source = {
        source_dir.name: _read_location_inventory(artifacts, source_dir)
        for source_dir in source_dirs
    }
    identities_by_group: dict[tuple[str, str], list[_IdentityRecord]] = defaultdict(
        list
    )
    for source, inventory_rows in inventory_by_source.items():
        del source
        for row in inventory_rows:
            if not row.normalized_identifier or not row.network_scope:
                continue
            identities_by_group[(row.normalized_identifier, row.network_scope)].append(
                row
            )

    assertions: list[CrossSourceAssertionRecord] = []
    issues: list[IssueRecord] = []
    for (normalized_identifier, network_scope), identity_rows in sorted(
        identities_by_group.items()
    ):
        eligible_identities: dict[str, _IdentityRecord] = {}
        for source, source_rows in _group_by_source(identity_rows).items():
            issue_context = _CrossSourceIssueContext(
                source=source,
                normalized_identifier=normalized_identifier,
                network_scope=network_scope,
            )
            high_confidence_rows = [
                row for row in source_rows if row.confidence.lower() == "high"
            ]
            if not high_confidence_rows:
                issues.append(
                    _cross_source_issue(
                        issue_context,
                        kind="cross_source_low_confidence_identity",
                        message=(
                            "Cross-source corroboration skipped because the location identity "
                            "confidence was not high."
                        ),
                    )
                )
                continue
            if len(high_confidence_rows) > 1:
                issues.append(
                    _cross_source_issue(
                        issue_context,
                        kind="cross_source_ambiguous_identity",
                        message=(
                            "Cross-source corroboration skipped because more than one high-confidence "
                            "location matched the same shared identity in one source."
                        ),
                    )
                )
                continue
            eligible_identities[source] = high_confidence_rows[0]
        if len(eligible_identities) < 2:
            continue
        join_rows_by_source: dict[str, dict[_JoinKey, BalanceSnapshot]] = {}
        for source, identity in eligible_identities.items():
            balances_for_identity = tuple(
                snapshot
                for snapshot in snapshots_by_source.get(source, ())
                if str(snapshot.location_id) == identity.location_id
            )
            join_rows, duplicate_issues = _index_join_rows(
                source=source,
                normalized_identifier=normalized_identifier,
                network_scope=network_scope,
                snapshots=balances_for_identity,
            )
            join_rows_by_source[source] = join_rows
            issues.extend(duplicate_issues)
        comparable_sources = tuple(sorted(join_rows_by_source))
        for left_index, left_source in enumerate(comparable_sources):
            for right_source in comparable_sources[left_index + 1 :]:
                left_identity = eligible_identities[left_source]
                right_identity = eligible_identities[right_source]
                left_rows = join_rows_by_source[left_source]
                right_rows = join_rows_by_source[right_source]
                for join_key in sorted(
                    set(left_rows) | set(right_rows),
                    key=lambda item: (
                        item.instrument_id,
                        item.balance_kind,
                        str(item.target_at),
                        str(item.target_precision),
                    ),
                ):
                    assertions.append(
                        _build_assertion(
                            _ComparablePair(
                                normalized_identifier=normalized_identifier,
                                network_scope=network_scope,
                                join_key=join_key,
                                left_source=left_source,
                                left_identity=left_identity,
                                left_snapshot=left_rows.get(join_key),
                                right_source=right_source,
                                right_identity=right_identity,
                                right_snapshot=right_rows.get(join_key),
                            )
                        )
                    )
    return CrossSourceCorroborationResult(
        assertions=tuple(assertions),
        issues=tuple(issues),
    )


def _read_snapshots(
    evidence: EvidenceRepositoryPort,
    source_dir: BalanceSourceDir,
) -> tuple[BalanceSnapshot, ...]:
    if not source_dir.snapshot_path.is_file():
        return ()
    return evidence.read_balance_snapshots(source_dir.snapshot_path)


def _read_location_inventory(
    artifacts: ArtifactStorePort,
    source_dir: BalanceSourceDir,
) -> tuple[_IdentityRecord, ...]:
    if not source_dir.location_inventory_path.is_file():
        return ()
    rows = artifacts.read_rows(source_dir.location_inventory_path)
    return tuple(
        _IdentityRecord(
            source=row["source"],
            location_id=row["location_id"],
            normalized_identifier=row["normalized_identifier"],
            network_scope=row["network_scope"],
            confidence=row["confidence"],
        )
        for row in rows
    )


def _group_by_source(
    identity_rows: list[_IdentityRecord],
) -> dict[str, tuple[_IdentityRecord, ...]]:
    grouped: dict[str, list[_IdentityRecord]] = defaultdict(list)
    for row in identity_rows:
        grouped[row.source].append(row)
    return {source: tuple(rows) for source, rows in grouped.items()}


def _index_join_rows(
    *,
    source: str,
    normalized_identifier: str,
    network_scope: str,
    snapshots: tuple[BalanceSnapshot, ...],
) -> tuple[dict[_JoinKey, BalanceSnapshot], tuple[IssueRecord, ...]]:
    indexed: dict[_JoinKey, BalanceSnapshot] = {}
    issues: list[IssueRecord] = []
    duplicate_counts: dict[_JoinKey, int] = defaultdict(int)
    issue_context = _CrossSourceIssueContext(
        source=source,
        normalized_identifier=normalized_identifier,
        network_scope=network_scope,
    )
    for snapshot in snapshots:
        join_key = _JoinKey(
            instrument_id=_normalize_instrument_id(str(snapshot.instrument_id)),
            balance_kind=snapshot.balance_kind,
            target_at=snapshot.target_at,
            target_precision=snapshot.target_precision,
        )
        if join_key in indexed:
            duplicate_counts[join_key] += 1
            issues.append(
                _cross_source_issue(
                    issue_context,
                    kind="cross_source_ambiguous_identity",
                    message=(
                        "Cross-source corroboration skipped because more than one balance row "
                        "matched the same shared join key in one source."
                    ),
                    suffix=str(duplicate_counts[join_key]),
                )
            )
            continue
        indexed[join_key] = snapshot
    return indexed, tuple(issues)


def _build_assertion(pair: _ComparablePair) -> CrossSourceAssertionRecord:
    left_quantity = (
        ""
        if pair.left_snapshot is None
        else format_decimal(pair.left_snapshot.quantity)
    )
    right_quantity = (
        ""
        if pair.right_snapshot is None
        else format_decimal(pair.right_snapshot.quantity)
    )
    quantity_difference = ""
    if pair.left_snapshot is not None and pair.right_snapshot is not None:
        quantity_difference = format_decimal(
            pair.left_snapshot.quantity - pair.right_snapshot.quantity
        )
    status = _assertion_status(pair.left_snapshot, pair.right_snapshot)
    snapshot = pair.left_snapshot or pair.right_snapshot
    return CrossSourceAssertionRecord(
        left_source=pair.left_source,
        right_source=pair.right_source,
        normalized_identifier=pair.normalized_identifier,
        network_scope=pair.network_scope,
        instrument_id=pair.join_key.instrument_id,
        balance_kind=pair.join_key.balance_kind,
        left_location_id=(
            pair.left_identity.location_id if pair.left_snapshot is not None else ""
        ),
        right_location_id=(
            pair.right_identity.location_id if pair.right_snapshot is not None else ""
        ),
        left_quantity=left_quantity,
        right_quantity=right_quantity,
        quantity_difference=quantity_difference,
        status=status,
        as_of_at=""
        if snapshot is None
        else format_temporal_value(
            snapshot.target_at,
            precision=snapshot.target_precision,
            label="cross-source balance assertion target_at",
        ),
        as_of_precision="" if snapshot is None else snapshot.target_precision.value,
        notes=_status_notes(status),
    )


def _assertion_status(
    left_snapshot: BalanceSnapshot | None,
    right_snapshot: BalanceSnapshot | None,
) -> str:
    if left_snapshot is None:
        return "missing_left"
    if right_snapshot is None:
        return "missing_right"
    if left_snapshot.quantity != right_snapshot.quantity:
        return "drift"
    return "matched"


def _status_notes(status: str) -> str:
    if status == "missing_left":
        return "No comparable left-side balance row was available for this shared identity."
    if status == "missing_right":
        return "No comparable right-side balance row was available for this shared identity."
    if status == "drift":
        return "Comparable sources resolved to the same shared identity but reported different quantities."
    return "Comparable sources resolved to the same shared identity and quantity."


def _cross_source_issue(
    context: _CrossSourceIssueContext,
    *,
    kind: str,
    message: str,
    suffix: str = "",
) -> IssueRecord:
    suffix_text = f":{suffix}" if suffix else ""
    return IssueRecord(
        issue_id=(
            f"{context.source}:{context.network_scope}:{context.normalized_identifier}:"
            f"{kind}{suffix_text}"
        ),
        source=context.source,
        adapter_id="reconciliation",
        severity="medium",
        kind=kind,
        message=message,
    )


def _normalize_instrument_id(value: str) -> str:
    if value.startswith("symbol:") and "@" in value:
        return value.split("@", maxsplit=1)[0]
    return value
