#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ping_sitemaps.py
Google/Bing/Naver/Yandex에 27개 사이트맵 직접 ping
GSC에 수동 제출 없이 구글이 사이트맵을 인식하게 함
"""
import os, requests, time, sys, json, base64

GH_TOKEN = os.getenv("GH_PAT","")
GH_REPO  = os.getenv("GITHUB_REPOSITORY","huh0303-cmyk/-WP-QWEN-autobot")

SITES = [
    "https://k-health365.com",
    "https://koreamedicaltour.com",
    "https://koreainvest365.com",
    "https://ki-korea.com",
    "https://koreainsurance365.com",
    "https://kfinance365.com",
    "https://koreataxnlaw.com",
    "https://koreacrypto365.com",
    "https://krealestate365.com",
    "https://ktech365.com",
    "https://kskin365.com",
    "https://oliveyoungkorea.com",
    "https://kworld365.com",
    "https://k-trip365.com",
    "https://k-visa365.com",
    "https://koreawedding365.com",
    "https://kstudy365.com",
    "https://studyinkorea365.com",
    "https://kieca-korea.org",
    "https://ksa-korea.org",
    "https://sis-korea.com",
    "https://jobkorea365.com",
    "https://jobinkorea365.com",
    "https://jobkoreaglobal.com",
    "https://korea365.org",
    "https://koreanews365.com",
    "https://theseouljournal.com",
]

PING_ENGINES = {
    "Google": "https://www.google.com/ping?sitemap=",
    "Bing":   "https://www.bing.com/ping?sitemap=",
    "Naver":  "https://searchadvisor.naver.com/xml/submit?url=",
    "Yandex": "https://webmaster.yandex.com/ping?sitemap=",
}

results = {}
total_ok = total_fail = 0

print("="*60)
print("27개 사이트 사이트맵 검색엔진 ping")
print("="*60)
sys.stdout.flush()

for site in SITES:
    domain = site.replace("https://","")
    site_results = {"ok":[], "fail":[]}
    print(f"\n🌐 {domain}")

    sitemaps = [
        f"{site}/sitemap_index.xml",
        f"{site}/post-sitemap.xml",
    ]

    for sm in sitemaps:
        enc = requests.utils.quote(sm, safe="")
        for engine, ping_url in PING_ENGINES.items():
            try:
                r = requests.get(f"{ping_url}{enc}", timeout=10)
                if r.status_code in (200,201,202):
                    print(f"  ✅ {engine} ← {sm.split('/')[-1]}")
                    site_results["ok"].append(f"{engine}:{sm.split('/')[-1]}")
                    total_ok += 1
                else:
                    print(f"  ⚠️ {engine} HTTP {r.status_code}")
                    site_results["fail"].append(f"{engine}:{r.status_code}")
                    total_fail += 1
            except Exception as e:
                print(f"  ❌ {engine}: {str(e)[:40]}")
                total_fail += 1
            time.sleep(0.2)

    results[domain] = site_results
    time.sleep(0.5)
    sys.stdout.flush()

# 결과 커밋
final = {"total_ok":total_ok,"total_fail":total_fail,"sites":results}
if GH_TOKEN:
    content = base64.b64encode(json.dumps(final,ensure_ascii=False,indent=2).encode()).decode()
    gh_h = {"Authorization":f"token {GH_TOKEN}","Content-Type":"application/json"}
    path = "sitemap_ping_result.json"
    rg = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",headers=gh_h,timeout=10)
    sha = rg.json().get("sha","") if rg.status_code==200 else ""
    payload = {"message":"result: 27개 사이트맵 ping","content":content}
    if sha: payload["sha"] = sha
    r2 = requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                      headers=gh_h,json=payload,timeout=15)
    print(f"\n결과 커밋: {'✅' if 'content' in r2.json() else '❌'}")

print(f"\n{'='*60}")
print(f"✅ ping 성공: {total_ok}회 | ❌ 실패: {total_fail}회")
print(f"{'='*60}")
