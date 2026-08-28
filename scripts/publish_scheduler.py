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

2026-08-26 최소 30분 간격 안전장치 적용.
2026-08-26 최종 등급/빈도 정책 적용: A 17개는 주 3~4회, B 8개는
주 2~3회. 사이트별 ISO 주차 시드로 요일을 매주 다시 뽑고 각 사이트마다
토/일 중 하루를 반드시 포함한다. 뉴스 2개는 계속 별도 워크플로우가 담당한다.

2026-08-22 재개: master_autopost.yml/publish-scheduler.yml이 품질복구를
이유로 한동안 꺼져 있다가, 사용자 지시("25개 블로그사이트는 1일 1포스팅
시간 랜덤... 지금 실행해줘")로 다시 켬. 디스패치 대상을 새 워크플로우
daily-network-publish.yml로 바꿨고, 뉴스 2개 사이트(koreanews365/theseouljournal — newsrooms-daily-publisher.yml이
이미 별도 시간규칙으로 하루 3~10건 처리 중이라 이 스케줄러 대상이 아님)를
뺐다.
"""
import datetime
import json
import os
import random
import requests

from load_automation_hub_from_sheets import load_runtime_registry

KST = datetime.timezone(datetime.timedelta(hours=9))
now = datetime.datetime.now(KST)
today = now.strftime("%Y-%m-%d")

_registry = load_runtime_registry()
BLOG_CONFIG = {
    site.url.rstrip("/"): site
    for site in _registry.enabled("wordpress")
    if site.content_type == "blog" and site.publish_mode == "automatic"
}
A_GROUP = [url for url, site in BLOG_CONFIG.items() if site.group == "A"]
B_GROUP = [url for url, site in BLOG_CONFIG.items() if site.group == "B"]
SITES = A_GROUP + B_GROUP


def weekly_publish_days(site_url):
    """Return 0=Mon..6=Sun days for this site's current weekly plan."""
    iso = now.date().isocalendar()
    rng = random.Random(f"{iso.year}-W{iso.week}-{site_url}-weekly-cadence-v1")
    config = BLOG_CONFIG[site_url]
    count = rng.randint(config.weekly_min, config.weekly_max)
    weekend_day = rng.choice([5, 6])
    remaining = [day for day in range(7) if day != weekend_day]
    return sorted([weekend_day] + rng.sample(remaining, count - 1))


WEEKLY_PLANS = {site: weekly_publish_days(site) for site in SITES}
TODAY_SITES = [site for site in SITES if now.weekday() in WEEKLY_PLANS[site]]

# 오늘 대상만 순서를 섞고 45~75분 간격의 랜덤 슬롯에 배치한다. API 디스패치
# 자체에도 최소 30분 안전장치가 있어 우연히 같은 시각에 몰릴 수 없다.
_daily_rng = random.Random(f"{today}-network-spread-v2")
_daily_rng.shuffle(TODAY_SITES)
_minute_cursor = _daily_rng.randint(4 * 60, 7 * 60 + 30)
SLOTS = {}
_latest_minute = 23 * 60 + 15
_max_gap = ((_latest_minute - _minute_cursor) // max(1, len(TODAY_SITES) - 1)
            if len(TODAY_SITES) > 1 else 75)
for _index, _site in enumerate(TODAY_SITES):
    SLOTS[_site] = divmod(_minute_cursor, 60)
    if _index < len(TODAY_SITES) - 1:
        _minute_cursor += _daily_rng.randint(35, max(35, min(75, _max_gap)))

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
    return {"date": today, "fired": {}, "last_dispatch_at": None}


def main():
    state = load_state()
    fired = state.get("fired", {})
    now_minutes = now.hour * 60 + now.minute
    changed = False
    print(f"오늘 발행 대상 {len(TODAY_SITES)}/{len(SITES)}개 "
          f"(A 주3~4회, B 주2~3회, 주말 포함)")

    # 모든 블로그 디스패치 사이를 최소 30분 띄운다. 예전 방식은 각 사이트의
    # 목표시각만 독립 랜덤이라 우연히 같은 시각에 여러 사이트가 몰릴 수 있었다.
    last_dispatch_raw = state.get("last_dispatch_at")
    if last_dispatch_raw:
        try:
            last_dispatch = datetime.datetime.fromisoformat(last_dispatch_raw)
            if last_dispatch.tzinfo is None:
                last_dispatch = last_dispatch.replace(tzinfo=KST)
            elapsed_minutes = (now - last_dispatch.astimezone(KST)).total_seconds() / 60
        except Exception:
            elapsed_minutes = 30
    else:
        elapsed_minutes = 30

    if elapsed_minutes < 30:
        print(f"⏳ 마지막 디스패치 후 {elapsed_minutes:.1f}분 — 최소 30분 간격 대기")
        state["fired"] = fired
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        return

    # 목표시각이 지난 사이트를 시간순으로 처리하되 한 실행당 최대 1개만 발사한다.
    # 워크플로가 15분마다 실행되므로 실제 사이트 간격은 항상 30분 이상이다.
    due_sites = sorted(
        SLOTS.items(),
        key=lambda item: item[1][0] * 60 + item[1][1],
    )

    for site_url, (h, m) in due_sites:
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
                          "inputs": {"target_site_url": site_url,
                                     "publication_approved": "true"}},
                    timeout=20,
                )
                print(f"  ▶ {site_url} 발행 트리거 → HTTP {r.status_code}")
                if r.status_code in (200, 201, 204):
                    fired[site_url] = True
                    state["last_dispatch_at"] = now.isoformat()
                    changed = True
                    break
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
