#!/usr/bin/env python3

"""Shared orchestration for intake, profiling, normalization, staging, and wallet inventory."""

from __future__ import annotations

import csv
import json
import shutil
from collections import defaultdict
from dataclasses import replace
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Sequence

from archive_handling import inspect_archive_members, read_archive_member_bytes
from inspection import inspect_file
from overlap_engine import summarize_candidate_overlap, summarize_file_overlap, write_candidate_overlap_artifacts
from package_resolution import resolve_bundle_packages
from pipeline_common import (
    CANONICAL_BALANCE_HEADERS,
    CANONICAL_EVENT_HEADERS,
    EXCEPTION_HEADERS,
    PROFILE_INVENTORY_HEADERS,
    REPO_PROJECT_WINDOW_END,
    build_source_profile,
    filter_rows_by_timestamp_window,
    normalization_window_from_hints,
    parse_canonical_timestamp,
    read_profile,
    repo_project_window_start,
    source_slug,
    write_profile_artifacts,
)
from raw_layout import cointracking_baseline_dir, source_capture_root
from render_cointracking import RENDER_METADATA_HEADERS, render_cointracking_rows
from routing import resolve_routing_decision
from scope_identity import describe_scope_tokens, row_scope_tokens
from script_common import (
    CANONICAL_TIMEZONE,
    COINTRACKING_IMPORT_TIMEZONE,
    read_cointracking_rows,
    require_directory,
    require_file,
    sha256sum,
    write_cointracking_rows,
    write_csv_rows,
    write_json,
)
from source_adapters import decisions_fingerprint, get_adapter, load_exception_decisions
from source_manifest import write_manifest
from wallet_inventory_common import WALLET_EVIDENCE_HEADERS, WALLET_ISSUE_HEADERS, dedupe_rows, wallet_issue_row


WALLET_INVENTORY_HEADERS = (
    "wallet_id",
    "identifier_kind",
    "normalized_identifier",
    "display_identifier",
    "network_scopes",
    "source_labels",
    "controller_labels",
    "account_labels",
    "evidence_count",
    "primary_evidence_path",
    "status",
    "notes",
)

SOURCE_INVENTORY_HEADERS = (
    "source",
    "activity_after_cutoff",
    "first_post_cutoff_tx",
    "export_window_start",
    "export_window_end",
    "import_order",
    "status",
    "capture_path",
    "profile_status",
    "adapter",
    "normalization_status",
    "exception_count",
    "candidate_path",
    "notes",
)


def profile_source_capture(source: str, raw_dir: Path, out_dir: Path, manifest: Path | None = None) -> dict[str, object]:
    profile = build_source_profile(
        source=source,
        raw_dir=raw_dir,
        manifest_path=manifest,
        adapter_name="generic",
        adapter_supported=False,
    )
    adapter = get_adapter(source, profile)
    profile = replace(profile, adapter=adapter.name, adapter_supported=adapter.supported)
    timezone_summary, timezone_issues = adapter.validate_profile_timezones(profile)
    profile = replace(
        profile,
        timezone_summary=timezone_summary,
        timezone_issues=timezone_issues,
    )
    profile_json, inventory_csv = write_profile_artifacts(out_dir, profile)
    return {
        "source": profile.source,
        "adapter": profile.adapter,
        "adapter_supported": profile.adapter_supported,
        "manifest_fingerprint": profile.manifest_fingerprint,
        "timezone_status": timezone_summary["status"],
        "timezone_issue_count": timezone_summary["issue_count"],
        "profile_json": str(profile_json),
        "profile_inventory_csv": str(inventory_csv),
        "files_profiled": len(profile.file_inventory),
    }


def normalization_context_fingerprint(hints: dict[str, object] | None) -> str:
    payload = json.dumps(hints or {}, sort_keys=True, separators=(",", ":"))
    import hashlib

    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def normalize_source_capture(
    source: str,
    raw_dir: Path,
    out_dir: Path,
    *,
    profile_json: Path | None = None,
    manifest: Path | None = None,
    exception_decisions: Path | None = None,
    window_start: str | None = None,
    window_end: str | None = None,
    force: bool = False,
) -> dict[str, object]:
    profile = build_source_profile(
        source=source,
        raw_dir=raw_dir,
        manifest_path=manifest,
        adapter_name="generic",
        adapter_supported=False,
    )
    adapter = get_adapter(source, profile)
    profile = replace(profile, adapter=adapter.name, adapter_supported=adapter.supported)
    if profile_json is not None and profile_json.exists():
        profile_payload = read_profile(profile_json)
        profile_hints = profile_payload.get("normalization_hints")
        if isinstance(profile_hints, dict):
            profile = replace(
                profile,
                normalization_hints={**(profile.normalization_hints or {}), **profile_hints},
            )
    if window_start is not None or window_end is not None:
        profile = replace(
            profile,
            normalization_hints={
                **(profile.normalization_hints or {}),
                **({"normalization_window_start": window_start} if window_start is not None else {}),
                **({"normalization_window_end": window_end} if window_end is not None else {}),
            },
        )
    manifest_fingerprint = profile.manifest_fingerprint
    adapter_name = adapter.name
    effective_window_start, effective_window_end = normalization_window_from_hints(profile.normalization_hints)
    context_fingerprint = normalization_context_fingerprint(profile.normalization_hints)
    timezone_summary, timezone_issues = adapter.validate_profile_timezones(profile)
    profile = replace(profile, timezone_summary=timezone_summary, timezone_issues=timezone_issues)
    if timezone_issues:
        raise ValueError(
            f"Timezone validation failed for {source}: {len(timezone_issues)} issue(s). "
            "Run profile_source.py and review timezone_issues.csv before normalization."
        )
    decisions = load_exception_decisions(exception_decisions, profile.manifest_fingerprint)
    decisions_digest = decisions_fingerprint(decisions)

    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "normalization_summary.json"
    events_path = out_dir / "canonical_events.csv"
    balances_path = out_dir / "canonical_balances.csv"
    exceptions_path = out_dir / "exceptions.csv"
    candidate_path = out_dir / "cointracking_candidate.csv"
    overlap_dir = out_dir / "overlap_check"

    if not force and summary_path.exists():
        existing = read_profile(summary_path)
        if (
            existing.get("manifest_fingerprint") == manifest_fingerprint
            and existing.get("adapter") == adapter_name
            and existing.get("exception_decisions_fingerprint") == decisions_digest
            and existing.get("normalization_context_fingerprint", "") == context_fingerprint
            and existing.get("normalization_window_start", "") == effective_window_start
            and existing.get("normalization_window_end", "") == effective_window_end
            and events_path.exists()
            and balances_path.exists()
            and exceptions_path.exists()
            and candidate_path.exists()
        ):
            return {
                "source": source,
                "adapter": adapter_name,
                "manifest_fingerprint": manifest_fingerprint,
                "canonical_timezone": CANONICAL_TIMEZONE,
                "cointracking_import_timezone": COINTRACKING_IMPORT_TIMEZONE,
                "normalization_context_fingerprint": context_fingerprint,
                "normalization_window_start": effective_window_start,
                "normalization_window_end": effective_window_end,
                "timezone_status": str(existing.get("timezone_status", "not_checked")),
                "timezone_issue_count": int(existing.get("timezone_issue_count", 0)),
                "status": "cached",
                "canonical_events": int(existing.get("canonical_events", 0)),
                "events_outside_normalization_window": int(existing.get("events_outside_normalization_window", 0)),
                "exceptions": int(existing.get("exceptions", 0)),
                "cointracking_rows": int(existing.get("cointracking_rows", 0)),
                "summary_path": str(summary_path),
            }

    result = adapter.normalize(raw_dir.resolve(), profile, exception_decisions=decisions)
    canonical_events, excluded_events = filter_rows_by_timestamp_window(
        result.canonical_events,
        timestamp_key="timestamp",
        window_start=effective_window_start,
        window_end=effective_window_end,
    )

    write_csv_rows(events_path, list(CANONICAL_EVENT_HEADERS), canonical_events)
    write_csv_rows(balances_path, list(CANONICAL_BALANCE_HEADERS), result.canonical_balances)
    write_csv_rows(exceptions_path, list(EXCEPTION_HEADERS), result.exceptions)
    rendered_rows, skipped_rows = render_cointracking_rows(canonical_events)
    write_cointracking_rows(candidate_path, rendered_rows, extra_headers=RENDER_METADATA_HEADERS)

    baseline_dir = cointracking_baseline_dir(Path(__file__).resolve().parents[1])
    overlap_summary: dict[str, object] = {}
    if baseline_dir.exists():
        overlap_summary, overlap_rows = summarize_candidate_overlap(baseline_dir, candidate_path)
        write_candidate_overlap_artifacts(overlap_dir, overlap_summary, overlap_rows)

    summary = {
        "source": source,
        "adapter": adapter.name,
        "adapter_supported": profile.adapter_supported,
        "manifest_fingerprint": profile.manifest_fingerprint,
        "canonical_timezone": CANONICAL_TIMEZONE,
        "cointracking_import_timezone": COINTRACKING_IMPORT_TIMEZONE,
        "normalization_context_fingerprint": context_fingerprint,
        "normalization_window_start": effective_window_start,
        "normalization_window_end": effective_window_end,
        "timezone_status": timezone_summary["status"],
        "timezone_issue_count": timezone_summary["issue_count"],
        "canonical_events": len(canonical_events),
        "canonical_balances": len(result.canonical_balances),
        "events_outside_normalization_window": len(excluded_events),
        "exceptions": len(result.exceptions),
        "exception_decisions_fingerprint": decisions_digest,
        "cointracking_rows": len(rendered_rows),
        "skipped_non_mapped_rows": len(skipped_rows),
        "overlap_status": overlap_summary.get("status", ""),
        "overlap_rows_flagged": overlap_summary.get("rows_flagged", 0),
        "status": (
            "ready"
            if profile.adapter_supported and not result.exceptions
            else "needs_review" if profile.adapter_supported else "adapter_not_implemented"
        ),
        "paths": {
            "canonical_events": str(events_path),
            "canonical_balances": str(balances_path),
            "exceptions": str(exceptions_path),
            "cointracking_candidate": str(candidate_path),
            "overlap_summary": str(overlap_dir / "overlap_summary.json") if overlap_summary else "",
        },
    }
    write_json(summary_path, summary)
    return summary


def count_candidate_rows_outside_window(candidate: Path, *, window_start: str, window_end: str) -> int:
    start_dt = parse_canonical_timestamp(window_start, label="window_start") if window_start else None
    end_dt = parse_canonical_timestamp(window_end, label="window_end") if window_end else None
    rows_outside_window = 0
    for row in read_cointracking_rows(candidate):
        date_text = (row.get("Date") or "").strip()
        date_dt = parse_canonical_timestamp(date_text, label="candidate Date")
        if start_dt is not None and date_dt < start_dt:
            rows_outside_window += 1
            continue
        if end_dt is not None and date_dt > end_dt:
            rows_outside_window += 1
    return rows_outside_window


def read_normalization_summary(path: Path) -> dict[str, object]:
    summary_path = require_file(path.resolve(), "Normalization summary")
    with summary_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Normalization summary must be a JSON object: {summary_path}")
    return payload


def resolve_normalization_window(
    *,
    candidate: Path,
    normalization_summary: Path | None,
    window_start: str | None,
    window_end: str | None,
) -> tuple[str, str, str]:
    effective_window_start = repo_project_window_start() if window_start is None else window_start
    effective_window_end = REPO_PROJECT_WINDOW_END if window_end is None else window_end
    summary_path = normalization_summary
    if summary_path is None:
        sibling_path = candidate.parent / "normalization_summary.json"
        if sibling_path.exists():
            summary_path = sibling_path

    if summary_path is not None:
        payload = read_normalization_summary(summary_path)
        if window_start is None:
            summary_start = payload.get("normalization_window_start", "")
            if isinstance(summary_start, str) and summary_start:
                effective_window_start = summary_start
        if window_end is None:
            summary_end = payload.get("normalization_window_end", "")
            if isinstance(summary_end, str) and summary_end:
                effective_window_end = summary_end
        return effective_window_start, effective_window_end, str(summary_path.resolve())

    return effective_window_start, effective_window_end, ""


def stage_import_candidate(
    candidate: Path,
    baseline_export_dir: Path,
    out_dir: Path,
    *,
    staged_name: str | None = None,
    import_ready_dir: Path | None = None,
    normalization_summary: Path | None = None,
    window_start: str | None = None,
    window_end: str | None = None,
) -> dict[str, object]:
    candidate = require_file(candidate.resolve(), "CoinTracking candidate")
    out_dir = out_dir.resolve()
    overlap_dir = out_dir / "overlap_check"
    effective_window_start, effective_window_end, normalization_summary_path = resolve_normalization_window(
        candidate=candidate,
        normalization_summary=normalization_summary,
        window_start=window_start,
        window_end=window_end,
    )
    summary, flagged_rows = summarize_candidate_overlap(baseline_export_dir, candidate)
    write_candidate_overlap_artifacts(overlap_dir, summary, flagged_rows)

    if summary["status"] != "pass":
        result = {
            "status": "blocked",
            "candidate": str(candidate),
            "canonical_timezone": CANONICAL_TIMEZONE,
            "cointracking_import_timezone": COINTRACKING_IMPORT_TIMEZONE,
            "normalization_summary": normalization_summary_path,
            "normalization_window_start": effective_window_start,
            "normalization_window_end": effective_window_end,
            "overlap_summary": str(overlap_dir / "overlap_summary.json"),
            "rows_flagged": summary["rows_flagged"],
            "rows_outside_normalization_window": 0,
            "message": "Candidate failed overlap screening and was not staged.",
        }
        write_json(out_dir / "stage_summary.json", result)
        return result

    rows_outside_window = count_candidate_rows_outside_window(
        candidate,
        window_start=effective_window_start,
        window_end=effective_window_end,
    )
    if rows_outside_window:
        result = {
            "status": "blocked",
            "candidate": str(candidate),
            "canonical_timezone": CANONICAL_TIMEZONE,
            "cointracking_import_timezone": COINTRACKING_IMPORT_TIMEZONE,
            "normalization_summary": normalization_summary_path,
            "normalization_window_start": effective_window_start,
            "normalization_window_end": effective_window_end,
            "overlap_summary": str(overlap_dir / "overlap_summary.json"),
            "rows_flagged": 0,
            "rows_outside_normalization_window": rows_outside_window,
            "message": "Candidate contains row(s) outside the approved normalization window and was not staged.",
        }
        write_json(out_dir / "stage_summary.json", result)
        return result

    out_dir.mkdir(parents=True, exist_ok=True)
    staged_path = out_dir / (staged_name or candidate.name)
    shutil.copy2(candidate, staged_path)

    import_ready_path = ""
    if import_ready_dir is not None:
        import_ready_dir = import_ready_dir.resolve()
        import_ready_dir.mkdir(parents=True, exist_ok=True)
        ready_path = import_ready_dir / staged_path.name
        shutil.copy2(staged_path, ready_path)
        import_ready_path = str(ready_path)

    result = {
        "status": "staged",
        "candidate": str(candidate),
        "canonical_timezone": CANONICAL_TIMEZONE,
        "cointracking_import_timezone": COINTRACKING_IMPORT_TIMEZONE,
        "normalization_summary": normalization_summary_path,
        "normalization_window_start": effective_window_start,
        "normalization_window_end": effective_window_end,
        "staged_path": str(staged_path),
        "import_ready_path": import_ready_path,
        "overlap_summary": str(overlap_dir / "overlap_summary.json"),
        "rows_flagged": 0,
        "rows_outside_normalization_window": 0,
    }
    write_json(out_dir / "stage_summary.json", result)
    return result


def load_source_inventory(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    return [
        {header: (row.get(header, "") or "").strip() for header in SOURCE_INVENTORY_HEADERS}
        for row in rows
    ]


def profile_wallet_identifiers(
    source: str,
    raw_dir: Path,
    adapter_name: str = "",
) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, object]]:
    raw_dir = require_directory(raw_dir.resolve(), "Raw source directory")
    profile = build_source_profile(
        source=source,
        raw_dir=raw_dir,
        adapter_name="generic",
        adapter_supported=False,
    )
    adapter = get_adapter(source, profile)
    if adapter.name == "generic" and adapter_name:
        adapter = get_adapter(adapter_name, profile)
    evidence, issues = adapter.extract_wallet_identifiers(source, raw_dir, profile)
    summary = {
        "status": "passed" if not issues else "needs_review",
        "adapter": adapter.name,
        "wallet_count": len({row["wallet_id"] for row in evidence}),
        "evidence_rows": len(evidence),
        "issue_count": len(issues),
    }
    return evidence, issues, summary


def summarize_wallet_inventory(
    evidence_rows: Sequence[dict[str, str]],
    issue_rows: Sequence[dict[str, str]],
) -> tuple[list[dict[str, str]], dict[str, object]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in evidence_rows:
        grouped[row["wallet_id"]].append(row)

    inventory_rows: list[dict[str, str]] = []
    for wallet_id, rows in sorted(grouped.items()):
        identifier_kind = rows[0]["identifier_kind"]
        status = "ready"
        notes: list[str] = []
        if identifier_kind == "address_alias":
            status = "needs_linked_evidence"
            notes.append("Truncated alias only")
        inventory_rows.append(
            {
                "wallet_id": wallet_id,
                "identifier_kind": identifier_kind,
                "normalized_identifier": rows[0]["normalized_identifier"],
                "display_identifier": rows[0]["display_identifier"],
                "network_scopes": "; ".join(sorted({row["network_scope"] for row in rows if row["network_scope"]})),
                "source_labels": "; ".join(sorted({row["source"] for row in rows if row["source"]})),
                "controller_labels": "; ".join(sorted({row["controller"] for row in rows if row["controller"]})),
                "account_labels": "; ".join(sorted({row["account_label"] for row in rows if row["account_label"]})),
                "evidence_count": str(len(rows)),
                "primary_evidence_path": rows[0]["evidence_path"],
                "status": status,
                "notes": "; ".join(filter(None, [*notes, *sorted({row["note"] for row in rows if row["note"]})])),
            }
        )

    normalized_to_kinds: dict[str, set[str]] = defaultdict(set)
    for row in evidence_rows:
        normalized_to_kinds[row["normalized_identifier"]].add(row["identifier_kind"])

    generated_issues = list(issue_rows)
    for normalized_identifier, kinds in sorted(normalized_to_kinds.items()):
        if len(kinds) > 1:
            generated_issues.append(
                {
                    "source": "",
                    "capture_path": "",
                    "wallet_id": "",
                    "issue_kind": "identifier_kind_conflict",
                    "message": f"Identifier {normalized_identifier} was classified under multiple kinds: {', '.join(sorted(kinds))}",
                    "evidence_path": "",
                }
            )

    summary = {
        "status": "passed" if not generated_issues else "needs_review",
        "wallet_count": len(inventory_rows),
        "evidence_rows": len(evidence_rows),
        "issue_count": len(generated_issues),
        "identifier_kind_counts": {
            kind: sum(1 for row in inventory_rows if row["identifier_kind"] == kind)
            for kind in sorted({row["identifier_kind"] for row in inventory_rows})
        },
    }
    return inventory_rows, summary


def build_wallet_inventory_repo(repo_root: Path) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], dict[str, object]]:
    repo_root = require_directory(repo_root.resolve(), "Repo root")
    source_inventory_rows = load_source_inventory(repo_root / "03_analysis" / "issues" / "source_inventory.csv")
    source_specs = [
        {"source": row["source"], "capture_path": row["capture_path"], "adapter": row["adapter"]}
        for row in source_inventory_rows
        if row.get("capture_path")
    ]

    evidence_rows: list[dict[str, str]] = []
    issue_rows: list[dict[str, str]] = []
    seen_sources: set[tuple[str, str]] = set()
    for spec in source_specs:
        key = (spec["source"], spec["capture_path"])
        if key in seen_sources:
            continue
        seen_sources.add(key)
        raw_dir = repo_root / spec["capture_path"]
        if not raw_dir.exists():
            issue_rows.append(
                wallet_issue_row(
                    source=spec["source"],
                    raw_dir=raw_dir,
                    wallet_id="",
                    issue_kind="missing_capture_path",
                    message="Wallet inventory source row points to a capture path that does not exist.",
                )
            )
            continue
        source_evidence, source_issues, _ = profile_wallet_identifiers(
            spec["source"],
            raw_dir,
            adapter_name=spec.get("adapter", ""),
        )
        evidence_rows.extend(source_evidence)
        issue_rows.extend(source_issues)

    evidence_rows = dedupe_rows(evidence_rows, key_fields=WALLET_EVIDENCE_HEADERS)
    issue_rows = dedupe_rows(issue_rows, key_fields=WALLET_ISSUE_HEADERS)
    inventory_rows, summary = summarize_wallet_inventory(evidence_rows, issue_rows)
    return inventory_rows, evidence_rows, issue_rows, summary


def write_wallet_inventory_artifacts(
    out_dir: Path,
    *,
    inventory_rows: Sequence[dict[str, str]],
    evidence_rows: Sequence[dict[str, str]],
    issue_rows: Sequence[dict[str, str]],
    summary: dict[str, object],
) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    inventory_path = out_dir / "wallet_inventory.csv"
    evidence_path = out_dir / "wallet_inventory_evidence.csv"
    issues_path = out_dir / "wallet_inventory_issues.csv"
    summary_path = out_dir / "wallet_inventory_summary.json"
    write_csv_rows(inventory_path, list(WALLET_INVENTORY_HEADERS), inventory_rows)
    write_csv_rows(evidence_path, list(WALLET_EVIDENCE_HEADERS), evidence_rows)
    write_csv_rows(issues_path, list(WALLET_ISSUE_HEADERS), issue_rows)
    write_json(
        summary_path,
        {
            **summary,
            "inventory_path": str(inventory_path),
            "evidence_path": str(evidence_path),
            "issues_path": str(issues_path),
        },
    )
    return {
        "inventory_path": str(inventory_path),
        "evidence_path": str(evidence_path),
        "issues_path": str(issues_path),
        "summary_path": str(summary_path),
    }


def refresh_wallet_inventory(repo_root: Path, *, out_dir: Path | None = None) -> dict[str, object]:
    repo_root = require_directory(repo_root.resolve(), "Repo root")
    inventory_rows, evidence_rows, issue_rows, summary = build_wallet_inventory_repo(repo_root)
    paths = write_wallet_inventory_artifacts(
        out_dir or repo_root / "03_analysis" / "inventory",
        inventory_rows=inventory_rows,
        evidence_rows=evidence_rows,
        issue_rows=issue_rows,
        summary=summary,
    )
    return {
        **summary,
        **paths,
    }


def _build_capture_manifest_rows(planned_rows: Sequence[dict[str, str]]) -> list[dict[str, object]]:
    aliases_by_group: dict[str, list[str]] = defaultdict(list)
    for row in planned_rows:
        if row.get("alias_group"):
            aliases_by_group[row["alias_group"]].append(row["source_path"])
    rows: list[dict[str, object]] = []
    for row in sorted(
        (row for row in planned_rows if row.get("placement_status") in {"placed_primary", "placed_renamed"}),
        key=lambda item: item["destination_relative_path"],
    ):
        destination_path = Path(row["destination_path"])
        rows.append(
            {
                "filename": row["destination_relative_path"],
                "bundle_id": row["bundle_id"],
                "bundle_type": row["bundle_type"],
                "bundle_relative_path": row["bundle_relative_path"],
                "source_paths": "; ".join(sorted(dict.fromkeys(aliases_by_group.get(row["alias_group"], [row["source_path"]])))),
                "alias_group": row["alias_group"],
                "collision_status": row["collision_status"],
                "size_bytes": destination_path.stat().st_size if destination_path.exists() else row["size_bytes"],
                "sha256": row["sha256"],
            }
        )
    return rows


def _overlap_windows(a_start: str, a_end: str, b_start: str, b_end: str) -> bool:
    if not all((a_start, a_end, b_start, b_end)):
        return False
    a_start_dt = parse_canonical_timestamp(a_start, label="a_start")
    a_end_dt = parse_canonical_timestamp(a_end, label="a_end")
    b_start_dt = parse_canonical_timestamp(b_start, label="b_start")
    b_end_dt = parse_canonical_timestamp(b_end, label="b_end")
    return a_start_dt <= b_end_dt and b_start_dt <= a_end_dt


@lru_cache(maxsize=None)
def _capture_window_inventory(capture_dir: Path) -> tuple[tuple[str, str, str], ...]:
    rows: list[tuple[str, str, str]] = []
    for path in sorted(file for file in capture_dir.rglob("*") if file.is_file() and file.name != "manifest.csv"):
        inspection_row = inspect_file(path)
        rows.append((str(path), inspection_row.get("min_timestamp", ""), inspection_row.get("max_timestamp", "")))
    return tuple(rows)


def _existing_capture_window_hits(repo_root: Path, decision_row: dict[str, str]) -> list[str]:
    if decision_row["role"] != "source_raw":
        return []
    existing_capture = source_capture_root(repo_root, decision_row["source_folder"]) / decision_row["capture_id"]
    if not existing_capture.exists():
        return []
    candidate_start = decision_row.get("inspection_min_timestamp", "")
    candidate_end = decision_row.get("inspection_max_timestamp", "")
    if not candidate_start or not candidate_end:
        return [str(existing_capture)]
    hits: list[str] = []
    for path, existing_start, existing_end in _capture_window_inventory(existing_capture):
        if _overlap_windows(candidate_start, candidate_end, existing_start, existing_end):
            hits.append(path)
            if len(hits) >= 5:
                break
    return hits


def _add_review_flag(row: dict[str, str], *, code: str, reason: str) -> None:
    row["review_required"] = "yes"
    row["review_reason"] = "; ".join(part for part in [row["review_reason"], reason] if part)
    row["review_codes"] = ";".join(sorted(set(filter(None, (row["review_codes"] + f";{code}").split(";")))))


def _apply_overlap_review_signals(row: dict[str, str]) -> None:
    overlap_reasons = {item for item in row.get("overlap_reasons", "").split(";") if item}
    if "incoming_duplicate" in overlap_reasons and row.get("overlap_incoming_match"):
        _add_review_flag(
            row,
            code="incoming_duplicate_overlap",
            reason=f"Duplicate content also appears elsewhere in the incoming batch: {row['overlap_incoming_match']}",
        )
    if "repo_manifest_match" in overlap_reasons and row.get("overlap_repo_matches"):
        _add_review_flag(
            row,
            code="repo_manifest_overlap",
            reason=f"File already exists in a repo manifest: {row['overlap_repo_matches']}",
        )


def _archive_members_for_plan(path: Path, inspection_row: dict[str, str]) -> list[dict[str, str]]:
    if inspection_row.get("archive_contains_crypto_records", "") != "yes":
        return []
    return inspect_archive_members(path, inspect_file)


def plan_intake_dump(
    *,
    repo_root: Path,
    incoming_dir: Path,
    report_dir: Path,
    apply: bool = False,
) -> dict[str, object]:
    repo_root = repo_root.resolve()
    incoming_dir = require_directory(incoming_dir.resolve(), "Incoming directory")
    report_dir = report_dir.resolve()
    files = sorted(path for path in incoming_dir.rglob("*") if path.is_file())
    overlap_summary, overlap_rows = summarize_file_overlap(files, repo_root=repo_root)
    overlap_by_path = {row["path"]: row for row in overlap_rows}

    planned_rows: list[dict[str, str]] = []
    review_count = 0
    for path in files:
        inspection_row = inspect_file(path)
        decision = resolve_routing_decision(
            repo_root=repo_root,
            incoming_root=incoming_dir,
            path=path,
            inspection_row=inspection_row,
        )
        overlap_row = overlap_by_path.get(str(path.resolve()), {})
        review_codes = list(decision.review_codes)
        if decision.review_required:
            review_count += 1
        planned_rows.append(
            {
                "path": str(path.resolve()),
                "source_path": str(path.resolve()),
                "archive_source_path": "",
                "archive_member_name": "",
                "role": decision.role,
                "source_label": decision.source_label,
                "source_folder": decision.source_folder,
                "system_label": decision.system_label,
                "capture_id": decision.capture_id,
                "capture_basis": decision.capture_basis,
                "date_policy": decision.date_policy,
                "bundle_id": decision.bundle_id,
                "bundle_type": decision.bundle_type,
                "bundle_relative_path": decision.bundle_relative_path,
                "destination_dir": str(decision.destination_dir),
                "destination_path": str(decision.destination_path),
                "destination_relative_path": str(Path(decision.bundle_id) / decision.bundle_relative_path),
                "placed_filename": Path(decision.destination_path).name,
                "placement_status": "planned",
                "collision_status": "none",
                "alias_group": "",
                "confidence": decision.confidence,
                "review_required": "yes" if decision.review_required else "no",
                "review_reason": decision.review_reason,
                "review_codes": ";".join(review_codes),
                "merge_recommendation": decision.merge_recommendation,
                "inventory_match_status": decision.inventory_match_status,
                "inventory_match_reason": decision.inventory_match_reason,
                "suggested_source_label": decision.suggested_source_label,
                "suggested_source_folder": decision.suggested_source_folder,
                "inspection_family": inspection_row.get("family", ""),
                "inspection_scope_tokens": inspection_row.get("scope_tokens", ""),
                "inspection_scope_preview": inspection_row.get("scope_preview", ""),
                "inspection_min_timestamp": inspection_row.get("min_timestamp", ""),
                "inspection_max_timestamp": inspection_row.get("max_timestamp", ""),
                "overlap_reasons": overlap_row.get("reasons", ""),
                "overlap_repo_matches": overlap_row.get("repo_matches", ""),
                "overlap_incoming_match": overlap_row.get("incoming_match", ""),
                "raw_overlap_status": "",
                "raw_overlap_targets": "",
                "sha256": sha256sum(path),
                "size_bytes": str(path.stat().st_size),
            }
        )
        _apply_overlap_review_signals(planned_rows[-1])
        for member in _archive_members_for_plan(path, inspection_row):
            member_name = member["member_name"]
            planned_rows.append(
                {
                    "path": f"{path.resolve()}::{member_name}",
                    "source_path": f"{path.resolve()}::{member_name}",
                    "archive_source_path": str(path.resolve()),
                    "archive_member_name": member_name,
                    "role": decision.role,
                    "source_label": decision.source_label,
                    "source_folder": decision.source_folder,
                    "system_label": decision.system_label,
                    "capture_id": decision.capture_id,
                    "capture_basis": decision.capture_basis,
                    "date_policy": decision.date_policy,
                    "bundle_id": decision.bundle_id,
                    "bundle_type": decision.bundle_type,
                    "bundle_relative_path": str(Path("contents") / member_name),
                    "destination_dir": str(decision.destination_dir),
                    "destination_path": str(decision.destination_dir / "contents" / member_name),
                    "destination_relative_path": str(Path(decision.bundle_id) / "contents" / member_name),
                    "placed_filename": Path(member_name).name,
                    "placement_status": "planned",
                    "collision_status": "none",
                    "alias_group": "",
                    "confidence": decision.confidence,
                    "review_required": "no",
                    "review_reason": "",
                    "review_codes": "",
                    "merge_recommendation": decision.merge_recommendation,
                    "inventory_match_status": decision.inventory_match_status,
                    "inventory_match_reason": decision.inventory_match_reason,
                    "suggested_source_label": decision.suggested_source_label,
                    "suggested_source_folder": decision.suggested_source_folder,
                    "inspection_family": member.get("family", ""),
                    "inspection_scope_tokens": member.get("scope_tokens", ""),
                    "inspection_scope_preview": member.get("scope_preview", ""),
                    "inspection_min_timestamp": member.get("min_timestamp", ""),
                    "inspection_max_timestamp": member.get("max_timestamp", ""),
                    "overlap_reasons": "",
                    "overlap_repo_matches": "",
                    "overlap_incoming_match": "",
                    "raw_overlap_status": "",
                    "raw_overlap_targets": "",
                    "sha256": member["sha256"],
                    "size_bytes": member["size_bytes"],
                }
            )

    package_resolution = resolve_bundle_packages(planned_rows)
    bundle_scope_tokens: dict[tuple[str, str, str, str], frozenset[str]] = defaultdict(frozenset)
    for row in planned_rows:
        package_key = (row["role"], row["source_folder"], row["capture_id"], row["bundle_id"])
        bundle_scope_tokens[package_key] = frozenset(set(bundle_scope_tokens.get(package_key, frozenset())) | set(row_scope_tokens(row)))
    duplicate_packages: set[tuple[str, str, str, str]] = set()
    merged_packages: set[tuple[str, str, str, str]] = set()
    merge_primary_packages: set[tuple[str, str, str, str]] = set()
    overlap_packages: set[tuple[str, str, str, str]] = set()
    mixed_cycle_packages: set[tuple[str, str, str, str]] = set()
    for index, row in enumerate(planned_rows):
        package_key = (row["role"], row["source_folder"], row["capture_id"], row["bundle_id"])
        package_decision = package_resolution.package_decisions.get(package_key)
        row_action = package_resolution.row_actions[index]
        row["package_row_status"] = row_action["package_row_status"]
        if package_decision is None:
            row["package_status"] = ""
            row["package_primary_bundle_id"] = ""
            row["package_related_bundles"] = ""
            row["package_cycle_status"] = ""
            continue
        row["package_status"] = package_decision["package_status"]
        row["package_primary_bundle_id"] = package_decision["package_primary_bundle_id"]
        row["package_related_bundles"] = package_decision["package_related_bundles"]
        row["package_cycle_status"] = package_decision["package_cycle_status"]
        row["package_scope_status"] = package_decision.get("package_scope_status", "")
        row["package_decision_reason"] = package_decision.get("package_decision_reason", "")
        row["package_scope_preview"] = describe_scope_tokens(bundle_scope_tokens.get(package_key, frozenset()), repo_root)
        if package_decision["package_status"].startswith("duplicate_package"):
            duplicate_packages.add(package_key)
            row["placement_status"] = "package_duplicate_skip"
        elif package_decision["package_status"] == "merge_member":
            merged_packages.add(package_key)
        elif package_decision["package_status"] == "merge_primary":
            merge_primary_packages.add(package_key)
        elif package_decision["package_status"] == "overlap_partial_review":
            overlap_packages.add(package_key)
            related_bundle_ids = [item.strip() for item in row["package_related_bundles"].split(";") if item.strip()]
            scope_note = ""
            if row["package_scope_status"] == "incompatible_scope" and related_bundle_ids:
                own_scope = row["package_scope_preview"]
                related_key = (row["role"], row["source_folder"], row["capture_id"], related_bundle_ids[0])
                related_scope = describe_scope_tokens(bundle_scope_tokens.get(related_key, frozenset()), repo_root)
                if own_scope or related_scope:
                    scope_note = f"Scope mismatch ({own_scope or 'unknown'} vs {related_scope or 'unknown'})."
            row["review_required"] = "yes"
            row["review_reason"] = "; ".join(
                part
                for part in [
                    row["review_reason"],
                    f"Package overlap with {package_decision['package_related_bundles']}",
                    row["package_decision_reason"],
                    scope_note,
                ]
                if part
            )
            row["review_codes"] = ";".join(sorted(set(filter(None, (row["review_codes"] + ";package_overlap_review").split(";")))))
        elif package_decision["package_status"] == "mixed_cycle_review":
            mixed_cycle_packages.add(package_key)
            row["review_required"] = "yes"
            row["review_reason"] = "; ".join(
                part
                for part in [row["review_reason"], "Bundle appears to mix files from multiple export-cycle days.", row["package_decision_reason"]]
                if part
            )
            row["review_codes"] = ";".join(sorted(set(filter(None, (row["review_codes"] + ";package_cycle_mixed").split(";")))))

        if row["package_row_status"] == "package_merge_into_primary":
            primary_bundle_id = row["package_primary_bundle_id"]
            capture_dir = Path(row["destination_dir"]).parent
            row["bundle_id"] = primary_bundle_id
            row["destination_dir"] = str(capture_dir / primary_bundle_id)
            row["destination_path"] = str(Path(row["destination_dir"]) / row["bundle_relative_path"])
            row["destination_relative_path"] = str(Path(primary_bundle_id) / row["bundle_relative_path"])
            row["placed_filename"] = Path(row["bundle_relative_path"]).name
        elif row["package_row_status"] == "package_merge_superseded_skip":
            row["placement_status"] = "package_merge_superseded_skip"

    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in planned_rows:
        groups[row["destination_path"]].append(row)

    copied_files = 0
    renamed_collisions = 0
    alias_groups = 0
    for destination_path, rows in groups.items():
        active_rows = [
            row
            for row in rows
            if not row.get("package_status", "").startswith("duplicate_package")
            and row.get("package_row_status") != "package_merge_superseded_skip"
        ]
        if not active_rows:
            for row in rows:
                row["placement_status"] = (
                    "package_merge_superseded_skip" if row.get("package_row_status") == "package_merge_superseded_skip" else "package_duplicate_skip"
                )
            continue
        rows = active_rows
        if len(rows) == 1:
            rows[0]["placement_status"] = "placed_primary"
            continue

        rows.sort(key=lambda item: (item["sha256"], item["source_path"]))
        alias_group = source_slug(destination_path) or "alias"
        alias_groups += 1
        primary_by_hash: dict[str, dict[str, str]] = {}
        for row in rows:
            primary = primary_by_hash.get(row["sha256"])
            if primary is None:
                primary_by_hash[row["sha256"]] = row
                row["alias_group"] = alias_group
                row["placement_status"] = "placed_primary"
                row["collision_status"] = "none"
                continue
            row["alias_group"] = alias_group
            row["placement_status"] = "alias_only"
            row["collision_status"] = "identical_duplicate_alias"

        distinct_primary_rows = sorted(primary_by_hash.values(), key=lambda item: item["source_path"])
        if len(distinct_primary_rows) > 1:
            for index, row in enumerate(distinct_primary_rows):
                suffix = Path(row["destination_path"]).suffix
                stem = Path(row["destination_path"]).stem
                row["placement_status"] = "placed_primary" if index == 0 else "placed_renamed"
                if index > 0:
                    renamed_collisions += 1
                    new_name = f"{stem}__{row['sha256'][:8]}{suffix}"
                    row["placed_filename"] = new_name
                    row["collision_status"] = "renamed_content_collision"
                    row["review_required"] = "yes"
                    row["review_reason"] = "; ".join(part for part in [row["review_reason"], "Content collision required deterministic rename."] if part)
                    row["review_codes"] = ";".join(sorted(set(filter(None, (row["review_codes"] + ";collision_renamed").split(";")))))
                    row["destination_relative_path"] = str(Path(row["bundle_id"]) / new_name)
                    row["destination_path"] = str(Path(row["destination_dir"]) / new_name)

    for row in planned_rows:
        raw_hits = _existing_capture_window_hits(repo_root, row)
        row["raw_overlap_status"] = "capture_window_overlap" if raw_hits else ""
        row["raw_overlap_targets"] = "; ".join(raw_hits)
        if raw_hits:
            _add_review_flag(
                row,
                code="raw_capture_overlap",
                reason=f"Existing raw capture for {row['source_folder']}/{row['capture_id']} has overlapping activity: {row['raw_overlap_targets']}",
            )
    review_count = sum(1 for row in planned_rows if row["review_required"] == "yes")

    if apply:
        for row in planned_rows:
            if row["placement_status"] not in {"placed_primary", "placed_renamed"}:
                continue
            destination_path = Path(row["destination_path"])
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            if "::" in row["source_path"]:
                archive_path = Path(row["archive_source_path"])
                destination_path.write_bytes(read_archive_member_bytes(archive_path, row["archive_member_name"]))
            else:
                shutil.copy2(Path(row["source_path"]), destination_path)
            copied_files += 1
        capture_rows: dict[Path, list[dict[str, str]]] = defaultdict(list)
        for row in planned_rows:
            capture_rows[Path(row["destination_dir"]).parent].append(row)
        for capture_dir, rows in sorted(capture_rows.items()):
            manifest_rows = _build_capture_manifest_rows(rows)
            write_manifest(capture_dir / "manifest.csv", manifest_rows)

    report_dir.mkdir(parents=True, exist_ok=True)
    write_csv_rows(
        report_dir / "intake_plan.csv",
        list(planned_rows[0].keys()) if planned_rows else [
            "path",
            "source_path",
            "archive_source_path",
            "archive_member_name",
            "role",
            "source_label",
            "source_folder",
            "system_label",
            "capture_id",
            "capture_basis",
            "date_policy",
            "bundle_id",
            "bundle_type",
            "bundle_relative_path",
            "destination_dir",
            "destination_path",
            "destination_relative_path",
            "placed_filename",
            "placement_status",
            "collision_status",
            "alias_group",
            "package_status",
            "package_primary_bundle_id",
            "package_related_bundles",
            "package_cycle_status",
            "package_scope_status",
            "package_scope_preview",
            "package_decision_reason",
            "package_row_status",
            "confidence",
            "review_required",
            "review_reason",
            "review_codes",
            "merge_recommendation",
            "inventory_match_status",
            "inventory_match_reason",
            "suggested_source_label",
            "suggested_source_folder",
            "inspection_family",
            "inspection_scope_tokens",
            "inspection_scope_preview",
            "inspection_min_timestamp",
            "inspection_max_timestamp",
            "overlap_reasons",
            "overlap_repo_matches",
            "overlap_incoming_match",
            "raw_overlap_status",
            "raw_overlap_targets",
            "sha256",
            "size_bytes",
        ],
        planned_rows,
    )
    write_json(report_dir / "file_overlap_summary.json", overlap_summary)
    write_csv_rows(
        report_dir / "file_overlap_rows.csv",
        ["path", "sha256", "reasons", "incoming_match", "repo_matches"],
        overlap_rows,
    )
    summary = {
        "status": "applied" if apply else "planned",
        "incoming_dir": str(incoming_dir),
        "planned_files": len(planned_rows),
        "copied_files": copied_files,
        "review_required_files": review_count,
        "alias_groups": alias_groups,
        "renamed_collisions": renamed_collisions,
        "duplicate_packages": len(duplicate_packages),
        "merge_primary_packages": len(merge_primary_packages),
        "merged_packages": len(merged_packages),
        "overlap_packages": len(overlap_packages),
        "mixed_cycle_packages": len(mixed_cycle_packages),
        "report_dir": str(report_dir),
        "file_overlap_summary": str(report_dir / "file_overlap_summary.json"),
        "intake_plan_csv": str(report_dir / "intake_plan.csv"),
    }
    write_json(report_dir / "intake_summary.json", summary)
    return summary
