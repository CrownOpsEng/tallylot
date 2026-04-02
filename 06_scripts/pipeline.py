#!/usr/bin/env python3

"""Shared orchestration for intake, profiling, normalization, staging, and wallet inventory."""

from __future__ import annotations

import csv
import json
import shutil
from collections import defaultdict
from dataclasses import replace
from pathlib import Path
from typing import Iterable, Sequence

from inspection import inspect_file
from overlap_engine import summarize_candidate_overlap, summarize_file_overlap, write_candidate_overlap_artifacts
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
    write_profile_artifacts,
)
from render_cointracking import RENDER_METADATA_HEADERS, render_cointracking_rows
from routing import resolve_routing_decision
from script_common import (
    CANONICAL_TIMEZONE,
    COINTRACKING_IMPORT_TIMEZONE,
    read_cointracking_rows,
    require_directory,
    require_file,
    write_cointracking_rows,
    write_csv_rows,
    write_json,
)
from source_adapters import decisions_fingerprint, get_adapter, load_exception_decisions
from source_manifest import build_manifest_rows, write_manifest
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

    baseline_dir = Path(__file__).resolve().parents[1] / "01_raw_exports" / "cointracking" / "2023-08-05_full_export"
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
    copied_files = 0
    review_count = 0
    for path in files:
        inspection_row = inspect_file(path)
        decision = resolve_routing_decision(
            repo_root=repo_root,
            incoming_root=incoming_dir,
            path=path,
            inspection_row=inspection_row,
        )
        destination_path = decision.destination_dir / path.name
        if apply and not decision.review_required:
            decision.destination_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination_path)
            copied_files += 1
        if decision.review_required:
            review_count += 1
        overlap_row = overlap_by_path.get(str(path.resolve()), {})
        planned_rows.append(
            {
                "path": str(path.resolve()),
                "role": decision.role,
                "source_label": decision.source_label,
                "system_label": decision.system_label,
                "capture_id": decision.capture_id,
                "capture_basis": decision.capture_basis,
                "batch_slug": decision.batch_slug,
                "destination_dir": str(decision.destination_dir),
                "destination_path": str(destination_path),
                "confidence": decision.confidence,
                "review_required": "yes" if decision.review_required else "no",
                "review_reason": decision.review_reason,
                "merge_recommendation": decision.merge_recommendation,
                "inspection_family": inspection_row.get("family", ""),
                "inspection_min_timestamp": inspection_row.get("min_timestamp", ""),
                "inspection_max_timestamp": inspection_row.get("max_timestamp", ""),
                "overlap_reasons": overlap_row.get("reasons", ""),
                "overlap_repo_matches": overlap_row.get("repo_matches", ""),
                "overlap_incoming_match": overlap_row.get("incoming_match", ""),
            }
        )

    if apply:
        touched_dirs = sorted({Path(row["destination_dir"]) for row in planned_rows if row["review_required"] == "no"})
        for directory in touched_dirs:
            rows = build_manifest_rows(directory, directory / "manifest.csv")
            write_manifest(directory / "manifest.csv", rows)

    report_dir.mkdir(parents=True, exist_ok=True)
    write_csv_rows(
        report_dir / "intake_plan.csv",
        list(planned_rows[0].keys()) if planned_rows else [
            "path",
            "role",
            "source_label",
            "system_label",
            "capture_id",
            "capture_basis",
            "batch_slug",
            "destination_dir",
            "destination_path",
            "confidence",
            "review_required",
            "review_reason",
            "merge_recommendation",
            "inspection_family",
            "inspection_min_timestamp",
            "inspection_max_timestamp",
            "overlap_reasons",
            "overlap_repo_matches",
            "overlap_incoming_match",
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
        "report_dir": str(report_dir),
        "file_overlap_summary": str(report_dir / "file_overlap_summary.json"),
        "intake_plan_csv": str(report_dir / "intake_plan.csv"),
    }
    write_json(report_dir / "intake_summary.json", summary)
    return summary
