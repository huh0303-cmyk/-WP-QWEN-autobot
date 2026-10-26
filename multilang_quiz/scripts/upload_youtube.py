#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube 업로드 — 항상 비공개로 올리고 자동 공개 전환은 하지 않는다.
사용자가 스튜디오에서 직접 확인하고 공개 버튼을 눌러야만 실제로 게시된다
(예전엔 publishAt을 지정해 업로드 후 일정 시간 뒤 자동 공개되도록 되어
있었는데, 이게 사용자 승인 없이 그대로 발행돼버리는 문제라 제거함).

2026-08-02: 언어별 전용 토큰(YOUTUBE_OAUTH_REFRESH_TOKEN_{LANG})이 없을 때
공용 fallback 토큰으로 조용히 넘어가던 로직을 제거했다. 그 fallback이 엉뚱한
채널(스타벅스 플리 채널)을 가리키고 있어서 9개 언어가 전부 그 채널 하나로
뒤섞여 올라간 사고가 있었음. 이제 채널 토큰이 없으면 그 언어는 그냥
건너뛴다 — "정해진 채널에만 발행" 원칙을 코드로 강제.

2026-08-14 채널 구조 확정(사용자 확인): 언어마다 별도 채널이 아니라 딱 2개
채널로 나뉜다 — 영어는 English_Survival 전용 채널, 나머지 8개 언어
(일본어/스페인어/베트남어/프랑스어/독일어/중국어/아랍어/러시아어)는 전부
SIS-Language Center 채널 하나로 합쳐서 올린다.

필요 Secrets: ML_YT_CLIENT_ID/ML_YT_CLIENT_SECRET (또는 YOUTUBE_OAUTH_CLIENT_ID/SECRET,
공용 재사용 가능) + YOUTUBE_OAUTH_REFRESH_TOKEN_ENGLISH_BROAD(English_Survival) +
YOUTUBE_OAUTH_REFRESH_TOKEN_STUDIOSTARBUCKS_BROAD(SIS-Language Center — 옛 코드네임
"Studio_starbucks" 그대로 시크릿명에 남아있음, 나머지 8개 언어 공용).
2026-08-14 실제 토큰으로 채널 신원 직접 검증 완료(channels.list API 호출) —
TOPIK_BROAD→@seoultopik, ENGLISH_BROAD→@english_survival,
STUDIOSTARBUCKS_BROAD→@sis_languagecenter, STARBUCKS_BROAD(다른 것!)→@starbucksvibes
(플레이리스트 채널, 이 퀴즈 파이프라인과 무관 — 이름이 비슷해서 헷갈리기 쉬움).
"""
import os, sys, datetime, random, time, requests, hashlib, re
from common import list_videos, SOCIAL_LANGS, get_secret
import report

# 언어 → 실제 채널 토큰 시크릿 이름 매핑 (영어만 자기 채널, 나머지는 전부 SIS로)
CHANNEL_TOKEN_KEY = {"en": "ENGLISH_BROAD"}
_DEFAULT_TOKEN_KEY = "STUDIOSTARBUCKS_BROAD"

# 채널별 업로드 시각을 서로 다르게 분산시킨다 (2026-08-03 사용자 지시:
# "다 각각 채널로 가는거다. 시간도 다 다르게.." - 여러 채널이 똑같은 순간에
# 몰아서 업로드되면 봇처럼 보이므로, 언어 사이마다 랜덤 대기를 둔다).
# 수동 실행(workflow_dispatch)일 때는 빠른 확인을 위해 대기를 건너뛴다.
UPLOAD_GAP_MIN_SEC = 300    # 5분
UPLOAD_GAP_MAX_SEC = 2700   # 45분

def get_access_token(lang):
    # 정해진 채널의 토큰만 사용한다 — 엉뚱한 채널로 뒤섞여 올라가는 사고를
    # 코드 차원에서 원천 차단(2026-08-14: en→English_Survival, 나머지 전부→SIS).
    token_key = CHANNEL_TOKEN_KEY.get(lang, _DEFAULT_TOKEN_KEY)
    refresh_token = get_secret(f"YOUTUBE_OAUTH_REFRESH_TOKEN_{token_key}")
    if not refresh_token:
        return None
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": get_secret("ML_YT_CLIENT_ID", "YOUTUBE_OAUTH_CLIENT_ID"),
        "client_secret": get_secret("ML_YT_CLIENT_SECRET", "YOUTUBE_OAUTH_CLIENT_SECRET"),
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]

def content_fingerprint(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def existing_channel_fingerprints(access_token):
    """Read the channel's uploads playlist and collect our content hash markers.
    Fail closed if the API cannot verify history: never upload blindly."""
    headers = {"Authorization": f"Bearer {access_token}"}
    r = requests.get("https://www.googleapis.com/youtube/v3/channels",
                     headers=headers, params={"part": "contentDetails", "mine": "true"},
                     timeout=30)
    r.raise_for_status()
    items = r.json().get("items", [])
    if not items:
        raise RuntimeError("현재 OAuth 토큰의 채널을 확인할 수 없어 중복 검사를 중단합니다")
    playlist_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    found = set()
    page_token = None
    while True:
        params = {"part": "snippet,contentDetails", "playlistId": playlist_id,
                  "maxResults": 50}
        if page_token:
            params["pageToken"] = page_token
        page = requests.get("https://www.googleapis.com/youtube/v3/playlistItems",
                            headers=headers, params=params, timeout=30)
        page.raise_for_status()
        video_ids = [x.get("contentDetails", {}).get("videoId")
                     for x in page.json().get("items", [])]
        video_ids = [v for v in video_ids if v]
        for start in range(0, len(video_ids), 50):
            vr = requests.get("https://www.googleapis.com/youtube/v3/videos",
                              headers=headers,
                              params={"part": "snippet", "id": ",".join(video_ids[start:start+50])},
                              timeout=30)
            vr.raise_for_status()
            for video in vr.json().get("items", []):
                description = video.get("snippet", {}).get("description", "")
                found.update(re.findall(r"<!-- quiz-content-sha256:([0-9a-f]{64}) -->", description))
        page_token = page.json().get("nextPageToken")
        if not page_token:
            break
    return found

def upload_one(access_token, path, title, desc):
    size = os.path.getsize(path)
    fingerprint = content_fingerprint(path)
    marker = f"\n\n<!-- quiz-content-sha256:{fingerprint} -->"
    desc = desc + marker
    metadata = {
        "snippet": {"title": title, "description": desc, "categoryId": "27",
                    "tags": ["language learning", "vocabulary quiz", "shorts"]},
        # publishAt을 지정하지 않음 -> 계속 비공개로 남아있고, 사람이 스튜디오에서
        # 직접 확인 후 공개 버튼을 눌러야만 실제로 게시된다.
        "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False},
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Length": str(size),
        "X-Upload-Content-Type": "video/mp4",
    }
    r = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        headers=headers, json=metadata, timeout=30)
    r.raise_for_status()
    upload_url = r.headers.get("Location")
    with open(path, "rb") as f:
        r2 = requests.put(upload_url, headers={"Content-Type": "video/mp4"}, data=f, timeout=600)
    r2.raise_for_status()
    return r2.json().get("id")

def main():
    videos = list_videos(SOCIAL_LANGS)
    if not videos:
        print("업로드할 영상이 없습니다 (outputs/quiz_*_beginner.mp4)")
        return
    if not get_secret("ML_YT_CLIENT_ID", "YOUTUBE_OAUTH_CLIENT_ID"):
        print("유튜브 토큰 미설정 - 유튜브 업로드 건너뜀")
        return
    is_scheduled_run = os.environ.get("GITHUB_EVENT_NAME") == "schedule"
    uploaded_count = 0
    # Build the history once per channel; languages sharing a channel share one set.
    history_by_token = {}
    for lang, path, title, desc in videos:
        try:
            token = get_access_token(lang)
            if not token:
                token_key = CHANNEL_TOKEN_KEY.get(lang, _DEFAULT_TOKEN_KEY)
                print(f"[YouTube][{lang}] 채널 토큰(YOUTUBE_OAUTH_REFRESH_TOKEN_{token_key}) "
                      f"미설정 - 다른 채널로 잘못 올라가지 않도록 건너뜀")
                report.add("YouTube", lang, "skipped", "채널 토큰 미설정")
                continue
            token_key = CHANNEL_TOKEN_KEY.get(lang, _DEFAULT_TOKEN_KEY)
            if token_key not in history_by_token:
                try:
                    history_by_token[token_key] = existing_channel_fingerprints(token)
                except Exception as e:
                    print(f"[YouTube][{lang}] 기존 업로드 이력을 확인할 수 없어 안전을 위해 업로드 중단: {e}")
                    report.add("YouTube", lang, "skipped", "중복 검사 실패 — 안전 중단")
                    continue
            fingerprint = content_fingerprint(path)
            if fingerprint in history_by_token[token_key]:
                print(f"[YouTube][{lang}] 동일 영상 해시가 이미 채널에 있어 업로드 건너뜀: {os.path.basename(path)}")
                report.add("YouTube", lang, "skipped", "동일 콘텐츠 중복")
                continue
            if uploaded_count > 0 and is_scheduled_run:
                delay = random.randint(UPLOAD_GAP_MIN_SEC, UPLOAD_GAP_MAX_SEC)
                print(f"[YouTube] 채널별 업로드 시간 분산을 위해 {delay}초 대기 후 [{lang}] 업로드")
                time.sleep(delay)
            vid = upload_one(token, path, title, desc)
            history_by_token[token_key].add(fingerprint)
            uploaded_count += 1
            print(f"[YouTube][{lang}] 업로드 완료 (비공개 - 스튜디오에서 직접 공개 승인 필요): https://youtube.com/watch?v={vid}")
            report.add("YouTube", lang, "success", f"https://youtube.com/watch?v={vid}")
        except Exception as e:
            print(f"[YouTube][{lang}] 업로드 실패: {e}")
            report.add("YouTube", lang, "fail", str(e))

if __name__ == "__main__":
    main()
