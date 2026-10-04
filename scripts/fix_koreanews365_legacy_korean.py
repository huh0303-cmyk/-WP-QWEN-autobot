#!/usr/bin/env python3
"""One-time repair: convert the legacy koreanews365.blogspot.com blog to Korean.

Safety:
- Targets only the exact legacy blog URL / blog ID.
- Never deletes posts.
- Preserves publication status, labels count, images, links and HTML structure.
- Translates title/body/labels only.
"""
from __future__ import annotations

import html
import json
import os
import re
import time
from pathlib import Path

import requests

BLOG_URL = "https://koreanews365.blogspot.com/"
BLOG_ID = "1548983591062080646"
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
DRY_RUN = os.getenv("DRY_RUN", "false").strip().lower() == "true"
OUT = Path("artifacts/koreanews365_ko_repair.json")

TAG_RE = re.compile(r"<[^>]+>", re.S)
URL_RE = re.compile(r"https?://[^\s<>\"']+")
PLACEHOLDER_RE = re.compile(r"__SAFE_(?:TAG|URL)_\d+__")


def oauth_token() -> str:
    r = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": os.environ["BLOGGER_GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["BLOGGER_GOOGLE_CLIENT_SECRET"],
            "refresh_token": os.environ["BLOGGER_GOOGLE_REFRESH_TOKEN"],
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def api(method: str, url: str, headers: dict, **kwargs):
    for attempt in range(1, 6):
        r = requests.request(method, url, headers=headers, timeout=60, **kwargs)
        if r.status_code not in {429, 500, 502, 503, 504}:
            r.raise_for_status()
            return r
        if attempt == 5:
            r.raise_for_status()
        time.sleep(attempt * 3)
    raise RuntimeError("unreachable")


def protect_html(value: str):
    saved: list[tuple[str, str]] = []

    def tag(m):
        key = f"__SAFE_TAG_{len(saved)}__"
        saved.append((key, m.group(0)))
        return key

    protected = TAG_RE.sub(tag, value or "")

    def url(m):
        key = f"__SAFE_URL_{len(saved)}__"
        saved.append((key, m.group(0)))
        return key

    protected = URL_RE.sub(url, protected)
    return protected, dict(saved)


def restore_html(value: str, saved: dict[str, str]) -> str:
    out = value
    for key, original in saved.items():
        out = out.replace(key, original)
    return out


def openai_translate(title: str, content: str, labels: list[str]) -> dict:
    protected_content, saved = protect_html(content)
    label_text = json.dumps(labels, ensure_ascii=False)
    prompt = f"""You are the Korean editor of KoreaNews365, a Korean-language general news and current-affairs publication.

Translate the following Japanese Blogger post into natural, professional Korean.
Rules:
1. Translate the TITLE, BODY, and LABELS into Korean.
2. Do not add, remove, invent, correct, or speculate about facts.
3. Preserve the exact meaning and chronology of the source.
4. Keep every placeholder such as __SAFE_TAG_0__ and __SAFE_URL_1__ exactly as written. Do not translate, rename, duplicate, or delete placeholders.
5. The placeholders represent HTML tags and URLs and will be restored automatically.
6. Keep the article readable as a Korean news/article post. Do not add a Korean-summary section or commentary.
7. Return JSON only with keys: title, content, labels.
8. labels must be a JSON array of short Korean labels.

TITLE:
{title}

LABELS:
{label_text}

BODY:
{protected_content}
"""

    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
                 "Content-Type": "application/json"},
        json={
            "model": OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": "You translate Japanese editorial HTML into Korean without changing facts or HTML placeholders."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        },
        timeout=180,
    )
    r.raise_for_status()
    payload = r.json()
    raw = payload["choices"][0]["message"]["content"]
    result = json.loads(raw)

    new_content = restore_html(str(result["content"]), saved)
    # Every protected object must survive exactly once.
    for key in saved:
        if new_content.count(saved[key]) != 1:
            raise RuntimeError(f"HTML preservation failed for {key}")

    return {
        "title": str(result["title"]).strip(),
        "content": new_content,
        "labels": [str(x).strip() for x in result.get("labels", []) if str(x).strip()],
    }


def list_posts(headers: dict) -> list[dict]:
    url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts"
    posts = []
    token = ""
    while True:
        params = {"status": "live", "view": "ADMIN", "fetchBodies": "true", "maxResults": 50}
        if token:
            params["pageToken"] = token
        data = api("GET", url, headers, params=params).json()
        posts.extend(data.get("items", []))
        token = data.get("nextPageToken", "")
        if not token:
            break
    return posts


def verify_target(headers: dict) -> None:
    data = api("GET", f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}", headers).json()
    actual = str(data.get("url", "")).rstrip("/")
    if actual != BLOG_URL.rstrip("/"):
        raise RuntimeError(f"Target mismatch: expected {BLOG_URL}, got {actual}")


def main() -> int:
    required = ["BLOGGER_GOOGLE_CLIENT_ID", "BLOGGER_GOOGLE_CLIENT_SECRET",
                "BLOGGER_GOOGLE_REFRESH_TOKEN", "OPENAI_API_KEY"]
    missing = [x for x in required if not os.getenv(x)]
    if missing:
        raise SystemExit("Missing required secrets: " + ", ".join(missing))

    token = oauth_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    verify_target(headers)
    posts = list_posts(headers)

    results = []
    for post in posts:
        old_title = html.unescape(str(post.get("title", ""))).strip()
        old_content = str(post.get("content", ""))
        old_labels = list(post.get("labels") or [])
        translated = openai_translate(old_title, old_content, old_labels)

        # Never allow a translation that still looks predominantly Japanese.
        japanese_chars = len(re.findall(r"[\u3040-\u30ff\u3400-\u4dbf]", translated["title"] + translated["content"]))
        korean_chars = len(re.findall(r"[\uac00-\ud7a3]", translated["title"] + translated["content"]))
        if japanese_chars > 20 and japanese_chars > korean_chars:
            raise RuntimeError(f"Translation still appears Japanese: post {post['id']}")

        record = {
            "post_id": str(post["id"]),
            "url": post.get("url", ""),
            "old_title": old_title,
            "new_title": translated["title"],
            "old_labels": old_labels,
            "new_labels": translated["labels"],
            "images_before": len(re.findall(r"<img\b", old_content, re.I)),
            "dry_run": DRY_RUN,
        }

        if not DRY_RUN:
            endpoint = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/{post['id']}"
            body = {
                "kind": "blogger#post",
                "id": str(post["id"]),
                "title": translated["title"],
                "content": translated["content"],
                "labels": translated["labels"],
            }
            updated = api("PATCH", endpoint, headers, json=body).json()
            updated_content = str(updated.get("content", ""))
            if len(re.findall(r"<img\b", updated_content, re.I)) != record["images_before"]:
                raise RuntimeError(f"Image preservation verification failed: post {post['id']}")
            record["status"] = "updated"
        else:
            record["status"] = "dry_run"

        results.append(record)
        time.sleep(1)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "blog_url": BLOG_URL,
        "blog_id": BLOG_ID,
        "posts_found": len(posts),
        "posts_updated": sum(r["status"] == "updated" for r in results),
        "results": results,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "blog_url": BLOG_URL,
        "posts_found": len(posts),
        "posts_updated": sum(r["status"] == "updated" for r in results),
        "dry_run": DRY_RUN,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
