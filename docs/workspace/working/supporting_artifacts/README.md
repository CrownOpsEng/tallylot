---
title: "Supporting Artifacts"
summary: "Rules for non-raw derivative materials discovered during intake and review work."
doc_type: reference
audience: both
owner: repo
status: active
---

This subtree holds non-raw derivatives discovered during intake.

Examples:

- manual or semi-manual calc workbooks
- manual balance submission packages under `balance_submissions/<source>/`
- tracker-specific import-helper files
- screenshots or rendered HTML evidence saves
- intake or validation report packages
- transformed helper artifacts that should not live under raw source exports

Files here are useful support material, but they are not raw system-of-record
evidence.

Do not place these files here:

- untouched upstream PDFs
- untouched upstream HTML exports
- untouched upstream sidecars required to interpret an original export

When intake places supporting artifacts under a source-scoped path, it uses the
same stable source-label mapping rules as raw source intake. Update
`analysis/issues/source_label_map.csv` when a legacy or manual intake pass must
stay tied to an existing operator-managed source label.

Use
[`balance_submissions/README.md`](balance_submissions/README.md)
for the scaffolded manual balance submission package layout and handoff rules.
