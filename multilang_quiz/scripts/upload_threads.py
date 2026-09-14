#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Threads 업로드 (앱 심사 필요)
video_urls.txt(lang|url)를 읽어 공개 URL 기반으로 업로드합니다.
필요 Secrets: ML_THREADS_USER_ID, ML_THREADS_ACCESS_TOKEN
"""
import os, time, requests
from common import META
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

def upload_one(user_id, token, video_url, text):
    r1 = requests.post(f"https://graph.threads.net/v1.0/{user_id}/threads", data={
        "media_type": "VIDEO", "video_url": video_url, "text": text, "access_token": token,
    }, timeout=60)
    r1.raise_for_status()
    creation_id = r1.json()["id"]

    for _ in range(30):
        status = requests.get(f"https://graph.threads.net/v1.0/{creation_id}",
                               params={"fields": "status", "access_token": token}, timeout=30).json()
        if status.get("status") == "FINISHED":
            break
        time.sleep(10)

    r2 = requests.post(f"https://graph.threads.net/v1.0/{user_id}/threads_publish", data={
        "creation_id": creation_id, "access_token": token,
    }, timeout=60)
    r2.raise_for_status()
    return r2.json().get("id")

def main():
    urls = read_urls()
    if not urls:
        print("video_urls.txt 없음 - 공개 URL 준비 필요 (prepare_public_urls.py 먼저 실행)")
        return
    user_id = os.environ.get("ML_THREADS_USER_ID")
    token = os.environ.get("ML_THREADS_ACCESS_TOKEN")
    if not user_id or not token:
        print("ML_THREADS_USER_ID / ML_THREADS_ACCESS_TOKEN 미설정 - 스레드 업로드 건너뜀")
        return
    for lang, url in urls.items():
        text = META.get(lang, {}).get("title", "")
        try:
            mid = upload_one(user_id, token, url, text)
            print(f"[Threads][{lang}] 업로드 완료: {mid}")
            report.add("Threads", lang, "success", str(mid))
        except Exception as e:
            print(f"[Threads][{lang}] 업로드 실패: {e}")
            report.add("Threads", lang, "fail", str(e))

if __name__ == "__main__":
    main()
