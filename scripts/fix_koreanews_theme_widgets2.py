#!/usr/bin/env python3
"""2차 정리: 'Ad Spot - Above Posts' 영역에 남아있는 Mission News 테마 자체
홍보 배너(afthemes/elespare/tastewp/blockspare 링크) 5개 삭제, 그리고 좌우
'Latest Posts' 위젯(ct_mission_news_post_list)의 실제 렌더링 전체를 출력해서
왜 비어보이는지 확인한다."""
import os

import requests

SITE = "https://koreanews365.com"
USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
PASSWORD = os.getenv("KOREANEWS365COM", "").strip()
PROMO_DOMAINS = ("afthemes.com", "elespare.com", "tastewp.com", "blockspare.com")


def call(method, path, **kwargs):
    r = requests.request(method, f"{SITE}/wp-json/{path}", auth=(USER, PASSWORD),
                          timeout=45, **kwargs)
    r.raise_for_status()
    return r.json() if r.content else {}


def main():
    if not PASSWORD:
        raise SystemExit("Missing KOREANEWS365COM secret")

    widgets = call("GET", "wp/v2/widgets", params={"per_page": 100})

    promo = [w for w in widgets if any(d in str(w.get("rendered", "")) for d in PROMO_DOMAINS)]
    print(f"테마 홍보 배너 위젯 {len(promo)}개 발견")
    for w in promo:
        try:
            call("DELETE", f"wp/v2/widgets/{w['id']}", params={"force": True})
            print(f"  삭제됨: {w['id']} (sidebar={w.get('sidebar')})")
        except Exception as e:
            print(f"  삭제 실패({w['id']}): {e}")

    print("\n--- Latest Posts 위젯 전체 렌더링 ---")
    for wid in ("ct_mission_news_post_list-1", "ct_mission_news_post_list-2"):
        try:
            w = call("GET", f"wp/v2/widgets/{wid}", params={"context": "edit"})
            print(f"\n[{wid}] sidebar={w.get('sidebar')}")
            print(f"  instance: {w.get('instance')}")
            print(f"  rendered (full): {w.get('rendered')}")
        except Exception as e:
            print(f"  조회 실패({wid}): {e}")


if __name__ == "__main__":
    main()
