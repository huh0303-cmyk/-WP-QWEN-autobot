#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""27개 사이트: 검토대기(hold) + 스팸(spam) 댓글 전체 영구삭제"""
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


def purge_status(url, pw, status, log):
    deleted = 0
    failed = 0
    while True:
        try:
            r = requests.get(f"{url}/wp-json/wp/v2/comments", auth=auth(pw),
                              params={"status": status, "per_page": 100, "_fields": "id"},
                              timeout=20)
        except Exception as e:
            log(f"  ⚠️ [{status}] 목록조회 실패: {e}")
            break
        if r.status_code != 200:
            break
        batch = r.json()
        if not isinstance(batch, list) or not batch:
            break
        for c in batch:
            try:
                rr = requests.delete(f"{url}/wp-json/wp/v2/comments/{c['id']}", auth=auth(pw),
                                      params={"force": True}, timeout=15)
                if rr.status_code in (200, 201):
                    deleted += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
        if len(batch) < 100:
            break
    return deleted, failed


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
        d1, f1 = purge_status(url, pw, "hold", log)
        d2, f2 = purge_status(url, pw, "spam", log)
        log(f"  🗑️ 검토대기 삭제 {d1}건(실패{f1}) | 스팸함 삭제 {d2}건(실패{f2})")

    with open("purge_pending_comments_result.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
