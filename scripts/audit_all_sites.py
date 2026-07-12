#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_all_sites.py

k-health365.com을 제외한 26개 사이트의 기존 발행글을 전수조사합니다.

검출 기준:
  1) 제목에 2026이 아닌 연도(2024/2025/2027 등) 포함 -> 제목에서 연도 제거 (자동수정)
  2) 카테고리 미배정(Uncategorized, id=1 또는 빈 값) -> 해당 사이트에서 가장 많이 쓰인
     카테고리로 자동 배정 (자동수정)
  3) 더미 슬러그 (post-123 형태, 제목 자동생성 실패) -> 삭제후보
  4) 같은 사이트 내 제목 완전 중복 -> 먼저 발행된 것만 남기고 나머지 삭제후보
  5) 본문 2500자 미만 -> 삭제후보

안전장치:
  - DRY_RUN=True: 후보 목록/개수만 출력, 실제 변경 없음
  - 삭제는 "trash"(복구가능) 방식
  - 한 사이트의 삭제후보 비율이 SAFETY_RATIO_LIMIT을 넘으면 그 사이트는 자동 스킵
  - 제목연도수정/카테고리배정은 안전한 수정이므로 DRY_RUN과 무관하게 항상 실제 반영
    (단, 최초 1회는 DRY_RUN=True로 먼저 확인 권장)
"""
import os, re, requests
from collections import Counter

DRY_RUN = False          # 삭제만 제어. 연도수정/카테고리배정은 항상 즉시 반영됨
DELETE_MODE = "trash"    # trash(복구가능) 권장
MIN_CONTENT_CHARS = 2500
GENERIC_SLUG_PATTERN = re.compile(r"^post-\d+$")
YEAR_PATTERN = re.compile(r'(?<!\d)(19\d{2}|20\d{2})(?!\d)')
KEEP_YEAR = "2026"
SAFETY_RATIO_LIMIT = 0.70

WP_USER = "huh0303@gmail.com"

SITES = [
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

_LOG = []
def log(m=""):
    print(m)
    _LOG.append(str(m))


def auth(pw):
    return requests.auth.HTTPBasicAuth(WP_USER, pw)


def fetch_all_posts(site_url, pw):
    posts = []
    page = 1
    while True:
        try:
            r = requests.get(f"{site_url}/wp-json/wp/v2/posts", auth=auth(pw),
                              params={"per_page": 50, "page": page, "status": "publish",
                                      "_fields": "id,date,slug,title,link,categories,content"},
                              timeout=25)
        except Exception as e:
            log(f"    ⚠️ 연결 오류: {e}")
            break
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < 50:
            break
        page += 1
    return posts


def clean_title_year(title):
    def repl(m):
        return "" if m.group(1) != KEEP_YEAR else m.group(1)
    t = YEAR_PATTERN.sub(repl, title)
    t = re.sub(r'[\[\(]\s*[\]\)]', '', t)
    t = re.sub(r'\s{2,}', ' ', t)
    t = re.sub(r'^[\s\-–\|:,]+|[\s\-–\|:,]+$', '', t)
    return t.strip()


def content_char_count(post):
    html = post.get("content", {}).get("rendered", "")
    text = re.sub(r"<[^>]+>", "", html).strip()
    return len(text)


def main():
    grand_total = 0
    grand_deleted = 0
    grand_title_fixed = 0
    grand_cat_fixed = 0
    skipped_sites = []

    for site_url, secret_name in SITES:
        pw = os.environ.get(secret_name)
        log(f"\n🌐 {site_url}")
        if not pw:
            log("   ⚠️ 환경변수 없음 → 건너뜀")
            continue

        posts = fetch_all_posts(site_url, pw)
        total = len(posts)
        if total == 0:
            log("   게시물 없음 또는 접속 실패")
            continue
        grand_total += total

        # 사이트에서 가장 많이 쓰인 카테고리 찾기 (미배정 글 배정용)
        cat_counter = Counter()
        for p in posts:
            for c in p.get("categories", []):
                if c != 1:
                    cat_counter[c] += 1
        default_cat = cat_counter.most_common(1)[0][0] if cat_counter else None

        # 제목 중복 탐지용
        title_seen = {}
        candidates = {}  # post_id -> reasons list

        for p in posts:
            title_raw = p.get("title", {}).get("rendered", "")
            reasons = []

            # 1) 연도 수정 (즉시 반영, 삭제 아님)
            new_title = clean_title_year(title_raw)
            if new_title and new_title != title_raw:
                r = requests.post(f"{site_url}/wp-json/wp/v2/posts/{p['id']}",
                                   auth=auth(pw), json={"title": new_title}, timeout=20)
                if r.status_code in (200, 201):
                    grand_title_fixed += 1
                    log(f"   [연도수정] #{p['id']}: '{title_raw[:30]}' -> '{new_title[:30]}'")

            # 2) 카테고리 미배정 수정 (즉시 반영)
            cats = p.get("categories", [])
            if default_cat and (not cats or cats == [1]):
                r = requests.post(f"{site_url}/wp-json/wp/v2/posts/{p['id']}",
                                   auth=auth(pw), json={"categories": [default_cat]}, timeout=20)
                if r.status_code in (200, 201):
                    grand_cat_fixed += 1
                    log(f"   [카테고리배정] #{p['id']}: -> 카테고리ID {default_cat}")

            # 3) 더미 슬러그
            if GENERIC_SLUG_PATTERN.match(p.get("slug", "")):
                reasons.append("더미슬러그")

            # 4) 중복 제목
            key = new_title.strip().lower() if new_title else title_raw.strip().lower()
            if key:
                if key in title_seen:
                    reasons.append(f"제목중복(원본#{title_seen[key]})")
                else:
                    title_seen[key] = p["id"]

            # 5) 본문 부족
            chars = content_char_count(p)
            if chars < MIN_CONTENT_CHARS:
                reasons.append(f"본문부족({chars}자)")

            if reasons:
                candidates[p["id"]] = (p, reasons)

        ratio = len(candidates) / total if total else 0
        log(f"   전체 {total}개 중 삭제후보 {len(candidates)}개 ({ratio:.0%})")

        if ratio > SAFETY_RATIO_LIMIT:
            log(f"   🛑 위험: 후보비율 {SAFETY_RATIO_LIMIT:.0%} 초과 → 이 사이트 삭제는 자동 스킵")
            skipped_sites.append(site_url)
            continue

        if DRY_RUN:
            for pid, (p, reasons) in candidates.items():
                t = p.get("title", {}).get("rendered", "")
                log(f"     - [{', '.join(reasons)}] {t[:40]}")
            continue

        force = (DELETE_MODE == "delete")
        deleted, failed = 0, 0
        for pid, (p, reasons) in candidates.items():
            params = {"force": "true"} if force else {}
            r = requests.delete(f"{site_url}/wp-json/wp/v2/posts/{pid}",
                                 auth=auth(pw), params=params, timeout=20)
            if r.status_code in (200, 201):
                deleted += 1
            else:
                failed += 1
        grand_deleted += deleted
        log(f"   🗑️ 처리완료: {deleted}개 성공, {failed}개 실패")

    log(f"\n{'='*80}")
    log(f"전체 요약: 총 게시물 {grand_total}개")
    log(f"  - 제목 연도 수정: {grand_title_fixed}건")
    log(f"  - 카테고리 자동배정: {grand_cat_fixed}건")
    log(f"  - 삭제(휴지통): {grand_deleted}건")
    if skipped_sites:
        log(f"  - 안전상 스킵된 사이트: {', '.join(skipped_sites)}")
    log(f"{'='*80}")

    with open("audit_all_sites_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(_LOG))


if __name__ == "__main__":
    main()
