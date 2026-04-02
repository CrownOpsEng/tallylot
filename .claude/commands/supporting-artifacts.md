# Supporting Artifacts

Use this route when supporting evidence exists outside the main CSV normalization
path.

1. run `checkpoint extract-pdf-balances` for supported Coinbase, Binance, or
   Shakepay statement PDFs
2. review the extracted balance rows before using them as evidence
3. keep the PDF-derived artifacts in supporting or reconciliation review paths;
   do not treat them as canonical transaction imports

Use `docs/guides/operator-quickstart.md` for the short surrounding workflow,
`docs/guides/normalize-screen-stage.md` and `docs/guides/verify-a-round.md`
for the detailed operator procedures, and `docs/README.md` when you need the
nearest human-facing entrypoint.
