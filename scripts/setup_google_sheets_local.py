#!/usr/bin/env python3
"""Create a git-ignored local Google Sheets OAuth file from a Desktop client JSON."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / ".local" / "google_sheets_oauth.json"
SCOPES = ["https://www.googleapis.com/auth/drive"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("client_json", help="Google Cloud에서 받은 데스크톱 앱 OAuth JSON 경로")
    args = parser.parse_args()
    source = Path(args.client_json).expanduser().resolve()
    if not source.exists():
        raise SystemExit(f"파일을 찾을 수 없습니다: {source}")
    raw = json.loads(source.read_text(encoding="utf-8"))
    installed = raw.get("installed")
    if not installed:
        raise SystemExit("'데스크톱 앱' 유형의 OAuth 클라이언트 JSON이 아닙니다.")
    from google_auth_oauthlib.flow import InstalledAppFlow
    flow = InstalledAppFlow.from_client_secrets_file(str(source), SCOPES)
    credentials = flow.run_local_server(port=0, open_browser=True, prompt="consent", access_type="offline")
    if not credentials.refresh_token:
        raise SystemExit("refresh_token을 받지 못했습니다. Google 계정 연결을 취소한 뒤 다시 승인하세요.")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({
        "client_id": installed["client_id"],
        "client_secret": installed["client_secret"],
        "refresh_token": credentials.refresh_token,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"완료: {OUTPUT}")
    print("이 파일은 .gitignore의 .local/ 아래에 있어 GitHub에 올라가지 않습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
