#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
download_drive_folder.py
─────────────────────────────────────────────────────────────
서비스 계정으로 구글 드라이브 폴더 안의 파일들을 로컬로 내려받는다.
실행할 때마다 폴더를 다시 조회하기 때문에, 그 사이 드라이브에 새로 추가된
파일만 자동으로 추가 다운로드된다(이미 받은 파일은 이름+용량이 같으면
건너뜀 - 재실행해도 매번 전체를 다시 받지 않음).

사용법:
    pip install google-api-python-client google-auth

    python scripts/download_drive_folder.py \\
        "https://drive.google.com/drive/folders/폴더ID" \\
        "C:\\suno_local" \\
        --creds "C:\\Users\\huh03\\Downloads\\k-visa365-com-....json"

(폴더 URL 대신 폴더 ID만 넣어도 됨)
"""
import os
import re
import io
import sys
import argparse


def extract_folder_id(s):
    m = re.search(r"/folders/([a-zA-Z0-9_-]+)", s)
    return m.group(1) if m else s.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", help="드라이브 폴더 URL 또는 폴더 ID")
    ap.add_argument("out_dir", help="로컬에 저장할 폴더")
    ap.add_argument("--creds", required=True, help="서비스 계정 JSON 키 파일 경로")
    args = ap.parse_args()

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseDownload
    except ImportError:
        print("먼저 설치: pip install google-api-python-client google-auth")
        raise SystemExit(1)

    folder_id = extract_folder_id(args.folder)
    os.makedirs(args.out_dir, exist_ok=True)

    creds = service_account.Credentials.from_service_account_file(
        args.creds, scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    service = build("drive", "v3", credentials=creds)

    existing = {}
    for f in os.listdir(args.out_dir):
        p = os.path.join(args.out_dir, f)
        if os.path.isfile(p):
            existing[f] = os.path.getsize(p)

    page_token = None
    total = downloaded = skipped = 0
    while True:
        resp = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="nextPageToken, files(id, name, size, mimeType)",
            pageSize=1000,
            pageToken=page_token,
        ).execute()

        for f in resp.get("files", []):
            total += 1
            name, fid = f["name"], f["id"]
            size = int(f.get("size", 0) or 0)

            if name in existing and existing[name] == size and size > 0:
                skipped += 1
                continue

            print(f"[{total}] 다운로드: {name} ({size/1024/1024:.1f}MB)")
            path = os.path.join(args.out_dir, name)
            try:
                request = service.files().get_media(fileId=fid)
                with io.FileIO(path, "wb") as fh:
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while not done:
                        _, done = downloader.next_chunk()
                downloaded += 1
            except Exception as e:
                print(f"   ⚠️ 실패: {e}")

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    print(f"\n완료 — 드라이브 파일 총 {total}개 / 새로 받음 {downloaded}개 / "
          f"이미 있어서 건너뜀 {skipped}개")
    print(f"저장 위치: {args.out_dir}")


if __name__ == "__main__":
    main()
