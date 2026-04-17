---
title: "Timezone Validation Outputs"
summary: "Reference for timezone provenance outputs and validation issues."
doc_type: reference
audience: human
owner: repo
status: active
naming_scope: current_state
nav_order: 40
---

The typed profile stage records timezone provenance before normalization.

## Runtime Contract

- Runtime datetimes are timezone-aware UTC in:
  - source translation drafts
  - transaction facts
  - balance snapshots
  - balance evidence
- Persisted artifact timestamps remain `YYYY-MM-DD HH:MM:SS` without an offset.
  Runtime readers interpret that text as UTC.
- Adapter normalization must convert provider timestamps to UTC-aware runtime
  values before draft, fact, or evidence construction.

## Profile Outputs

`source profile` writes:

- `profile.json` with a `timezone_summary`
- `profile_inventory.csv` with these timezone columns:
  - `timestamp_resolution`
  - `timezone_mode`
  - `timezone_value`
  - `timezone_conflict`
- `timezone_issues.csv`

## Current Provenance Modes

| Mode | Meaning |
| ---- | ------- |
| `header_utc` | The CSV header explicitly declares UTC |
| `value_utc` | The timestamp value itself declares UTC or an offset |
| `date_only` | The source provides only a calendar date |
| `naive` | The source provides a timestamp without timezone evidence |
| `conflict` | The file exposes contradictory timezone hints |

`timezone_issues.csv` is reserved for blocking conflicts. Non-blocking timezone
assumptions remain visible in the profile summary and, when normalization makes
an interpretive choice, in `normalization_reviews.csv`.

## Current Structured CSV Behavior

The working structured CSV adapter uses naive timestamps in its source export.
Profiling records those files as `timezone_mode=naive`, and normalization emits
the dataset review `timestamp_timezone_assumed_utc` so the assumption is
explicit before staging.
