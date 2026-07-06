#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cleanup_all_sites.py

27개 사이트 전체를 대상으로 아래 3가지 기준에 해당하는 글을 정리합니다.
  1) 더미 글 (제목 없이 자동 슬러그로 발행된 post-123 형태)
  2) 본문 2000자 미만
  3) rank_math_seo_score 90점 미만 (0점=미측정은 제외, 즉 실제로 채점된 글만 대상)

★★★ 안전장치 ★★★
- 기본값 DRY_RUN = True: 사이트별로 삭제 후보 "개수"만 요약해서 보여줍니다.
  (개별 글 목록까지 보고 싶으면 VERBOSE = True로 바꾸세요. 27개 사이트 전체 글을
   다 출력하면 로그가 아주 길어지니 기본은 요약만 하도록 했습니다.)
- 삭제 방식 기본값은 "trash" (복구 가능). 영구삭제(force)는 DELETE_MODE="delete"로
  바꿔야만 실행됩니다.
- 한 사이트의 삭제 후보가 전체 글의 SAFETY_RATIO_LIMIT(기본 70%)를 넘으면
  "위험 사이트"로 표시하고 그 사이트는 자동으로 건너뜁니다 (실수로 사이트 전체를
  날리는 사고 방지). 필요하면 사이트명을 SAFETY_OVERRIDE 목록에 넣어서 강제 진행 가능.
"""

import os
import re
import base64
import requests
from datetime import datetime, timedelta

_LOG_LINES = []
def log(msg=""):
    print(msg)
    _LOG_LINES.append(str(msg))

# ============ 설정 ============

DRY_RUN = True          # ★★★ True = 목록/개수만 확인, 실제 삭제 안 함
VERBOSE = False         # True로 하면 사이트별 삭제후보 글 제목까지 전부 출력
DELETE_MODE = "trash"   # "trash"(복구가능) 권장 / "delete"(영구삭제)

MIN_SEO_SCORE = 90       # 이 점수 미만이면 후보 (0점=미측정은 제외)
MIN_CONTENT_CHARS = 2000 # 본문(텍스트만) 이 글자수 미만이면 후보
GENERIC_SLUG_PATTERN = re.compile(r"^post-\d+$")

SAFETY_RATIO_LIMIT = 0.70   # 삭제후보가 전체글의 70% 넘으면 자동 스킵
SAFETY_OVERRIDE = set()     # 강제로 진행하고 싶은 사이트 url을 여기 추가

WP_USER = "huh0303@gmail.com"  # 기존 autopost_mega.py와 동일 계정

# 27개 사이트: (url, GitHub Secret 이름)
SITES = [
    ("https://k-health365.com",        "KHEALTH365COM"),
    ("https://koreamedicaltour.com",   "KOREAMEDICALTOURCOM"),
    ("https://koreainvest365.com",     "KOREAINVEST365COM"),
    ("https://ki-korea.com",           "KIKOREACOM"),
    ("https://koreainsurance365.com",  "KOREAINSURANCE365COM"),
    ("https://kfinance365.com",        "KFINANCE365COM"),
    ("https://koreataxnlaw.com",       "KOREATAXNLAWCOM"),
    ("https://koreacrypto365.com",     "KOREACRYPTO365COM"),
    ("https://krealestate365.com",     "KREALESTATE365COM"),
    ("https://ktech365.com",           "KTECH365COM"),
    ("https://kskin365.com",           "KSKIN365COM"),
    ("https://oliveyoungkorea.com",    "OLIVEYOUNGKOREACOM"),
    ("https://kworld365.com",          "KWORLD365COM"),
    ("https://k-trip365.com",          "KTRIP365COM"),
    ("https://k-visa365.com",          "KVISA365COM"),
    ("https://koreawedding365.com",    "KOREAWEDDING365COM"),
    ("https://kstudy365.com",          "KSTUDY365COM"),
    ("https://studyinkorea365.com",    "STUDYINKOREA365COM"),
    ("https://kieca-korea.org",        "KIECAKOREAORG"),
    ("https://ksa-korea.org",          "KSAKOREAORG"),
    ("https://sis-korea.com",          "SISKOREACOM"),
    ("https://jobkorea365.com",        "JOBKOREA365COM"),
    ("https://jobinkorea365.com",      "JOBINKOREA365COM"),
    ("https://jobkoreaglobal.com",     "JOBKOREAGLOBALCOM"),
    ("https://korea365.org",           "KOREA365ORG"),
    ("https://koreanews365.com",       "KOREANEWS365COM"),
    ("https://theseouljournal.com",    "THESEOULJOURNALCOM"),
]

# ================================================


def fetch_all_posts(site_url, pw):
    posts = []
    page = 1
    while True:
        url = f"{site_url}/wp-json/wp/v2/posts"
        params = {"per_page": 50, "page": page, "status": "publish",
                  "_fields": "id,date,slug,title,link,meta,content"}
        try:
            r = requests.get(url, auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                              params=params, timeout=20)
        except Exception as e:
            log(f"    ⚠️ 연결 오류: {e}")
            break
        if r.status_code != 200:
            if page == 1:
                log(f"    ⚠️ API 오류 (status {r.status_code}) - 인증/접속 확인 필요")
            break
        batch = r.json()
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < 50:
            break
        page += 1
    return posts


def get_seo_score(post):
    meta = post.get("meta", {}) or {}
    score = meta.get("rank_math_seo_score", "")
    try:
        return int(float(str(score))) if score not in ("", None) else 0
    except Exception:
        return 0


def content_char_count(post):
    html = post.get("content", {}).get("rendered", "")
    text = re.sub(r"<[^>]+>", "", html).strip()
    return len(text)


def is_generic_slug(post):
    return bool(GENERIC_SLUG_PATTERN.match(post.get("slug", "")))


def classify(post):
    reasons = []
    if is_generic_slug(post):
        reasons.append("더미(제목없음)")
    chars = content_char_count(post)
    if chars < MIN_CONTENT_CHARS:
        reasons.append(f"본문부족({chars}자)")
    score = get_seo_score(post)
    if 0 < score < MIN_SEO_SCORE:
        reasons.append(f"SEO낮음({score}점)")
    return reasons


def main():
    log(f"{'='*90}")
    log(f"모드: {'DRY RUN (미리보기만)' if DRY_RUN else f'실제 삭제 실행 ({DELETE_MODE})'}")
    log(f"기준: 더미슬러그 / 본문<{MIN_CONTENT_CHARS}자 / SEO<{MIN_SEO_SCORE}점")
    log(f"{'='*90}\n")

    grand_total_posts = 0
    grand_total_candidates = 0
    skipped_sites = []

    for site_url, secret_name in SITES:
        pw = os.environ.get(secret_name)
        log(f"\n🌐 {site_url}")
        if not pw:
            log(f"   ⚠️ 환경변수 {secret_name} 없음 → 건너뜀")
            continue

        posts = fetch_all_posts(site_url, pw)
        total = len(posts)
        if total == 0:
            log(f"   게시물 없음 또는 접속 실패")
            continue

        candidates = []
        for p in posts:
            reasons = classify(p)
            if reasons:
                candidates.append((p, reasons))

        ratio = len(candidates) / total if total else 0
        grand_total_posts += total
        grand_total_candidates += len(candidates)

        log(f"   전체 {total}개 중 삭제후보 {len(candidates)}개 ({ratio:.0%})")

        if VERBOSE:
            for p, reasons in candidates:
                title = p.get("title", {}).get("rendered", "(제목없음)")
                log(f"     - [{', '.join(reasons)}] {title[:40]} | {p['link']}")

        if ratio > SAFETY_RATIO_LIMIT and site_url not in SAFETY_OVERRIDE:
            log(f"   🛑 위험: 후보 비율이 {SAFETY_RATIO_LIMIT:.0%}를 초과 → 이 사이트는 "
                  f"자동 스킵합니다 (전체 삭제 사고 방지). 확인 후 SAFETY_OVERRIDE에 추가하세요.")
            skipped_sites.append(site_url)
            continue

        if DRY_RUN or not candidates:
            continue

        force = (DELETE_MODE == "delete")
        deleted, failed = 0, 0
        for p, reasons in candidates:
            durl = f"{site_url}/wp-json/wp/v2/posts/{p['id']}"
            params = {"force": "true"} if force else {}
            dr = requests.delete(durl, auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                                  params=params, timeout=20)
            if dr.status_code in (200, 201):
                deleted += 1
            else:
                failed += 1
        log(f"   🗑️ 처리완료: {deleted}개 성공, {failed}개 실패")

    log(f"\n{'='*90}")
    log(f"전체 요약: {len(SITES)}개 사이트 / 총 게시물 {grand_total_posts}개 / "
          f"삭제후보 {grand_total_candidates}개")
    if skipped_sites:
        log(f"⚠️ 안전상 자동 스킵된 사이트({len(skipped_sites)}개): {', '.join(skipped_sites)}")
    if DRY_RUN:
        log(f"\n★ DRY RUN이었습니다. 목록을 확인 후 스크립트 상단 DRY_RUN=False로 바꿔서")
        log(f"★ 다시 실행하면 위 후보들이 '{DELETE_MODE}' 처리됩니다.")
    log(f"{'='*90}")

    with open("cleanup_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(_LOG_LINES))


if __name__ == "__main__":
    main()
