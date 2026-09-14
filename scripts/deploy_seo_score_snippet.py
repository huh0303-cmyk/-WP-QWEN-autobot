#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deploy_seo_score_snippet.py
─────────────────────────────────────────────────────────────
27개 사이트 전부에 rank_math_seo_score를 REST API meta에 노출시키는
Code Snippets 스니펫을 심는다. (WP_USER 계정이 Code Snippets REST 권한이
있는지 먼저 확인 후, 있으면 생성+활성화까지 한 번에 처리)
"""
import os
import requests

WP_USER = "huh0303@gmail.com"

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

SNIPPET_NAME = "REST: expose rank_math_seo_score"
SNIPPET_CODE = """add_action('init', function () {
    register_post_meta('post', 'rank_math_seo_score', array(
        'show_in_rest' => true,
        'single' => true,
        'type' => 'string',
        'auth_callback' => '__return_true',
    ));
});"""


def log(msg):
    print(msg, flush=True)


def check_auth(site_url, auth):
    r = requests.get(f"{site_url}/wp-json/wp/v2/users/me", auth=auth, timeout=20)
    if r.status_code != 200:
        return None, f"users/me HTTP {r.status_code}: {r.text[:150]}"
    data = r.json()
    return data.get("roles", []), None


def find_existing(site_url, auth):
    r = requests.get(f"{site_url}/wp-json/code-snippets/v1/snippets",
                      auth=auth, params={"per_page": 100}, timeout=20)
    if r.status_code != 200:
        return None, f"list HTTP {r.status_code}: {r.text[:150]}"
    items = r.json()
    for it in items:
        if it.get("name") == SNIPPET_NAME:
            return it, None
    return None, None


def deploy_site(site_url, secret_name):
    pw = os.environ.get(secret_name)
    if not pw:
        return f"[{site_url}] 시크릿 없음 → 건너뜀"

    auth = requests.auth.HTTPBasicAuth(WP_USER, pw)

    try:
        roles, err = check_auth(site_url, auth)
        if err:
            return f"[{site_url}] ⚠️ 인증 확인 실패: {err}"

        existing, err = find_existing(site_url, auth)
        if err:
            return f"[{site_url}] ⚠️ 스니펫 목록 조회 실패 (roles={roles}): {err}"

        if existing:
            sid = existing["id"]
            if existing.get("active"):
                return f"[{site_url}] ✅ 이미 배포+활성화됨 (id={sid}, roles={roles})"
            r = requests.put(f"{site_url}/wp-json/code-snippets/v1/snippets/{sid}",
                              auth=auth, json={"active": True}, timeout=20)
            if r.status_code in (200, 201):
                return f"[{site_url}] ✅ 기존 스니펫 활성화 완료 (id={sid})"
            return f"[{site_url}] ⚠️ 활성화 실패 HTTP {r.status_code}: {r.text[:150]}"

        payload = {
            "name": SNIPPET_NAME,
            "desc": "Rank Math SEO 점수를 WP REST API meta에 노출 (전수조사/모니터링 스크립트용)",
            "code": SNIPPET_CODE,
            "scope": "global",
            "active": True,
        }
        r = requests.post(f"{site_url}/wp-json/code-snippets/v1/snippets",
                           auth=auth, json=payload, timeout=20)
        if r.status_code in (200, 201):
            return f"[{site_url}] ✅ 신규 배포+활성화 완료 (roles={roles})"
        return f"[{site_url}] ⚠️ 생성 실패 HTTP {r.status_code} (roles={roles}): {r.text[:200]}"
    except Exception as e:
        return f"[{site_url}] ⚠️ 오류: {str(e)[:200]}"


def main():
    results = []
    for site_url, secret_name in SITES:
        line = deploy_site(site_url, secret_name)
        log(line)
        results.append(line)

    ok = sum(1 for l in results if "✅" in l)
    log("\n" + "=" * 60)
    log(f"완료: {ok}/{len(SITES)}개 사이트 배포 성공")
    fails = [l for l in results if "✅" not in l]
    if fails:
        log("실패/건너뜀 목록:")
        for l in fails:
            log(f"  {l}")


if __name__ == "__main__":
    main()
