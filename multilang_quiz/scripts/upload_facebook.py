#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Facebook 페이지 영상 업로드 — 미게시(published=false) 상태로 올려서
페이지 콘텐츠 도구에 임시글로만 저장되고, 사람이 직접 게시해야 실제로 보임.
필요 Secrets: ML_FB_PAGE_ID, ML_FB_PAGE_ACCESS_TOKEN
"""
import os, requests
from common import list_videos, SOCIAL_LANGS, get_secret
import report

def upload_one(page_id, token, path, title, desc):
    url = f"https://graph-video.facebook.com/v19.0/{page_id}/videos"
    with open(path, "rb") as f:
        files = {"source": f}
        data = {"access_token": token, "description": f"{title}\n\n{desc}", "published": "false"}
        r = requests.post(url, data=data, files=files, timeout=600)
    if not r.ok:
        raise RuntimeError(f"{r.status_code} {r.text[:400]}")
    return r.json().get("id")

def main():
    videos = list_videos(SOCIAL_LANGS)
    if not videos:
        print("업로드할 영상이 없습니다"); return
    page_id = get_secret("ML_FB_PAGE_ID", "FB_PAGE_ID", "FACEBOOK_PAGE_ID")
    token = get_secret("ML_FB_PAGE_ACCESS_TOKEN", "FB_PAGE_ACCESS_TOKEN")
    if not page_id or not token:
        print("ML_FB_PAGE_ID / ML_FB_PAGE_ACCESS_TOKEN 미설정 - 페이스북 업로드 건너뜀")
        return
    for lang, path, title, desc in videos:
        try:
            vid = upload_one(page_id, token, path, title, desc)
            print(f"[Facebook][{lang}] 업로드 완료: {vid}")
            report.add("Facebook", lang, "success", str(vid))
        except Exception as e:
            print(f"[Facebook][{lang}] 업로드 실패: {e}")
            report.add("Facebook", lang, "fail", str(e))

if __name__ == "__main__":
    main()
