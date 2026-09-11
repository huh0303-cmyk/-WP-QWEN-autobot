import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from measurement_contract import CONNECTED, NEEDS_CONNECTION, guarded_sum, net_profit, source_row


class MeasurementContractTests(unittest.TestCase):
    def test_missing_source_is_explicit_and_never_zero(self):
        row = source_row("AdSense")
        self.assertEqual(row["status"], NEEDS_CONNECTION)
        self.assertIsNone(row["today"])
        self.assertIsNone(guarded_sum([row], "today"))

    def test_partial_period_does_not_claim_connected(self):
        row = source_row("YouTube", {"today": 100, "seven_days": 500})
        self.assertEqual(row["status"], NEEDS_CONNECTION)

    def test_net_profit_requires_every_source(self):
        revenue = [source_row("AdSense", {"today": 1000, "seven_days": 5000, "month": 9000})]
        costs = [source_row("OpenAI", {"today": 100, "seven_days": 400, "month": 700})]
        self.assertEqual(revenue[0]["status"], CONNECTED)
        self.assertEqual(net_profit(revenue, costs, "today"), 900)
        costs.append(source_row("Replicate"))
        self.assertIsNone(net_profit(revenue, costs, "today"))
