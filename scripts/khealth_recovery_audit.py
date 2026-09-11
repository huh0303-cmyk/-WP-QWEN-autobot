#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""k-health365.com 복구용 전수 감사 — 절대 아무것도 지우거나 고치지 않는다.

REST 공개 API로는 발행글이 0건으로 보이지만(현재 사이트가 "찾을 수 없음"
상태), 실제로는 초안/비공개 등 다른 상태로 글이 남아있을 수 있어서
status=any(인증 필요)로 전수 조회한 뒤 다음을 찾아 JSON으로만 기록한다:

- broken_title: 제목에 ```html/<p> 같은 마크다운·HTML 코드펜스 잔재
- future_year: 본문/제목에 현재 연도보다 앞선(2027+) 연도
- lorem_ipsum: 본문에 플레이스홀더 텍스트
- boilerplate: "Product Highlight"/"Marketer" 같은, 우리 생성 코드 어디에도
  없는 문자열 — 실제 글 본문에 박혀있다면 어느 글인지 표시
- near_duplicate_titles: 정규화 후 동일/거의 동일한 제목

사용법:
    python scripts/khealth_recovery_audit.py --output artifacts/khealth-recovery-audit.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher

import requests

SITE = "https://k-health365.com"
WP_USER = os.environ.get("WP_USER", "").strip() or "huh0303@gmail.com"
PASSWORD = os.environ.get("KHEALTH365COM", "").strip()
CURRENT_YEAR = datetime.now(timezone.utc).year

BOILERPLATE_MARKERS = ["Product Highlight", "Lorem ipsum", "lorem ipsum", "Marketer"]
# 순서 중요: 더 구체적인 패턴을 먼저 둬서, 한 종류의 깨짐이 여러 패턴에
# 겹쳐 잡히며 노이즈를 만들지 않게 한다(예: ```html 은 ``` 로도 다시 안 잡음).
BROKEN_TITLE_PATTERNS = [r"```html", r"```", r"<p>", r"<html", r"^html\b"]


def fetch_all_posts():
    if not PASSWORD:
        raise SystemExit("Missing KHEALTH365COM app password")
    auth = (WP_USER, PASSWORD)
    posts = []
    page = 1
    while True:
        r = requests.get(
            f"{SITE}/wp-json/wp/v2/posts",
            auth=auth,
            params={
                "per_page": 100, "page": page, "status": "any",
                "_fields": "id,date,modified,status,link,title,content,excerpt",
            },
            timeout=30,
        )
        if r.status_code != 200:
            raise RuntimeError(f"posts fetch failed page={page}: HTTP {r.status_code} {r.text[:300]}")
        batch = r.json()
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return posts


def _rendered(field: dict | str) -> str:
    if isinstance(field, dict):
        return field.get("rendered", "")
    return field or ""


def _plain_text(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html)


def _normalize_title(title: str) -> str:
    return re.sub(r"[^0-9a-zA-Z가-힣]+", "", title).lower()


def find_broken_titles(title: str) -> list[str]:
    """가장 구체적인 패턴 하나만 보고한다 — ```html 은 ``` 로 또 잡혀서
    같은 깨짐이 두 번 보고되지 않게 첫 매치에서 멈춘다."""
    for pattern in BROKEN_TITLE_PATTERNS:
        if re.search(pattern, title, re.IGNORECASE):
            return [pattern]
    return []


def find_future_years(text: str) -> list[str]:
    # \b는 안 쓴다 — 한글은 파이썬 정규식에서 \w로 취급돼서 "2027년"처럼
    # 숫자 바로 뒤에 한글이 오면 단어경계가 안 생겨 매치가 실패한다.
    # 대신 숫자 앞뒤로 다른 숫자만 없으면(더 긴 숫자열의 일부가 아니면) 된다.
    years = set(re.findall(r"(?<!\d)(20\d{2})(?!\d)", text))
    return sorted(y for y in years if int(y) > CURRENT_YEAR)


def find_boilerplate(text: str) -> list[str]:
    return [marker for marker in BOILERPLATE_MARKERS if marker.lower() in text.lower()]


def find_near_duplicate_titles(posts: list[dict]) -> list[dict]:
    normalized = [(p["id"], _normalize_title(_rendered(p["title"]))) for p in posts]
    duplicates = []
    seen_pairs = set()
    for i in range(len(normalized)):
        id_a, norm_a = normalized[i]
        if not norm_a:
            continue
        for j in range(i + 1, len(normalized)):
            id_b, norm_b = normalized[j]
            if not norm_b or (id_a, id_b) in seen_pairs:
                continue
            ratio = SequenceMatcher(None, norm_a, norm_b).ratio()
            if norm_a == norm_b or ratio >= 0.9:
                duplicates.append({"post_id_a": id_a, "post_id_b": id_b, "similarity": round(ratio, 3)})
                seen_pairs.add((id_a, id_b))
    return duplicates


def audit_post(post: dict) -> dict | None:
    title = _rendered(post.get("title"))
    content_html = _rendered(post.get("content"))
    excerpt_html = _rendered(post.get("excerpt"))
    plain = _plain_text(content_html) + " " + _plain_text(excerpt_html)

    issues = {}
    broken = find_broken_titles(title)
    if broken:
        issues["broken_title"] = broken
    future_years = find_future_years(title + " " + plain)
    if future_years:
        issues["future_year"] = future_years
    if "lorem ipsum" in plain.lower():
        issues["lorem_ipsum"] = True
    boilerplate = find_boilerplate(plain) + find_boilerplate(title)
    if boilerplate:
        issues["boilerplate"] = sorted(set(boilerplate))

    if not issues:
        return None
    return {
        "id": post["id"],
        "status": post.get("status"),
        "date": post.get("date"),
        "link": post.get("link"),
        "title": title,
        "issues": issues,
    }


def build_audit() -> dict:
    posts = fetch_all_posts()
    flagged = [row for row in (audit_post(p) for p in posts) if row]
    duplicates = find_near_duplicate_titles(posts)
    status_counts: dict[str, int] = {}
    for p in posts:
        status_counts[p.get("status", "unknown")] = status_counts.get(p.get("status", "unknown"), 0) + 1

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "site": SITE,
        "mode": "AUDIT_ONLY_NO_CHANGES",
        "total_posts_scanned": len(posts),
        "status_counts": status_counts,
        "flagged_posts": flagged,
        "flagged_count": len(flagged),
        "near_duplicate_titles": duplicates,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/khealth-recovery-audit.json")
    args = parser.parse_args()

    audit = build_audit()
    from pathlib import Path
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "total_posts_scanned": audit["total_posts_scanned"],
        "status_counts": audit["status_counts"],
        "flagged_count": audit["flagged_count"],
        "near_duplicates": len(audit["near_duplicate_titles"]),
    }, ensure_ascii=False))
    print(f"AUDIT_WRITTEN={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
