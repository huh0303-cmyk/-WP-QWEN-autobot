#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TikTok 자동 업로드 (Content Posting API, 초안함으로 전송 -> 최종 게시는 본인)
필요 Secrets: ML_TIKTOK_CLIENT_KEY, ML_TIKTOK_CLIENT_SECRET, ML_TIKTOK_ACCESS_TOKEN
"""
import os, requests
from common import list_videos, SOCIAL_LANGS
import report

API = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"

def upload_one(access_token, path, title):
    size = os.path.getsize(path)
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    body = {"source_info": {"source": "FILE_UPLOAD", "video_size": size,
                             "chunk_size": size, "total_chunk_count": 1}}
    r = requests.post(API, headers=headers, json=body, timeout=30)
    r.raise_for_status()
    data = r.json().get("data", {})
    upload_url = data.get("upload_url")
    if not upload_url:
        raise RuntimeError(f"upload_url 없음: {r.text}")
    with open(path, "rb") as f:
        content = f.read()
    r2 = requests.put(upload_url, headers={
        "Content-Range": f"bytes 0-{size-1}/{size}", "Content-Type": "video/mp4",
    }, data=content, timeout=600)
    r2.raise_for_status()
    return data.get("publish_id")

def main():
    videos = list_videos(SOCIAL_LANGS)
    if not videos:
        print("업로드할 영상이 없습니다"); return
    token = os.environ.get("ML_TIKTOK_ACCESS_TOKEN")
    if not token:
        print("ML_TIKTOK_ACCESS_TOKEN 미설정 - 틱톡 업로드 건너뜀")
        return
    for lang, path, title, desc in videos:
        try:
            pid = upload_one(token, path, title)
            print(f"[TikTok][{lang}] 초안함 전송 완료: {pid}")
            report.add("TikTok", lang, "success", str(pid))
        except Exception as e:
            print(f"[TikTok][{lang}] 업로드 실패: {e}")
            report.add("TikTok", lang, "fail", str(e))

if __name__ == "__main__":
    main()
