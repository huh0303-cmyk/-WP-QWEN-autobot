#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_newsroom_broken_titles.py (읽기 전용)
─────────────────────────────────────────────────────────────
2026-08-22: theseouljournal.com/koreanews365.com에서 RSS 헤드라인(완성된
문장)이 일반 키워드용 제목 템플릿에 그대로 끼워 넣어져서 "...101: What
First-Timers Should Know" 같은 말도 안 되는 제목이 된 옛 글들을 찾는다.
build_news_headline()이 도입된 이후(대략 7/19~) 글은 정상이라, 그 이전
발행분 위주로 남아있는 문제.

탐지 방식: autopost_mega.py의 TITLE_TEMPLATES_KO/EN 각각의 "고정 문구"
부분을 정규식으로 만들어 제목에서 찾고, {keyword} 자리에 들어간 텍스트가
비정상적으로 길면(완성된 문장일 가능성) 깨진 제목으로 판정한다.
"""
import json
import re
import sys

import requests

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

TITLE_TEMPLATES_EN = [
    "{keyword}: Where to Start", "{n} Things to Check Before {keyword}",
    "A Practical Look at {keyword}", "{keyword}, Step by Step",
    "Getting {keyword} Right the First Time", "{keyword} Checklist You Shouldn't Skip",
    "How {keyword} Actually Works", "{keyword}: What to Prepare First",
    "{keyword}, Explained Simply", "How Much Should You Budget for {keyword}?",
    "{n} Questions People Ask About {keyword}", "{keyword} 101: Where First-Timers Should Begin",
    "{keyword} Made Simple", "{keyword} in {year}: What's Changed",
    "The Real Cost of {keyword} — What to Expect", "Before You Try {keyword}, Read This First",
    "{keyword}: Details That Are Easy to Miss", "A Practical Look at {keyword} for International Readers",
    "{keyword}: A Beginner's Starting Point", "{keyword} — Common Points of Confusion, Cleared Up",
    "How {keyword} Has Changed in {year}", "{keyword} Q&A: Answers From the Field",
    "{keyword}, Broken Down Step by Step", "{n} Things to Look For When Choosing {keyword}",
    "How People Are Approaching {keyword} This Year", "{keyword}: Frequently Confused Points",
    "Save Time and Money on {keyword}", "{keyword}: A Closer Look",
    "Planning for {keyword}? Start Here", "{keyword}, From Someone Who's Been There",
    # 뉴스 재작성 함수 도입 전, 다른 스타일의 템플릿이 더 있었을 가능성 대비
    "{n} Mistakes People Make With {keyword}", "Behind the Scenes: What {keyword} Actually Involves",
    "{keyword} vs What You Think You Know: Key Differences",
    "Rethinking {keyword}: A Fresh Perspective for {year}",
]
TITLE_TEMPLATES_KO = [
    "{keyword}, 이것부터 확인하세요", "{keyword} 관리, 이 {n}가지만 지켜도 달라집니다",
    "{keyword}에 대해 알아두면 좋은 것들", "{keyword}, 어디서부터 시작해야 할까",
    "{keyword} 제대로 준비하는 법", "놓치기 쉬운 {keyword} 체크포인트",
    "{keyword}, 실제로는 이렇게 진행됩니다", "{keyword} 하기 전에 알아두면 좋은 것들",
    "{keyword}, 핵심만 짚어드립니다", "{keyword}, 얼마나 준비해야 할까",
    "{keyword}에서 자주 나오는 질문 {n}가지", "{keyword} 첫걸음 — 순서대로 정리",
    "{keyword}, 쉽게 풀어드립니다", "{year}년 {keyword}, 이렇게 달라졌습니다",
    "{keyword}의 실제 비용 — 미리 알아야 할 것들", "{keyword} 시작 전에 꼭 읽어야 할 글",
    "{keyword}에서 놓치기 쉬운 부분들", "외국인을 위한 {keyword} 실전 가이드",
    "{keyword} 입문 — 처음이라면 꼭 알아야 할 것", "{keyword} 준비할 때 헷갈리는 부분 정리",
    "{year}년 달라진 {keyword}, 무엇이 바뀌었나", "{keyword} 궁금증, 하나씩 풀어봅니다",
    "{keyword}, 순서대로 따라 하면 됩니다", "{keyword} 고를 때 살펴봐야 할 {n}가지",
    "{keyword}, 요즘 이렇게 준비합니다", "{keyword} 관련 자주 헷갈리는 부분",
    "{keyword}, 시간과 비용을 아끼는 방법", "{keyword} 살펴보기 — 알아두면 유용한 정보",
    "{keyword} 계획하고 계신가요? 이것부터", "{keyword}, 현지에서 실제로 겪는 것들",
]

SITES = ["https://theseouljournal.com", "https://koreanews365.com"]


def template_to_regex(tmpl):
    esc = re.escape(tmpl)
    esc = esc.replace(re.escape("{keyword}"), r"(?P<kw>.{3,300}?)")
    esc = esc.replace(re.escape("{n}"), r"\d+")
    esc = esc.replace(re.escape("{year}"), r"\d{4}")
    return re.compile("^" + esc + "$")


def is_broken(title, templates):
    for tmpl in templates:
        m = template_to_regex(tmpl).match(title)
        if m:
            kw = m.group("kw")
            # 완성된 문장일 가능성 신호: 너무 길거나, 단어수가 많거나, 문장부호 포함
            word_count = len(kw.split())
            if len(kw) > 55 or word_count > 8 or re.search(r"[.!?,;:]", kw):
                return True, tmpl, kw
    return False, None, None


def fetch_all_posts(site_url):
    posts = []
    page = 1
    while True:
        r = requests.get(f"{site_url}/wp-json/wp/v2/posts",
                          params={"per_page": 100, "page": page,
                                  "_fields": "id,title,link,date,content", "status": "publish"},
                          timeout=20)
        if r.status_code != 200:
            break
        batch = r.json()
        if not isinstance(batch, list) or not batch:
            break
        posts.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return posts


def main():
    manifest = []
    for site_url in SITES:
        templates = TITLE_TEMPLATES_KO if "koreanews365" in site_url else TITLE_TEMPLATES_EN
        posts = fetch_all_posts(site_url)
        print(f"=== {site_url}: 발행글 {len(posts)}건 감사 ===")
        for p in posts:
            title = re.sub(r"<[^>]+>", "", p["title"]["rendered"]).strip()
            title = title.replace("&#8217;", "'").replace("&#8216;", "'").replace("&amp;", "&")
            broken, tmpl, kw = is_broken(title, templates)
            content = p.get("content", {}).get("rendered", "")
            has_email_leak = "huh0303@gmail.com" in content
            if broken or has_email_leak:
                manifest.append({
                    "site": site_url, "id": p["id"], "link": p["link"], "date": p["date"],
                    "title": title, "broken_title": broken, "recovered_keyword": kw,
                    "email_leak": has_email_leak,
                })
                flags = []
                if broken: flags.append("BROKEN_TITLE")
                if has_email_leak: flags.append("EMAIL_LEAK")
                print(f"  [{','.join(flags)}] #{p['id']} ({p['date'][:10]}) {title[:90]}")

    with open("newsroom_broken_titles_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"\n총 {len(manifest)}건 → newsroom_broken_titles_manifest.json 저장")


if __name__ == "__main__":
    main()
