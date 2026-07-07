#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SEO 점수 메타필드가 REST API에서 실제로 어떻게 노출되는지 진단"""
import os, json
import requests

WP_USER = "huh0303@gmail.com"
SITE_URL = "https://k-health365.com"
WP_PASS = os.getenv("KHEALTH365COM", "")


def main():
    if not WP_PASS:
        print("❌ 비밀번호 없음")
        return

    # 최근 발행글 1개를 context=edit로 전체 필드 조회
    r = requests.get(f"{SITE_URL}/wp-json/wp/v2/posts",
                     auth=(WP_USER, WP_PASS),
                     params={"per_page": 1, "status": "publish", "context": "edit"},
                     timeout=20)
    print(f"HTTP {r.status_code}")
    if r.status_code != 200:
        print(r.text[:500])
        return

    posts = r.json()
    if not posts:
        print("글 없음")
        return

    post = posts[0]
    post_id = post["id"]
    print(f"\n최근 글 ID: {post_id}, 제목: {post.get('title',{}).get('rendered','')[:50]}")
    print(f"\n[meta 필드 전체 내용]")
    print(json.dumps(post.get("meta", {}), indent=2, ensure_ascii=False))

    # RankMath REST 엔드포인트가 별도로 있는지 확인
    print(f"\n[RankMath 전용 엔드포인트 시도]")
    r2 = requests.get(f"{SITE_URL}/wp-json/rankmath/v1/getHead",
                      auth=(WP_USER, WP_PASS),
                      params={"url": post.get("link", "")},
                      timeout=15)
    print(f"rankmath/v1/getHead → HTTP {r2.status_code}")

    # custom-fields 형태로도 확인
    print(f"\n[전체 post 응답에서 meta 관련 키 전부 나열]")
    for k in post.keys():
        if "meta" in k.lower() or "rank" in k.lower() or "seo" in k.lower():
            print(f"  {k}: {str(post[k])[:200]}")


if __name__ == "__main__":
    main()
