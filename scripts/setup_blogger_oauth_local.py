#!/usr/bin/env python3
"""Issue a Blogger-only refresh token without replacing shared Drive OAuth.

This must be run interactively on the operator's local computer. The resulting
file is stored below git-ignored ``.local/`` and token values are never printed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / ".local" / "blogger_oauth.json"
SCOPES = ["https://www.googleapis.com/auth/blogger"]


def load_desktop_client(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    installed = raw.get("installed")
    if not installed or not installed.get("client_id") or not installed.get("client_secret"):
        raise ValueError("'데스크톱 앱' 유형의 OAuth 클라이언트 JSON이 아닙니다.")
    return installed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Blogger 쓰기 전용 OAuth refresh token을 로컬에서 발급합니다."
    )
    parser.add_argument("client_json", help="Google Cloud 데스크톱 앱 OAuth JSON 경로")
    args = parser.parse_args()
    source = Path(args.client_json).expanduser().resolve()
    if not source.is_file():
        raise SystemExit(f"파일을 찾을 수 없습니다: {source}")

    try:
        installed = load_desktop_client(source)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc

    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(str(source), SCOPES)
    credentials = flow.run_local_server(
        port=0,
        open_browser=True,
        prompt="consent",
        access_type="offline",
        include_granted_scopes="true",
    )
    if not credentials.refresh_token:
        raise SystemExit(
            "refresh_token을 받지 못했습니다. Google 계정의 기존 앱 연결을 "
            "취소한 뒤 prompt=consent로 다시 승인하세요."
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(
            {
                "client_id": installed["client_id"],
                "client_secret": installed["client_secret"],
                "refresh_token": credentials.refresh_token,
                "scopes": SCOPES,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"발급 완료: {OUTPUT}")
    print("토큰 값은 출력하지 않았습니다. 이 파일은 .gitignore의 .local/ 아래에 있습니다.")
    print("GitHub Secrets에는 BLOGGER_GOOGLE_CLIENT_ID, BLOGGER_GOOGLE_CLIENT_SECRET, BLOGGER_GOOGLE_REFRESH_TOKEN으로 등록하세요.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
