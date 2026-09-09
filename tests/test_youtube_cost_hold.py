import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("cost_queue", ROOT / "automation_hub/youtube_vps_queue.py")
queue = importlib.util.module_from_spec(spec)
spec.loader.exec_module(queue)


class CostHoldTests(unittest.TestCase):
    def test_pause_preserves_queue_and_refuses_new_paid_work(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root / "hold"
            with patch.dict("os.environ", {"YOUTUBE_COST_HOLD_FILE": str(marker), "YOUTUBE_VPS_QUEUE_DIR": str(root / "queue")}):
                first = queue.enqueue("nasa", "NASA", "test")
                marker.touch()
                with self.assertRaisesRegex(RuntimeError, "비용 점검"):
                    queue.enqueue("history", "History", "test")
                self.assertTrue(queue.cost_hold_active())
                self.assertEqual(queue.pending_count(), 1)
                self.assertTrue((root / "queue/pending" / (first["job_id"] + ".json")).exists())
                marker.unlink()
                queue.enqueue("history", "History", "test")
                self.assertEqual(queue.pending_count(), 2)


if __name__ == "__main__":
    unittest.main()
