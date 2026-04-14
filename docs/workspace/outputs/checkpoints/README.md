---
title: "Checkpoints"
summary: "Rules for frozen source-backed checkpoints and related sidecar artifacts."
doc_type: reference
audience: both
owner: repo
status: active
---

Store frozen checkpoints here.

Checkpoint artifacts should be system-native and source-backed. Sidecar oracle
or comparison exports may live beside them when useful, but those support
artifacts do not define the checkpoint.

Expected final closeout path:

- `outputs/checkpoints/2025-12-31-final/`
