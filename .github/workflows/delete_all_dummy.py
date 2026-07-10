#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
delete_all_dummy.py — 27개 사이트 더미글 전수 즉시 삭제
"""
import os, requests, time, re, sys

WP_USER = "huh0303@gmail.com"

SITES = [
    ("https://k-health365.com",        "KHEALTH365COM"),
    ("https://koreamedicaltour.com",    "KOREAMEDICALTOURCOM"),
    ("https://koreainvest365.com",      "KOREAINVEST365COM"),
    ("https://ki-korea.com",            "KIKOREACOM"),
    ("https://koreainsurance365.com",   "KOREAINSURANCE365COM"),
    ("https://kfinance365.com",         "KFINANCE365COM"),
    ("https://koreataxnlaw.com",        "KOREATAXNLAWCOM"),
    ("https://koreacrypto365.com",      "KOREACRYPTO365COM"),
    ("https://krealestate365.com",      "KREALESTATE365COM"),
    ("https://ktech365.com",            "KTECH365COM"),
    ("https://kskin365.com",            "KSKIN365COM"),
    ("https://oliveyoungkorea.com",     "OLIVEYOUNGKOREACOM"),
    ("https://kworld365.com",           "KWORLD365COM"),
    ("https://k-trip365.com",           "KTRIP365COM"),
    ("https://k-visa365.com",           "KVISA365COM"),
    ("https://koreawedding365.com",     "KOREAWEDDING365COM"),
    ("https://kstudy365.com",           "KSTUDY365COM"),
    ("https://studyinkorea365.com",     "STUDYINKOREA365COM"),
    ("https://kieca-korea.org",         "KIECAKOREAORG"),
    ("https://ksa-korea.org",           "KSAKOREAORG"),
    ("https://sis-korea.com",           "SISKOREACOM"),
    ("https://jobkorea365.com",         "JOBKOREA365COM"),
    ("https://jobinkorea365.com",       "JOBINKOREA365COM"),
    ("https://jobkoreaglobal.com",      "JOBKOREAGLOBALCOM"),
    ("https://korea365.org",            "KOREA365ORG"),
    ("https://koreanews365.com",        "KOREANEWS365COM"),
    ("https://theseouljournal.com",     "THESEOULJOURNALCOM"),
]

DUMMY_SLUG_PATTERNS = [
    r'^post-\d+$',          # post-5, post-67, post-116, post-88
    r'^\d+$',               # 숫자만
    r'^page-\d+$',          # page-숫자
    r'^sample-page$',       # 기본 샘플 페이지
    r'^hello-world$',       # 기본 hello world
    r'^auto-draft-\d*$',    # auto-draft
]

def is_dummy_slug(slug):
    for pat in DUMMY_SLUG_PATTERNS:
        if re.match(pat, slug, re.IGNORECASE):
            return True
    if slug in ('post', 'posts', 'page', 'pages'):
        return True
    return False

def get_plain_text(html):
    return re.sub(r'<[^>]+>', '', html or '').strip()

grand_deleted = 0
grand_failed  = 0
grand_ok      = 0

print("=" * 65)
print("27개 사이트 더미글 전수조사 + 즉시 영구삭제")
print("=" * 65)
sys.stdout.flush()

for site_url, env_key in SITES:
    pw = os.getenv(env_key, "")
    if not pw:
        print(f"\n⚠️  {site_url} — Secret 없음 스킵")
        sys.stdout.flush()
        continue

    base = f"{site_url}/wp-json/wp/v2"
    auth = (WP_USER, pw)
    site_deleted = 0
    site_ok      = 0

    print(f"\n{'─'*55}")
    print(f"🌐 {site_url}")
    sys.stdout.flush()

    for post_status in ["publish", "draft", "future", "private", "trash"]:
        page = 1
        while True:
            try:
                r = requests.get(
                    f"{base}/posts",
                    auth=auth,
                    params={
                        "per_page": 100,
                        "page": page,
                        "status": post_status,
                        "_fields": "id,slug,title,content"
                    },
                    timeout=30
                )
                if r.status_code == 400:
                    break  # 해당 status 없음
                if r.status_code != 200:
                    break
                posts = r.json()
                if not posts:
                    break

                for p in posts:
                    pid   = p.get("id")
                    slug  = p.get("slug", "")
                    title = p.get("title", {})
                    t_raw = title.get("rendered","") if isinstance(title,dict) else str(title)
                    title_text = get_plain_text(t_raw)
                    content = p.get("content",{})
                    body    = content.get("rendered","") if isinstance(content,dict) else ""
                    body_text = get_plain_text(body)

                    dummy = False
                    reason = ""

                    # 더미 슬러그
                    if is_dummy_slug(slug):
                        dummy  = True
                        reason = f"더미슬러그({slug})"
                    # 본문 100자 미만 + 제목 없음
                    elif not title_text and len(body_text) < 50:
                        dummy  = True
                        reason = "제목+본문없음"

                    if dummy:
                        try:
                            rd = requests.delete(
                                f"{base}/posts/{pid}",
                                auth=auth,
                                params={"force": "true"},
                                timeout=15
                            )
                            if rd.status_code in (200, 201, 204, 410):
                                print(f"  ✅ 삭제 id={pid} slug={slug:25s} {reason}")
                                site_deleted  += 1
                                grand_deleted += 1
                            else:
                                print(f"  ❌ 실패 id={pid} slug={slug} HTTP={rd.status_code}")
                                grand_failed  += 1
                        except Exception as e:
                            print(f"  ⚠️  id={pid} {e}")
                            grand_failed += 1
                        time.sleep(0.3)
                        sys.stdout.flush()
                    else:
                        site_ok    += 1
                        grand_ok   += 1

                if len(posts) < 100:
                    break
                page += 1
                time.sleep(0.2)

            except Exception as e:
                print(f"  ⚠️  {post_status} 조회 오류: {e}")
                sys.stdout.flush()
                break

    print(f"  → 삭제 {site_deleted}개 | 정상보존 {site_ok}개")
    sys.stdout.flush()
    time.sleep(0.5)

print(f"\n{'='*65}")
print(f"✅ 전체 완료")
print(f"   삭제: {grand_deleted}개")
print(f"   실패: {grand_failed}개")
print(f"   정상보존: {grand_ok}개")
print(f"{'='*65}")
