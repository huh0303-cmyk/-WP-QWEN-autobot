#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
recategorize_fallback_posts.py
개선된 pick_best_category()(카테고리 힌트 우선 + 정규화 매칭 + Gemini 시맨틱
폴백)를 이용해서, 이미 'Etc/기타'에 잘못 분류된 채로 발행된 기존 글들을
찾아 올바른 카테고리로 재배정한다.
"""
import os, sys, json
import requests

sys.path.insert(0, os.path.dirname(__file__))
import autopost_mega as ap

TARGETS = [
    ("https://kieca-korea.org", "KIECAKOREAORG"),
    ("https://ksa-korea.org", "KSAKOREAORG"),
    ("https://k-health365.com", "KHEALTH365COM"),
    ("https://koreanews365.com", "KOREANEWS365COM"),
]
FALLBACK_NAMES = {"etc", "기타", "etc.", "other", "others"}

def main():
    all_results = []
    for site_url, pass_env in TARGETS:
        pw = os.environ.get(pass_env, "")
        if not pw:
            print(f"⏭️  {site_url}: 비밀번호 없음")
            continue

        cats = ap.load_site_categories(site_url, pw)
        etc_ids = [cid for cid, n in cats if n.strip().lower() in FALLBACK_NAMES]
        if not etc_ids:
            print(f"⏭️  {site_url}: fallback 카테고리 없음")
            continue

        print(f"\n=== {site_url} ===")
        moved, kept = 0, 0
        for etc_id in etc_ids:
            r = requests.get(f"{site_url}/wp-json/wp/v2/posts", auth=(ap.WP_USER, pw),
                              params={"categories": etc_id, "per_page": 50,
                                      "_fields": "id,title,link,categories"}, timeout=20)
            if r.status_code != 200:
                print(f"  ❌ 목록 조회 실패: {r.status_code}")
                continue
            posts = r.json()
            print(f"  fallback 카테고리(id={etc_id}) 글 {len(posts)}건")

            for p in posts:
                title = p["title"]["rendered"]
                new_cat_id = ap.pick_best_category(site_url, pw, keyword="", title=title)
                if new_cat_id and new_cat_id != etc_id:
                    rc = requests.post(f"{site_url}/wp-json/wp/v2/posts/{p['id']}", auth=(ap.WP_USER, pw),
                                        json={"categories": [new_cat_id]}, timeout=20)
                    cat_name = next((n for cid, n in cats if cid == new_cat_id), "?")
                    if rc.status_code in (200, 201):
                        print(f"    ✅ [{title[:40]}] -> {cat_name}")
                        moved += 1
                        all_results.append({"site": site_url, "title": title, "link": p["link"],
                                             "new_category": cat_name, "status": "moved"})
                    else:
                        print(f"    ❌ 업데이트 실패({rc.status_code}): {title[:40]}")
                        all_results.append({"site": site_url, "title": title, "link": p["link"],
                                             "status": "failed", "error": rc.text[:200]})
                else:
                    print(f"    ⏭️  [{title[:40]}] 더 나은 카테고리 못찾음 (Etc 유지)")
                    kept += 1
                    all_results.append({"site": site_url, "title": title, "link": p["link"],
                                         "status": "kept_etc"})
        print(f"  -> 이동 {moved}건 / 유지 {kept}건")

    with open("recategorize_fallback_result.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
