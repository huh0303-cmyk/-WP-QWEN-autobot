"""Bind a claimed calendar job, then record its private result without retrying upload."""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from automation_hub.youtube_calendar import read_calendar, update_row
from automation_hub.youtube_identity import expected_channel_id
from gsheets_direct import get_sheets_service


def notify_review(service, sid, row, url, notes):
    """Report only a validated private receipt; retries never repeat an upload."""
    marker = f"[review-email-sent:{row['id']}]"
    if marker in notes:
        return
    from scripts.publishing_completion_notify import send_email
    body = (f"유튜브 비공개 업로드가 준비되었습니다.\n일정: {row['id']}\n"
            f"채널: {row['key']}\n관리자 검토 링크: {url}\n\n"
            "아직 공개되지 않았습니다. Studio에서 내용을 검토하고 직접 공개 버튼을 눌러주세요.")
    if not send_email(f"[비공개 업로드 완료·검토 요청] {row['id']} {row['key']}", body):
        raise RuntimeError("Private upload saved, but review email was not sent; retry reporting only")
    update_row(service, sid, row, "비공개 업로드", url, notes + "\n" + marker)


def private_result(path, channel):
    if not Path(path).is_file():
        return "", "worker did not produce a private upload result"
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    vid = data.get("video_id", "")
    import re
    if (not re.fullmatch(r"[A-Za-z0-9_-]{11}", vid)
            or data.get("privacy_status") != "private" or data.get("public_allowed") is not False
            or data.get("channel_key") != channel
            or data.get("verified_channel_id") != expected_channel_id(channel)):
        return "", "result failed private/channel identity validation"
    return f"https://studio.youtube.com/video/{vid}/edit", ""


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
    run_id = os.environ["GITHUB_RUN_ID"]
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
    if row["status"] == "비공개 업로드" and row["url"]:
        url, error = private_result(args.result, channel)
        if error or url != row["url"]:
            raise RuntimeError("Cannot retry email without the matching private receipt")
        notify_review(service, sid, row, url, row["notes"])
        return
    url, error = private_result(args.result, channel)
    status = "비공개 업로드" if url else "실패"
    run_url = f"https://github.com/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{run_id}"
    notes = row["notes"] + f"\n{run_url}\n" + (error or "검토 후 관리자 페이지에서 직접 공개; 자동공개 없음")
    update_row(service, sid, row, status, url, notes)
    service.spreadsheets().values().append(spreadsheetId=sid, range="'자동화_유튜브실행'!A:I",
        valueInputOption="RAW", insertDataOption="INSERT_ROWS", body={"values": [[
            row["when"].isoformat(), channel, row["cells"][2], os.getenv("WORKER_WORKFLOW", ""),
            status, run_url, "", url, error]]}).execute()
    if url:
        notify_review(service, sid, row, url, notes)


if __name__ == "__main__":
    main()
