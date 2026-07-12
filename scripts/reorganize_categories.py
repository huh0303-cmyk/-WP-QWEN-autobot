#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reorganize_categories.py
k-health365.com 카테고리를 정확히 4개로 정리합니다.
- health-medical-info      -> 이름 변경: "건강정보"
- disease-management       -> 이름 변경: "질병별대처법"
- health-supplements       -> 이름 변경: "건강기능식품소개" (기준 카테고리로 유지)
- health-functional-food   -> 이 카테고리의 글들을 health-supplements로 옮긴 뒤 삭제
- etc                      -> 이름 유지: "기타"
"""
import os, requests

SITE_URL = "https://k-health365.com"
WP_USER = "huh0303@gmail.com"
WP_PASS = os.environ.get("KHEALTH365COM")
AUTH = requests.auth.HTTPBasicAuth(WP_USER, WP_PASS)

_LOG = []
def log(m=""):
    print(m)
    _LOG.append(str(m))


def get_categories():
    r = requests.get(f"{SITE_URL}/wp-json/wp/v2/categories",
                      auth=AUTH, params={"per_page": 100}, timeout=20)
    r.raise_for_status()
    return {c["slug"]: c for c in r.json()}


def rename_category(cat_id, new_name):
    r = requests.post(f"{SITE_URL}/wp-json/wp/v2/categories/{cat_id}",
                       auth=AUTH, json={"name": new_name}, timeout=20)
    ok = r.status_code in (200, 201)
    log(f"  {'✅' if ok else '⚠️'} 카테고리ID {cat_id} 이름 변경 -> '{new_name}' (status={r.status_code})")
    return ok


def get_all_posts_in_category(cat_id):
    posts = []
    page = 1
    while True:
        r = requests.get(f"{SITE_URL}/wp-json/wp/v2/posts",
                          auth=AUTH, params={"categories": cat_id, "per_page": 100,
                                              "page": page, "_fields": "id,categories"},
                          timeout=20)
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return posts


def move_posts(posts, from_id, to_id):
    moved, failed = 0, 0
    for p in posts:
        cats = set(p.get("categories", []))
        cats.discard(from_id)
        cats.add(to_id)
        r = requests.post(f"{SITE_URL}/wp-json/wp/v2/posts/{p['id']}",
                           auth=AUTH, json={"categories": list(cats)}, timeout=20)
        if r.status_code in (200, 201):
            moved += 1
        else:
            failed += 1
    return moved, failed


def delete_category(cat_id):
    r = requests.delete(f"{SITE_URL}/wp-json/wp/v2/categories/{cat_id}",
                         auth=AUTH, params={"force": "true"}, timeout=20)
    ok = r.status_code in (200, 201)
    log(f"  {'✅' if ok else '⚠️'} 카테고리ID {cat_id} 삭제 (status={r.status_code})")
    return ok


def main():
    if not WP_PASS:
        log("⚠️ KHEALTH365COM 환경변수 없음")
        return

    log("[1/4] 현재 카테고리 조회...")
    cats = get_categories()
    for slug, c in cats.items():
        log(f"   {slug}: id={c['id']}, name='{c['name']}', count={c['count']}")

    if "health-medical-info" in cats:
        log("\n[2/4] 이름 변경")
        rename_category(cats["health-medical-info"]["id"], "건강정보")
    if "disease-management" in cats:
        rename_category(cats["disease-management"]["id"], "질병별대처법")
    if "health-supplements" in cats:
        rename_category(cats["health-supplements"]["id"], "건강기능식품소개")
    if "etc" in cats:
        rename_category(cats["etc"]["id"], "기타")

    if "health-functional-food" in cats and "health-supplements" in cats:
        from_id = cats["health-functional-food"]["id"]
        to_id = cats["health-supplements"]["id"]
        log(f"\n[3/4] health-functional-food({from_id}) 글들을 "
            f"health-supplements({to_id})로 이동...")
        posts = get_all_posts_in_category(from_id)
        log(f"   대상 게시물 {len(posts)}개")
        moved, failed = move_posts(posts, from_id, to_id)
        log(f"   이동완료 {moved}개, 실패 {failed}개")

        log("\n[4/4] 빈 health-functional-food 카테고리 삭제")
        delete_category(from_id)
    else:
        log("\n[3-4/4] 병합 대상 카테고리를 찾지 못해 건너뜀")

    log("\n최종 카테고리 상태 재조회...")
    final_cats = get_categories()
    for slug, c in final_cats.items():
        log(f"   {slug}: name='{c['name']}', count={c['count']}")

    with open("reorganize_categories_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(_LOG))


if __name__ == "__main__":
    main()
