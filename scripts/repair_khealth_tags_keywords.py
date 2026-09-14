#!/usr/bin/env python3
"""Audit every K-Health365 post and repair missing tags/focus keywords.

Post status, title and content are never changed. Near-duplicate titles are
reported for human review and are never deleted by this job.
"""
from __future__ import annotations

import html
import json
import os
import re
from difflib import SequenceMatcher
from pathlib import Path

import requests

SITE = "https://k-health365.com"
WP_USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
PASSWORD = os.getenv("KHEALTH365COM", "").strip()
STATUSES = ("publish", "future", "draft", "pending", "private")
OUT = Path("artifacts/khealth-tags-keywords-repair.json")
STOP = {"예약됨", "가이드", "완벽", "총정리", "알아보기", "위한", "관한", "그리고", "방법", "정보"}


def request(method: str, path: str, **kwargs):
    response = requests.request(method, f"{SITE}/wp-json/wp/v2/{path}", auth=(WP_USER, PASSWORD), timeout=40, **kwargs)
    response.raise_for_status()
    return response


def title_text(post: dict) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", (post.get("title") or {}).get("rendered", ""))).split())


def focus_from_title(title: str) -> str:
    text = re.sub(r"\s*[—|]\s*(예약됨|초안).*?$", "", title, flags=re.I).strip()
    for separator in (":", "—", "|"):
        candidate = text.split(separator, 1)[0].strip()
        if 3 <= len(candidate) <= 75:
            text = candidate
            break
    return text[:80].strip(" -:|")


def tags_from_title(title: str, focus: str) -> list[str]:
    tokens = re.findall(r"[가-힣A-Za-z][가-힣A-Za-z0-9+-]*", re.sub(r"[—|:].*$", "", title))
    values = [focus]
    for token in tokens:
        token = token.strip("-+")
        if len(token) >= 2 and token not in STOP and token.lower() not in {v.lower() for v in values}:
            values.append(token[:80])
    if len(values) < 5:
        values.extend(["건강관리", "건강정보", "예방과 관리", "복용 주의사항", "생활 건강"])
    unique = []
    for value in values:
        if value and value.lower() not in {x.lower() for x in unique}:
            unique.append(value)
    return unique[:8]


def fetch_posts() -> list[dict]:
    posts = []
    for status in STATUSES:
        page = 1
        while True:
            response = request("GET", "posts", params={"status": status, "context": "edit", "per_page": 100,
                                                        "page": page, "_fields": "id,status,title,tags,meta"})
            batch = response.json()
            posts.extend(batch)
            if len(batch) < 100:
                break
            page += 1
    return posts


def ensure_tag(name: str, cache: dict[str, int]) -> int:
    key = name.casefold()
    if key in cache:
        return cache[key]
    found = request("GET", "tags", params={"search": name, "per_page": 100}).json()
    exact = next((row for row in found if html.unescape(row.get("name", "")).casefold() == key), None)
    if exact:
        cache[key] = int(exact["id"])
        return cache[key]
    response = requests.post(f"{SITE}/wp-json/wp/v2/tags", auth=(WP_USER, PASSWORD), json={"name": name}, timeout=40)
    if response.status_code == 400 and response.json().get("code") == "term_exists":
        cache[key] = int(response.json()["data"]["term_id"])
        return cache[key]
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
            if left == right or ratio >= 0.92:
                found.append({"post_id_a": left_id, "post_id_b": right_id, "similarity": round(ratio, 3),
                              "title_a": left_title, "title_b": right_title})
    return found


def main() -> int:
    if not PASSWORD:
        raise SystemExit("KHEALTH365COM is required")
    posts = fetch_posts()
    cache: dict[str, int] = {}
    result = {"site": SITE, "scanned": len(posts), "tags_filled": 0, "focus_filled": 0,
              "verified": 0, "failed": [], "duplicates": duplicate_candidates(posts)}
    for post in posts:
        current_tags = [int(x) for x in post.get("tags") or []]
        current_focus = str((post.get("meta") or {}).get("rank_math_focus_keyword") or "").strip()
        if current_tags and current_focus:
            continue
        title = title_text(post)
        focus = current_focus or focus_from_title(title)
        payload: dict = {}
        if not current_focus:
            payload["meta"] = {"rank_math_focus_keyword": focus}
        if not current_tags:
            payload["tags"] = [ensure_tag(name, cache) for name in tags_from_title(title, focus)]
        try:
            request("POST", f"posts/{post['id']}", json=payload)
            saved = request("GET", f"posts/{post['id']}", params={"context": "edit", "_fields": "id,tags,meta"}).json()
            saved_focus = str((saved.get("meta") or {}).get("rank_math_focus_keyword") or "").strip()
            if not saved.get("tags") or not saved_focus:
                raise RuntimeError("tags_or_focus_not_persisted")
            result["tags_filled"] += int(not current_tags)
            result["focus_filled"] += int(not current_focus)
            result["verified"] += 1
        except Exception as exc:
            result["failed"].append({"post_id": post.get("id"), "error": str(exc)[:250]})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("scanned", "tags_filled", "focus_filled", "verified")}
                     | {"duplicate_candidates": len(result["duplicates"]), "failed": len(result["failed"])}, ensure_ascii=False))
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
