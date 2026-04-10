from __future__ import annotations

import json
import shutil
from pathlib import Path


def materialize_capture_root(
    root: Path,
    *,
    source: str,
    source_dir: Path | None = None,
    capture_label: str = "2026-03-23T14-15-16Z",
    capture_uid: str = "01HV4A5H7VJH7M3Y5A6B7C8D9E",
) -> Path:
    workspace_root = root / "workspace"
    capture_root = (
        workspace_root / "evidence" / "raw" / "source" / source / capture_label
    )
    capture_root.mkdir(parents=True, exist_ok=True)
    if source_dir is not None:
        shutil.copytree(source_dir, capture_root, dirs_exist_ok=True)
    (capture_root / "capture.json").write_text(
        json.dumps(
            {
                "capture_uid": capture_uid,
                "source": source,
                "capture_label": capture_label,
                "intake_started_at": "2026-03-23 14:15:16",
                "intake_completed_at": "2026-03-23 14:15:16",
                "intake_method": "source_intake_apply",
                "incoming_ref": f"incoming/{source}",
                "manifest_fingerprint": "manifest:fixture",
                "status": "captured",
                "notes": "",
            }
        ),
        encoding="utf-8",
    )
    return capture_root
