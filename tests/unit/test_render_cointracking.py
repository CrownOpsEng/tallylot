from __future__ import annotations

import unittest

import render_cointracking


class RenderCointrackingTests(unittest.TestCase):
    def test_render_cointracking_rows_maps_mapped_rows_and_skips_non_mapped(self) -> None:
        mapped = {
            "event_id": "evt-1",
            "source": "Coinbase",
            "adapter": "coinbase",
            "account": "Coinbase",
            "wallet": "Coinbase",
            "raw_file": "coinbase.csv",
            "raw_row_ref": "buy-1",
            "timestamp": "2019-09-11 01:06:35",
            "event_kind": "Trade",
            "asset_in": "BTC",
            "amount_in": "0.00175640",
            "asset_out": "CAD",
            "amount_out": "25.00000000",
            "fee_asset": "CAD",
            "fee_amount": "1.46965254",
            "tx_hash": "coinbase-retail-buy-1",
            "description": "Bought 0.0017564 BTC for $25.00 CAD",
            "confidence": "high",
            "status": "mapped",
            "render_type": "Trade",
            "render_exchange": "Coinbase",
            "render_group": "",
            "render_comment": "Bought 0.0017564 BTC for $25.00 CAD",
            "render_comment_mode": "exact",
            "render_tx_id": "coinbase-retail-buy-1",
            "render_tx_id_mode": "ignore",
            "render_allowed_types": "Trade",
            "render_match_window_seconds": "20",
            "render_fee_tolerance": "0.03000000",
            "render_notes": "normalized",
        }
        unresolved = dict(mapped, event_id="evt-2", status="needs_review")

        candidate_rows, skipped_rows = render_cointracking.render_cointracking_rows([mapped, unresolved])

        self.assertEqual(1, len(candidate_rows))
        self.assertEqual(1, len(skipped_rows))
        self.assertEqual("Trade", candidate_rows[0]["Type"])
        self.assertEqual("evt-1", candidate_rows[0]["canonical_event_id"])

