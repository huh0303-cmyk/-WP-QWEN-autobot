#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lookup_final_25_channels.py
─────────────────────────────────────────────────────────────
읽기 전용, OAuth 불필요. 최종 확정 25개 채널 handle 전체를 한 번에
공개 API(forHandle)로 조회해서 channel_id, 개설일(publishedAt),
구독자수, 영상수를 한꺼번에 뽑는다. 구글시트 붙여넣기용 최종표 작성 목적.
"""
import json
import os
from pathlib import Path

import requests

API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

# (번호, 그룹, key, 후보 handle) — handle 미확정인 japanese_survival은 후보 여러 개
FINAL_25 = [
    (1, "플리", "globalmusic", "cafe_romantic"),
    (2, "플리", "healing", "cafe_healing1"),
    (3, "플리", "starbucks", "Starbucksvibes"),
    (4, "플리", "mbb", "cafe_mozart"),
    (5, "플리", "kpop", "kpop_studio7"),
    (6, "지식", "nasa", "NASA_XFILES"),
    (7, "지식", "history", "HISTORY_TV_TODAY"),
    (8, "지식", "invention", "INVENTION_STORY1"),
    (9, "지식", "silent_era", "OLD_HOLLYWOOD1"),
    (10, "지식", "retro_reels", "RETRO_USA1"),
    (11, "언어Survival", "korean_survival", "KoreanSurvival"),
    (12, "언어Survival", "japanese_survival", "seoul_japanese_survival"),
    (13, "언어Survival", "german_survival", "SIS_GermanSurvival"),
    (14, "언어Survival", "french_survival", "SIS_FrenchSurvival"),
    (15, "언어Survival", "italian_survival", "SIS_ItalianSurvival"),
    (16, "언어Survival", "spanish_survival", "SIS_SpanishSurvival"),
    (17, "언어Survival", "chinese_survival", "SIS_ChineseSurvival"),
    (18, "언어Survival", "portuguese_survival", "Portuguese_survival"),
    (19, "언어Survival", "vietnamese_survival", "SIS_VietnameseSurvival"),
    (20, "언어Survival", "english_survival", "English_survival"),
    (21, "기타", "topik", "seoul_topik1"),
    (22, "기타", "health_jp", "Health_Clinic_Japan"),
    (23, "기타", "health_usa", "health_clinic_USA"),
    (24, "기타", "shopping1", "jisoopicks"),
    (25, "기타", "shopping2", "sis_languagecenter"),
]

# japanese_survival handle 미확정이라 여러 후보 추가 시도
JAPANESE_CANDIDATES = [
    "seoul_japanese_survival", "SIS_JapaneseSurvival", "seoul_japanese",
    "Japanese_survival", "JapaneseSurvival",
]

SHOPPING2_CANDIDATES = [
    "sis_languagecenter", "SIS_LanguageCenter", "SIS_Language", "sis_language",
    "SISLanguageCenter", "seoul_language_center", "SIS_Languagecenter",
]


def log(msg):
    print(msg, flush=True)


def lookup(handle):
    try:
        r = requests.get(
            "https://youtube.googleapis.com/youtube/v3/channels",
            params={"part": "snippet,statistics", "forHandle": handle, "key": API_KEY},
            timeout=20,
        )
        data = r.json()
        items = data.get("items", [])
        if not items:
            return {"handle": handle, "found": False}
        item = items[0]
        snip = item.get("snippet", {})
        stats = item.get("statistics", {})
        return {
            "handle": handle,
            "found": True,
            "channel_id": item.get("id", ""),
            "title": snip.get("title", ""),
            "published_at": snip.get("publishedAt", ""),
            "subscriber_count": stats.get("subscriberCount", ""),
            "video_count": stats.get("videoCount", ""),
        }
    except Exception as e:
        return {"handle": handle, "found": False, "raw_error": str(e)}


def main():
    if not API_KEY:
        log("NO_API_KEY")
        raise SystemExit(1)

    results = []
    for num, group, key, handle in FINAL_25:
        r = lookup(handle)
        r.update({"num": num, "group": group, "key": key})
        results.append(r)
        if r["found"]:
            log(f"OK\t{num}\t{group}\t{key}\t@{r['handle']}\t{r['title']}\t{r['channel_id']}\t{r['published_at']}\t{r['subscriber_count']}\t{r['video_count']}")
        else:
            log(f"MISS\t{num}\t{group}\t{key}\t@{handle}")

    # japanese_survival 후보 추가 시도 (12번이 못 찾았을 경우 대비)
    jp_result = next((r for r in results if r["key"] == "japanese_survival"), None)
    jp_extra = []
    if jp_result and not jp_result["found"]:
        for cand in JAPANESE_CANDIDATES:
            r = lookup(cand)
            jp_extra.append(r)
            if r["found"]:
                log(f"JP_CANDIDATE_OK\t@{r['handle']}\t{r['title']}\t{r['channel_id']}\t{r['published_at']}\t{r['subscriber_count']}\t{r['video_count']}")
            else:
                log(f"JP_CANDIDATE_MISS\t@{cand}")

    shop2_result = next((r for r in results if r["key"] == "shopping2"), None)
    shop2_extra = []
    if shop2_result and not shop2_result["found"]:
        for cand in SHOPPING2_CANDIDATES:
            r = lookup(cand)
            shop2_extra.append(r)
            if r["found"]:
                log(f"SHOP2_CANDIDATE_OK\t@{r['handle']}\t{r['title']}\t{r['channel_id']}\t{r['published_at']}\t{r['subscriber_count']}\t{r['video_count']}")
            else:
                log(f"SHOP2_CANDIDATE_MISS\t@{cand}")

    Path("artifacts").mkdir(parents=True, exist_ok=True)
    Path("artifacts/final_25_channel_report.json").write_text(
        json.dumps({"results": results, "japanese_extra": jp_extra, "shopping2_extra": shop2_extra}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
