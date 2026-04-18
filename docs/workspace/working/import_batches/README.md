---
title: "Approved Import Batches"
summary: "Reference for approved per-source import batches and their required support files."
doc_type: reference
audience: both
owner: repo
status: active
naming_scope: workspace_reference
---

Place the next approved import batch for a single source here.

In the current runtime, this is usually an approved external-import package.
Keep the folder semantics generic even when a round uses one concrete adapter.

Every file here should have:

- an upstream raw source export
- a reviewed normalization path
- a passing `make oracle ARGS='batch screen'` result saved beside the candidate
- a matching entry in the round log before import
