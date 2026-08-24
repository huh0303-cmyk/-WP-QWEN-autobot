#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scan_ai_artifacts.py
─────────────────────────────────────────────────────────────
27개 사이트 전체 발행글을 대상으로, 프롬프트 지시문이나 AI 디스클레이머
문구가 실수로 그대로 본문에 새어들어간 "AI 흔적"을 찾는다. (읽기 전용,
공개 REST 데이터만 사용 — 인증 불필요)

SAFE_TO_STRIP: 순수 잡음이라 통째로 지워도 정보 손실이 없는 패턴
  (예: "body HTML" 라벨, "[OUTPUT FORMAT]" 지시문 echo, AI 디스클레이머 문장)
  → ai_artifact_manifest.json에 기록, clean_ai_artifacts.py가 실제 제거.

REPORT_ONLY: 자동 삭제 시 문장이 어색해질 수 있어 수동 확인이 필요한 패턴
  (예: 마크다운 ** 잔재, 코드펜스) → 콘솔에 카운트만 출력.
"""
import re
import json
import requests

SITES = [
    "https://k-health365.com", "https://koreamedicaltour.com", "https://koreainvest365.com",
    "https://ki-korea.com", "https://koreainsurance365.com", "https://kfinance365.com",
    "https://koreataxnlaw.com", "https://koreacrypto365.com", "https://krealestate365.com",
    "https://ktech365.com", "https://oliveyoungkorea.com",
    "https://kworld365.com", "https://k-trip365.com", "https://k-visa365.com",
    "https://koreawedding365.com", "https://kstudy365.com", "https://studyinkorea365.com",
    "https://kieca-korea.org", "https://ksa-korea.org", "https://sis-korea.com",
    "https://jobkorea365.com", "https://jobinkorea365.com", "https://jobkoreaglobal.com",
    "https://korea365.org", "https://koreanews365.com", "https://theseouljournal.com",
]

SAFE_TO_STRIP = [
    (r'<p>\s*body\s*HTML\s*</p>\s*', "body HTML 잔재"),
    (r'(?<![a-zA-Z])body\s+HTML(?![a-zA-Z])', "body HTML 잔재(태그 밖)"),
    (r'\[OUTPUT FORMAT[^\]]*\]', "[OUTPUT FORMAT] 지시문 echo"),
    (r"\[THIS SITE.?S UNIQUE STRUCTURE[^\]]*\]", "[THIS SITE'S UNIQUE STRUCTURE] 지시문 echo"),
    (r'<p>\s*FAQ_START\s*</p>\s*', "FAQ_START 잔재"),
    (r'<p>\s*FAQ_END\s*</p>\s*', "FAQ_END 잔재"),
    (r'<p>\s*TITLE:\s*</p>\s*', "TITLE: 라벨 잔재"),
    (r'<p>\s*As an AI language model[^<]*</p>\s*', "AI 디스클레이머(as an AI language model)"),
    (r"<p>\s*I'?m an AI[^<]*</p>\s*", "AI 디스클레이머(I'm an AI)"),
    (r'<p>\s*I cannot browse the internet[^<]*</p>\s*', "AI 디스클레이머(cannot browse)"),
    (r'<p>\s*I do not have (real-time|access to real-time)[^<]*</p>\s*', "AI 디스클레이머(no real-time access)"),
]

REPORT_ONLY = [
    (r'```[a-zA-Z]*', "마크다운 코드펜스 잔재"),
    (r'\*\*[^*<>\n]{3,60}\*\*', "마크다운 볼드(**) 잔재"),
]

MANIFEST_PATH = "ai_artifact_manifest.json"


def log(msg):
    print(msg, flush=True)


def get_all_posts(site):
    posts = []
    page = 1
    while True:
        try:
            r = requests.get(
                f"{site}/wp-json/wp/v2/posts",
                params={"per_page": 100, "page": page, "status": "publish",
                        "_fields": "id,link,title,content"},
                timeout=30,
            )
        except Exception as e:
            log(f"  ⚠️ {site} page{page} 요청 오류: {e}")
            break
        if r.status_code != 200:
            break
        items = r.json()
        if not isinstance(items, list) or not items:
            break
        posts.extend(items)
        if len(items) < 100:
            break
        page += 1
    return posts


def main():
    manifest = []
    report_counts = {label: 0 for _, label in REPORT_ONLY}
    total_posts = 0

    for site in SITES:
        posts = get_all_posts(site)
        total_posts += len(posts)
        site_hits = 0
        for post in posts:
            content = post.get("content", {}).get("rendered", "") or ""
            title = re.sub(r"<[^>]+>", "", post.get("title", {}).get("rendered", "") or "")
            matched_patterns = []
            for pat, label in SAFE_TO_STRIP:
                if re.search(pat, content, re.IGNORECASE):
                    matched_patterns.append(label)
            if matched_patterns:
                manifest.append({
                    "site": site, "post_id": post["id"], "link": post.get("link", ""),
                    "title": title, "artifacts": matched_patterns,
                })
                site_hits += 1
            for pat, label in REPORT_ONLY:
                if re.search(pat, content):
                    report_counts[label] += 1
        log(f"[{site}] {len(posts)}개 글 중 {site_hits}건에서 AI 흔적 발견")
        with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

    log("=" * 60)
    log(f"전체 {total_posts}개 글 조사 완료. 삭제 대상 {len(manifest)}건 → {MANIFEST_PATH}")
    log("참고용(자동삭제 안 함, 수동 확인 필요):")
    for label, count in report_counts.items():
        if count:
            log(f"  - {label}: {count}건")


if __name__ == "__main__":
    main()
