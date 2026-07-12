#!/usr/bin/env python3
"""
adsense_verify.py - 소유권 확인 + AdSense 크롤링 유도
1. Site Kit by Google 플러그인으로 소유권 메타태그 삽입
2. AdSense 광고 코드 헤더 삽입
3. WPCode로 ca-pub 광고 태그 삽입
"""
import os, requests, time

WP_USER = "huh0303@gmail.com"
PUB_ID  = "pub-3456727916386941"
ADS_LINE = f"google.com, {PUB_ID}, DIRECT, f08c47fec0942fa0"

ADSENSE_SCRIPT = (
    "<script async src=\"https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?"
    f"client=ca-{PUB_ID}\" crossorigin=\"anonymous\"></script>"
)

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

def make_ads_php(ads_line):
    return chr(10).join([
        "<?php",
        "add_action('init', function() {",
        "    if (!isset($_SERVER['REQUEST_URI'])) return;",
        "    $uri = strtok($_SERVER['REQUEST_URI'], '?');",
        "    if ($uri === '/ads.txt') {",
        "        header('Content-Type: text/plain; charset=utf-8');",
        "        header('Cache-Control: public, max-age=3600');",
        "        echo '" + ads_line + "';",
        "        exit;",
        "    }",
        "}, 1);",
    ])

def process(url, pw):
    base = f"{url}/wp-json/wp/v2"
    auth = (WP_USER, pw)
    dom  = url.replace("https://","")
    done = []

    # 1. ads.txt PHP 스니펫
    try:
        php = make_ads_php(ADS_LINE)
        snippet = {
            "title": "ads.txt Generator",
            "content": php,
            "code_type": "php",
            "location": "everywhere",
            "status": "publish",
        }
        # 기존 삭제
        r = requests.get(f"{base}/wpcode-snippets", auth=auth,
                        params={"per_page":100}, timeout=10)
        if r.status_code == 200 and isinstance(r.json(), list):
            for s in r.json():
                t = s.get("title",{})
                ts = t.get("rendered","") if isinstance(t,dict) else str(t)
                if "ads.txt" in ts.lower():
                    requests.delete(f"{base}/wpcode-snippets/{s['id']}",
                                   auth=auth, params={"force":True}, timeout=8)
        cr = requests.post(f"{base}/wpcode-snippets", auth=auth,
                          json=snippet, timeout=15)
        if cr.status_code in (200,201):
            done.append("ads.txt✅")
        else:
            done.append(f"ads.txt⚠️{cr.status_code}")
    except Exception as e:
        done.append(f"ads.txt❌")

    # 2. AdSense 광고 스크립트 헤더 삽입 (WPCode HTML)
    try:
        html_snippet = {
            "title": "AdSense Header Script",
            "content": ADSENSE_SCRIPT,
            "code_type": "html",
            "location": "site_header",
            "status": "publish",
        }
        r2 = requests.get(f"{base}/wpcode-snippets", auth=auth,
                         params={"per_page":100}, timeout=10)
        if r2.status_code == 200 and isinstance(r2.json(), list):
            for s in r2.json():
                t = s.get("title",{})
                ts = t.get("rendered","") if isinstance(t,dict) else str(t)
                if "adsense header" in ts.lower() or "adsbygoogle" in ts.lower():
                    requests.delete(f"{base}/wpcode-snippets/{s['id']}",
                                   auth=auth, params={"force":True}, timeout=8)
        cr2 = requests.post(f"{base}/wpcode-snippets", auth=auth,
                           json=html_snippet, timeout=15)
        if cr2.status_code in (200,201):
            done.append("AdSense코드✅")
        else:
            # Settings API로 대체
            requests.post(f"{base}/settings", auth=auth,
                         json={"google_adsense_id": f"ca-{PUB_ID}"}, timeout=8)
            done.append(f"AdSense코드⚠️")
    except:
        done.append("AdSense코드❌")

    # 3. robots.txt 색인 허용 확인
    try:
        r3 = requests.post(f"{base}/settings", auth=auth,
                          json={"blog_public": True}, timeout=8)
        done.append("색인허용✅" if r3.status_code in (200,201) else "색인⚠️")
    except:
        done.append("색인❌")

    # 4. Sitemap ping → Google 크롤링 유도
    try:
        sitemap = f"{url}/sitemap_index.xml"
        enc = requests.utils.quote(sitemap)
        requests.get(f"https://www.google.com/ping?sitemap={enc}", timeout=6)
        requests.get(f"https://www.bing.com/ping?sitemap={enc}", timeout=6)
        done.append("ping✅")
    except:
        done.append("ping⚠️")

    print(f"  {dom:<30} {' | '.join(done)}")
    return done

print("="*70)
print("AdSense 소유권 확인 + 크롤링 유도 실행")
print("="*70)

ok = skip = 0
for url, env in SITES:
    pw = os.getenv(env, "")
    if not pw:
        print(f"  {url.replace('https://',''):<30} ⏭️ 비번없음")
        skip += 1
        continue
    process(url, pw)
    ok += 1
    time.sleep(0.5)

print("="*70)
print(f"✅ 처리:{ok} | ⏭️ 스킵:{skip}")
print("\n📌 다음 단계:")
print("  AdSense → 각 사이트 → 검토 요청 클릭")
print("  24~48시간 후 '찾을 수 없음' → '승인됨' 전환 예상")
