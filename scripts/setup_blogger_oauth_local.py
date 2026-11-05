#!/usr/bin/env python3
"""Issue a combined Drive + Blogger refresh token without adding GitHub secrets.

Accepts either a Google Desktop OAuth client JSON or a previous local OAuth
token JSON containing client_id/client_secret. The resulting token stays in
git-ignored .local/ and is scope-verified before it can replace a shared secret.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / ".local" / "google_oauth_drive_blogger.json"
# Preserve the existing Drive permission while adding Blogger management.
# This allows one existing GitHub refresh-token secret to serve both APIs.
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/blogger",
]


def load_desktop_client(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    installed = raw.get("installed")
    if not installed and raw.get("client_id") and raw.get("client_secret"):
        # Reuse a previously authorized local client without reading its old
        # refresh token. This is useful when the original Desktop client JSON
        # was archived but its local OAuth credential file remains available.
        installed = {
            "client_id": raw["client_id"],
            "client_secret": raw["client_secret"],
            "auth_uri": raw.get("auth_uri", "https://accounts.google.com/o/oauth2/auth"),
            "token_uri": raw.get("token_uri", "https://oauth2.googleapis.com/token"),
            "redirect_uris": ["http://localhost"],
        }
    if not installed or not installed.get("client_id") or not installed.get("client_secret"):
        raise ValueError("OAuth client JSON or prior local OAuth credential file is required.")
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

    flow = InstalledAppFlow.from_client_config({"installed": installed}, SCOPES)
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

    # Verify the actual granted scopes before replacing the shared GitHub token.
    token_response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": installed["client_id"],
            "client_secret": installed["client_secret"],
            "refresh_token": credentials.refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    if token_response.status_code >= 400:
        raise SystemExit(f"새 refresh token 검증 실패: HTTP {token_response.status_code}")
    access_token = token_response.json()["access_token"]
    scope_response = requests.get(
        "https://oauth2.googleapis.com/tokeninfo",
        params={"access_token": access_token},
        timeout=20,
    )
    if scope_response.status_code != 200:
        raise SystemExit(f"실제 OAuth scope 확인 실패: HTTP {scope_response.status_code}")
    granted_scopes = set(scope_response.json().get("scope", "").split())
    required_scopes = set(SCOPES)
    if not required_scopes.issubset(granted_scopes):
        missing = sorted(required_scopes - granted_scopes)
        raise SystemExit("필수 scope 누락; 기존 GitHub token은 변경하지 마세요: " + ", ".join(missing))
    print("검증된 OAuth scope: " + ", ".join(sorted(granted_scopes)))

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
    print("Drive scope 보존과 Blogger scope 추가가 확인됐습니다.")
    print("새 GitHub Secret을 만들지 말고 기존 GOOGLE_OAUTH_REFRESH_TOKEN만 교체하세요.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
