from __future__ import annotations

from tallylot.application.intake.captures.lifecycle import (
    SourceInventorySummaryReduction,
    reduce_source_inventory_summary,
)


def test_source_summary_reducer_does_not_preserve_assembled_without_output() -> None:
    reduced = reduce_source_inventory_summary(
        reduction=SourceInventorySummaryReduction(
            source="coinbase",
            capture_rows=(
                [
                    _capture_row(
                        "01HV4A5H7VJH7M3Y5A6B7C8D9E",
                        status="normalized",
                    ),
                    _capture_row(
                        "01HV4A5H7VJH7M3Y5A6B7C8D9E",
                        status="assembly_included",
                    ),
                    _capture_row(
                        "01HV4A5H7VJH7M3Y5A6B7C8D9E",
                        status="assembly_excluded",
                    ),
                ]
            ),
            source_rows=[
                {
                    "source": "coinbase",
                    "activity_after_cutoff": "unknown",
                    "scope_status": "in_scope",
                    "status": "assembled",
                    "capture_count": "1",
                    "latest_capture_uid": "01HV4A5H7VJH7M3Y5A6B7C8D9E",
                    "latest_capture_label": "2026-03-23T14-15-16Z",
                    "latest_capture_completed_at": "2026-03-23 14:15:16",
                    "assembly_status": "assembled",
                    "assembled_root_ref": "working/normalized/sources/coinbase",
                    "adapter_hints": "coinbase",
                    "notes": "",
                },
            ],
            assembled_root_ref="working/normalized/sources/coinbase",
            assembled_output_present=False,
        )
    )

    assert reduced["status"] == "normalized"
    assert reduced["assembly_status"] == "excluded"
    assert reduced["assembled_root_ref"] == ""


def test_source_summary_reducer_keeps_pending_without_assembly_exclusions() -> None:
    reduced = reduce_source_inventory_summary(
        reduction=SourceInventorySummaryReduction(
            source="coinbase",
            capture_rows=[
                _capture_row(
                    "01HV4A5H7VJH7M3Y5A6B7C8D9E",
                    status="profiled",
                ),
            ],
            source_rows=[
                {
                    "source": "coinbase",
                    "activity_after_cutoff": "unknown",
                    "scope_status": "in_scope",
                    "status": "profiled",
                    "capture_count": "1",
                    "latest_capture_uid": "01HV4A5H7VJH7M3Y5A6B7C8D9E",
                    "latest_capture_label": "2026-03-23T14-15-16Z",
                    "latest_capture_completed_at": "2026-03-23 14:15:16",
                    "assembly_status": "pending",
                    "assembled_root_ref": "",
                    "adapter_hints": "coinbase",
                    "notes": "",
                },
            ],
            assembled_root_ref="working/normalized/sources/coinbase",
            assembled_output_present=False,
            assembly_excluded_capture_count=0,
        )
    )

    assert reduced["status"] == "profiled"
    assert reduced["assembly_status"] == "pending"
    assert reduced["assembled_root_ref"] == ""


def test_source_summary_reducer_ignores_blocked_rows_after_a_valid_capture() -> None:
    reduced = reduce_source_inventory_summary(
        reduction=SourceInventorySummaryReduction(
            source="binance",
            capture_rows=[
                _capture_row(
                    "01HV4A5H7VJH7M3Y5A6B7C8D9E",
                    status="capture_blocked",
                    source="binance",
                    capture_label="2026-03-24T14-15-16Z",
                    intake_completed_at="2026-03-24 14:15:16",
                ),
                _capture_row(
                    "01HV4A5H7VJH7M3Y5A6B7C8D9F",
                    status="normalized",
                    source="binance",
                    capture_label="2026-03-23T14-15-16Z",
                    intake_completed_at="2026-03-23 14:15:16",
                ),
            ],
            source_rows=[],
        )
    )

    assert reduced["status"] == "normalized"
    assert reduced["capture_count"] == "2"
    assert reduced["latest_capture_uid"] == "01HV4A5H7VJH7M3Y5A6B7C8D9F"
    assert reduced["latest_capture_label"] == "2026-03-23T14-15-16Z"
    assert reduced["latest_capture_completed_at"] == "2026-03-23 14:15:16"


def _capture_row(
    capture_uid: str,
    *,
    status: str,
    source: str = "coinbase",
    capture_label: str = "2026-03-23T14-15-16Z",
    intake_completed_at: str = "2026-03-23 14:15:16",
    capture_root_ref: str | None = None,
) -> dict[str, str]:
    return {
        "capture_uid": capture_uid,
        "source": source,
        "capture_label": capture_label,
        "status": status,
        "intake_started_at": "2026-03-23 14:15:16",
        "intake_completed_at": intake_completed_at,
        "intake_method": "source_intake_apply",
        "incoming_ref": f"incoming/{source}",
        "capture_root_ref": (
            capture_root_ref
            if capture_root_ref is not None
            else f"evidence/raw/source/{source}/{capture_label}"
        ),
        "manifest_fingerprint": f"manifest:{capture_uid}",
        "file_count": "1",
        "observed_period_start": "2026-03-23",
        "observed_period_end": "2026-03-23",
        "observed_group_count": "1",
        "supersedes_capture_uid": "",
        "notes": "",
    }
