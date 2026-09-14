"""VPS owns the fixed KST schedule; dispatch only the free statistics workflow."""
import argparse
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
import requests

KST = timezone(timedelta(hours=9))
STATE = Path("/var/lib/korea365/core-metrics-dispatch.json")


def dispatch(dry_run=False):
    now = datetime.now(KST)
    day = now.date().isoformat()
    if dry_run:
        print(json.dumps({"timezone":"Asia/Seoul", "schedule":"07:00:00", "current_kst":now.isoformat(), "paid_ai":False}))
        return
    if now.hour != 7 or now.minute >= 10:
        raise RuntimeError("Outside the fixed 07:00 collection window; no late baseline dispatched")
    try:
        prior = json.loads(STATE.read_text())
    except (OSError, ValueError):
        prior = {}
    if prior.get("date") == day:
        print("Already attempted today; no duplicate dispatch")
        return
    token = os.environ["CONTROL_CENTER_GITHUB_TOKEN"]
    STATE.parent.mkdir(parents=True, exist_ok=True)
    record = {"date":day, "requested_at":now.isoformat(), "status":"dispatching"}
    STATE.write_text(json.dumps(record))
    # Persist before the network call: an ambiguous timeout must never resend.
    response = requests.post("https://api.github.com/repos/huh0303-cmyk/-WP-QWEN-autobot/actions/workflows/core-metrics-report.yml/dispatches",
        headers={"Authorization":"Bearer " + token, "Accept":"application/vnd.github+json", "X-GitHub-Api-Version":"2026-03-10"},
        json={"ref":"main", "return_run_details":True, "inputs":{"send_email":"true", "baseline_date":day}}, timeout=30)
    response.raise_for_status()
    if response.status_code != 200 or not isinstance(response.json().get("workflow_run_id"), int):
        raise RuntimeError("Dispatch receipt uncertain; inspect GitHub before retrying")
    record.update(status="accepted", run_id=response.json()["workflow_run_id"])
    STATE.write_text(json.dumps(record))
    print(json.dumps(record))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    dispatch(parser.parse_args().dry_run)
