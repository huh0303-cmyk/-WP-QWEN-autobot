#!/usr/bin/env python3
"""AdSense 검토 요청 + ads.txt 확인 + 크롤링 유도"""
import os, requests, time

WP_USER = "huh0303@gmail.com"
PUB_ID  = "pub-3456727916386941"
ADS_LINE = f"google.com, {PUB_ID}, DIRECT, f08c47fec0942fa0"

SITES = [
    ("https://k-health365.com",       "KHEALTH365COM"),
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

ADSENSE_HEAD = (
    '<script async src="https://pagead2.googlesyndication.com/pagead/js/'
    f'adsbygoogle.js?client=ca-{PUB_ID}" crossorigin="anonymous"></script>'
)

def make_ads_php():
    lines = [
        "<?php",
        "add_action('init', function() {",
        "    if (!isset($_SERVER['REQUEST_URI'])) return;",
        "    $uri = strtok($_SERVER['REQUEST_URI'], '?');",
        "    if ($uri === '/ads.txt') {",
        "        header('Content-Type: text/plain; charset=utf-8');",
        "        header('Cache-Control: public, max-age=3600');",
        "        echo '" + ADS_LINE + "';",
        "        exit;",
        "    }",
        "}, 1);",
    ]
    return "\n".join(lines)

def process(url, pw):
    base = f"{url}/wp-json/wp/v2"
    auth = (WP_USER, pw)
    dom  = url.replace("https://","")
    done = []

    # 1. ads.txt 현재 확인
    try:
        r = requests.get(f"{url}/ads.txt", timeout=8,
                        headers={"User-Agent":"Googlebot/2.1"})
        if r.status_code == 200 and PUB_ID in r.text:
            done.append("ads.txt✅")
        else:
            # ads.txt 없으면 WPCode로 삽입
            php = make_ads_php()
            snippet = {"title":"ads.txt Generator","content":php,
                      "code_type":"php","location":"everywhere","status":"publish"}
            # 기존 삭제
            r2 = requests.get(f"{base}/wpcode-snippets", auth=auth,
                             params={"per_page":100}, timeout=10)
            if r2.status_code == 200 and isinstance(r2.json(), list):
                for s in r2.json():
                    t = s.get("title",{})
                    ts = t.get("rendered","") if isinstance(t,dict) else str(t)
                    if "ads.txt" in ts.lower():
                        requests.delete(f"{base}/wpcode-snippets/{s['id']}",
                                       auth=auth, params={"force":True}, timeout=8)
            cr = requests.post(f"{base}/wpcode-snippets", auth=auth,
                              json=snippet, timeout=15)
            done.append(f"ads.txt재삽입{'✅' if cr.status_code in (200,201) else '⚠️'}")
    except:
        done.append("ads.txt❌")

    # 2. AdSense 헤더 스크립트 삽입 (크롤링 유도)
    try:
        existing = requests.get(f"{base}/wpcode-snippets", auth=auth,
                               params={"per_page":100}, timeout=10)
        has_adsense = False
        if existing.status_code == 200:
            for s in existing.json():
                t = s.get("title",{})
                ts = t.get("rendered","") if isinstance(t,dict) else str(t)
                if "adsense header" in ts.lower() or "adsbygoogle" in ts.lower():
                    has_adsense = True
                    break
        if not has_adsense:
            hs = {"title":"AdSense Header","content":ADSENSE_HEAD,
                 "code_type":"html","location":"site_header","status":"publish"}
            cr2 = requests.post(f"{base}/wpcode-snippets", auth=auth,
                               json=hs, timeout=15)
            done.append(f"AdSense헤더{'✅' if cr2.status_code in (200,201) else '⚠️'}")
        else:
            done.append("AdSense헤더✅기존")
    except:
        done.append("AdSense헤더❌")

    # 3. 색인 허용
    try:
        requests.post(f"{base}/settings", auth=auth,
                     json={"blog_public":True}, timeout=8)
        done.append("색인✅")
    except:
        done.append("색인❌")

    # 4. Google + Bing Sitemap ping
    try:
        sm = requests.utils.quote(f"{url}/sitemap_index.xml")
        requests.get(f"https://www.google.com/ping?sitemap={sm}", timeout=6)
        requests.get(f"https://www.bing.com/ping?sitemap={sm}", timeout=6)
        done.append("ping✅")
    except:
        done.append("ping⚠️")

    print(f"  {dom:<32} {' '.join(done)}")

print("="*70)
print(f"AdSense 승인 준비 — 27개 사이트 전체 처리")
print(f"ads.txt 확인 + AdSense 헤더 삽입 + Google ping")
print("="*70)

ok = skip = 0
for url, env in SITES:
    pw = os.getenv(env, "")
    if not pw:
        print(f"  {url.replace('https://',''):<32} ⏭️ 비번없음")
        skip += 1
        continue
    process(url, pw)
    ok += 1
    time.sleep(0.5)

print("="*70)
print(f"✅ 처리완료:{ok} | ⏭️ 스킵:{skip}")
print()
print("📌 다음 단계 (처장님이 직접):")
print("   adsense.google.com → 사이트 목록")
print("   각 사이트 클릭 → '검토 요청' 버튼 클릭")
print()
print("   우선순위 (글 50건+):")
sites_priority = [
    "k-trip365.com (444건)",
    "theseouljournal.com (131건)",
    "koreanews365.com (127건)",
    "korea365.org (111건)",
    "koreataxnlaw.com (89건)",
    "koreainsurance365.com (80건)",
    "kskin365.com (72건)",
    "jobinkorea365.com (64건)",
    "k-visa365.com (62건)",
    "jobkorea365.com (57건)",
]
for s in sites_priority:
    print(f"   → {s}")
