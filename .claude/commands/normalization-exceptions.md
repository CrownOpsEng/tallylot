# Normalization Exceptions

Review these artifacts after `source normalize`:

- `exceptions.csv` for blocking or unsupported rows
- `normalization_reviews.csv` for explicit assumptions and canonicalizations
- `transactions.csv` for the internal normalized bridge transaction set

If the issue is a candidate-shape or overlap problem, render a candidate with
`output render file` and continue with `batch screen` rather than editing the
candidate blindly.
