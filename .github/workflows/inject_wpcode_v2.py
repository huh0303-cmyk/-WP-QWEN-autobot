#!/usr/bin/env python3
"""
inject_wpcode_v2.py
WPCode 플러그인으로 애드센스 헤더 코드 26개 사이트 삽입
WPCode REST API: /wp-json/wpcode/v1/snippets
"""
import os, requests, time, sys, json, base64

WP_USER  = "huh0303@gmail.com"
PUB_ID   = "ca-pub-3456727916386941"
GH_TOKEN = os.getenv("GH_PAT","")
GH_REPO  = os.getenv("GITHUB_REPOSITORY","")

ADSENSE_CODE = f'''<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={PUB_ID}" crossorigin="anonymous"></script>
<link rel="preconnect" href="https://pagead2.googlesyndication.com" crossorigin>
<link rel="preconnect" href="https://googleads.g.doubleclick.net" crossorigin>
<style>
ins.adsbygoogle {{ display: block; min-height: 90px; }}
ins.adsbygoogle[data-ad-status="unfilled"],
ins.adsbygoogle:not([data-ad-status]) {{ min-height: 90px !important; background: transparent; }}
.ad-slot, .adsense, .google-auto-placed {{ min-height: 90px; display: block; }}
</style>'''

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

results = {"ok":[], "already":[], "fail":[]}

print("="*60)
print("WPCode로 애드센스 코드 27개 사이트 삽입")
print("="*60)
sys.stdout.flush()

for site_url, env_key in SITES:
    pw = os.getenv(env_key,"")
    if not pw:
        print(f"\n⚠️  {site_url} — Secret없음")
        results["fail"].append(site_url.replace("https://",""))
        continue

    domain = site_url.replace("https://","")
    auth   = (WP_USER, pw)
    print(f"\n🌐 {domain}")
    sys.stdout.flush()

    inserted = False

    # WPCode API 여러 버전 시도
    for api_base in [
        f"{site_url}/wp-json/wpcode/v1",
        f"{site_url}/wp-json/wpcode/v2",
    ]:
        ep = f"{api_base}/snippets"
        try:
            # 목록 조회
            r = requests.get(ep, auth=auth, timeout=10)
            print(f"  {ep}: HTTP {r.status_code}")

            if r.status_code != 200:
                continue

            # 응답 파싱
            resp = r.json()
            items = resp if isinstance(resp, list) else \
                    resp.get("snippets", resp.get("items", resp.get("data",[])))

            # 이미 있는지 확인
            already = False
            for item in items:
                code = str(item.get("code","")) + str(item.get("snippet_code",""))
                if PUB_ID in code or "adsbygoogle" in code:
                    print(f"  ✅ 이미 있음 (ID:{item.get('id')})")
                    results["already"].append(domain)
                    already = True
                    inserted = True
                    break

            if already:
                break

            # 새 스니펫 생성 — WPCode 다양한 필드명 시도
            payloads = [
                # WPCode v1 형식
                {
                    "title":    "Google AdSense Auto Ads",
                    "code":     ADSENSE_CODE,
                    "location": "header",
                    "active":   True,
                    "type":     "html",
                },
                # WPCode v2 형식
                {
                    "title":         "Google AdSense Auto Ads",
                    "snippet_code":  ADSENSE_CODE,
                    "insert_location": "header",
                    "is_active":     True,
                    "code_type":     "html",
                },
                # 최소 형식
                {
                    "title":  "Google AdSense Auto Ads",
                    "code":   ADSENSE_CODE,
                    "active": True,
                },
            ]

            for payload in payloads:
                r2 = requests.post(ep, auth=auth, json=payload, timeout=15)
                print(f"  생성 시도: HTTP {r2.status_code}")
                if r2.status_code in (200, 201):
                    resp2 = r2.json()
                    new_id = resp2.get("id") or resp2.get("snippet_id") or resp2.get("data",{}).get("id")
                    print(f"  ✅ 생성 완료! (ID: {new_id})")
                    results["ok"].append(domain)
                    inserted = True
                    break
                else:
                    err = r2.text[:100]
                    print(f"  응답: {err}")

            if inserted:
                break

        except Exception as e:
            print(f"  ❌ {e}")

    if not inserted and domain not in [x for lst in results.values() for x in lst]:
        results["fail"].append(domain)

    time.sleep(0.5)

# 결과 저장
if GH_TOKEN:
    content = base64.b64encode(json.dumps(results,ensure_ascii=False,indent=2).encode()).decode()
    gh_h = {"Authorization":f"token {GH_TOKEN}","Content-Type":"application/json"}
    path = "wpcode_final_result.json"
    rg = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                     headers=gh_h,timeout=10)
    sha = rg.json().get("sha","") if rg.status_code==200 else ""
    payload = {"message":"result: WPCode 애드센스 최종","content":content}
    if sha: payload["sha"] = sha
    requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                headers=gh_h,json=payload,timeout=15)

print(f"\n{'='*60}")
print(f"✅ 완료")
print(f"   성공:       {len(results['ok'])}개 {results['ok'][:3]}")
print(f"   이미 있음:  {len(results['already'])}개")
print(f"   실패:       {len(results['fail'])}개")
if results['fail']:
    print(f"   실패목록: {results['fail'][:5]}")
print(f"{'='*60}")
