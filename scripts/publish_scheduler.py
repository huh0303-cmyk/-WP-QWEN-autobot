#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2026-08-04: 하루 3슬롯(고정 앵커 ±60분) → 하루 1회, 완전 랜덤 시각(00:00~23:59
KST 아무 때나)으로 변경 (사용자 지시: "완전 랜덤한 시간으로. 글 1개씩만").
사이트당 발행량도 SITES_CONFIG의 daily=1로 맞춰서, 하루에 한 번만 사이트당
1건씩 나가게 한다.
15분마다 실행되는 publish-scheduler.yml 워크플로우가 이 스크립트를 돌려서,
'오늘의 랜덤 목표시각'을 지난 첫 실행에서 master_autopost.yml을 workflow_dispatch로 발사한다.
하루에 두 번 쏘지 않도록 scheduler_state.json으로 발사 여부를 기록한다.
"""
import datetime
import json
import os
import random
import requests

KST = datetime.timezone(datetime.timedelta(hours=9))
now = datetime.datetime.now(KST)
today = now.strftime("%Y-%m-%d")

# 완전 랜덤 시각(00:00~23:59) - 앵커 없이 하루 1개 슬롯만 사용
_today_seed = random.Random(f"{today}-fullrandom")
SLOTS = {
    "1": (_today_seed.randint(0, 23), _today_seed.randint(0, 59)),
}

STATE_FILE = "scheduler_state.json"

GH_TOKEN = os.environ["GH_DISPATCH_TOKEN"]
REPO = os.environ["GITHUB_REPOSITORY"]


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                s = json.load(f)
            if s.get("date") == today:
                return s
        except Exception:
            pass
    return {"date": today, "fired": {}}


def main():
    state = load_state()
    fired = state.get("fired", {})
    now_minutes = now.hour * 60 + now.minute
    changed = False

    for slot, (h, m) in SLOTS.items():
        if fired.get(slot):
            continue
        target_minutes = h * 60 + m
        diff = now_minutes - target_minutes

        print(f"슬롯{slot} 오늘 완전랜덤 목표={h:02d}:{m:02d} KST "
              f"현재={now.strftime('%H:%M')} diff={diff:.1f}분")

        # 목표시각이 지났고 오늘 아직 발행 안 됐으면 무조건 발사.
        # (예전엔 diff<=14 로 좁은 창을 뒀는데, GitHub cron이 */15분 설정과 달리
        #  실제로는 1.5~2.5시간 간격으로만 도는 경우가 많아서 그 창을 계속 놓쳐
        #  27개 사이트가 최대 39시간 발행 중단되는 사고가 있었음. 상한 제거로 해결.)
        if diff >= 0:
            try:
                r = requests.post(
                    f"https://api.github.com/repos/{REPO}/actions/workflows/master_autopost.yml/dispatches",
                    headers={"Authorization": f"token {GH_TOKEN}",
                             "Accept": "application/vnd.github+json"},
                    json={"ref": "main", "inputs": {"step": "post", "run_slot": slot}},
                    timeout=20,
                )
                print(f"  ▶ 슬롯{slot} 발행 트리거 → HTTP {r.status_code}")
                if r.status_code in (200, 201, 204):
                    fired[slot] = True
                    changed = True
                else:
                    print(f"  ⚠️ 슬롯{slot} 디스패치 실패 (HTTP {r.status_code}) — 다음 실행에서 재시도")
            except Exception as e:
                print(f"  ⚠️ 슬롯{slot} 디스패치 예외: {e} — 다음 실행에서 재시도")

    state["fired"] = fired
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    with open(os.environ.get("GITHUB_OUTPUT", "/dev/null"), "a") as gh_out:
        gh_out.write(f"changed={'true' if changed else 'false'}\n")


if __name__ == "__main__":
    main()
