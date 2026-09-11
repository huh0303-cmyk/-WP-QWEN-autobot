# -*- coding: utf-8 -*-
"""
글 제목/본문에 남아있는 '2024'를 전부 '2026'으로 교체.

원칙:
  1. URL 슬러그(permalink)는 절대 건드리지 않는다 — 이미 색인된 주소를 지키기 위함
  2. 제목·본문에서 '2024' 문자열만 정확히 '2026'으로 치환 (그 외 내용은 그대로)
  3. '2024'가 없는 글은 건드리지 않는다 (불필요한 재발행/수정이력 방지)
  4. 사이트/글 사이 딜레이로 서버 부담 최소화

사용법:
  python scripts/fix_2024_to_2026.py                 # 27개 사이트 전체
  python scripts/fix_2024_to_2026.py --site <url>    # 특정 사이트만
"""
import os, sys, time, random, argparse, requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER


def get_all_published_posts(site_url, wp_pass, per_page=50):
    posts, page = [], 1
    while True:
        try:
            r = requests.get(
                f"{site_url}/wp-json/wp/v2/posts", auth=(WP_USER, wp_pass),
                params={"per_page": per_page, "page": page, "status": "publish",
                        "_fields": "id,title,content,link"}, timeout=25)
        except Exception as e:
            print(f"  ⚠️ 요청 실패: {e}"); break
        if r.status_code != 200:
            if r.status_code != 400:
                print(f"  ⚠️ 상태코드 {r.status_code}")
            break
        batch = r.json()
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < per_page:
            break
        page += 1
    return posts


def fix_site(site):
    url = site["url"]
    pw = os.getenv(site["wp_pass_env"], "")
    if not pw:
        print(f"⏭  {url} — 비밀번호 없음, 스킵"); return 0, 0, 0

    print(f"\n{'─'*50}\n🌐 {url}")
    posts = get_all_published_posts(url, pw)
    print(f"  발행글 {len(posts)}개 확인")

    updated = skipped = failed = 0
    for p in posts:
        pid = p["id"]
        title_raw = p.get("title", {})
        title = title_raw.get("rendered", "") if isinstance(title_raw, dict) else str(title_raw)
        content_raw = p.get("content", {})
        content = content_raw.get("rendered", "") if isinstance(content_raw, dict) else str(content_raw)

        if "2024" not in title and "2024" not in content:
            skipped += 1
            continue

        new_title = title.replace("2024", "2026")
        new_content = content.replace("2024", "2026")

        payload = {}
        if new_title != title:
            payload["title"] = new_title
        if new_content != content:
            payload["content"] = new_content

        try:
            r = requests.patch(
                f"{url}/wp-json/wp/v2/posts/{pid}", auth=(WP_USER, pw),
                json=payload, timeout=25)
            if r.status_code in (200, 201):
                updated += 1
                print(f"  ✅ [{pid}] {title[:50]} → {new_title[:50]}")
            else:
                failed += 1
                print(f"  ❌ [{pid}] 실패 {r.status_code}: {r.text[:100]}")
        except Exception as e:
            failed += 1
            print(f"  ❌ [{pid}] 예외: {e}")

        time.sleep(random.uniform(1.5, 3.0))

    print(f"  → 완료: 수정 {updated} / 스킵(2024없음) {skipped} / 실패 {failed}")
    return updated, skipped, failed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="")
    args = ap.parse_args()

    targets = [s for s in SITES_CONFIG if (not args.site or s["url"] == args.site)]
    if not targets:
        print(f"❌ 사이트를 찾을 수 없음: {args.site}"); return

    tot_u = tot_s = tot_f = 0
    for site in targets:
        u, s, f = fix_site(site)
        tot_u += u; tot_s += s; tot_f += f
        time.sleep(random.uniform(3, 6))

    print(f"\n{'='*60}")
    print(f"✅ 전체 완료 — 수정:{tot_u} / 스킵:{tot_s} / 실패:{tot_f}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
