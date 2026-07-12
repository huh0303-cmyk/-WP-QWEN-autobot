#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_rankmath_noindex.py — 27개 사이트 Rank Math noindex 설정
방법: WP REST API → /wp-json/wp/v2/settings 로
      rank_math_titles 옵션의 tag/author/date/search → noindex 설정
"""
import os, requests, time, sys, json, base64

WP_USER  = "huh0303@gmail.com"
GH_TOKEN = os.getenv("GH_PAT","")
GH_REPO  = os.getenv("GITHUB_REPOSITORY","huh0303-cmyk/-WP-QWEN-autobot")

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

results = []
grand_ok = grand_fail = 0

print("="*60)
print("27개 사이트 Rank Math noindex 설정")
print("태그·작성자·날짜·검색 페이지 → noindex")
print("="*60)
sys.stdout.flush()

for site_url, env_key in SITES:
    pw = os.getenv(env_key, "")
    if not pw:
        print(f"\n⚠️  {site_url} — Secret없음 스킵")
        continue

    base = f"{site_url}/wp-json/wp/v2"
    auth = (WP_USER, pw)
    site_ok = site_fail = 0
    done = []

    print(f"\n{'─'*50}")
    print(f"🌐 {site_url}")
    sys.stdout.flush()

    # ── 1. blog_public = True ─────────────────────────────
    try:
        r = requests.post(f"{base}/settings", auth=auth,
                          json={"blog_public": True}, timeout=10)
        if r.status_code == 200:
            print(f"  ✅ blog_public → True")
            site_ok += 1; done.append("blog_public")
    except Exception as e:
        print(f"  ⚠️ blog_public: {e}")

    # ── 2. Rank Math REST API v1 ─────────────────────────
    # /wp-json/rankmath/v1/settings (Rank Math 2.x)
    try:
        r = requests.get(f"{site_url}/wp-json/rankmath/v1/settings",
                         auth=auth, timeout=10)
        if r.status_code == 200:
            current = r.json()
            # 현재 titles 설정 가져오기
            titles = current.get("titles", {})

            # noindex 적용할 항목들
            noindex_targets = {
                "post_tag": {"robots": "noindex, follow"},
                "author":   {"robots": "noindex, follow"},
                "date":     {"robots": "noindex, follow"},
                "search":   {"robots": "noindex, follow"},
            }

            for target, setting in noindex_targets.items():
                if target in titles:
                    titles[target].update({"robots": ["noindex", "follow"]})
                else:
                    titles[target] = {"robots": ["noindex", "follow"]}

            # 업데이트 전송
            r2 = requests.post(
                f"{site_url}/wp-json/rankmath/v1/settings",
                auth=auth,
                json={"titles": titles},
                timeout=15
            )
            if r2.status_code in (200, 201):
                print(f"  ✅ Rank Math REST API 설정 완료")
                site_ok += 1; done.append("rankmath_api")
            else:
                print(f"  ⚠️ Rank Math REST: HTTP {r2.status_code}")
        else:
            print(f"  📍 Rank Math REST API: HTTP {r.status_code} (없음)")
    except Exception as e:
        print(f"  📍 Rank Math REST API 없음: {e}")

    # ── 3. WP Options 직접 수정 ──────────────────────────
    # rank_math_titles 옵션을 WP REST Settings에서 직접 PATCH
    # (Rank Math가 WP REST Settings에 등록한 경우)
    try:
        r = requests.get(f"{base}/settings", auth=auth, timeout=10)
        if r.status_code == 200:
            all_settings = r.json()
            # rank_math 관련 키 탐지
            rm_keys = {k:v for k,v in all_settings.items() if 'rank_math' in k}
            if rm_keys:
                print(f"  📋 WP Settings에 Rank Math 키 발견: {list(rm_keys.keys())[:3]}")
    except: pass

    # ── 4. WP Options API (플러그인 없이) ────────────────
    # wp-json/wp/v2/settings에 없는 경우 → custom REST endpoint
    # rank_math/v1/updateSettings 시도
    try:
        r = requests.post(
            f"{site_url}/wp-json/rankmath/v1/updateSettings",
            auth=auth,
            json={
                "general": {
                    "noindex_archive_subpage": 1,
                    "noindex_password_protected": 1,
                },
                "titles": {
                    "post_tag": {
                        "robots": ["noindex", "follow"],
                        "sitemap": 0,
                    },
                    "post_author": {
                        "robots": ["noindex", "follow"],
                        "sitemap": 0,
                    },
                    "author": {
                        "robots": ["noindex", "follow"],
                        "sitemap": 0,
                    },
                    "date": {
                        "robots": ["noindex", "follow"],
                        "sitemap": 0,
                    },
                    "search": {
                        "robots": ["noindex", "follow"],
                    },
                }
            },
            timeout=15
        )
        if r.status_code in (200, 201):
            print(f"  ✅ updateSettings 성공")
            site_ok += 1; done.append("updateSettings")
        else:
            print(f"  📍 updateSettings: HTTP {r.status_code}")
    except Exception as e:
        print(f"  📍 updateSettings 없음: {e}")

    # ── 5. 사이트맵에서 태그·작성자 제외 ─────────────────
    # Rank Math 사이트맵 설정: 태그·작성자 페이지를 사이트맵에서 제외
    sitemap_payloads = [
        {"sitemap": {"exclude_roles": ["author"], "exclude_terms": ["post_tag"]}},
    ]
    for sp in sitemap_payloads:
        try:
            r = requests.post(
                f"{site_url}/wp-json/rankmath/v1/settings",
                auth=auth, json=sp, timeout=10
            )
        except: pass

    # ── 6. 퍼머링크 재저장 (사이트맵 갱신) ───────────────
    try:
        for _ in range(2):
            requests.post(f"{base}/settings", auth=auth,
                          json={"permalink_structure": "/%postname%/"}, timeout=10)
            time.sleep(0.5)
        print(f"  ✅ 퍼머링크 재저장")
        site_ok += 1; done.append("permalink_resave")
    except Exception as e:
        print(f"  ⚠️ 퍼머링크: {e}")

    results.append({"site": site_url, "ok": site_ok, "fail": site_fail, "done": done})
    grand_ok += site_ok; grand_fail += site_fail
    print(f"  → 성공:{site_ok} | 완료:{done}")
    sys.stdout.flush()
    time.sleep(0.8)

# 결과 커밋
final = {"grand_ok": grand_ok, "grand_fail": grand_fail, "sites": results}
if GH_TOKEN:
    content = base64.b64encode(json.dumps(final, ensure_ascii=False, indent=2).encode()).decode()
    gh_h = {"Authorization": f"token {GH_TOKEN}", "Content-Type": "application/json"}
    path = "rankmath_noindex_result.json"
    r = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}", headers=gh_h, timeout=10)
    sha = r.json().get("sha","") if r.status_code==200 else ""
    payload = {"message":"result: Rank Math noindex 설정","content":content}
    if sha: payload["sha"] = sha
    r2 = requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                      headers=gh_h, json=payload, timeout=15)
    print(f"\n결과 커밋: {'✅' if 'content' in r2.json() else '❌'}")

print(f"\n{'='*60}")
print(f"✅ 완료 | 성공:{grand_ok} | 실패:{grand_fail}")
print(f"{'='*60}")
