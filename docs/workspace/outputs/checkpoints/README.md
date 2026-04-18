---
title: "Checkpoint Outputs"
summary: "Rules for frozen source-backed checkpoints and related sidecar files."
doc_type: reference
audience: both
owner: repo
status: active
naming_scope: workspace_reference
---

Store frozen checkpoints here.

Checkpoint files should be system-native and source-backed. Sidecar oracle
or comparison exports may live beside them when useful, but those support
files do not define the checkpoint.

Expected final closeout path:

- `outputs/checkpoints/2025-12-31-final/`
