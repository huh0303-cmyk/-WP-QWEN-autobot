#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Instagram/Threads는 로컬 파일이 아닌 '공개 URL'을 요구합니다.
그래서 생성된 mp4를 GitHub Release 애셋으로 올리고, 그 다운로드 URL을
video_urls.txt (lang|url 형식)에 기록해서 이후 스텝들이 읽어 쓰게 합니다.

필요 환경변수: GITHUB_TOKEN, GITHUB_REPOSITORY (Actions에서 자동 제공)
"""
import os, sys, time, requests
from common import list_videos, SOCIAL_LANGS

def main():
    videos = list_videos(SOCIAL_LANGS)
    if not videos:
        print("업로드할 영상이 없습니다"); return

    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        print("GITHUB_TOKEN/GITHUB_REPOSITORY 없음 - 공개 URL 생성 건너뜀")
        return

    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    tag = f"quiz-{int(time.time())}"
    r = requests.post(f"https://api.github.com/repos/{repo}/releases", headers=headers, json={
        "tag_name": tag, "name": f"Quiz videos {tag}", "body": "자동 생성된 다국어 단어 퀴즈 영상",
    }, timeout=30)
    r.raise_for_status()
    release_id = r.json()["id"]

    lines = []
    for lang, path, title, desc in videos:
        fname = os.path.basename(path)
        upload_url = f"https://uploads.github.com/repos/{repo}/releases/{release_id}/assets?name={fname}"
        with open(path, "rb") as f:
            ru = requests.post(upload_url, headers={**headers, "Content-Type": "video/mp4"},
                                data=f.read(), timeout=300)
        ru.raise_for_status()
        url = ru.json()["browser_download_url"]
        lines.append(f"{lang}|{url}")
        print(f"[Release] {lang} -> {url}")

    with open("video_urls.txt", "w") as f:
        f.write("\n".join(lines) + "\n")

if __name__ == "__main__":
    main()
