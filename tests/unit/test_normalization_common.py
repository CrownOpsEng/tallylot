from __future__ import annotations

import unittest

import normalization_common


class NormalizationCommonTests(unittest.TestCase):
    def test_attach_fee_to_event_sets_fee_fields(self) -> None:
        event = {
            "event_id": "evt-1",
            "fee_amount": "",
            "fee_asset": "",
        }

        updated = normalization_common.attach_fee_to_event(event, fee_amount="0.123", fee_asset="eth")

        self.assertEqual("0.12300000", updated["fee_amount"])
        self.assertEqual("ETH", updated["fee_asset"])
        self.assertEqual("", event["fee_amount"])

    def test_attach_fee_to_event_list_updates_selected_event(self) -> None:
        events = [
            {"event_id": "evt-1", "fee_amount": "", "fee_asset": ""},
            {"event_id": "evt-2", "fee_amount": "", "fee_asset": ""},
        ]

        updated = normalization_common.attach_fee_to_event_list(
            events,
            fee_amount="0.5",
            fee_asset="bnb",
            index=1,
        )

        self.assertEqual("", updated[0]["fee_amount"])
        self.assertEqual("0.50000000", updated[1]["fee_amount"])
        self.assertEqual("BNB", updated[1]["fee_asset"])

    def test_attach_fee_to_event_rejects_conflicting_fee(self) -> None:
        event = {
            "event_id": "evt-1",
            "fee_amount": "0.10000000",
            "fee_asset": "ETH",
        }

        with self.assertRaisesRegex(ValueError, "conflicting fee"):
            normalization_common.attach_fee_to_event(event, fee_amount="0.2", fee_asset="ETH")
