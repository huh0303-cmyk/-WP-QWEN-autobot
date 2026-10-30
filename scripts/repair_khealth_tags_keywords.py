#!/usr/bin/env python3
"""Repair K-Health365 topic pollution across existing WordPress posts.

This script does not delete posts. It only corrects known repeated expo
headlines, replaces duplicate/generic focus keywords, and removes unrelated
tag IDs from posts in publish/future/draft/pending/private states.
"""
from __future__ import annotations

import html
import json
import os
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

import requests

SITE = "https://k-health365.com"
WP_USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
PASSWORD = os.getenv("KHEALTH365COM", "").strip()
STATUSES = ("publish", "future", "draft", "pending", "private")
OUT = Path("artifacts/khealth-tags-keywords-repair.json")
STOP = {
    "예약됨", "가이드", "완벽", "총정리", "알아보기", "위한", "관한", "그리고",
    "방법", "정보", "확인할", "확인하는", "활용을", "통한", "에서", "으로",
    "the", "and", "for", "with", "guide", "tips", "best",
}

# Known repeated-template titles seen in the K-Health365 scheduled queue.
# Exact matches only; already-corrected titles are left untouched.
TITLE_RENAMES = {
    "통합의학박람회 관람을 통한 근거 중심 건강 정보 선별과 일상 관리 방안":
        "통합의학박람회 안내 자료의 근거 수준을 확인하는 5단계",
    "통합의학박람회에서 확인하는 근거 기반 질환 예방과 올바른 보완요법 활용 기준":
        "보완요법 홍보 문구를 평가할 때 확인할 임상 근거",
    "신체 균형 회복을 위한 웰니스 트렌드 기반의 생활 습관 관리 전략":
        "웰니스 프로그램 비용을 내기 전 확인할 효과·안전 기준",
    "통합의학박람회 활용을 통한 근거 기반 질환 예방 및 보완요법 이해":
        "보완요법과 표준 치료를 병행할 때 확인할 위험과 원칙",
    "통합의학박람회에서 확인하는 근거 기반 질환 예방과 통합적 건강 관리 지침":
        "건강 상담 후 의료진에게 확인할 질문과 다음 단계",
    "통합의학박람회 활용을 통한 질환 예방과 근거 중심의 건강 관리 체계 수립":
        "만성질환 위험을 평가하고 검진 계획을 세우는 방법",
    "통합의학박람회에서 확인하는 근거 중심의 건강 관리와 질환 예방 수칙":
        "건강박람회 자료의 출처와 연구 근거를 검증하는 법",
    "대한민국 통합의학박람회 개막과 보완의학의 객관적 검증 및 질환 예방 가이드":
        "보완의학의 안전성을 확인할 때 살펴볼 근거와 한계",
}


def request(method: str, path: str, **kwargs):
    response = requests.request(
        method, f"{SITE}/wp-json/wp/v2/{path}", auth=(WP_USER, PASSWORD),
        timeout=40, **kwargs,
    )
    response.raise_for_status()
    return response


def title_text(post: dict) -> str:
    raw = (post.get("title") or {}).get("rendered", "") if isinstance(post.get("title"), dict) else post.get("title", "")
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", raw)).split())


def focus_from_title(title: str) -> str:
    text = re.sub(r"\s*[—|]\s*(예약됨|초안).*?$", "", title, flags=re.I).strip()
    tokens = re.findall(r"[가-힣A-Za-z][가-힣A-Za-z0-9+-]*", text)
    cleaned = []
    for token in tokens:
        token = re.sub(r"(에서|으로|에게|과|와|을|를|은|는|이|가|에|의|할|하는|된|통한|위한|등)$", "", token)
        if len(token) >= 2 and token.casefold() not in STOP and token.casefold() not in {x.casefold() for x in cleaned}:
            cleaned.append(token)
    # Prefer the distinctive end of the headline instead of a repeated broad lead.
    return " ".join(cleaned[-4:] if len(cleaned) > 4 else cleaned)[:80].strip()


def candidate_tags(title: str, focus: str) -> list[str]:
    tokens = re.findall(r"[가-힣A-Za-z][가-힣A-Za-z0-9+-]*", title)
    phrases = [focus]
    for size in (2, 3):
        for i in range(max(0, len(tokens) - size + 1)):
            phrases.append(" ".join(tokens[i:i + size]))
    phrases.extend(tokens)
    # The shared guard removes anything not tied to the title/focus and caps at 5.
    from automation_hub.article_metadata_guard import sanitize_article_labels
    return sanitize_article_labels(phrases, title=title, keyword=focus, limit=5)


def fetch_posts() -> list[dict]:
    posts = []
    for status in STATUSES:
        page = 1
        while True:
            batch = request(
                "GET", "posts",
                params={"status": status, "context": "edit", "per_page": 100, "page": page,
                        "_fields": "id,status,date,slug,title,tags,meta"},
            ).json()
            posts.extend(batch)
            if len(batch) < 100:
                break
            page += 1
    return posts


def fetch_tag_names() -> dict[int, str]:
    names: dict[int, str] = {}
    page = 1
    while True:
        batch = request("GET", "tags", params={"per_page": 100, "page": page, "_fields": "id,name"}).json()
        for tag in batch:
            names[int(tag["id"])] = html.unescape(str(tag.get("name") or ""))
        if len(batch) < 100:
            break
        page += 1
    return names


def ensure_tag(name: str, cache: dict[str, int]) -> int:
    key = name.casefold()
    if key in cache:
        return cache[key]
    found = request("GET", "tags", params={"search": name, "per_page": 100, "_fields": "id,name"}).json()
    exact = next((row for row in found if html.unescape(row.get("name", "")).casefold() == key), None)
    if exact:
        cache[key] = int(exact["id"])
        return cache[key]
    response = requests.post(
        f"{SITE}/wp-json/wp/v2/tags", auth=(WP_USER, PASSWORD),
        json={"name": name}, timeout=40,
    )
    if response.status_code == 400:
        try:
            term_id = response.json().get("data", {}).get("term_id")
            if term_id:
                cache[key] = int(term_id)
                return cache[key]
        except Exception:
            pass
    response.raise_for_status()
    cache[key] = int(response.json()["id"])
    return cache[key]


def normalized(title: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]+", "", title.casefold())


def duplicate_candidates(posts: list[dict]) -> list[dict]:
    values = [(int(p["id"]), title_text(p), normalized(title_text(p))) for p in posts]
    found = []
    for i, (left_id, left_title, left) in enumerate(values):
        if not left:
            continue
        for right_id, right_title, right in values[i + 1:]:
            ratio = SequenceMatcher(None, left, right).ratio() if right else 0
            if left == right or ratio >= 0.82:
                found.append({"post_id_a": left_id, "post_id_b": right_id, "similarity": round(ratio, 3),
                              "title_a": left_title, "title_b": right_title})
    return found


def main() -> int:
    if not PASSWORD:
        raise SystemExit("KHEALTH365COM is required")
    posts = fetch_posts()
    focus_counts = Counter(
        str((post.get("meta") or {}).get("rank_math_focus_keyword") or "").strip().casefold()
        for post in posts
        if str((post.get("meta") or {}).get("rank_math_focus_keyword") or "").strip()
    )
    tag_names = fetch_tag_names()
    tag_cache = {name.casefold(): tag_id for tag_id, name in tag_names.items()}
    result = {
        "site": SITE, "scanned": len(posts), "titles_changed": 0, "tags_repaired": 0,
        "focus_keywords_repaired": 0, "verified": 0, "failed": [], "duplicates_after": [],
    }

    for post in posts:
        post_id = int(post["id"])
        title = title_text(post)
        current_tags = [int(x) for x in post.get("tags") or []]
        meta = post.get("meta") or {}
        current_focus = str(meta.get("rank_math_focus_keyword") or "").strip()
        payload: dict = {}

        new_title = TITLE_RENAMES.get(title)
        if new_title and new_title != title:
            payload["title"] = new_title
            title = new_title
            result["titles_changed"] += 1

        # Duplicate focus phrases are too broad for a multi-angle editorial queue.
        if not current_focus or focus_counts[current_focus.casefold()] > 1:
            focus = focus_from_title(title)
        else:
            focus = current_focus
        if focus and focus != current_focus:
            payload["meta"] = {"rank_math_focus_keyword": focus}
            result["focus_keywords_repaired"] += 1

        existing_names = [tag_names[tag_id] for tag_id in current_tags if tag_id in tag_names]
        labels = candidate_tags(title, focus or title)
        # Prefer existing relevant labels, then add title-derived phrases to fill only if useful.
        from automation_hub.article_metadata_guard import sanitize_article_labels
        labels = sanitize_article_labels(existing_names + labels, title=title, keyword=focus or title, limit=5)
        desired_ids = [ensure_tag(label, tag_cache) for label in labels]
        if current_tags != desired_ids:
            payload["tags"] = desired_ids
            result["tags_repaired"] += 1

        if payload:
            try:
                request("POST", f"posts/{post_id}", json=payload)
                saved = request("GET", f"posts/{post_id}", params={"context": "edit", "_fields": "id,title,tags,meta"}).json()
                if "tags" in payload and [int(x) for x in saved.get("tags") or []] != payload["tags"]:
                    raise RuntimeError("tag_ids_not_persisted")
                if "title" in payload and title_text(saved) != new_title:
                    raise RuntimeError("title_not_persisted")
                result["verified"] += 1
            except Exception as exc:
                result["failed"].append({"post_id": post_id, "error": str(exc)[:250]})

    # Re-fetch titles so the report reflects the actual saved state.
    final_posts = fetch_posts()
    result["duplicates_after"] = duplicate_candidates(final_posts)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "scanned": result["scanned"], "titles_changed": result["titles_changed"],
        "tags_repaired": result["tags_repaired"], "focus_keywords_repaired": result["focus_keywords_repaired"],
        "verified": result["verified"], "failed": len(result["failed"]),
        "remaining_duplicate_pairs": len(result["duplicates_after"]),
    }, ensure_ascii=False))
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
