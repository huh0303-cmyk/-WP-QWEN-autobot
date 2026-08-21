#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
refresh_keyword_pool.py
─────────────────────────────────────────────────────────────
2026-08-22: koreainvest365.com 키워드 풀이 19개뿐이라 발행 이력 대비
너무 작아서 제목 중복 스킵이 빈발함(실사용자 테스트로 확인). 사용자 지시:
"키워드가 가장 중요해.. 지금 다시 리서치해서 가장 핫한 키워드로... 이건
매주 일요일마다 재검색해서 키워드 pool을 업데이트해줘."

Gemini의 Google 검색 그라운딩(google_search 툴)을 이용해 실제 최신 웹 검색
결과에 기반한 키워드를 생성한다 — 별도 검색 API 키 없이(이미 있는
GEMINI_API_KEY만으로) "지금 진짜 화제인 주제"를 반영할 수 있는 유일한
현실적 경로. 검색 그라운딩이 실패하면(모델/SDK 버전 이슈 등) 모델 자체
지식 기반 생성으로 폴백하되, 그 사실을 로그에 명확히 남긴다.

기존 파일은 항상 data/keywords/_backup_YYYYMMDD/에 백업 후 교체(기존
27개 사이트 삭제작업 원칙과 동일 — 조사 결과를 덮어쓰기 전에 항상 보존).
"""
import datetime
import os
import re
import sys

from google import genai
from google.genai import types as genai_types

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = os.environ.get("KEYWORD_RESEARCH_MODEL", "gemini-2.5-flash")

# 사이트별 리서치 대상 — 지금은 koreainvest365만, 다른 사이트도 같은 문제(키워드
# 풀 대비 발행이력 과다)가 확인되면 여기에 추가하면 동일 로직으로 확장 가능.
TARGETS = [
    {
        "file": "data/keywords/keywords_kinvest.txt",
        "domain_desc": "South Korea investing: KOSPI/Kosdaq stocks, ETFs and funds, "
                        "and crypto/digital-asset policy — written for an international "
                        "(non-Korean-resident) English-reading investor audience",
        "categories": ["Korea Stocks", "Korea Funds & ETF", "Crypto & Digital"],
        "count": 50,
    },
]

PROMPT_TMPL = """Search the web right now for what is actually trending TODAY ({today}) in
this topic area: {domain}.

Based on real current search interest (not generic evergreen topics), produce exactly
{count} distinct English SEO keyword phrases a blog would target this week, split across
these categories: {categories}.

Rules:
- Each keyword is a short search-style phrase (3-6 words), not a full sentence.
- Ground them in what's actually happening right now (specific companies, specific policy
  developments, specific product/ETF names, specific market events) — not vague evergreen
  phrases like "how to invest in Korea".
- No two keywords should be near-duplicates of each other.
- Output ONLY the keyword list, one per line, tab-separated as: keyword<TAB>category
  Category must be exactly one of: {categories}
- No numbering, no headers, no explanation, no markdown — just the {count} raw lines.
"""


def parse_lines(text, valid_categories, expected_count):
    lines = []
    for raw in text.strip().split("\n"):
        raw = raw.strip()
        if not raw or "\t" not in raw:
            continue
        kw, cat = raw.split("\t", 1)
        kw, cat = kw.strip(), cat.strip()
        if not kw or cat not in valid_categories:
            continue
        if len(kw) < 3 or len(kw) > 80:
            continue
        lines.append((kw, cat))
    # 중복 제거(대소문자 무시), 순서 유지
    seen = set()
    deduped = []
    for kw, cat in lines:
        k = kw.lower()
        if k in seen:
            continue
        seen.add(k)
        deduped.append((kw, cat))
    return deduped[:expected_count]


def research_keywords(client, target, today_str):
    categories_str = " / ".join(target["categories"])
    prompt = PROMPT_TMPL.format(
        today=today_str, domain=target["domain_desc"],
        count=target["count"], categories=categories_str,
    )
    grounded = True
    try:
        resp = client.models.generate_content(
            model=MODEL, contents=prompt,
            config=genai_types.GenerateContentConfig(
                tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())],
                temperature=0.9,
            ),
        )
        text = resp.text
    except Exception as e:
        print(f"  ⚠️ 검색 그라운딩 실패({e}) → 모델 자체 지식으로 폴백")
        grounded = False
        resp = client.models.generate_content(
            model=MODEL, contents=prompt,
            config={"temperature": 0.9, "max_output_tokens": 4096},
        )
        text = resp.text
    return text, grounded


def main():
    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY 없음"); sys.exit(1)
    client = genai.Client(api_key=GEMINI_API_KEY)
    today = datetime.datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    backup_dir = f"data/keywords/_backup_{today.strftime('%Y%m%d')}"

    any_updated = False
    for target in TARGETS:
        path = target["file"]
        print(f"\n=== {path} 리서치 시작 ({today_str} 기준) ===")
        text, grounded = research_keywords(client, target, today_str)
        parsed = parse_lines(text, target["categories"], target["count"])
        min_ok = max(20, target["count"] // 2)  # 결과가 절반도 안 되면 신뢰 못 함
        if len(parsed) < min_ok:
            print(f"  ❌ 파싱된 키워드 {len(parsed)}개 < 최소 {min_ok}개 — 이번 갱신 스킵 "
                  f"(기존 파일 유지, 원문 응답 앞부분: {text[:200]!r})")
            continue

        os.makedirs(backup_dir, exist_ok=True)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                old_content = f.read()
            backup_path = os.path.join(backup_dir, os.path.basename(path))
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(old_content)
            print(f"  💾 기존 파일 백업: {backup_path}")

        with open(path, "w", encoding="utf-8") as f:
            for kw, cat in parsed:
                f.write(f"{kw}\t{cat}\n")
        tag = "검색 그라운딩" if grounded else "모델 지식 폴백(검색 그라운딩 실패)"
        print(f"  ✅ {len(parsed)}개 키워드로 교체 완료 [{tag}]")
        any_updated = True

    if not any_updated:
        print("\n⚠️ 갱신된 파일 없음")
        sys.exit(1)


if __name__ == "__main__":
    main()
