# -*- coding: utf-8 -*-
"""
27개 사이트 전체 발행글의 제목을 build_diverse_title()로 전면 재생성해 교체한다.
- URL 슬러그는 절대 안 건드림 (permalink 유지, 색인 이력 보존)
- 실제 rank_math_focus_keyword를 기반으로 새 제목 생성
- 깨진 제목("in ?" 같은 빈 연도자리, 반복 클리셰 패턴) 전부 정리
"""
import os, sys, time, random, argparse, requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER, build_diverse_title


def get_all_published_posts(site_url, wp_pass, per_page=20):
    posts, page = [], 1
    while True:
        try:
            r = requests.get(f"{site_url}/wp-json/wp/v2/posts", auth=(WP_USER, wp_pass),
                              params={"per_page": per_page, "page": page, "status": "publish",
                                      "_fields": "id,title,meta"}, timeout=30)
        except Exception as e:
            print(f"  ⚠️ 요청 실패: {e}"); break
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < per_page:
            break
        page += 1
    return posts


def retitle_site(site):
    url = site["url"]
    lang = site.get("lang", "ko")
    pw = os.getenv(site["wp_pass_env"], "")
    if not pw:
        print(f"⏭  {url} — 비밀번호 없음"); return 0, 0

    print(f"\n{'─'*50}\n🌐 {url}")
    posts = get_all_published_posts(url, pw)
    print(f"  발행글 {len(posts)}개")

    updated = failed = 0
    for p in posts:
        pid = p["id"]
        old_title = p.get("title", {}).get("rendered", "")
        meta_obj = p.get("meta", {}) or {}
        keyword = meta_obj.get("rank_math_focus_keyword", "") or old_title
        kw = keyword.split(",")[0].strip()

        new_title = build_diverse_title(kw, lang, site_url=url)
        try:
            r = requests.patch(f"{url}/wp-json/wp/v2/posts/{pid}", auth=(WP_USER, pw),
                                json={"title": new_title}, timeout=20)
            if r.status_code in (200, 201):
                updated += 1
                print(f"  ✅ [{pid}] {old_title[:35]} → {new_title[:35]}")
            else:
                failed += 1
        except Exception as e:
            failed += 1
            print(f"  ❌ [{pid}] {e}")

        time.sleep(random.uniform(0.8, 1.5))

    print(f"  → 완료: 교체 {updated} / 실패 {failed}")
    return updated, failed


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="")
    args = ap.parse_args()

    targets = [s for s in SITES_CONFIG if (not args.site or s["url"] == args.site)]
    tot_u = tot_f = 0
    for site in targets:
        u, f = retitle_site(site)
        tot_u += u; tot_f += f
        time.sleep(random.uniform(2, 4))

    print(f"\n{'='*60}\n✅ 전체 완료 — 교체:{tot_u} / 실패:{tot_f}\n{'='*60}")
