# Source Raw Exports

Store untouched external source evidence here. This branch is only for exchange, wallet, explorer, bot, and other upstream-system exports.

Rules:

- never overwrite raw files
- keep original filenames when practical
- keep each capture in its own canonical capture folder when routing new intake
- write `manifest.csv` inside the capture folder, not at the source root
- do not place CoinTracking exports here; those belong under `evidence/raw/portfolio/`

Preferred structure for new intake:

- `evidence/raw/source/<source>/<capture_id>/`
- `evidence/raw/source/<source>/<capture_id>/manifest.csv`

Bundle-aware intake may create nested bundle paths inside a capture, for example:

- `evidence/raw/source/<source>/<capture_id>/<bundle_id>/archive/...`
- `evidence/raw/source/<source>/<capture_id>/<bundle_id>/contents/...`

Some older tracked captures still use pre-refactor subpaths such as `raw/`. Keep those files immutable, but do not copy that layout into new intake work.
