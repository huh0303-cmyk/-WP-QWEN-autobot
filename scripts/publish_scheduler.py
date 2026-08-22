#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2026-08-04: 하루 3슬롯(고정 앵커 ±60분) → 하루 1회, 완전 랜덤 시각(00:00~23:59
KST 아무 때나)으로 변경.
2026-08-19: 그 "하루 1회"가 27개 사이트 전부를 한 번에 몰아서 발행시키는
구조였음(사용자 지적 — "같은 운영자가 굴리는 네트워크"로 보이는 신호를
스스로 만들고 있었음). 사이트마다 각자 독립된 랜덤 시각(오늘 날짜+사이트
URL로 시드)을 갖도록 바꿔서, 하루 동안 27번 서로 다른 순간에 흩어져
발행되게 한다. master_autopost.yml을 site별로 publish_site 입력을 줘서
디스패치 — 주기(publish_every_n_days)/페이싱 로직은 autopost_mega.py의
get_slot_posts가 그대로 담당하고, 여기선 "오늘 이 사이트를 건드릴 시각"만
결정한다.
15분마다 실행되는 publish-scheduler.yml 워크플로우가 이 스크립트를 돌려서,
사이트별 '오늘의 랜덤 목표시각'을 지난 것들만 그 순간 첫 실행에서
master_autopost.yml을 workflow_dispatch(step=post, publish_site=<url>)로 발사한다.
같은 사이트를 하루에 두 번 쏘지 않도록 scheduler_state.json으로 발사 여부를
사이트별로 기록한다.

2026-08-22 재개: master_autopost.yml/publish-scheduler.yml이 품질복구를
이유로 한동안 꺼져 있다가, 사용자 지시("25개 블로그사이트는 1일 1포스팅
시간 랜덤... 지금 실행해줘")로 다시 켬. 디스패치 대상을 새 워크플로우
daily-network-publish.yml로 바꿨고, SITES 목록에서 퇴역한 kskin365.com과
뉴스 2개 사이트(koreanews365/theseouljournal — newsrooms-daily-publisher.yml이
이미 별도 시간규칙으로 하루 3~10건 처리 중이라 이 스케줄러 대상이 아님)를
뺐다.
"""
import datetime
import json
import os
import random
import requests

KST = datetime.timezone(datetime.timedelta(hours=9))
now = datetime.datetime.now(KST)
today = now.strftime("%Y-%m-%d")

# autopost_mega.py의 SITES_CONFIG 중 이 스케줄러가 담당하는 24개 사이트.
# kskin365.com(퇴역)과 koreanews365/theseouljournal(별도 뉴스 스케줄러 사용
# 중)은 제외 — 무거운 google-genai 등 의존성 없이 순수 requests만 쓰는 이
# 스케줄러 워크플로우에서 autopost_mega.py를 그대로 import하지 않으려고
# 독립 목록 유지(다른 스케줄/감사 스크립트들과 동일한 관례).
SITES = [
    "https://k-health365.com", "https://koreamedicaltour.com", "https://koreainvest365.com",
    "https://ki-korea.com", "https://koreainsurance365.com", "https://kfinance365.com",
    "https://koreataxnlaw.com", "https://koreacrypto365.com", "https://krealestate365.com",
    "https://ktech365.com", "https://oliveyoungkorea.com",
    "https://kworld365.com", "https://k-trip365.com", "https://k-visa365.com",
    "https://koreawedding365.com", "https://kstudy365.com", "https://studyinkorea365.com",
    "https://kieca-korea.org", "https://ksa-korea.org", "https://sis-korea.com",
    "https://jobkorea365.com", "https://jobinkorea365.com", "https://jobkoreaglobal.com",
    "https://korea365.org",
]

# 사이트마다 오늘 날짜+URL로 독립 시드 → 서로 다른 랜덤 시각(00:00~23:59), 매일 재추첨
SLOTS = {}
for _site in SITES:
    _seed = random.Random(f"{today}-{_site}-fullrandom-persite")
    SLOTS[_site] = (_seed.randint(0, 23), _seed.randint(0, 59))

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

    for site_url, (h, m) in SLOTS.items():
        if fired.get(site_url):
            continue
        target_minutes = h * 60 + m
        diff = now_minutes - target_minutes

        print(f"{site_url} 오늘 목표={h:02d}:{m:02d} KST "
              f"현재={now.strftime('%H:%M')} diff={diff:.1f}분")

        # 목표시각이 지났고 오늘 아직 이 사이트를 안 쐈으면 무조건 발사.
        # (상한을 두면 GitHub cron이 */15분 설정과 달리 실제로는 더 늘어져
        #  도는 경우 창을 놓쳐서 그 사이트가 그날 아예 스킵될 수 있음 — 예전
        #  단일슬롯 스케줄러에서 겪은 문제와 동일해서 여기도 상한 없음.)
        if diff >= 0:
            try:
                r = requests.post(
                    f"https://api.github.com/repos/{REPO}/actions/workflows/daily-network-publish.yml/dispatches",
                    headers={"Authorization": f"token {GH_TOKEN}",
                             "Accept": "application/vnd.github+json"},
                    json={"ref": "main",
                          "inputs": {"target_site_url": site_url}},
                    timeout=20,
                )
                print(f"  ▶ {site_url} 발행 트리거 → HTTP {r.status_code}")
                if r.status_code in (200, 201, 204):
                    fired[site_url] = True
                    changed = True
                else:
                    print(f"  ⚠️ {site_url} 디스패치 실패 (HTTP {r.status_code}) — 다음 실행에서 재시도")
            except Exception as e:
                print(f"  ⚠️ {site_url} 디스패치 예외: {e} — 다음 실행에서 재시도")

    state["fired"] = fired
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    with open(os.environ.get("GITHUB_OUTPUT", "/dev/null"), "a") as gh_out:
        gh_out.write(f"changed={'true' if changed else 'false'}\n")


if __name__ == "__main__":
    main()
