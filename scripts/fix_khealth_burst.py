#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_khealth_burst.py
─────────────────────────────────────────────────────────────
2026-08-28: khealth-restore.yml이 apply_changes=true로 실행되며
draft/private 상태였던 글 43개를 오늘 12:26~12:27 KST 사이(83초)에
한꺼번에 publish로 되돌렸다. "하루 1포스팅" 원칙 위반 + 깨진 글 1개
(AI 플레이스홀더 응답이 그대로 발행) + 중복/유사중복 글 7쌍 포함.

처리:
  1) 깨진 글 1개 + 중복쌍 중 7개 → status=private로 되돌림
  2) 남은 35개 중 1개만 오늘 날짜 유지, 나머지 34개는 내일부터
     하루 1개씩 미래 날짜(status=future)로 재배치
"""
import os
import random
import sys
from datetime import datetime, timedelta

import requests

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SITE_URL = "https://k-health365.com"
WP_USER = "huh0303@gmail.com"
WP_PASS = os.environ.get("KHEALTH365COM", "")

# 깨진 글 1개 + 중복쌍에서 제거할 7개(더 지저분한 슬러그/나중 것 기준)
PRIVATE_IDS = [3353, 3484, 3377, 3419, 3446, 3440, 3449, 3464]

# 나머지 35개(오늘 버스트 발행분 - 위 8개 제외), id 오름차순
KEEP_IDS = [
    3356, 3359, 3362, 3365, 3368, 3371, 3374, 3380, 3383, 3386,
    3389, 3392, 3395, 3398, 3401, 3404, 3407, 3410, 3413, 3416,
    3422, 3425, 3428, 3431, 3434, 3437, 3443, 3452, 3455, 3458,
    3461, 3471, 3474, 3478, 3487,
]

KST = timedelta(hours=9)


def set_private(post_id: int) -> None:
    r = requests.post(
        f"{SITE_URL}/wp-json/wp/v2/posts/{post_id}",
        auth=(WP_USER, WP_PASS), json={"status": "private"}, timeout=30,
    )
    r.raise_for_status()
    print(f"  🔒 id={post_id} → private")


def schedule(post_id: int, target_date_kst: datetime, keep_today: bool) -> None:
    date_gmt = target_date_kst - KST
    data = {
        "date": target_date_kst.strftime("%Y-%m-%dT%H:%M:%S"),
        "date_gmt": date_gmt.strftime("%Y-%m-%dT%H:%M:%S"),
        "status": "publish" if keep_today else "future",
    }
    r = requests.post(
        f"{SITE_URL}/wp-json/wp/v2/posts/{post_id}",
        auth=(WP_USER, WP_PASS), json=data, timeout=30,
    )
    r.raise_for_status()
    tag = "publish(오늘)" if keep_today else "future(예약)"
    print(f"  📅 id={post_id} → {tag} {target_date_kst.strftime('%Y-%m-%d %H:%M')}")


def main():
    if not WP_PASS:
        print("❌ KHEALTH365COM 시크릿 없음")
        sys.exit(1)

    print(f"1) 비공개 전환 ({len(PRIVATE_IDS)}개: 깨진 글 1 + 중복쌍 7)")
    for pid in PRIVATE_IDS:
        set_private(pid)

    print(f"\n2) 날짜 재배치 ({len(KEEP_IDS)}개: 오늘 1개 + 이후 하루 1개씩)")
    now_kst = datetime.utcnow() + KST
    today_9am = now_kst.replace(hour=9, minute=0, second=0, microsecond=0)

    rng = random.Random(20260828)
    for i, pid in enumerate(KEEP_IDS):
        if i == 0:
            schedule(pid, now_kst, keep_today=True)
            continue
        day_offset = i  # +1일차부터 순차
        hour = rng.randint(9, 20)
        minute = rng.randint(0, 59)
        target = (today_9am + timedelta(days=day_offset)).replace(hour=hour, minute=minute)
        schedule(pid, target, keep_today=False)

    print("\n✅ 완료")


if __name__ == "__main__":
    main()
