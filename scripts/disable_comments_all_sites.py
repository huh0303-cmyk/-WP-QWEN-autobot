#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
disable_comments_all_sites.py
27개 사이트 전체:
  1) 기존 발행글 전수 comment_status/ping_status → closed (검토요청 이메일의 근본 원인)
  2) 사이트 기본 설정(default_comment_status/default_ping_status) → closed
     (REST가 막혀있는 사이트는 건너뛰고 로그만 남김)
"""
import os, requests, time

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

_LOG = []
def log(m=""):
    print(m)
    _LOG.append(str(m))

def fetch_open_posts(site, auth):
    """comment_status 또는 ping_status가 open인 글만 수집"""
    targets = []
    page = 1
    while True:
        try:
            r = requests.get(f"{site}/wp-json/wp/v2/posts", auth=auth,
                              params={"per_page": 100, "page": page, "status": "publish",
                                      "context": "edit",
                                      "_fields": "id,comment_status,ping_status"}, timeout=25)
        except Exception as e:
            log(f"  ⚠️ 목록 조회 오류(p{page}): {e}")
            break
        if r.status_code != 200:
            if page == 1:
                log(f"  ⚠️ 목록 조회 실패: HTTP {r.status_code} {r.text[:150]}")
            break
        batch = r.json()
        if not batch:
            break
        for p in batch:
            if p.get("comment_status") != "closed" or p.get("ping_status") != "closed":
                targets.append(p["id"])
        if len(batch) < 100:
            break
        page += 1
    return targets

def close_settings(site, auth):
    try:
        r = requests.post(f"{site}/wp-json/wp/v2/settings", auth=auth,
                           json={"default_comment_status": "closed",
                                 "default_ping_status": "closed"}, timeout=20)
        if r.status_code == 200:
            log(f"  ✅ 사이트 기본 설정(신규 글 기본값) closed로 변경")
        else:
            log(f"  ⚠️ 설정 변경 실패: HTTP {r.status_code} {r.text[:150]}")
    except Exception as e:
        log(f"  ⚠️ 설정 변경 오류: {e}")

def main():
    grand_total_closed = 0
    for site, env_key in SITES:
        pw = os.getenv(env_key, "")
        domain = site.replace("https://", "")
        log(f"\n🌐 {domain}")
        if not pw:
            log("  ⚠️ Secret 없음 — 스킵")
            continue
        auth = requests.auth.HTTPBasicAuth(WP_USER, pw)

        close_settings(site, auth)

        targets = fetch_open_posts(site, auth)
        log(f"  댓글/핑백 열려있는 글: {len(targets)}건")
        closed = 0
        for pid in targets:
            try:
                r = requests.post(f"{site}/wp-json/wp/v2/posts/{pid}", auth=auth,
                                   json={"comment_status": "closed", "ping_status": "closed"},
                                   timeout=20)
                if r.status_code in (200, 201):
                    closed += 1
                else:
                    log(f"    [{pid}] 실패 HTTP {r.status_code}")
            except Exception as e:
                log(f"    [{pid}] 오류: {e}")
            time.sleep(0.15)
        log(f"  ✅ {closed}/{len(targets)}건 댓글/핑백 닫음")
        grand_total_closed += closed

    log(f"\n{'='*50}")
    log(f"전체 완료: 총 {grand_total_closed}건 댓글/핑백 닫음")
    log(f"{'='*50}")

    with open("disable_comments_all_sites_result.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(_LOG))

if __name__ == "__main__":
    main()
