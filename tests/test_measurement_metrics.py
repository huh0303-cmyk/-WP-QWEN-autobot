import importlib.util
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("daily_site_traffic", ROOT / "scripts" / "daily_site_traffic.py")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class MeasurementMetricTests(unittest.TestCase):
    def test_index_metrics_are_derived_without_inventing_missing_values(self):
        self.assertEqual(
            MODULE.derive_index_metrics(80, 100, 75),
            {"unindexed": 20, "index_rate": 80.0, "recent_index_increase": 5},
        )
        self.assertEqual(
            MODULE.derive_index_metrics(None, 100, 75),
            {"unindexed": None, "index_rate": None, "recent_index_increase": None},
        )

    def test_index_rate_does_not_divide_by_zero(self):
        result = MODULE.derive_index_metrics(0, 0, 0)
        self.assertIsNone(result["index_rate"])
        self.assertEqual(result["unindexed"], 0)

    def test_missing_previous_snapshot_is_not_reported_as_zero_growth(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = pathlib.Path(directory) / "missing.json"
            self.assertEqual(MODULE.load_previous_index_counts(missing), {})


if __name__ == "__main__":
    unittest.main()
