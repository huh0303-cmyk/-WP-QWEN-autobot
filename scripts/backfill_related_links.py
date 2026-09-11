# -*- coding: utf-8 -*-
"""
기존에 이미 발행된 글들에 '관련 글' 블록을 소급 적용하는 스크립트.

원칙 (안전 최우선):
  1. 본문 내용은 절대 수정하지 않는다 — 끝에 블록만 추가(append)
  2. 이미 관련글 블록이 있는 글은 건너뛴다 (재실행해도 중복 삽입 안 됨)
  3. 사이트/글 사이에 딜레이를 둬서 서버(WAF)에 부담을 주지 않는다
  4. 새 글 발행 로직(autopost_mega.py)과 완전히 동일한 함수를 재사용
     → 새 글/기존 글 모두 같은 기준

사용법 (GitHub Actions에서):
  python scripts/backfill_related_links.py            # 27개 사이트 전체
  python scripts/backfill_related_links.py --site https://k-health365.com   # 특정 사이트만
"""
import os, sys, time, random, argparse, requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import (
    SITES_CONFIG, WP_USER, build_related_links_html, fetch_recent_wp_posts
)

MARKER = 'class="related-links"'  # 이미 삽입됐는지 판별하는 표식


def get_all_published_posts(site_url, wp_pass, per_page=50):
    """해당 사이트의 모든 발행글 (id, title, content, link)을 페이지네이션으로 전부 가져온다."""
    posts, page = [], 1
    while True:
        try:
            r = requests.get(
                f"{site_url}/wp-json/wp/v2/posts", auth=(WP_USER, wp_pass),
                params={"per_page": per_page, "page": page, "status": "publish",
                        "_fields": "id,title,content,link"}, timeout=20)
        except Exception as e:
            print(f"  ⚠️ 요청 실패: {e}"); break
        if r.status_code != 200:
            if r.status_code != 400:  # 400 = 마지막 페이지 초과 (정상 종료)
                print(f"  ⚠️ 상태코드 {r.status_code}: {r.text[:150]}")
            break
        batch = r.json()
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < per_page:
            break
        page += 1
    return posts


def backfill_site(site):
    url = site["url"]; lang = site.get("lang", "ko")
    pw = os.getenv(site["wp_pass_env"], "")
    if not pw:
        print(f"⏭  {url} — 비밀번호 없음, 스킵"); return 0, 0, 0

    print(f"\n{'─'*50}\n🌐 {url}")
    posts = get_all_published_posts(url, pw)
    print(f"  발행글 {len(posts)}개 발견")

    updated = skipped = failed = 0
    for p in posts:
        pid = p["id"]
        title_raw = p.get("title", {})
        title = title_raw.get("rendered", "") if isinstance(title_raw, dict) else str(title_raw)
        content_raw = p.get("content", {})
        content = content_raw.get("rendered", "") if isinstance(content_raw, dict) else str(content_raw)

        if MARKER in content:
            skipped += 1
            continue

        related_html = build_related_links_html(url, pw, lang, exclude_title=title)
        if not related_html:
            skipped += 1
            continue

        new_content = content + related_html
        try:
            r = requests.patch(
                f"{url}/wp-json/wp/v2/posts/{pid}", auth=(WP_USER, pw),
                json={"content": new_content}, timeout=20)
            if r.status_code in (200, 201):
                updated += 1
                print(f"  ✅ [{pid}] {title[:40]}")
            else:
                failed += 1
                print(f"  ❌ [{pid}] 실패 {r.status_code}: {r.text[:100]}")
        except Exception as e:
            failed += 1
            print(f"  ❌ [{pid}] 예외: {e}")

        time.sleep(random.uniform(1.5, 3.0))  # 서버 부담 방지

    print(f"  → 완료: 수정 {updated} / 스킵 {skipped} / 실패 {failed}")
    return updated, skipped, failed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="", help="특정 사이트 URL만 처리 (비우면 전체 27개)")
    args = ap.parse_args()

    targets = [s for s in SITES_CONFIG if (not args.site or s["url"] == args.site)]
    if not targets:
        print(f"❌ 사이트를 찾을 수 없음: {args.site}"); return

    tot_u = tot_s = tot_f = 0
    for site in targets:
        u, s, f = backfill_site(site)
        tot_u += u; tot_s += s; tot_f += f
        time.sleep(random.uniform(3, 6))  # 사이트 간 딜레이

    print(f"\n{'='*60}")
    print(f"✅ 전체 완료 — 수정:{tot_u} / 스킵:{tot_s} / 실패:{tot_f}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
