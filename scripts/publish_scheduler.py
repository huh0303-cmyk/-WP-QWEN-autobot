#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
목표 발행시각(KST): 07:25 / 13:07 / 19:50 — 매일 ±60분 랜덤으로 실제 발행시각이 달라짐.
15분마다 실행되는 publish-scheduler.yml 워크플로우가 이 스크립트를 돌려서,
'오늘의 랜덤 목표시각'을 지난 첫 실행에서 master_autopost.yml을 workflow_dispatch로 발사한다.
같은 슬롯을 하루에 두 번 쏘지 않도록 scheduler_state.json으로 발사 여부를 기록한다.
"""
import datetime
import json
import os
import random
import requests

KST = datetime.timezone(datetime.timedelta(hours=9))
now = datetime.datetime.now(KST)
today = now.strftime("%Y-%m-%d")

SLOTS = {
    "1": (7, 25),
    "2": (13, 7),
    "3": (19, 50),
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
        base_minutes = h * 60 + m
        offset = random.Random(f"{today}-slot{slot}").uniform(-60, 60)
        target_minutes = base_minutes + offset
        diff = now_minutes - target_minutes

        print(f"슬롯{slot} 오늘 목표={int(target_minutes)//60:02d}:{int(target_minutes)%60:02d} KST "
              f"(기준 {h:02d}:{m:02d} {'+' if offset>=0 else ''}{offset:.0f}분) 현재={now.strftime('%H:%M')} diff={diff:.1f}분")

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
