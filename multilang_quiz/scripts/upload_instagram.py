#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Instagram 릴스 업로드 (Business/Creator 계정 + Facebook 페이지 연결 필요, 앱 심사 필요)
video_urls.txt(lang|url)를 읽어 공개 URL 기반으로 업로드합니다.
필요 Secrets: ML_IG_USER_ID, ML_IG_ACCESS_TOKEN
"""
import os, time, requests
from common import META, get_secret
import report

def read_urls():
    if not os.path.exists("video_urls.txt"):
        return {}
    result = {}
    with open("video_urls.txt") as f:
        for line in f:
            line = line.strip()
            if not line or "|" not in line:
                continue
            lang, url = line.split("|", 1)
            result[lang] = url
    return result

def upload_one(ig_user_id, token, video_url, caption):
    r = requests.post(f"https://graph.facebook.com/v19.0/{ig_user_id}/media", data={
        "media_type": "REELS", "video_url": video_url, "caption": caption, "access_token": token,
    }, timeout=60)
    if not r.ok:
        raise RuntimeError(f"{r.status_code} {r.text[:400]}")
    creation_id = r.json()["id"]

    for _ in range(30):
        status = requests.get(f"https://graph.facebook.com/v19.0/{creation_id}",
                               params={"fields": "status_code", "access_token": token}, timeout=30).json()
        if status.get("status_code") == "FINISHED":
            break
        time.sleep(10)

    r2 = requests.post(f"https://graph.facebook.com/v19.0/{ig_user_id}/media_publish", data={
        "creation_id": creation_id, "access_token": token,
    }, timeout=60)
    if not r2.ok:
        raise RuntimeError(f"{r2.status_code} {r2.text[:400]}")
    return r2.json().get("id")

def main():
    urls = read_urls()
    if not urls:
        print("video_urls.txt 없음 - 공개 URL 준비 필요 (prepare_public_urls.py 먼저 실행)")
        return
    ig_user_id = get_secret("ML_IG_USER_ID", "IG_USER_ID")
    token = get_secret("ML_IG_ACCESS_TOKEN", "IG_ACCESS_TOKEN")
    if not ig_user_id or not token:
        print("ML_IG_USER_ID / ML_IG_ACCESS_TOKEN 미설정 - 인스타그램 업로드 건너뜀")
        return
    for lang, url in urls.items():
        caption = META.get(lang, {}).get("desc", "")
        try:
            mid = upload_one(ig_user_id, token, url, caption)
            print(f"[Instagram][{lang}] 업로드 완료: {mid}")
            report.add("Instagram", lang, "success", str(mid))
        except Exception as e:
            print(f"[Instagram][{lang}] 업로드 실패: {e}")
            report.add("Instagram", lang, "fail", str(e))

if __name__ == "__main__":
    main()
