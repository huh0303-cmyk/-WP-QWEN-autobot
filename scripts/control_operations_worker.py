"""VPS receipt monitor: never creates scheduled publication runs itself."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from control_center.app import _operation_worker

if __name__ == "__main__":
    _operation_worker.run()
