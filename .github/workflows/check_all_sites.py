#!/usr/bin/env python3
"""27개 사이트 ads.txt / robots.txt / 색인 상태 확인"""
import os, requests, time

WP_USER = "huh0303@gmail.com"
PUB_ID  = "pub-3456727916386941"
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0.0.0"}

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

def check(url, pw):
    dom = url.replace("https://","")
    result = {"dom": dom, "ads": "❌", "robots": "❌",
              "noindex": "?", "wp_url": "?", "posts": "?"}

    # 1. ads.txt
    try:
        r = requests.get(f"{url}/ads.txt", timeout=8, headers=HDR)
        if r.status_code == 200 and PUB_ID in r.text:
            result["ads"] = "✅"
        elif r.status_code == 200:
            result["ads"] = f"⚠️내용오류"
        else:
            result["ads"] = f"❌{r.status_code}"
    except Exception as e:
        result["ads"] = f"❌"

    # 2. robots.txt
    try:
        r = requests.get(f"{url}/robots.txt", timeout=8, headers=HDR)
        if r.status_code == 200:
            txt = r.text.lower()
            if "disallow: /" in txt and "allow: /" not in txt:
                result["robots"] = "🔴전체차단"
            elif "allow: /" in txt or "user-agent: *" in txt:
                result["robots"] = "✅"
            else:
                result["robots"] = "⚠️불명확"
        else:
            result["robots"] = f"❌{r.status_code}"
    except:
        result["robots"] = "❌"

    if not pw:
        return result

    # 3. WP URL 설정 (www 여부)
    try:
        r = requests.get(f"{url}/wp-json/wp/v2/settings",
                        auth=(WP_USER, pw), timeout=8)
        if r.status_code == 200:
            s = r.json()
            site_url = s.get("url","")
            home_url = s.get("home","")
            has_www = "www." in site_url or "www." in home_url
            result["wp_url"] = f"⚠️www포함" if has_www else "✅non-www"
    except:
        result["wp_url"] = "❌"

    # 4. 글수 + noindex 확인
    try:
        r = requests.get(f"{url}/wp-json/wp/v2/posts",
                        auth=(WP_USER, pw),
                        params={"per_page":1,"status":"publish"}, timeout=8)
        if r.status_code == 200:
            total = int(r.headers.get("X-WP-Total", 0))
            result["posts"] = str(total)
    except:
        result["posts"] = "?"

    return result

print(f"{'#':>2} {'도메인':<28} {'ads.txt':>8} {'robots':>8} {'wp_url':>10} {'글수':>5}")
print("═"*70)

ads_ok = robots_ok = www_ok = 0
problems = []

for i, (url, env) in enumerate(SITES, 1):
    pw = os.getenv(env, "")
    r  = check(url, pw)

    if "✅" in r["ads"]:    ads_ok += 1
    if "✅" in r["robots"]: robots_ok += 1
    if "✅" in r["wp_url"]: www_ok += 1

    # 문제 사이트 기록
    issues = []
    if "✅" not in r["ads"]:    issues.append(f"ads.txt:{r['ads']}")
    if "✅" not in r["robots"]: issues.append(f"robots:{r['robots']}")
    if "✅" not in r["wp_url"] and r["wp_url"] != "?":
        issues.append(f"url:{r['wp_url']}")
    if issues:
        problems.append((i, r["dom"], issues))

    print(f"{i:>2} {r['dom']:<28} {r['ads']:>8} {r['robots']:>8} {r['wp_url']:>10} {r['posts']:>5}건")
    time.sleep(0.3)

print("═"*70)
print(f"ads.txt✅:{ads_ok}/27 | robots✅:{robots_ok}/27 | non-www✅:{www_ok}/27")

if problems:
    print(f"\n🔴 수정 필요 사이트 ({len(problems)}개):")
    for i, dom, issues in problems:
        print(f"  [{i}] {dom}: {' | '.join(issues)}")
else:
    print("\n✅ 모든 사이트 정상!")
