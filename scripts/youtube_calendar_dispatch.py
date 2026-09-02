"""Claim calendar rows before dispatch. Ambiguous dispatches are never retried."""
import datetime as dt
import json
import os
import uuid

import requests
from automation_hub.youtube_calendar import KST, READY, read_calendar, select_due, update_row
from automation_hub.youtube_registry import load_channels
from gsheets_direct import get_sheets_service


ACTIVE_RUN_STATES = {"queued", "in_progress", "requested", "waiting", "pending"}


def youtube_worker_active(repo, token, workflows):
    """Fail closed when worker state cannot be proven idle."""
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    for workflow in sorted(set(workflows)):
        response = requests.get(
            f"https://api.github.com/repos/{repo}/actions/workflows/{workflow}/runs",
            headers=headers, params={"per_page": 20}, timeout=30,
        )
        response.raise_for_status()
        if any(run.get("status") in ACTIVE_RUN_STATES for run in response.json().get("workflow_runs", [])):
            return True
    return False


def main():
    sid = os.environ["SHEET_ID"]
    repo = os.environ["GITHUB_REPOSITORY"]
    dry = os.environ.get("DRY_RUN", "true").lower() == "true"
    service = get_sheets_service()
    channels = {c.channel_key: c for c in load_channels() if c.enabled}
    settings = service.spreadsheets().values().get(spreadsheetId=sid,
        range="'자동화_유튜브채널'!A1:R20").execute().get("values", [])
    if not settings or settings[0][:7] != ["channel_key", "channel_type", "display_name", "channel_id", "secret_profile", "workflow", "enabled"]:
        raise RuntimeError("YouTube settings header mismatch")
    enabled = set()
    for r in settings[1:]:
        if len(r) < 7 or r[0] not in channels or r[6] not in ("ON", "TRUE", "1"):
            continue
        c = channels[r[0]]
        if r[3] != c.channel_id or r[5] != c.workflow:
            raise RuntimeError(f"Channel identity/workflow mismatch: {c.channel_key}")
        enabled.add(c.channel_key)
    now = dt.datetime.now(KST)
    token = os.environ.get("GH_DISPATCH_TOKEN", "")
    if not dry:
        if not token:
            raise RuntimeError("GH_DISPATCH_TOKEN is required for production dispatch")
        try:
            if youtube_worker_active(repo, token, (c.workflow for c in channels.values())):
                print("YouTube worker is active; no new calendar claim was created")
                return 0
        except requests.RequestException as exc:
            raise RuntimeError("Could not prove YouTube workers idle; refusing dispatch") from exc
    selected, skipped = select_due(read_calendar(service, sid), now, enabled,
                                  min(10, max(1, int(os.getenv("MAX_DISPATCH", "3")))) if dry else 1)
    print(json.dumps({"mode": "dry_run" if dry else "private-production", "due": [
        {"id": r["id"], "channel": r["key"], "planned_at": r["when"].isoformat(), "topic": r["topic"]}
        for r in selected], "suppressed_duplicates": skipped, "public_allowed": False}, ensure_ascii=False))
    if dry:
        return 0
    for planned in selected:
        # Re-resolve by stable ID immediately before claiming; don't trust a stale row number.
        live = read_calendar(service, sid)
        eligible, _ = select_due(live, dt.datetime.now(KST), enabled, 10)
        row = next((r for r in eligible if r["id"] == planned["id"] and r["cells"] == planned["cells"]), None)
        if row is None:
            continue
        token = uuid.uuid4().hex
        marker = f"[yt-calendar:{row['id']}:{token}]"
        notes = row["notes"] + "\n" + marker + " 비공개 제작 요청; 공개는 관리자 수동 버튼만"
        update_row(service, sid, row, "자료수집", "", notes)
        c = channels[row["key"]]
        inputs = {"channel": c.channel_key, "topic": row["topic"], "schedule_id": row["id"],
                  "claim_token": token, "publish_delay_hours": ""}
        if c.channel_type == "playlist":
            inputs["language"] = row["language"]
        try:
            response = requests.post(f"https://api.github.com/repos/{repo}/actions/workflows/{c.workflow}/dispatches",
                headers={"Authorization": f"Bearer {os.environ['GH_DISPATCH_TOKEN']}", "Accept": "application/vnd.github+json"},
                json={"ref": "main", "inputs": inputs}, timeout=30)
            response.raise_for_status()
        except requests.RequestException:
            # The server may have accepted a timed-out request. Leave the claim intact.
            print(f"Dispatch not confirmed for {row['id']}; retained claim, manual inspection required")
            return 1
        print(f"Dispatched {row['id']} to {c.channel_key}; private only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
