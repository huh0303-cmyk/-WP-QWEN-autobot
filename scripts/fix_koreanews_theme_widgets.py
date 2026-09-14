#!/usr/bin/env python3
"""Mission News 테마를 koreanews365.com에 새로 활성화한 뒤 남아있는 테마
데모 위젯("Build a WordPress News Site Fast", "About Author" 등 영문/힌디어
샘플 콘텐츠)을 찾아서 제거한다. theseouljournal.com은 이미 깨끗한 상태이므로
비교 기준으로 삼는다. 사용자 지시(2026-08-21) — 테마 전환 후 보기 좋게 튜닝."""
import os
import sys

import requests

SITE = "https://koreanews365.com"
USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
PASSWORD = os.getenv("KOREANEWS365COM", "").strip()
DEMO_MARKERS = ("Build a WordPress News Site", "About Author",
                "quality code and elegant design", "हिंदी")


def call(method, path, **kwargs):
    r = requests.request(method, f"{SITE}/wp-json/{path}", auth=(USER, PASSWORD),
                          timeout=45, **kwargs)
    r.raise_for_status()
    return r.json() if r.content else {}


def main():
    if not PASSWORD:
        raise SystemExit("Missing KOREANEWS365COM secret")

    sidebars = call("GET", "wp/v2/sidebars")
    print(f"사이드바 영역 {len(sidebars)}개 발견")

    widgets = call("GET", "wp/v2/widgets", params={"per_page": 100})
    print(f"위젯 총 {len(widgets)}개")

    removed = []
    for w in widgets:
        rendered = str(w.get("rendered", "")) + str(w.get("instance", {}))
        if any(marker in rendered for marker in DEMO_MARKERS):
            removed.append(w)

    if not removed:
        print("데모 마커가 포함된 위젯을 못 찾음 — 위젯 목록 원본 출력:")
        for w in widgets:
            print(f"  id={w.get('id')} idBase={w.get('id_base')} sidebar={w.get('sidebar')}")
        sys.exit(0)

    print(f"\n데모 콘텐츠로 판단된 위젯 {len(removed)}개:")
    for w in removed:
        print(f"  id={w['id']} idBase={w.get('id_base')} sidebar={w.get('sidebar')}")

    for w in removed:
        try:
            call("DELETE", f"wp/v2/widgets/{w['id']}", params={"force": True})
            print(f"  삭제됨: {w['id']}")
        except Exception as e:
            print(f"  삭제 실패({w['id']}): {e}")

    print("\n완료")


if __name__ == "__main__":
    main()
