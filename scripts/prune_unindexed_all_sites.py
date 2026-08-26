#!/usr/bin/env python3
"""2026-08-26 사용자 지시 — 25개 블로그를 '승인 재도전용 깨끗한 상태'로 정리.

원칙
- 뉴스 2개(koreanews365.com, theseouljournal.com)는 대상에서 제외.
- kskin365.com / oliveyoungkorea.com 은 기존 글을 전면 리셋: 현재 공개글 전부 비공개.
  (두 사이트는 이전 색인 정리에서 누락됐고, 공개 샘플에서 대량 AI 템플릿 흔적이 확인됨.)
- 나머지 23개 블로그는 '색인 여부'보다 '품질'을 우선한다. 아래 강한 휴리스틱에서
  저품질/대량생산 흔적/이미지 부실이 명확한 글만 비공개로 전환한다.
- 삭제는 하지 않고 WordPress status=private 로만 바꾼다. 언제든 복구 가능하다.
- 외부 유료 LLM/API를 호출하지 않는다. 정리 자체에 추가 API 비용이 들지 않는다.
"""

import json
import os
import re
import sys
from collections import Counter
from html import unescape

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_registry import ACTIVE_SITES  # noqa: E402

WP_USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
RESULTS_PATH = "prune_unindexed_result.json"

NEWS_DOMAINS = {"koreanews365.com", "theseouljournal.com"}
FULL_RESET_DOMAINS = {"kskin365.com", "oliveyoungkorea.com"}

# 대량 AI/SEO 자동생산에서 반복적으로 보였던 흔적. 하나만으로 자르지 않고 누적 점수로 판단.
AI_TRACE_PATTERNS = [
    r"SEO\s*Meta",
    r"Meta\s*Description\s*:",
    r"Labels\s*:",
    r"Hashtags\s*:",
    r"About the Author",
    r"Get in Touch",
    r"Extensive Industry Report",
    r"crafted by an industry expert with \d+ years",
    r"Why This Is Trending Now",
    r"Why this is trending now",
    r"Answers From the Field",
    r"Frequently Confused Points",
    r"Frequently Overlooked Facts",
    r"Where First-Timers Should Begin",
    r"A Beginner.?s Starting Point",
    r"Read This First",
    r"Ultimate Guide",
    r"Ultimate .* Review",
    r"Unlocking Your",
    r"Get Ready for Your",
]

GENERIC_IMAGE_WORDS = {
    "image", "photo", "picture", "pexels", "pixabay", "unsplash", "stock",
    "default", "placeholder", "featured", "thumbnail", "related", "관련", "이미지",
}


def strip_html(value):
    if isinstance(value, dict):
        value = value.get("rendered", "")
    value = value or ""
    value = re.sub(r"<script\b[^>]*>.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style\b[^>]*>.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", unescape(value)).strip()


def tokenize(s):
    # 영문/숫자/한글 단어 모두 추출. 너무 짧은 토큰은 제외.
    return [x.lower() for x in re.findall(r"[A-Za-z0-9가-힣]{3,}", s or "")]


def fetch_posts(site_url):
    posts, page = [], 1
    while True:
        r = requests.get(
            f"{site_url}/wp-json/wp/v2/posts",
            params={
                "status": "publish", "per_page": 100, "page": page,
                "_fields": "id,link,date,title,content,excerpt,featured_media,categories,tags",
            },
            headers={"User-Agent": "Mozilla/5.0"}, timeout=35,
        )
        if r.status_code == 400 and "rest_post_invalid_page_number" in r.text:
            break
        if r.status_code != 200:
            raise RuntimeError(f"글목록 HTTP {r.status_code}: {r.text[:160]}")
        batch = r.json()
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return posts


def fetch_media(site_url, media_id):
    if not media_id:
        return None
    r = requests.get(
        f"{site_url}/wp-json/wp/v2/media/{media_id}",
        params={"_fields": "id,alt_text,caption,title,description,source_url,media_type,mime_type"},
        headers={"User-Agent": "Mozilla/5.0"}, timeout=25,
    )
    return r.json() if r.status_code == 200 else None


def set_private(site_url, pw, post_id):
    r = requests.post(
        f"{site_url}/wp-json/wp/v2/posts/{post_id}",
        auth=(WP_USER, pw), json={"status": "private"}, timeout=35,
    )
    return r.status_code in (200, 201), r.status_code, r.text[:180]


def quality_reasons(site_url, post):
    title = strip_html(post.get("title"))
    body = strip_html(post.get("content"))
    reasons = []
    score = 0

    words = tokenize(body)
    wc = len(words)
    # 너무 짧거나 너무 길게 기계적으로 찍힌 글 모두 감점. 승인용 기반 글은 실질 정보량을 요구.
    if wc < 650:
        score += 3
        reasons.append(f"본문 짧음({wc}단어)")
    if wc > 4200:
        score += 1
        reasons.append(f"본문 과도하게 김({wc}단어)")

    # AI/SEO 템플릿 흔적
    trace_hits = [p for p in AI_TRACE_PATTERNS if re.search(p, body + " " + title, flags=re.I)]
    if trace_hits:
        score += min(5, len(trace_hits))
        reasons.append(f"AI/SEO 템플릿 흔적 {len(trace_hits)}개")

    # 이모지 과다: 자동 생성 K-beauty 글에서 특히 강하게 확인된 패턴
    emoji_count = len(re.findall(r"[\U0001F300-\U0001FAFF]", body + title))
    if emoji_count >= 5:
        score += 2
        reasons.append(f"이모지 과다({emoji_count})")

    # 키워드 반복/스팸성
    if words:
        counts = Counter(words)
        top_word, top_count = counts.most_common(1)[0]
        ratio = top_count / max(1, len(words))
        if top_count >= 18 and ratio >= 0.035:
            score += 3
            reasons.append(f"키워드 과반복({top_word}:{top_count})")

    # 제목 자체가 자동 변형 템플릿처럼 보이는 경우
    title_templates = [
        r"Q&A\s*:", r"Frequently .* Points", r"Where to Start", r"Read This First",
        r"Right the First Time", r"How People Are Approaching", r"The Real Cost of",
        r"101\s*:", r"Beginner.?s Starting Point",
    ]
    if any(re.search(p, title, re.I) for p in title_templates):
        score += 2
        reasons.append("제목 자동변형 템플릿")

    # 본문에 동일 문구/링크 앵커가 비정상적으로 반복되는 흔적
    if body.lower().count("extensive industry report") >= 2:
        score += 4
        reasons.append("동일 관련링크 문구 반복")

    # 대표이미지: 없으면 강한 감점. 있더라도 메타가 완전 비어 있으면 승인용 품질 기준에서 부실로 판단.
    media_id = post.get("featured_media") or 0
    if not media_id:
        score += 4
        reasons.append("대표이미지 없음")
    else:
        media = fetch_media(site_url, media_id)
        if not media:
            score += 2
            reasons.append("대표이미지 조회 실패")
        else:
            meta = " ".join([
                str(media.get("alt_text") or ""),
                strip_html(media.get("title")),
                strip_html(media.get("caption")),
                strip_html(media.get("description")),
                str(media.get("source_url") or ""),
            ])
            meta_tokens = set(tokenize(meta)) - GENERIC_IMAGE_WORDS
            title_tokens = set(tokenize(title))
            if not str(media.get("alt_text") or "").strip():
                score += 2
                reasons.append("대표이미지 ALT 없음")
            # 제목과 이미지 메타의 의미 단서가 전혀 겹치지 않으면 '상관없는 이미지' 가능성을 강하게 봄.
            if title_tokens and meta_tokens and not (title_tokens & meta_tokens):
                score += 2
                reasons.append("대표이미지-제목 연관 단서 없음")

    # 구조적 노이즈: 빈 H2/H3가 반복된 글
    raw = (post.get("content") or {}).get("rendered", "") if isinstance(post.get("content"), dict) else str(post.get("content") or "")
    empty_headings = len(re.findall(r"<h[23][^>]*>\s*</h[23]>", raw, re.I))
    if empty_headings >= 2:
        score += 2
        reasons.append(f"빈 소제목 반복({empty_headings})")

    # 5점 이상이면 '명확히 저품질/대량생산 흔적'로 비공개.
    return score, reasons, wc


def main():
    all_results = {}
    targets = [row for row in ACTIVE_SITES if row[0].replace("https://", "") not in NEWS_DOMAINS]

    print(f"대상 블로그: {len(targets)}개 (뉴스 2개 제외)")
    for site_url, env_key, lifecycle in targets:
        domain = site_url.replace("https://", "")
        pw = os.environ.get(env_key, "").strip()
        if not pw:
            all_results[domain] = {"status": "SKIP_NO_SECRET", "secret": env_key}
            print(f"\n=== {domain}: {env_key} 시크릿 없음, 스킵 ===")
            continue

        try:
            posts = fetch_posts(site_url)
        except Exception as e:
            all_results[domain] = {"status": "FETCH_FAILED", "error": str(e)}
            print(f"\n=== {domain}: {e} ===")
            continue

        summary = {
            "status": "OK", "total_public_before": len(posts),
            "kept_public": 0, "made_private": 0, "private_failed": 0,
            "mode": "FULL_RESET" if domain in FULL_RESET_DOMAINS else "QUALITY_FILTER",
            "private_items": [], "kept_items": [],
        }
        print(f"\n=== {domain}: 공개글 {len(posts)}개 / {summary['mode']} ===")

        for p in posts:
            title = strip_html(p.get("title"))
            if domain in FULL_RESET_DOMAINS:
                should_private = True
                score, reasons, wc = 99, ["사용자 승인 전면 리셋 대상"], len(tokenize(strip_html(p.get("content"))))
            else:
                score, reasons, wc = quality_reasons(site_url, p)
                should_private = score >= 5

            if should_private:
                ok, status_code, detail = set_private(site_url, pw, p["id"])
                item = {"id": p["id"], "title": title, "score": score, "words": wc, "reasons": reasons}
                if ok:
                    summary["made_private"] += 1
                    summary["private_items"].append(item)
                    print(f"  PRIVATE [{score}] {title[:85]} :: {', '.join(reasons)}")
                else:
                    summary["private_failed"] += 1
                    item["http"] = status_code
                    item["error"] = detail
                    summary["private_items"].append(item)
                    print(f"  FAIL {status_code} {title[:85]}")
            else:
                summary["kept_public"] += 1
                summary["kept_items"].append({"id": p["id"], "title": title, "score": score, "words": wc, "reasons": reasons})
                print(f"  KEEP    [{score}] {title[:85]}")

        all_results[domain] = summary
        with open(RESULTS_PATH, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)

    totals = {
        "sites_processed": sum(1 for x in all_results.values() if x.get("status") == "OK"),
        "sites_skipped": sum(1 for x in all_results.values() if x.get("status") != "OK"),
        "public_before": sum(x.get("total_public_before", 0) for x in all_results.values()),
        "made_private": sum(x.get("made_private", 0) for x in all_results.values()),
        "kept_public": sum(x.get("kept_public", 0) for x in all_results.values()),
        "private_failed": sum(x.get("private_failed", 0) for x in all_results.values()),
    }
    all_results["_TOTALS"] = totals
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print("\n=== 전체 요약 ===")
    print(json.dumps(totals, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
