#!/usr/bin/env python3

"""Normalize Coinbase raw exports into CoinTracking-schema transaction and balance files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from coinbase_common import (
    BALANCE_HEADERS,
    COINBASE_METADATA_HEADERS,
    coinbase_balance_rows_from_text,
    csv_dict_rows,
    normalize_coinbase_transactions,
    retail_csv_rows,
)
from script_common import CANONICAL_TIMEZONE, COINTRACKING_IMPORT_TIMEZONE, extract_pdf_text, write_cointracking_rows, write_csv_rows


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--retail-csv", required=True, type=Path)
    parser.add_argument("--pro-statement", action="append", default=[], type=Path)
    parser.add_argument("--pro-fills", action="append", default=[], type=Path)
    parser.add_argument("--pdf", action="append", default=[], type=Path)
    parser.add_argument("--tx-output", required=True, type=Path)
    parser.add_argument("--balance-output", type=Path)
    return parser.parse_args(argv)


def normalize_coinbase_exports(
    retail_csv: Path,
    *,
    pro_statement_paths: list[Path],
    pro_fill_paths: list[Path],
    pdf_paths: list[Path],
    tx_output: Path,
    balance_output: Path | None = None,
) -> dict[str, object]:
    retail_rows = retail_csv_rows(retail_csv)
    pro_statement_rows = []
    for path in pro_statement_paths:
        for row in csv_dict_rows(path, "Coinbase Pro statement CSV"):
            row["_file"] = path.name
            pro_statement_rows.append(row)
    pro_fill_rows = []
    for path in pro_fill_paths:
        for row in csv_dict_rows(path, "Coinbase Pro fills CSV"):
            row["_file"] = path.name
            pro_fill_rows.append(row)

    normalized_transactions = normalize_coinbase_transactions(
        retail_rows,
        pro_statement_rows,
        pro_fill_rows,
        retail_source=retail_csv,
    )
    write_cointracking_rows(tx_output, normalized_transactions, extra_headers=COINBASE_METADATA_HEADERS)

    balance_rows = []
    for pdf_path in pdf_paths:
        balance_rows.extend(coinbase_balance_rows_from_text(extract_pdf_text(pdf_path), pdf_path.name))
    if balance_output is not None:
        write_csv_rows(balance_output, list(BALANCE_HEADERS), balance_rows)

    return {
        "normalized_transaction_rows": len(normalized_transactions),
        "normalized_balance_rows": len(balance_rows),
        "canonical_timezone": CANONICAL_TIMEZONE,
        "cointracking_import_timezone": COINTRACKING_IMPORT_TIMEZONE,
        "tx_output": str(tx_output),
        "balance_output": str(balance_output) if balance_output is not None else "",
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    summary = normalize_coinbase_exports(
        args.retail_csv,
        pro_statement_paths=args.pro_statement,
        pro_fill_paths=args.pro_fills,
        pdf_paths=args.pdf,
        tx_output=args.tx_output,
        balance_output=args.balance_output,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
