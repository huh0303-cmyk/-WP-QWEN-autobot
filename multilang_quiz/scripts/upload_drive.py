#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
생성된 mp4를 언어별 구글드라이브 폴더에 저장.
- 서비스 계정(Service Account) 방식 사용 (GitHub Actions는 사람이 로그인할 수 없어서
  브라우저 OAuth 대신 서비스 계정 키로 인증)
- 각 폴더는 미리 그 서비스 계정 이메일에 "편집자"로 공유되어 있어야 함

필요 Secret: ML_GDRIVE_SERVICE_ACCOUNT_JSON (서비스 계정 키 JSON 파일 내용 전체를 그대로 붙여넣기)
"""
import os, json, datetime, requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from common import list_videos
from drive_folders import DRIVE_FOLDERS, LANG_FILE_CODE
import report

SCOPES = ["https://www.googleapis.com/auth/drive"]

def get_access_token():
    raw = os.environ.get("ML_GDRIVE_SERVICE_ACCOUNT_JSON")
    if not raw:
        return None
    info = json.loads(raw)
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    creds.refresh(Request())
    return creds.token

def upload_one(access_token, path, folder_id, filename):
    metadata = {"name": filename, "parents": [folder_id]}
    boundary = "sisTopikBoundary"
    with open(path, "rb") as f:
        media = f.read()

    body = (
        f"--{boundary}\r\n"
        f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{json.dumps(metadata)}\r\n"
        f"--{boundary}\r\n"
        f"Content-Type: video/mp4\r\n\r\n"
    ).encode("utf-8") + media + f"\r\n--{boundary}--".encode("utf-8")

    r = requests.post(
        "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": f"multipart/related; boundary={boundary}",
        },
        data=body, timeout=300,
    )
    r.raise_for_status()
    return r.json().get("id")

def main():
    videos = list_videos()
    if not videos:
        print("업로드할 영상이 없습니다"); return

    token = get_access_token()
    if not token:
        print("ML_GDRIVE_SERVICE_ACCOUNT_JSON 미설정 - 구글드라이브 업로드 건너뜀")
        return

    # 파일명 규칙: MM-DD-YYYY-언어코드.mp4 (예: 07-31-2026-JP.mp4)
    date_str = datetime.datetime.now().strftime("%m-%d-%Y")

    for lang, path, title, desc in videos:
        folder_id = DRIVE_FOLDERS.get(lang)
        code = LANG_FILE_CODE.get(lang, lang.upper())
        if not folder_id:
            print(f"[Drive][{lang}] 폴더 ID 없음 - 건너뜀")
            continue
        fname = f"{date_str}-{code}.mp4"
        try:
            file_id = upload_one(token, path, folder_id, fname)
            print(f"[Drive][{lang}] 저장 완료: {fname} (file_id={file_id})")
            report.add("Google Drive", lang, "success", fname)
        except Exception as e:
            print(f"[Drive][{lang}] 저장 실패: {e}")
            report.add("Google Drive", lang, "fail", str(e))

if __name__ == "__main__":
    main()
