#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""(1회성) MBB 채널 원곡 폴더에 실제 어떤 파일이 있는지 목록만 출력한다. 읽기 전용."""
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

FOLDER_ID = os.environ.get("MUSIC_SOURCE_FOLDER_ID_MBB") or os.environ.get(
    "MUSIC_SOURCE_FOLDER_ID", "1RqL44lM5oUSW5_PAZLHHlevrVkr1ibxd")


def main():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_OAUTH_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GOOGLE_OAUTH_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_OAUTH_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    service = build("drive", "v3", credentials=creds)
    print(f"폴더 ID: {FOLDER_ID}")
    page_token = None
    n = 0
    while True:
        resp = service.files().list(
            q=f"'{FOLDER_ID}' in parents and trashed=false",
            fields="nextPageToken, files(id, name, mimeType, size)",
            pageToken=page_token, pageSize=200,
        ).execute()
        for f in resp.get("files", []):
            n += 1
            size_mb = int(f.get("size", 0) or 0) / 1024 / 1024
            print(f"  {n:3d}. {f['name']} ({size_mb:.1f}MB)")
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    print(f"총 {n}개 파일")


if __name__ == "__main__":
    main()
