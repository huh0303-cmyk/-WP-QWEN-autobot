#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""27개 사이트: (1) 신규 글 기본 댓글 상태 closed로 변경 (2) 기존 발행글 전체 댓글 닫기"""
import os
import requests

WP_USER = "huh0303@gmail.com"

SITES = [
    ("https://k-health365.com", "KHEALTH365COM"),
    ("https://koreamedicaltour.com", "KOREAMEDICALTOURCOM"),
    ("https://koreainvest365.com", "KOREAINVEST365COM"),
    ("https://ki-korea.com", "KIKOREACOM"),
    ("https://koreainsurance365.com", "KOREAINSURANCE365COM"),
    ("https://kfinance365.com", "KFINANCE365COM"),
    ("https://koreataxnlaw.com", "KOREATAXNLAWCOM"),
    ("https://koreacrypto365.com", "KOREACRYPTO365COM"),
    ("https://krealestate365.com", "KREALESTATE365COM"),
    ("https://ktech365.com", "KTECH365COM"),
    ("https://kskin365.com", "KSKIN365COM"),
    ("https://oliveyoungkorea.com", "OLIVEYOUNGKOREACOM"),
    ("https://kworld365.com", "KWORLD365COM"),
    ("https://k-trip365.com", "KTRIP365COM"),
    ("https://k-visa365.com", "KVISA365COM"),
    ("https://koreawedding365.com", "KOREAWEDDING365COM"),
    ("https://kstudy365.com", "KSTUDY365COM"),
    ("https://studyinkorea365.com", "STUDYINKOREA365COM"),
    ("https://kieca-korea.org", "KIECAKOREAORG"),
    ("https://ksa-korea.org", "KSAKOREAORG"),
    ("https://sis-korea.com", "SISKOREACOM"),
    ("https://jobkorea365.com", "JOBKOREA365COM"),
    ("https://jobinkorea365.com", "JOBINKOREA365COM"),
    ("https://jobkoreaglobal.com", "JOBKOREAGLOBALCOM"),
    ("https://korea365.org", "KOREA365ORG"),
    ("https://koreanews365.com", "KOREANEWS365COM"),
    ("https://theseouljournal.com", "THESEOULJOURNALCOM"),
]


def auth(pw):
    return requests.auth.HTTPBasicAuth(WP_USER, pw)


def set_default_closed(url, pw, log):
    try:
        r = requests.post(f"{url}/wp-json/wp/v2/settings", auth=auth(pw),
                           json={"default_comment_status": "closed",
                                 "default_ping_status": "closed"}, timeout=20)
        ok = r.status_code in (200, 201)
        log(f"  {'✅' if ok else '⚠️'} 신규글 기본댓글 OFF 설정 (HTTP {r.status_code})")
        return ok
    except Exception as e:
        log(f"  ⚠️ 설정 실패: {e}")
        return False


def close_all_existing_posts(url, pw, log):
    closed = 0
    already = 0
    failed = 0
    ping_closed = 0
    page = 1
    while True:
        try:
            r = requests.get(f"{url}/wp-json/wp/v2/posts", auth=auth(pw),
                              params={"per_page": 100, "page": page, "status": "publish",
                                      "_fields": "id,comment_status,ping_status"}, timeout=20)
        except Exception as e:
            log(f"  ⚠️ 목록조회 실패 page={page}: {e}")
            break
        if r.status_code != 200:
            break
        batch = r.json()
        if not isinstance(batch, list) or not batch:
            break
        for p in batch:
            needs_comment = p.get("comment_status") != "closed"
            needs_ping = p.get("ping_status") != "closed"
            if not needs_comment and not needs_ping:
                already += 1
                continue
            payload = {}
            if needs_comment:
                payload["comment_status"] = "closed"
            if needs_ping:
                payload["ping_status"] = "closed"
            try:
                rr = requests.post(f"{url}/wp-json/wp/v2/posts/{p['id']}", auth=auth(pw),
                                    json=payload, timeout=15)
                if rr.status_code in (200, 201):
                    if needs_comment:
                        closed += 1
                    if needs_ping:
                        ping_closed += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
        if len(batch) < 100:
            break
        page += 1
    log(f"  📪 댓글닫기: 신규닫음 {closed}건 | 핑백닫음 {ping_closed}건 | 이미완료 {already}건 | 실패 {failed}건")
    return closed, already, failed


def main():
    lines = []

    def log(m):
        print(m)
        lines.append(m)

    for url, env_key in SITES:
        pw = os.getenv(env_key, "")
        log(f"\n🌐 {url}")
        if not pw:
            log("  ⚠️ 비밀번호 없음 — 스킵")
            continue
        set_default_closed(url, pw, log)
        close_all_existing_posts(url, pw, log)

    with open("close_comments_result.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
