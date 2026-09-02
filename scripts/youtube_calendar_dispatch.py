"""Claim calendar rows before dispatch. Ambiguous dispatches are never retried."""
import datetime as dt
import json
import os
import uuid

import requests
from automation_hub.sheet_schema import YOUTUBE_CHANNEL_HEADER
from automation_hub.youtube_calendar import (
    KST, READY, next_calendar_run, read_calendar, select_due, select_passed, update_row,
)
from automation_hub.youtube_registry import load_channels
from gsheets_direct import get_sheets_service


ACTIVE_RUN_STATES = {"queued", "in_progress", "requested", "waiting", "pending"}
YOUTUBE_CHANNEL_TAB = "자동화_유튜브채널"
YOUTUBE_RUN_TAB = "자동화_유튜브실행"


def parse_settings(values, channels):
    if not values or [str(value) for value in values[0]] != YOUTUBE_CHANNEL_HEADER:
        raise RuntimeError("YouTube settings header mismatch")
    rows = {}
    for index, raw in enumerate(values[1:], 2):
        if not raw or not str(raw[0]).strip():
            continue
        values_row = [str(value or "").strip() for value in raw] + [""] * max(0, len(YOUTUBE_CHANNEL_HEADER) - len(raw))
        row = dict(zip(YOUTUBE_CHANNEL_HEADER, values_row))
        row["sheet_row"] = index
        if row["channel_key"] in rows:
            raise RuntimeError(f"Duplicate YouTube channel setting: {row['channel_key']}")
        rows[row["channel_key"]] = row
    if set(rows) != set(channels):
        raise RuntimeError("YouTube settings must contain the exact canonical 10-channel roster")
    return rows


def setting_is_due(setting, now):
    raw = setting.get("next_run_at", "").strip()
    if not raw:
        return True
    try:
        parsed = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeError(f"invalid next_run_at for {setting['channel_key']}: {raw}") from exc
    if parsed.tzinfo is None:
        raise RuntimeError(f"next_run_at must include timezone for {setting['channel_key']}")
    return now >= parsed.astimezone(KST)


def append_run_log(service, sid, *, when, channel, status, workflow="", run_url="", video_url="", error=""):
    service.spreadsheets().values().append(
        spreadsheetId=sid, range=f"'{YOUTUBE_RUN_TAB}'!A:I", valueInputOption="RAW",
        insertDataOption="INSERT_ROWS", body={"values": [[
            when.isoformat(), channel.channel_key, channel.channel_type, workflow or channel.workflow,
            status, run_url, "", video_url, error[:500],
        ]]},
    ).execute()


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
    channels = {c.channel_key: c for c in load_channels()}
    now = dt.datetime.now(KST)
    settings_values = service.spreadsheets().values().get(spreadsheetId=sid,
        range=f"'{YOUTUBE_CHANNEL_TAB}'!A1:R20").execute().get("values", [])
    settings = parse_settings(settings_values, channels)
    enabled = set()
    for key, setting in settings.items():
        c = channels[key]
        if setting["channel_type"] != c.channel_type or setting["display_name"] != c.display_name or setting["channel_id"] != c.channel_id or setting["secret_profile"] != c.secret_profile or setting["workflow"] != c.workflow:
            raise RuntimeError(f"Channel identity/workflow mismatch: {c.channel_key}")
        if setting["interval_days_min"] != "2" or setting["interval_days_max"] != "3":
            raise RuntimeError(f"Channel interval must be 2-3 days: {c.channel_key}")
        state = setting["enabled"].upper()
        if not c.enabled or state in ("OFF", "FALSE", "0"):
            continue
        if state not in ("ON", "TRUE", "1"):
            raise RuntimeError(f"Invalid ON/OFF value for {c.channel_key}: {setting['enabled']}")
        if setting_is_due(setting, now):
            enabled.add(c.channel_key)
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
    calendar_rows = read_calendar(service, sid)
    passed = select_passed(calendar_rows, now)
    selected, skipped = select_due(calendar_rows, now, enabled,
                                  min(10, max(1, int(os.getenv("MAX_DISPATCH", "3")))) if dry else 1)
    print(json.dumps({"mode": "dry_run" if dry else "private-production", "due": [
        {"id": r["id"], "channel": r["key"], "planned_at": r["when"].isoformat(), "topic": r["topic"]}
        for r in selected], "passed": [{"id": r["id"], "channel": r["key"], "reason": "past-window-pass"} for r in passed],
        "suppressed_duplicates": skipped, "public_allowed": False}, ensure_ascii=False))
    if dry:
        return 0
    for row in passed:
        note = row["notes"] + "\n[yt-pass] 실행창 경과; 과거 일정 자동 보충 실행 금지"
        update_row(service, sid, row, "PASS", row["url"], note)
        append_run_log(service, sid, when=now, channel=channels[row["key"]], status="PASS", error="past schedule window elapsed")
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
        except requests.RequestException as exc:
            # The server may have accepted a timed-out request. Leave the claim intact.
            append_run_log(service, sid, when=now, channel=c, status="dispatch_unconfirmed", error=str(exc))
            print(f"Dispatch not confirmed for {row['id']}; retained claim, manual inspection required")
            return 1
        future = next_calendar_run(live, c.channel_key, now)
        service.spreadsheets().values().update(
            spreadsheetId=sid, range=f"'{YOUTUBE_CHANNEL_TAB}'!P{settings[c.channel_key]['sheet_row']}:R{settings[c.channel_key]['sheet_row']}",
            valueInputOption="RAW", body={"values": [[future.isoformat() if future else "", now.isoformat(), "dispatched_private"]]},
        ).execute()
        append_run_log(service, sid, when=now, channel=c, status="dispatched_private")
        print(f"Dispatched {row['id']} to {c.channel_key}; private only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
