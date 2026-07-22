#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_blog_menu_kieca.py
kieca-korea.org의 실제 사이트 공통 내비게이션 메뉴(홈페이지 전용 커스텀 헤더가 아닌,
다른 모든 페이지에 뜨는 진짜 wp_nav_menu)에 "Blog" 항목을 추가해서
/blog/ 페이지로 이동할 수 있게 한다.
"""
import os, json, requests

SITE_URL = "https://kieca-korea.org"
WP_USER = "huh0303@gmail.com"
WP_PASS = os.environ["KIECAKOREAORG"]
auth = requests.auth.HTTPBasicAuth(WP_USER, WP_PASS)

def main():
    # 1) 메뉴 위치(테마가 실제로 어디에 어떤 메뉴를 꽂아놨는지) 확인
    r = requests.get(f"{SITE_URL}/wp-json/wp/v2/menu-locations", auth=auth, timeout=15)
    print("메뉴 위치:", r.status_code, r.text[:500])
    locations = r.json() if r.status_code == 200 else {}

    # 2) 전체 메뉴 목록
    r = requests.get(f"{SITE_URL}/wp-json/wp/v2/menus", auth=auth, params={"per_page": 50}, timeout=15)
    print("메뉴 목록:", r.status_code)
    if r.status_code != 200:
        print("본문:", r.text[:500])
        return
    menus = r.json()
    for m in menus:
        print(f"  - id={m['id']} name={m['name']} locations={m.get('locations')}")

    if not menus:
        print("❌ 메뉴가 하나도 없음")
        return

    # location이 매핑된(=실제로 화면에 노출되는) 메뉴를 우선 타겟으로 삼는다.
    # 여러 개면 전부에 추가 (상단 메뉴 + 혹시 있는 다른 메뉴 전부 커버)
    used_location_ids = set()
    for loc, loc_data in (locations.items() if isinstance(locations, dict) else []):
        # loc_data 예: {"name":"primary","menu":2,...} - 실제 menu id는 loc_data["menu"]
        if isinstance(loc_data, dict) and "menu" in loc_data:
            used_location_ids.add(loc_data["menu"])
        elif isinstance(loc_data, int):
            used_location_ids.add(loc_data)

    targets = [m for m in menus if m["id"] in used_location_ids] or menus

    # 3) blog 페이지(id=894, slug=blog)를 가리키는 메뉴 아이템을 각 타겟 메뉴에 추가
    #    이미 blog로 가는 항목이 있으면 중복 추가하지 않는다.
    results = []
    for menu in targets:
        menu_id = menu["id"]
        ri = requests.get(f"{SITE_URL}/wp-json/wp/v2/menu-items", auth=auth,
                           params={"menus": menu_id, "per_page": 100}, timeout=15)
        items = ri.json() if ri.status_code == 200 else []
        already = any(("/blog" in (it.get("url") or "")) for it in items) if isinstance(items, list) else False
        if already:
            print(f"⏭️  메뉴 '{menu['name']}'(id={menu_id})에 이미 blog 링크 있음 — 건너뜀")
            results.append({"menu": menu["name"], "status": "skipped_exists"})
            continue

        max_order = max([it.get("menu_order", 0) for it in items], default=0) if isinstance(items, list) else 0

        payload = {
            "title": "Blog",
            "url": f"{SITE_URL}/blog/",
            "status": "publish",
            "menus": menu_id,
            "menu_order": max_order + 1,
            "object": "page",
            "object_id": 894,
            "type": "post_type",
        }
        rc = requests.post(f"{SITE_URL}/wp-json/wp/v2/menu-items", auth=auth, json=payload, timeout=15)
        if rc.status_code in (200, 201):
            print(f"✅ 메뉴 '{menu['name']}'(id={menu_id})에 Blog 항목 추가 완료")
            results.append({"menu": menu["name"], "status": "added", "item_id": rc.json().get("id")})
        else:
            print(f"❌ 메뉴 '{menu['name']}'(id={menu_id}) 추가 실패: {rc.status_code} {rc.text[:300]}")
            results.append({"menu": menu["name"], "status": "failed", "error": rc.text[:300]})

    with open("add_blog_menu_kieca_result.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
