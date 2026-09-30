#!/usr/bin/env python3
"""Load the protected VPS Google runtime for the YouTube-only calendar roll."""
from __future__ import annotations

import json
import os
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
runtime = Path("/etc/korea365/youtube-runtime.json")
values = json.loads(runtime.read_text(encoding="utf-8"))
os.environ.update({key: str(value) for key, value in values.items() if value})
sys.argv = [str(ROOT / "scripts/roll_14day_content_calendar.py"), "--youtube-only"]
runpy.run_path(sys.argv[0], run_name="__main__")
