#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2026-08-23: 지식채널 5개(NASA_XFILES/HISTORY_TV_TODAY/INVENTION_STORY/
SILENT_ERA_FILM/RETRO_USA1)를 "채널당 주3회 고정 요일" 대신 "채널당 2~3일
간격으로 한 번에 하나씩, 랜덤 시각"으로 바꾼 스케줄러. publish_scheduler.py
(27개 블로그의 "사이트마다 오늘의 랜덤 목표시각" 패턴)와 동일한 방식을
채널 5개에 적용 — 15분마다 이 스크립트를 돌려서, 채널마다 "다음 발행
예정일"이 지났고 오늘의 랜덤 목표시각도 지난 채널만 curio-longform-daily.yml을
workflow_dispatch(channel=<key>)로 발사한다. 발사 후 그 채널의 다음 발행
예정일을 오늘+랜덤(2~3일)로 다시 정하고, 그 날짜의 랜덤 목표시각도 새로 뽑는다.
"""
import datetime
import json
import os
import random
import requests

KST = datetime.timezone(datetime.timedelta(hours=9))
now = datetime.datetime.now(KST)
today = now.strftime("%Y-%m-%d")
today_date = now.date()

CHANNELS = ["nasa", "history", "invention", "silent_era", "retro_reels"]

STATE_FILE = "curio_scheduler_state.json"

GH_TOKEN = os.environ["GH_DISPATCH_TOKEN"]
REPO = os.environ["GITHUB_REPOSITORY"]


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def parse_date(s):
    return datetime.datetime.strptime(s, "%Y-%m-%d").date()


def target_time_for(channel, due_date_str):
    """해당 채널의 '다음 발행 예정일'이 정해진 순간, 그 날짜+채널 이름으로
    시드를 고정해서 그 날의 랜덤 목표시각(시/분)을 하나 뽑는다."""
    seed = random.Random(f"{due_date_str}-{channel}-curio-random")
    return seed.randint(0, 23), seed.randint(0, 59)


def main():
    state = load_state()
    changed = False

    for channel in CHANNELS:
        entry = state.get(channel)
        if not entry:
            # 최초 실행: 오늘을 바로 발행 예정일로 잡는다(채널마다 목표시각은
            # 서로 다른 랜덤값이라 5개가 동시에 터지지 않고 하루 안에 흩어짐).
            entry = {"due_date": today}
            entry["target_h"], entry["target_m"] = target_time_for(channel, today)
            state[channel] = entry
            changed = True

        due_date = parse_date(entry["due_date"])
        if today_date < due_date:
            continue  # 아직 예정일 전

        target_h, target_m = entry["target_h"], entry["target_m"]
        now_minutes = now.hour * 60 + now.minute
        target_minutes = target_h * 60 + target_m
        diff = now_minutes - target_minutes if today_date == due_date else 999  # 예정일 지나쳤으면 즉시 발사

        print(f"{channel} 예정일={entry['due_date']} 목표={target_h:02d}:{target_m:02d} KST "
              f"현재={now.strftime('%Y-%m-%d %H:%M')} diff={diff}분")

        if diff < 0:
            continue  # 오늘이 예정일인데 아직 목표시각 전

        try:
            r = requests.post(
                f"https://api.github.com/repos/{REPO}/actions/workflows/curio-longform-daily.yml/dispatches",
                headers={"Authorization": f"token {GH_TOKEN}",
                         "Accept": "application/vnd.github+json"},
                json={"ref": "main", "inputs": {"channel": channel}},
                timeout=20,
            )
            print(f"  ▶ {channel} 발행 트리거 → HTTP {r.status_code}")
            if r.status_code in (200, 201, 204):
                next_gap = random.choice([2, 3])
                next_due = today_date + datetime.timedelta(days=next_gap)
                next_due_str = next_due.strftime("%Y-%m-%d")
                h, m = target_time_for(channel, next_due_str)
                state[channel] = {"due_date": next_due_str, "target_h": h, "target_m": m}
                changed = True
                print(f"    다음 예정: {next_due_str} {h:02d}:{m:02d} KST (+{next_gap}일)")
            else:
                print(f"  ⚠️ {channel} 디스패치 실패 (HTTP {r.status_code}) — 다음 실행에서 재시도")
        except Exception as e:
            print(f"  ⚠️ {channel} 디스패치 예외: {e} — 다음 실행에서 재시도")

    if changed:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
