#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lookup_youtube_handles_public.py
─────────────────────────────────────────────────────────────
읽기 전용, OAuth 불필요. YOUTUBE_API_KEY(공개 API 키)로 forHandle
조회만 한다 — apply_thumbnail_bank_to_live_videos.py와 같은 방식.

2026-09-27: archive 채널 10개 키의 실제 신원을 OAuth channels.list로
확인하려 했으나 전부 스코프 부족(403)으로 실패(discover_archive_
channel_identities.py). Chairman이 계정선택 화면에서 직접 확인한
후보 이름들과, config/youtube_channels.json에 이미 3주 전 기록된
핸들(NASA_XFILES 등)이 서로 다름 — 어느 쪽이 실제 존재하는 채널인지
공개 API로 교차 확인한다. 이 결과 자체가 OAuth 시크릿과 채널을
연결해주진 않지만(그건 여전히 사람 확인이 필요), 적어도 "그 이름의
채널이 실제로 존재하는지/그 채널ID가 뭔지"는 이걸로 확정할 수 있다.
"""
import json
import os
from pathlib import Path

import requests

API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

CANDIDATES = [
    # config/youtube_channels.json에 이미 기록된 핸들 (2026-09-05 스냅샷)
    "NASA_XFILES", "HISTORY_TV_TODAY", "INVENTION_STORY1", "OLD_HOLLYWOOD1", "RETRO_USA1",
    # 2026-09-27 계정선택 화면 스크린샷에 보인 _JOURNAL 브랜드
    "NASA_SPACE_JOURNAL", "HISTORY_TODAY_JOURNAL", "SCIENCE_FACTS_JOURNAL", "ClassicalJournal",
    "MYTH_LEGEND_JOURNAL", "INVENTION_JOURNAL", "AMERICAN_ARCHIVE_JOURNAL", "SILENT_ERA_JOURNAL",
    "RETRO_REELS_JOURNAL", "CLASSIC_READS_JOURNAL",
    # 시크릿 이름 그대로일 가능성 (Chairman 표에서 "이름 그대로"라고 한 4개)
    "AMERICAN_ARCHIVE_TIMES", "SILENT_ERA_TIMES", "RETRO_REELS_TIMES", "CLASSIC_READS_TIMES",
    # 8차 사고에서 이미 확인된 실제 채널(교차검증용 baseline)
    "French_Survival", "FrenchSurvival",
    # 2026-09-27 "LondonProject_Gemini"가 주장한 매핑 교차검증용 (Chairman이 그대로
    # 붙여넣어 전달함 — 실제 API로 확인 안 하면 신뢰 불가, 검증 없이 받아들이지 않는다)
    "Studio_k3", "kpop_studio7", "cafe_romantic", "cafe_healing1", "Starbucksvibes", "cafe_mozart",
    "SIS_GermanSurvival", "SIS_FrenchSurvival", "SIS_ItalianSurvival", "SIS_VietnameseSurvival",
    "SIS_SpanishSurvival", "SIS_ChineseSurvival", "Portuguese_survival", "English_survival",
    "seoul_japanese", "sis_languagecenter",
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
            return {"handle": handle, "found": False, "raw_error": data.get("error", {}).get("message", "")}
        item = items[0]
        return {
            "handle": handle,
            "found": True,
            "channel_id": item.get("id", ""),
            "title": item.get("snippet", {}).get("title", ""),
            "subscriber_count": item.get("statistics", {}).get("subscriberCount", ""),
            "video_count": item.get("statistics", {}).get("videoCount", ""),
        }
    except Exception as e:
        return {"handle": handle, "found": False, "raw_error": str(e)}


# 2026-09-27 "런던프로젝트GPT"가 25개 최종 확정본이라며 준 표를 그대로 안 믿고
# channel_id로 역조회해서 "지금 이 순간" 그 ID의 진짜 handle/title이 뭔지 확인한다.
# forHandle은 이름을 아는 상태에서 존재 확인용이고, id로 조회하면 모호함이 없다.
ID_CHECKS = [
    ("UCmt8f9yUT6iTxBys8eH4-Cg", "GPT 주장: SIS_FrenchSurvival / 내가 방금 찾은 값: AMERICAN_ARCHIVE_JOURNAL"),
    ("UCRZ0uc_bxKDMwz3noBBi9KQ", "GPT 주장: SIS_VietnameseSurvival / 내가 방금 찾은 값: ClassicalJournal"),
    ("UCKvKhETLGPaRV3qfWv2bM2g", "GPT 주장: Portuguese_survival / 내가 방금 찾은 값: SCIENCE_FACTS_JOURNAL"),
    ("UCGTd7RhfaUaGGbVRsNPUN6Q", "GPT 주장: SIS_ChineseSurvival / 미확인(처음 조회)"),
    ("UCKF98zgzm7YRWlyMaoJJKIQ", "GPT 주장: SIS_GermanSurvival / 내가 방금 찾은 값: CLASSIC_READS_JOURNAL"),
]


def lookup_by_id(channel_id):
    try:
        r = requests.get(
            "https://youtube.googleapis.com/youtube/v3/channels",
            params={"part": "snippet,statistics", "id": channel_id, "key": API_KEY},
            timeout=20,
        )
        data = r.json()
        items = data.get("items", [])
        if not items:
            return {"channel_id": channel_id, "found": False}
        item = items[0]
        return {
            "channel_id": channel_id,
            "found": True,
            "handle": item.get("snippet", {}).get("customUrl", ""),
            "title": item.get("snippet", {}).get("title", ""),
            "subscriber_count": item.get("statistics", {}).get("subscriberCount", ""),
        }
    except Exception as e:
        return {"channel_id": channel_id, "found": False, "raw_error": str(e)}


def main():
    if not API_KEY:
        log("❌ YOUTUBE_API_KEY 없음 — 공개 조회 불가")
        raise SystemExit(1)
    results = [lookup(h) for h in CANDIDATES]
    for r in results:
        if r["found"]:
            log(f"✅ @{r['handle']} → \"{r['title']}\" ({r['channel_id']}) "
                f"구독자 {r.get('subscriber_count','?')} 영상 {r.get('video_count','?')}")
        else:
            log(f"⬜ @{r['handle']}: 존재하지 않음 또는 조회 실패 ({r.get('raw_error','')})")

    log("")
    log("=== channel_id 역조회 (GPT 주장 교차검증) ===")
    id_results = []
    for cid, note in ID_CHECKS:
        r = lookup_by_id(cid)
        id_results.append({**r, "note": note})
        if r["found"]:
            log(f"🔎 {cid} → 지금 실제 handle=@{r['handle']} title=\"{r['title']}\" 구독자={r.get('subscriber_count','?')}  [{note}]")
        else:
            log(f"⬜ {cid}: 조회 실패  [{note}]")

    Path("artifacts").mkdir(parents=True, exist_ok=True)
    Path("artifacts/youtube_handle_lookup.json").write_text(
        json.dumps({"handle_lookup": results, "id_lookup": id_results}, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
