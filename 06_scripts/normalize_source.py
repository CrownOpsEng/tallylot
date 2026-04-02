#!/usr/bin/env python3

"""Normalize a raw source folder into canonical events, balances, and exceptions."""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
from typing import Sequence

from pipeline_common import (
    CANONICAL_BALANCE_HEADERS,
    CANONICAL_EVENT_HEADERS,
    EXCEPTION_HEADERS,
    build_source_profile,
    filter_rows_by_timestamp_window,
    normalization_window_from_hints,
    read_profile,
    write_csv_rows,
    write_json,
)
from render_cointracking import render_cointracking_rows
from script_common import CANONICAL_TIMEZONE, COINTRACKING_IMPORT_TIMEZONE
from source_adapters import decisions_fingerprint, get_adapter, load_exception_decisions


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--raw-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--profile-json", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--exception-decisions", type=Path)
    parser.add_argument("--window-start")
    parser.add_argument("--window-end")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def normalize_source(
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

    if not force and summary_path.exists():
        existing = read_profile(summary_path)
        if (
            existing.get("manifest_fingerprint") == manifest_fingerprint
            and existing.get("adapter") == adapter_name
            and existing.get("exception_decisions_fingerprint") == decisions_digest
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
    from render_cointracking import RENDER_METADATA_HEADERS
    from script_common import write_cointracking_rows

    write_cointracking_rows(candidate_path, rendered_rows, extra_headers=RENDER_METADATA_HEADERS)

    summary = {
        "source": source,
        "adapter": adapter.name,
        "adapter_supported": profile.adapter_supported,
        "manifest_fingerprint": profile.manifest_fingerprint,
        "canonical_timezone": CANONICAL_TIMEZONE,
        "cointracking_import_timezone": COINTRACKING_IMPORT_TIMEZONE,
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
        },
    }
    write_json(summary_path, summary)
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    summary = normalize_source(
        args.source,
        args.raw_dir,
        args.out_dir,
        profile_json=args.profile_json,
        manifest=args.manifest,
        exception_decisions=args.exception_decisions,
        window_start=args.window_start,
        window_end=args.window_end,
        force=args.force,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
