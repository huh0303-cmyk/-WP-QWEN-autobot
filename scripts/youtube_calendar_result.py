"""Bind a claimed calendar job, then record its verified release without retrying upload."""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from automation_hub.youtube_calendar import read_calendar, update_row
from automation_hub.youtube_identity import expected_channel_id
from automation_hub.youtube_release import calendar_status, public_allowed, result_url, upload_privacy_status
from gsheets_direct import get_sheets_service


def private_result(path, channel):
    """Compatibility name: validate the receipt against the current release policy."""
    if not Path(path).is_file():
        return "", "worker did not produce a YouTube upload result"
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    vid = data.get("video_id", "")
    import re
    if (not re.fullmatch(r"[A-Za-z0-9_-]{11}", vid)
            or data.get("privacy_status") != upload_privacy_status()
            or data.get("public_allowed") is not public_allowed()
            or data.get("channel_key") != channel
            or data.get("verified_channel_id") != expected_channel_id(channel)):
        return "", "result failed release/channel identity validation"
    return result_url(vid), ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["start", "upload-start", "finish"])
    parser.add_argument("--result", default="artifacts/youtube_result.json")
    args = parser.parse_args()
    schedule_id = os.getenv("SCHEDULE_ID", "")
    if not schedule_id:
        raise RuntimeError("Calendar schedule_id is required; use the central scheduler")
    sid, channel, token = os.environ["SHEET_ID"], os.environ["CHANNEL_KEY"], os.environ["CLAIM_TOKEN"]
    service = get_sheets_service()
    row = next(r for r in read_calendar(service, sid) if r["id"] == schedule_id)
    marker = f"[yt-calendar:{schedule_id}:{token}]"
    run_id = os.environ.get("VPS_JOB_ID") or os.environ.get("GITHUB_RUN_ID")
    if not run_id:
        raise RuntimeError("VPS_JOB_ID is required for a VPS worker run")
    worker = f"[yt-worker:{run_id}]"
    if row["key"] != channel or marker not in row["notes"]:
        raise RuntimeError("Calendar claim/channel mismatch")
    if args.mode == "start":
        if row["status"] != "자료수집" or row["url"] or "[yt-worker:" in row["notes"] or os.getenv("GITHUB_RUN_ATTEMPT", "1") != "1":
            raise RuntimeError("Claim already consumed; refusing duplicate generation/upload")
        update_row(service, sid, row, "자료수집", "", row["notes"] + "\n" + worker)
        return
    if worker not in row["notes"]:
        raise RuntimeError("No matching worker claim; leave calendar unchanged")
    if args.mode == "upload-start":
        if row["status"] != "자료수집" or row["url"] or "[yt-upload:" in row["notes"] or os.getenv("GITHUB_RUN_ATTEMPT", "1") != "1":
            raise RuntimeError("Upload already attempted; manual reconciliation required")
        update_row(service, sid, row, "자료수집", "", row["notes"] + f"\n[yt-upload:{run_id}]")
        return
    expected_status = calendar_status()
    if row["status"] == expected_status and row["url"]:
        url, error = private_result(args.result, channel)
        if error or url != row["url"]:
            raise RuntimeError("Cannot reconcile the calendar without the matching release receipt")
        return
    url, error = private_result(args.result, channel)
    status = expected_status if url else "실패"
    if os.environ.get("VPS_JOB_ID"):
        run_url = os.environ.get("CONTROL_CENTER_PUBLIC_URL", "https://control.korea365.org").rstrip("/") + "/#youtube"
    else:
        run_url = f"https://github.com/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{run_id}"
    notes = row["notes"] + f"\n{run_url}\n" + (error or "채널 ID 및 공개 상태 검증 완료; 업로드 즉시 공개")
    update_row(service, sid, row, status, url, notes)
    service.spreadsheets().values().append(spreadsheetId=sid, range="'자동화_유튜브실행'!A:I",
        valueInputOption="RAW", insertDataOption="INSERT_ROWS", body={"values": [[
            row["when"].isoformat(), channel, row["cells"][2], os.getenv("WORKER_WORKFLOW", ""),
            status, run_url, "", url, error]]}).execute()


if __name__ == "__main__":
    main()
