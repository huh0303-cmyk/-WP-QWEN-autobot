#!/usr/bin/env python3
"""Audit and repair every English Blogger post without touching its images.

The supported Blogger v3 Post resource has no per-post Search description
field.  This worker therefore repairs body/title through the API and emits a
complete editor-ready description for every post, with an exact edit URL.
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
import time
from difflib import SequenceMatcher
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.openai_text import openai_available, openai_generate_text

OUT = ROOT / "artifacts" / "blogger-all-posts-repair.json"
GENERIC_TITLE = re.compile(
    r"(?i)\b(?:a closer look|made simple|step[- ]by[- ]step|right the first time|"
    r"things to (?:look for|check)|questions people ask|what nobody tells you|"
    r"practical guide|complete guide|your (?:smart|confident|practical)?\s*checklist|"
    r"costs,? eligibility|frequently confused points|experts explain)\b"
)
SUMMARY_HEADING = re.compile(
    r"(?is)<h([1-6])\b[^>]*>\s*(?:<[^>]+>\s*)*(?:한국어|한글|Korean)\s*(?:핵심\s*)?(?:요약|summary)\s*(?:</[^>]+>\s*)*</h\1>"
)
SUMMARY_CHECKLIST_PARAGRAPH = re.compile(
    r"(?is)<p\b[^>]*>\s*(?:<(?:strong|b|span|em|i)\b[^>]*>\s*)*(?:한국어|한글)\s*(?:핵심\s*)?요약\s*체크리스트\s*:?.*?</p>"
    r"\s*(?:<(?:ul|ol)\b[^>]*>.*?</(?:ul|ol)>)?"
)
SUMMARY_PARAGRAPH = re.compile(
    r"(?is)<p\b[^>]*>\s*(?:<(?:strong|b|span|em|i)\b[^>]*>\s*)*(?:한국어|한글)\s*(?:핵심\s*)?요약\s*:?.*?</p>"
)


def access_token() -> str:
    response = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["BLOGGER_GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["BLOGGER_GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["BLOGGER_GOOGLE_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }, timeout=30)
    response.raise_for_status()
    return response.json()["access_token"]


def api_request(method: str, url: str, **kwargs) -> requests.Response:
    """Retry transient Blogger/Google failures without repeating a succeeded write."""
    for attempt in range(1, 6):
        response = requests.request(method, url, **kwargs)
        if response.status_code not in {429, 500, 502, 503, 504}:
            response.raise_for_status()
            return response
        if attempt == 5:
            response.raise_for_status()
        time.sleep(min(20, attempt * 3))
    raise RuntimeError("unreachable Blogger API retry state")


def load_sites() -> list[dict]:
    profiles = json.loads((ROOT / "config/content_engine_profiles.json").read_text(encoding="utf-8"))["profiles"]
    sites, seen = [], set()
    for profile in profiles:
        blog = profile.get("blogspot") or {}
        blog_id = str(blog.get("destination_id") or "")
        if not blog.get("ready_for_automation") or not blog_id or blog_id in seen:
            continue
        seen.add(blog_id)
        sites.append({"site_key": profile["site_key"], "blog_id": blog_id, "url": blog.get("url", ""), "theme": blog.get("theme") or profile.get("wordpress", {}).get("theme", ""), "language": profile.get("language", "en")})
    return sites


def list_all_posts(site: dict, headers: dict[str, str]) -> list[dict]:
    endpoint = f"https://www.googleapis.com/blogger/v3/blogs/{site['blog_id']}/posts"
    found: dict[str, dict] = {}
    for status in ("draft", "live", "scheduled"):
        token = ""
        while True:
            params = {"status": status, "view": "ADMIN", "fetchBodies": "true", "maxResults": 50}
            if token:
                params["pageToken"] = token
            response = api_request("GET", endpoint, params=params, headers=headers, timeout=45)
            payload = response.json()
            for post in payload.get("items", []):
                post["_status"] = status
                found[str(post.get("id"))] = post
            token = payload.get("nextPageToken", "")
            if not token:
                break
    return list(found.values())


def image_sources(content: str) -> list[str]:
    return re.findall(r'''(?is)<img\b[^>]*\bsrc=["']([^"']+)["']''', content or "")


def clean_english_content(content: str) -> tuple[str, int]:
    removed = 0
    content, count = SUMMARY_CHECKLIST_PARAGRAPH.subn("", content)
    removed += count
    content, count = SUMMARY_PARAGRAPH.subn("", content)
    removed += count
    while True:
        match = SUMMARY_HEADING.search(content)
        if not match:
            break
        next_heading = re.search(r"(?is)<h[1-6]\b", content[match.end():])
        end = match.end() + next_heading.start() if next_heading else len(content)
        content = content[:match.start()] + content[end:]
        removed += 1
    replacements = {
        "자주 묻는 질문 (FAQ)": "Frequently Asked Questions",
        "자주 묻는 질문": "Frequently Asked Questions",
        "관련 이미지": "related image",
    }
    for source, target in replacements.items():
        content = content.replace(source, target)
    return content, removed


def title_key(title: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", html.unescape(title).lower()).strip()


def repetitive_ids(records: list[dict]) -> set[str]:
    flagged = {r["post_id"] for r in records if GENERIC_TITLE.search(r["title"])}
    for index, left in enumerate(records):
        for right in records[index + 1:]:
            a, b = title_key(left["title"]), title_key(right["title"])
            if min(len(a), len(b)) >= 24 and SequenceMatcher(None, a, b).ratio() >= 0.78:
                flagged.update((left["post_id"], right["post_id"]))
    return flagged


def complete_description(title: str, content: str, language: str = "en") -> str:
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<[^>]+>", " ", content))).strip()
    topic = re.sub(r"\s+", " ", title).strip(" .,:;!?")
    topic = topic[:46].rsplit(" ", 1)[0] if len(topic) > 46 and " " in topic[:46] else topic[:46]
    if language == "ko":
        candidates = [
            f"{topic}의 핵심 내용과 준비 절차, 확인 기준, 비용과 시기, 실제 적용 방법, 놓치기 쉬운 주의사항을 독자가 바로 활용할 수 있도록 신뢰할 수 있는 기준과 함께 차근차근 정리합니다.",
            f"{topic}에 필요한 핵심 정보와 확인 순서, 준비 과정과 비용, 적용 방법과 주의사항을 실제 활용 흐름에 맞춰 비교하고 판단할 수 있도록 신뢰할 수 있는 기준과 함께 자세히 안내합니다.",
        ]
    else:
        candidates = [
        f"Explore {topic} with practical steps, key checks, timing, costs, and useful details for confident planning.",
        f"Learn about {topic}, including practical steps, key checks, timing, costs, and preparation tips.",
        ]
    first_sentence = re.split(r"(?<=[.!?])\s+", text)[0][:119].strip()
    if 100 <= len(first_sentence) <= 119 and first_sentence.endswith((".", "!", "?")):
        return first_sentence
    for candidate in candidates:
        if 100 <= len(candidate) <= 119:
            return candidate
    candidate = candidates[0]
    overflow = max(0, len(candidate) - 119)
    topic = topic[:max(12, len(topic) - overflow)].rstrip(" ,;:-")
    candidate = (
        f"{topic}의 핵심 내용과 준비 절차, 확인 기준, 비용과 시기, 실제 적용 방법, 놓치기 쉬운 주의사항을 독자가 바로 활용할 수 있도록 신뢰할 수 있는 기준과 함께 차근차근 정리합니다."
        if language == "ko" else
        f"Explore {topic} with practical steps, key checks, timing, costs, and useful details for confident planning."
    )
    if not 100 <= len(candidate) <= 119:
        raise ValueError(f"could not create complete search description for {title!r}")
    return candidate


def rewrite_title(record: dict, used_titles: list[str]) -> str:
    if not openai_available():
        raise RuntimeError("GPT-5 mini is required for non-repetitive title repair")
    body = re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<[^>]+>", " ", record["cleaned_content"]))).strip()
    language = "Korean" if record["language"] == "ko" else "English"
    for _ in range(3):
        prompt = f"""Rewrite one blog-post title in {language}.
Return only the title, without quotes or explanation.
Make it specific to the actual article, natural, and 35-68 characters including spaces.
Do not use Guide, Practical, Navigating, Step-by-Step, Made Simple, Checklist, What Nobody Tells You, A Closer Look, or Experts Explain.
Do not reuse the syntax or rhythm of the old title. Do not invent facts.
Old title: {record['title']}
Article text: {body[:1800]}
Titles already used in this portfolio: {' | '.join(used_titles[-80:])}
"""
        candidate = openai_generate_text(prompt, temperature=0.8, max_retries=1).strip().strip('"“”')
        candidate = re.sub(r"\s+", " ", candidate)
        if not 20 <= len(candidate) <= 70 or GENERIC_TITLE.search(candidate):
            continue
        normalized = title_key(candidate)
        if any(SequenceMatcher(None, normalized, title_key(existing)).ratio() >= 0.70 for existing in used_titles):
            continue
        return candidate
    raise RuntimeError(f"could not generate a unique title for {record['site_key']}:{record['post_id']}")


def main() -> int:
    apply_changes = os.environ.get("APPLY_CHANGES", "false").lower() == "true"
    headers = {"Authorization": f"Bearer {access_token()}"}
    records, site_counts = [], {}
    sites = load_sites()
    for site in sites:
        posts = list_all_posts(site, headers)
        site_counts[site["site_key"]] = len(posts)
        for post in posts:
            content = str(post.get("content") or "")
            cleaned, removed = clean_english_content(content) if site["language"] == "en" else (content, 0)
            if image_sources(content) != image_sources(cleaned):
                raise RuntimeError(f"image preservation guard failed for {site['site_key']}:{post.get('id')}")
            title = html.unescape(str(post.get("title") or "")).strip()
            records.append({
                "site_key": site["site_key"], "blog_id": site["blog_id"], "site_url": site["url"], "language": site["language"],
                "post_id": str(post.get("id") or ""), "status": post.get("_status", ""),
                "title": title, "content": content, "cleaned_content": cleaned,
                "korean_summary_blocks": removed, "content_changed": cleaned != content,
                "images_before": image_sources(content),
                "images_after_cleanup": image_sources(cleaned),
                "edit_url": f"https://www.blogger.com/blog/post/edit/{site['blog_id']}/{post.get('id', '')}",
            })
        time.sleep(0.1)

    flagged = repetitive_ids(records)
    used_titles = [record["title"] for record in records if record["post_id"] not in flagged]
    for record in records:
        record["title_repair_required"] = record["post_id"] in flagged
        record["new_title"] = rewrite_title(record, used_titles) if apply_changes and record["title_repair_required"] else record["title"]
        used_titles.append(record["new_title"])
        record["search_description"] = complete_description(record["new_title"], record["cleaned_content"], record["language"])
        record["search_description_length"] = len(record["search_description"])
        record["search_description_status"] = "editor_input_required_blogger_api_has_no_field"

    # Title rewriting requires editorial generation and is deliberately kept
    # separate from this deterministic inventory/cleanup pass.  The audit
    # identifies the exact records; no title is replaced with a guessed formula.
    repaired = 0
    if apply_changes:
        for record in records:
            if not record["content_changed"] and record["new_title"] == record["title"]:
                continue
            endpoint = f"https://www.googleapis.com/blogger/v3/blogs/{record['blog_id']}/posts/{record['post_id']}"
            response = api_request(
                "PATCH",
                endpoint, headers=headers,
                json={"kind": "blogger#post", "id": record["post_id"], "title": record["new_title"], "content": record["cleaned_content"]},
                timeout=45,
            )
            returned = response.json()
            if image_sources(str(returned.get("content") or "")) != record["images_before"]:
                raise RuntimeError(f"live image verification failed for {record['site_key']}:{record['post_id']}")
            record["content_repair_applied"] = True
            record["title_repair_applied"] = record["new_title"] != record["title"]
            repaired += 1

    for record in records:
        record.pop("content", None)
        record.pop("cleaned_content", None)
    summary = {
        "blogs_total": len(site_counts),
        "english_blogs": sum(site["language"] == "en" for site in sites),
        "korean_blogs": sum(site["language"] == "ko" for site in sites),
        "posts_total": len(records),
        "drafts": sum(r["status"] == "draft" for r in records),
        "published": sum(r["status"] == "live" for r in records),
        "scheduled": sum(r["status"] == "scheduled" for r in records),
        "korean_summary_posts": sum(r["korean_summary_blocks"] > 0 for r in records),
        "repetitive_title_posts": len(flagged),
        "titles_repaired": sum(bool(r.get("title_repair_applied")) for r in records),
        "search_descriptions_prepared": len(records),
        "content_repairs_applied": repaired,
        "images_preserved": all(r.get("images_before") == r.get("images_after_cleanup") for r in records),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"summary": summary, "site_counts": site_counts, "posts": records}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
