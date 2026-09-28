#!/usr/bin/env python3
"""Run the 33-site Blogger publisher with server-held credentials."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path("/opt/korea365")
RUNTIME_CONFIG = Path("/etc/korea365/article-runtime.json")
PUBLISHER = ROOT / "scripts" / "publish_blogger_33_now.py"


def main() -> int:
    runtime = json.loads(RUNTIME_CONFIG.read_text(encoding="utf-8"))
    env = os.environ.copy()
    for name in (
        "BLOGGER_GOOGLE_CLIENT_ID",
        "BLOGGER_GOOGLE_CLIENT_SECRET",
        "BLOGGER_GOOGLE_REFRESH_TOKEN",
    ):
        value = str(runtime.get(name, "")).strip()
        if not value:
            raise RuntimeError(f"missing required runtime value: {name}")
        env[name] = value

    run_date = os.environ.get("BLOGGER_RUN_DATE", "").strip()
    if not run_date:
        run_date = datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat()
    env["PUBLIC_RUN_KEY"] = f"blogger33-daily-{run_date}"
    env["BLOGGER_REVIEW_DRAFT_MODE"] = "false"

    completed = None
    for attempt in range(3):
        completed = subprocess.run(
            [sys.executable, str(PUBLISHER)],
            cwd=ROOT,
            env=env,
            check=False,
        )
        if completed.returncode == 0:
            return 0
        # A quota hold cannot clear during this short retry window. Preserve
        # the site's failure without spending more free requests.
        result_path = ROOT / "artifacts" / "blogger-33-public-results.json"
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
            quota_hold = (
                result.get("run_key") == env["PUBLIC_RUN_KEY"]
                and len(result.get("results", [])) == 1
                and result["results"][0].get("site") == env.get("BLOGGER_SITE_KEY")
                and result["results"][0].get("error") == "free_quota_wait_no_paid_fallback"
            )
        except (OSError, ValueError, KeyError, IndexError, TypeError):
            quota_hold = False
        if quota_hold:
            return completed.returncode
        if attempt < 2:
            time.sleep(30 * (attempt + 1))
    assert completed is not None
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
