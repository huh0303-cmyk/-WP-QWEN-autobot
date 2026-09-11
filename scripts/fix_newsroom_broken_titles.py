#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_newsroom_broken_titles.py
─────────────────────────────────────────────────────────────
2026-08-22: audit_newsroom_broken_titles.py가 찾은 190건(제목이 템플릿에
헤드라인 문장이 그대로 끼워져 말이 안 되거나 / CTA박스에 운영자 개인
이메일이 그대로 노출된 옛 글)을 실제로 고친다. 사용자 지시: "핑계 하지말고
바로 전수조사해서 고쳐줘."

- EMAIL_LEAK: CTA박스(<div class="cta-box"...>...</div>) 전체를 제거한다
  (뉴스모드는 원래 CTA가 없어야 하는 게 현재 설계 의도 — is_newsroom이면
  cta_html=""). 이메일만 바꾸는 게 아니라 박스 자체를 삭제.
- BROKEN_TITLE: manifest에 감지된 recovered_keyword(템플릿에 끼워졌던
  원래 헤드라인 문장)를 GPT로 자연스러운 헤드라인으로 재작성해서 제목을
  교체한다(autopost_mega.py의 build_news_headline()과 같은 원칙).

manifest(newsroom_broken_titles_manifest.json)를 먼저 읽고, 사이트별
wp_pass_env로 인증해서 WP REST PATCH로 반영한다.
"""
import json
import os
import re
import sys
import time

import requests

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

WP_USER = "huh0303@gmail.com"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

SITE_PASS_ENV = {
    "https://theseouljournal.com": "THESEOULJOURNALCOM",
    "https://koreanews365.com": "KOREANEWS365COM",
}

CTA_BOX_RE = re.compile(
    r'<div class="cta-box"[^>]*>.*?</div>\s*</div>\s*</div>',
    re.DOTALL,
)
# build_cta_html의 실제 출력 구조는 div가 3중이 아니라 1개 블록으로 닫히므로
# 좀 더 관대하게, 시작 태그부터 '균형 잡힌' 첫 </div>까지가 아니라
# "cta-box"가 열린 지점부터 그 문단이 끝나는 지점까지를 잡는 완화된 패턴도 시도.
CTA_BOX_RE_SIMPLE = re.compile(
    r'<div class="cta-box"[\s\S]*?Get in Touch[\s\S]*?</div>\s*</div>',
    re.IGNORECASE,
)


def strip_cta_box(content):
    if "cta-box" not in content and "huh0303@gmail.com" not in content:
        return content, False
    new_content = CTA_BOX_RE_SIMPLE.sub("", content)
    if "huh0303@gmail.com" in new_content:
        # 패턴이 안 맞으면 최후 수단: 이메일이 포함된 <p> 태그 하나만 제거
        new_content = re.sub(r'<p[^>]*>[^<]*huh0303@gmail\.com[^<]*</p>', '', new_content)
    if "huh0303@gmail.com" in new_content:
        # 그래도 남으면 문단 전체가 아니라 CTA 블록 전체(가장 가까운 div~/div)를
        # 폭넓게 제거하는 마지막 시도
        new_content = re.sub(
            r'<div[^>]*class="cta-box"[\s\S]*?</div>(\s*</div>)?', '', new_content
        )
    return new_content, new_content != content


def rewrite_headline(original_text, lang):
    if lang == "ko":
        prompt = ("다음은 예전에 제목 템플릿 버그로 망가진 뉴스 기사의 원래 헤드라인 소재입니다. "
                   "같은 의미를 살려 신문 기사 톤으로 짧고 자연스러운 헤드라인으로 다시 써주세요. "
                   "90자 이내, 따옴표 없이, 설명 없이 헤드라인만 출력.\n"
                   f"원문 소재: {original_text}\n헤드라인:")
    else:
        prompt = ("The following is the original headline material from a news article whose title "
                   "was broken by a template bug. Rewrite it as a short, natural, professional news "
                   "headline preserving the same meaning. Under 90 characters, no quotes, no "
                   "explanation, headline only.\n"
                   f"Original material: {original_text}\nHeadline:")
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    body = {"model": OPENAI_MODEL, "messages": [{"role": "user", "content": prompt}]}
    for attempt in range(3):
        try:
            r = requests.post("https://api.openai.com/v1/chat/completions",
                               headers=headers, json=body, timeout=60)
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"].strip()
            text = text.strip('"').strip("'")
            if 8 <= len(text) <= 160:
                return text
        except Exception as e:
            print(f"    ⚠️ 헤드라인 재작성 실패({attempt+1}회): {e}")
            time.sleep(5)
    return None


def main():
    if not os.path.exists("newsroom_broken_titles_manifest.json"):
        print("❌ manifest 없음 — audit_newsroom_broken_titles.py 먼저 실행 필요")
        sys.exit(1)
    with open("newsroom_broken_titles_manifest.json", encoding="utf-8") as f:
        manifest = json.load(f)

    fixed_title = fixed_email = failed = 0
    for item in manifest:
        site = item["site"]
        pw = os.getenv(SITE_PASS_ENV.get(site, ""), "")
        if not pw:
            print(f"  ⚠️ {SITE_PASS_ENV.get(site)} 시크릿 없음, 스킵: {item['link']}")
            failed += 1
            continue

        patch = {}
        # 1) 제목 재작성
        if item["broken_title"] and item["recovered_keyword"]:
            lang = "ko" if "koreanews365" in site else "en"
            new_title = rewrite_headline(item["recovered_keyword"], lang)
            if new_title:
                patch["title"] = new_title
            else:
                print(f"  ⚠️ 헤드라인 재작성 끝내 실패: #{item['id']}")

        # 2) 본문에서 CTA(개인이메일) 박스 제거 — 본문을 먼저 받아와야 함
        if item["email_leak"]:
            try:
                r = requests.get(f"{site}/wp-json/wp/v2/posts/{item['id']}",
                                  auth=(WP_USER, pw), params={"_fields": "content"}, timeout=20)
                r.raise_for_status()
                content = r.json()["content"]["rendered"]
                new_content, changed = strip_cta_box(content)
                if changed:
                    patch["content"] = new_content
                else:
                    print(f"  ⚠️ CTA 패턴 매칭 실패, 본문 수동 확인 필요: {item['link']}")
            except Exception as e:
                print(f"  ⚠️ 본문 조회 실패 #{item['id']}: {e}")

        if not patch:
            continue

        try:
            r = requests.post(f"{site}/wp-json/wp/v2/posts/{item['id']}",
                               auth=(WP_USER, pw), json=patch, timeout=30)
            if r.status_code == 200:
                tags = []
                if "title" in patch: tags.append("제목재작성"); fixed_title += 1
                if "content" in patch: tags.append("CTA제거"); fixed_email += 1
                print(f"  ✅ #{item['id']} [{','.join(tags)}] {item['link']}")
            else:
                print(f"  ❌ #{item['id']} PATCH 실패 HTTP {r.status_code}: {r.text[:150]}")
                failed += 1
        except Exception as e:
            print(f"  ❌ #{item['id']} 예외: {e}")
            failed += 1
        time.sleep(1)

    print(f"\n완료 — 제목수정:{fixed_title} / CTA제거:{fixed_email} / 실패:{failed} / 총 {len(manifest)}건")


if __name__ == "__main__":
    main()
