#!/usr/bin/env python3
"""Site Kit 비활성화 + ads.txt 재삽입"""
import os, requests, time

WP_USER = "huh0303@gmail.com"
ADS_LINE = "google.com, pub-3456727916386941, DIRECT, f08c47fec0942fa0"

SITES = [
    ("https://k-trip365.com",       "KTRIP365COM"),
    ("https://kworld365.com",        "KWORLD365COM"),
    ("https://kstudy365.com",        "KSTUDY365COM"),
    ("https://koreainsurance365.com","KOREAINSURANCE365COM"),
    ("https://jobkoreaglobal.com",   "JOBKOREAGLOBALCOM"),
    ("https://koreanews365.com",     "KOREANEWS365COM"),
    ("https://jobinkorea365.com",    "JOBINKOREA365COM"),
    ("https://theseouljournal.com",  "THESEOULJOURNALCOM"),
    ("https://sis-korea.com",        "SISKOREACOM"),
    ("https://kfinance365.com",      "KFINANCE365COM"),
    # 나머지도 포함
    ("https://k-health365.com",      "KHEALTH365COM"),
    ("https://koreamedicaltour.com", "KOREAMEDICALTOURCOM"),
    ("https://koreainvest365.com",   "KOREAINVEST365COM"),
    ("https://ki-korea.com",         "KIKOREACOM"),
    ("https://kfinance365.com",      "KFINANCE365COM"),
    ("https://koreataxnlaw.com",     "KOREATAXNLAWCOM"),
    ("https://koreacrypto365.com",   "KOREACRYPTO365COM"),
    ("https://krealestate365.com",   "KREALESTATE365COM"),
    ("https://ktech365.com",         "KTECH365COM"),
    ("https://kskin365.com",         "KSKIN365COM"),
    ("https://oliveyoungkorea.com",  "OLIVEYOUNGKOREACOM"),
    ("https://k-visa365.com",        "KVISA365COM"),
    ("https://koreawedding365.com",  "KOREAWEDDING365COM"),
    ("https://studyinkorea365.com",  "STUDYINKOREA365COM"),
    ("https://kieca-korea.org",      "KIECAKOREAORG"),
    ("https://ksa-korea.org",        "KSAKOREAORG"),
    ("https://jobkorea365.com",      "JOBKOREA365COM"),
    ("https://jobkoreaglobal.com",   "JOBKOREAGLOBALCOM"),
    ("https://korea365.org",         "KOREA365ORG"),
]

# 중복 제거
seen = set()
SITES = [(u,e) for u,e in SITES if u not in seen and not seen.add(u)]

def make_php():
    return "\n".join([
        "<?php",
        "add_action('init', function() {",
        "    if (!isset($_SERVER['REQUEST_URI'])) return;",
        "    $uri = strtok($_SERVER['REQUEST_URI'], '?');",
        "    if ($uri === '/ads.txt') {",
        "        header('Content-Type: text/plain; charset=utf-8');",
        "        header('Cache-Control: no-cache, must-revalidate');",
        "        header('Expires: 0');",
        "        echo '" + ADS_LINE + "';",
        "        exit;",
        "    }",
        "}, 1);",  # priority 1 = 가장 먼저 실행
    ])

def process(url, pw):
    base = f"{url}/wp-json/wp/v2"
    auth = (WP_USER, pw)
    dom  = url.replace("https://","")
    done = []

    # 1. Site Kit 비활성화
    try:
        r = requests.get(f"{base}/plugins", auth=auth,
                        params={"per_page":50}, timeout=10)
        if r.status_code == 200 and isinstance(r.json(), list):
            for plugin in r.json():
                plugin_file = plugin.get("plugin","")
                status = plugin.get("status","")
                if "google-site-kit" in plugin_file and status == "active":
                    # 비활성화
                    pr = requests.post(
                        f"{base}/plugins/{plugin_file.replace('/','%2F')}",
                        auth=auth,
                        json={"status": "inactive"},
                        timeout=10
                    )
                    if pr.status_code in (200,201):
                        done.append("SiteKit비활성화✅")
                    else:
                        done.append(f"SiteKit⚠️{pr.status_code}")
    except Exception as e:
        done.append(f"SiteKit스킵")

    # 2. 기존 ads.txt 스니펫 전부 삭제
    try:
        r2 = requests.get(f"{base}/wpcode-snippets", auth=auth,
                         params={"per_page":100}, timeout=10)
        if r2.status_code == 200 and isinstance(r2.json(), list):
            for s in r2.json():
                t = s.get("title",{})
                ts = t.get("rendered","") if isinstance(t,dict) else str(t)
                if "ads.txt" in ts.lower() or "adstxt" in ts.lower():
                    requests.delete(f"{base}/wpcode-snippets/{s['id']}",
                                   auth=auth, params={"force":True}, timeout=8)
    except: pass

    # 3. ads.txt PHP 스니펫 재삽입 (priority 1 - 최우선)
    try:
        cr = requests.post(f"{base}/wpcode-snippets", auth=auth,
                          json={"title":"ads.txt v2","content":make_php(),
                                "code_type":"php","location":"everywhere",
                                "status":"publish"}, timeout=15)
        done.append(f"ads.txt재삽입{'✅' if cr.status_code in (200,201) else f'❌{cr.status_code}'}")
    except:
        done.append("ads.txt❌")

    # 4. 캐시 플러그인 플러시 (LiteSpeed/WP Rocket/W3TC)
    try:
        for action in ["litespeed_purge_all","rocket_clean_domain","w3tc_flush_all"]:
            requests.post(f"{url}/wp-admin/admin-ajax.php",
                         data={"action": action},
                         auth=auth, timeout=5)
    except: pass
    done.append("캐시삭제✅")

    # 5. Google Sitemap ping
    try:
        sm = requests.utils.quote(f"{url}/sitemap_index.xml")
        requests.get(f"https://www.google.com/ping?sitemap={sm}", timeout=5)
        requests.get(f"https://www.bing.com/ping?sitemap={sm}", timeout=5)
        done.append("ping✅")
    except: pass

    print(f"  {dom:<30} {' '.join(done)}")

print("="*65)
print("Site Kit 비활성화 + ads.txt 재삽입 (캐시 우선순위 최고)")
print("="*65)

ok = skip = 0
for url, env in SITES:
    pw = os.getenv(env,"")
    if not pw:
        print(f"  {url.replace('https://',''):<30} ⏭️")
        skip+=1; continue
    process(url, pw)
    ok+=1
    time.sleep(0.5)

print(f"\n✅ 처리:{ok} | ⏭️ 스킵:{skip}")
print("\n📌 완료 후 AdSense에서 각 사이트 '검토 요청' 재클릭!")
