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

    def test_attach_fee_to_event_list_requires_single_unambiguous_event(self) -> None:
        events = [
            {"event_id": "evt-1", "timestamp": "2024-01-01 00:00:00", "fee_amount": "", "fee_asset": ""},
            {"event_id": "evt-2", "timestamp": "2024-01-01 00:00:00", "fee_amount": "", "fee_asset": ""},
        ]

        with self.assertRaisesRegex(ValueError, "single unambiguous target event"):
            normalization_common.attach_fee_to_event_list(
                events,
                fee_amount="0.5",
                fee_asset="bnb",
                timestamp="2024-01-01 00:00:00",
            )

    def test_attach_fee_to_event_rejects_conflicting_fee(self) -> None:
        event = {
            "event_id": "evt-1",
            "fee_amount": "0.10000000",
            "fee_asset": "ETH",
        }

        with self.assertRaisesRegex(ValueError, "conflicting fee"):
            normalization_common.attach_fee_to_event(event, fee_amount="0.2", fee_asset="ETH")

    def test_attach_fee_to_event_list_attaches_to_named_event(self) -> None:
        events = [
            {"event_id": "evt-1", "timestamp": "2024-01-01 00:00:00", "fee_amount": "", "fee_asset": ""},
            {"event_id": "evt-2", "timestamp": "2024-01-01 00:00:00", "fee_amount": "", "fee_asset": ""},
        ]

        updated = normalization_common.attach_fee_to_event_list(
            events,
            fee_amount="0.5",
            fee_asset="bnb",
            target_event_id="evt-2",
        )

        self.assertEqual("", updated[0]["fee_amount"])
        self.assertEqual("0.50000000", updated[1]["fee_amount"])
        self.assertEqual("BNB", updated[1]["fee_asset"])

    def test_attach_fee_to_event_list_supports_optional_timestamp_tolerance(self) -> None:
        events = [
            {"event_id": "evt-1", "timestamp": "2024-01-01 00:00:01", "fee_amount": "", "fee_asset": ""},
        ]

        updated = normalization_common.attach_fee_to_event_list(
            events,
            fee_amount="0.5",
            fee_asset="bnb",
            timestamp="2024-01-01 00:00:00",
            timestamp_tolerance_seconds=1,
        )

        self.assertEqual("0.50000000", updated[0]["fee_amount"])

    def test_attach_fee_to_event_list_emits_standalone_when_match_is_ambiguous(self) -> None:
        events = [
            {"event_id": "evt-1", "timestamp": "2024-01-01 00:00:00", "fee_amount": "", "fee_asset": ""},
            {"event_id": "evt-2", "timestamp": "2024-01-01 00:00:00", "fee_amount": "", "fee_asset": ""},
        ]
        standalone = {
            "event_id": "fee-1",
            "timestamp": "2024-01-01 00:00:00",
            "fee_amount": "",
            "fee_asset": "",
        }

        updated = normalization_common.attach_fee_to_event_list(
            events,
            fee_amount="0.5",
            fee_asset="bnb",
            timestamp="2024-01-01 00:00:00",
            standalone_event=standalone,
        )

        self.assertEqual(3, len(updated))
        self.assertEqual("fee-1", updated[-1]["event_id"])
