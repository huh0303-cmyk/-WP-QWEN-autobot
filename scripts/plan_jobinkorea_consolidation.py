#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plan_jobinkorea_consolidation.py (읽기 전용 — 조사만, 실행 없음)
─────────────────────────────────────────────────────────────
2026-08-22: 사용자 결정 — 구직 3사이트(jobkoreaglobal/jobkorea365/
jobinkorea365) 중 jobkoreaglobal은 고용주 대상이라 별도 유지, jobkorea365와
jobinkorea365는 둘 다 구직자 대상이라 jobkorea365.com으로 통합(색인율
15.9% > 12.3%)하기로 함. 이 스크립트는 jobinkorea365.com의 실제 색인된
글을 jobkorea365.com의 카테고리로 매핑해 301 리다이렉트 계획(manifest)만
만든다 — 실행(리다이렉트 실제 적용)은 별도 스크립트 + 사용자 확인 후.

우선순위: network-index-privacy-sweep.yml이 만든 index_audit_manifest.json이
있으면 그걸 재사용(이미 실제 GSC 데이터로 jobinkorea365.com 색인 여부를
갖고 있음) — 없으면 이 스크립트 자체적으로 WP REST에서 발행글만 가져와
"제목이 있다"는 사실만으로 초안을 만들고 색인 여부는 표시하지 않는다.

카테고리 매핑(제목/구조 기반 대략적 매핑 — 정확한 기사 대 기사 매칭은
신뢰할 수 없어서 카테고리 아카이브 페이지로 리다이렉트하는 게 SEO상
더 안전함):
  Job Search        -> jobkorea365.com/category/jobs (또는 실제 카테고리 slug)
  Interviews         -> jobkorea365.com/category/jobs
  Visa Compatibility -> jobkorea365.com/category/work-visa
  (매칭 안 되는 카테고리) -> jobkorea365.com 홈
"""
import json
import os
import re
import sys

import requests

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

FROM_SITE = "https://jobinkorea365.com"
TO_SITE = "https://jobkorea365.com"
AUDIT_MANIFEST = "index_audit_manifest.json"
OUT = "jobinkorea365_consolidation_manifest.json"

CATEGORY_MAP = {
    "job search": "jobs",
    "interviews": "jobs",
    "visa compatibility": "work-visa",
}
DEFAULT_TARGET = "/"  # 매칭 안 되면 홈으로


def load_target_categories():
    """jobkorea365.com에 실제 존재하는 카테고리(slug) 목록을 가져와서
    CATEGORY_MAP의 값이 진짜 존재하는지 검증."""
    try:
        r = requests.get(f"{TO_SITE}/wp-json/wp/v2/categories",
                          params={"per_page": 100, "_fields": "id,slug,name"}, timeout=15)
        r.raise_for_status()
        return {c["slug"]: c for c in r.json()}
    except Exception as e:
        print(f"  ⚠️ {TO_SITE} 카테고리 조회 실패: {e}")
        return {}


def load_indexed_from_sweep_manifest():
    """privacy sweep이 만든 index_audit_manifest.json에서 jobinkorea365.com의
    실제 색인된(state=indexed) 글만 뽑는다."""
    if not os.path.exists(AUDIT_MANIFEST):
        return None
    with open(AUDIT_MANIFEST, encoding="utf-8") as f:
        data = json.load(f)
    entry = data.get("sites", {}).get(FROM_SITE)
    if not entry:
        return None
    posts = [p for p in entry.get("posts", {}).values() if p.get("state") == "indexed"]
    return posts


def fetch_all_published_fallback():
    """sweep manifest가 아직 없을 때 폴백 — 발행글 전체를 가져오되
    색인 여부는 unknown으로 표시."""
    posts, page = [], 1
    while True:
        r = requests.get(f"{FROM_SITE}/wp-json/wp/v2/posts",
                          params={"per_page": 100, "page": page, "status": "publish",
                                   "_fields": "id,title,link,categories"}, timeout=20)
        if r.status_code != 200:
            break
        batch = r.json()
        if not isinstance(batch, list) or not batch:
            break
        for p in batch:
            posts.append({"id": p["id"], "url": p["link"],
                          "title": p["title"]["rendered"], "state": "unknown"})
        if len(batch) < 100:
            break
        page += 1
    return posts


def get_post_category_names(post_id):
    try:
        r = requests.get(f"{FROM_SITE}/wp-json/wp/v2/posts/{post_id}",
                          params={"_embed": "wp:term"}, timeout=15)
        r.raise_for_status()
        terms = r.json().get("_embedded", {}).get("wp:term", [[]])
        cats = terms[0] if terms else []
        return [c["name"] for c in cats]
    except Exception:
        return []


def main():
    posts = load_indexed_from_sweep_manifest()
    source = "GSC 실색인 데이터(index_audit_manifest.json)"
    if posts is None:
        print(f"  ℹ️ {AUDIT_MANIFEST} 아직 없음(스윕 진행 중) — 발행글 전체로 초안만 작성, 색인여부는 unknown")
        posts = fetch_all_published_fallback()
        source = "WP 발행글 전체(색인여부 미확인, 초안)"

    target_cats = load_target_categories()
    plan = []
    for p in posts:
        title = re.sub(r"<[^>]+>", "", p.get("title", "")).strip()
        # index_audit_manifest.json이든 폴백이든 둘 다 카테고리 정보가 없어서
        # 매번 개별 조회 필요(사이트 하나 대상이라 부담 크지 않음).
        cat_names = get_post_category_names(p["id"])
        url = p.get("url") or p.get("url", "")
        cat_key = next((c.lower() for c in cat_names if c.lower() in CATEGORY_MAP), None)
        target_slug = CATEGORY_MAP.get(cat_key)
        if target_slug and target_slug in target_cats:
            redirect_to = f"{TO_SITE}/category/{target_slug}/"
        else:
            redirect_to = f"{TO_SITE}{DEFAULT_TARGET}"
        plan.append({
            "id": p["id"], "from_url": p.get("url", ""), "title": title,
            "index_state": p.get("state", "unknown"),
            "source_categories": cat_names, "redirect_to": redirect_to,
        })

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"source": source, "from_site": FROM_SITE, "to_site": TO_SITE,
                    "count": len(plan), "plan": plan}, f, ensure_ascii=False, indent=2)

    print(f"=== {FROM_SITE} → {TO_SITE} 통합 계획 ({source}) ===")
    print(f"총 {len(plan)}건")
    by_target = {}
    for item in plan:
        by_target.setdefault(item["redirect_to"], 0)
        by_target[item["redirect_to"]] += 1
    for t, c in sorted(by_target.items(), key=lambda x: -x[1]):
        print(f"  {c:4d}건 → {t}")
    print(f"\n상세 계획 저장: {OUT} (아직 실행 안 됨 — 검토 후 적용 스크립트 별도 실행 필요)")


if __name__ == "__main__":
    main()
