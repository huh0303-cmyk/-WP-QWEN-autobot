#!/usr/bin/env python3
"""Read-only: koreanews365.com의 전체 사이드바/위젯 구조를 출력해서
'좌우 latest post 비어있음' 원인을 진단한다."""
import os

import requests

SITE = "https://koreanews365.com"
USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
PASSWORD = os.getenv("KOREANEWS365COM", "").strip()


def call(method, path, **kwargs):
    r = requests.request(method, f"{SITE}/wp-json/{path}", auth=(USER, PASSWORD),
                          timeout=45, **kwargs)
    r.raise_for_status()
    return r.json() if r.content else {}


def main():
    if not PASSWORD:
        raise SystemExit("Missing KOREANEWS365COM secret")

    sidebars = call("GET", "wp/v2/sidebars")
    widgets = call("GET", "wp/v2/widgets", params={"per_page": 100})
    by_sidebar = {}
    for w in widgets:
        by_sidebar.setdefault(w.get("sidebar"), []).append(w)

    for sb in sidebars:
        sid = sb.get("id")
        name = sb.get("name")
        ws = by_sidebar.get(sid, [])
        print(f"\n=== [{sid}] {name} — 위젯 {len(ws)}개 ===")
        for w in ws:
            rendered = str(w.get("rendered", ""))[:150].replace("\n", " ")
            print(f"  id={w.get('id')} idBase={w.get('id_base')} rendered_preview={rendered!r}")

    unassigned = by_sidebar.get(None, []) or by_sidebar.get("wp_inactive_widgets", [])
    if unassigned:
        print(f"\n=== 미배치/비활성 위젯 {len(unassigned)}개 ===")
        for w in unassigned:
            print(f"  id={w.get('id')} idBase={w.get('id_base')}")


if __name__ == "__main__":
    main()
