#!/usr/bin/env python3
"""
inject_via_wpcode.py
WPCode 플러그인 스니펫 API로 애드센스 코드 삽입
WPCode REST endpoint: /wp-json/wpcode/v1/snippets
"""
import os, requests, time, sys, json, base64

WP_USER    = "huh0303@gmail.com"
PUB_ID     = "ca-pub-3456727916386941"
GH_TOKEN   = os.getenv("GH_PAT","")
GH_REPO    = os.getenv("GITHUB_REPOSITORY","")

# k-health365.com에 있는 것과 동일한 헤더 코드
HEADER_CODE = f'''<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={PUB_ID}" crossorigin="anonymous"></script>
<link rel="preconnect" href="https://pagead2.googlesyndication.com" crossorigin>
<link rel="preconnect" href="https://googleads.g.doubleclick.net" crossorigin>
<style>
ins.adsbygoogle {{ display: block; min-height: 90px; }}
ins.adsbygoogle[data-ad-status="unfilled"],
ins.adsbygoogle:not([data-ad-status]) {{ min-height: 90px !important; background: transparent; }}
.ad-slot, .adsense, .google-auto-placed {{ min-height: 90px; display: block; }}
</style>'''

SITES = [
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

results = {"ok":[], "fail":[]}

print("="*60)
print("WPCode로 애드센스 코드 26개 사이트 삽입")
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
    inserted = False

    print(f"\n🌐 {domain}")
    sys.stdout.flush()

    # ── WPCode v1 스니펫 API ──────────────────────────────
    wpcode_ep = f"{site_url}/wp-json/wpcode/v1/snippets"

    # 기존 스니펫 목록 조회
    try:
        r = requests.get(wpcode_ep, auth=auth, timeout=10)
        print(f"  WPCode API: HTTP {r.status_code}")

        if r.status_code == 200:
            snippets = r.json()
            # 이미 애드센스 코드 있는지 확인
            existing = None
            for sn in (snippets if isinstance(snippets,list) else snippets.get("items",[])):
                if PUB_ID in str(sn.get("code","")) or PUB_ID in str(sn.get("snippet_code","")):
                    existing = sn
                    break

            if existing:
                print(f"  ✅ 이미 존재 (ID: {existing.get('id')})")
                results["ok"].append(domain)
                inserted = True
            else:
                # 새 스니펫 생성
                new_snippet = {
                    "name":     "Google AdSense Auto Ads",
                    "code":     HEADER_CODE,
                    "location": "header",  # wp_head
                    "active":   True,
                    "type":     "html",
                }
                r2 = requests.post(wpcode_ep, auth=auth, json=new_snippet, timeout=15)
                print(f"  스니펫 생성: HTTP {r2.status_code}")

                if r2.status_code in (200, 201):
                    sid = r2.json().get("id") or r2.json().get("snippet_id")
                    print(f"  ✅ WPCode 스니펫 생성 완료 (ID: {sid})")
                    results["ok"].append(domain)
                    inserted = True
                else:
                    print(f"  응답: {r2.text[:150]}")

        elif r.status_code == 401:
            print(f"  ⚠️ 인증 실패")
        elif r.status_code == 404:
            print(f"  ⚠️ WPCode 미설치")
        else:
            print(f"  응답: {r.text[:100]}")

    except Exception as e:
        print(f"  ❌ {e}")

    # ── WPCode v2 시도 ────────────────────────────────────
    if not inserted:
        for alt_ep in [
            f"{site_url}/wp-json/wpcode/v2/snippets",
            f"{site_url}/wp-json/wp-code-manager/v1/snippets",
        ]:
            try:
                r = requests.get(alt_ep, auth=auth, timeout=6)
                if r.status_code == 200:
                    print(f"  대안 API: {alt_ep}")
                    r2 = requests.post(alt_ep, auth=auth,
                                      json={"name":"AdSense","code":HEADER_CODE,
                                            "location":"header","active":True},
                                      timeout=10)
                    if r2.status_code in (200,201):
                        print(f"  ✅ 대안 API로 삽입 성공")
                        results["ok"].append(domain)
                        inserted = True
                        break
            except: pass

    if not inserted:
        results["fail"].append(domain)

    time.sleep(0.5)

# 결과 저장
if GH_TOKEN:
    content = base64.b64encode(json.dumps(results,ensure_ascii=False,indent=2).encode()).decode()
    gh_h = {"Authorization":f"token {GH_TOKEN}","Content-Type":"application/json"}
    path = "adsense_wpcode_result.json"
    rg = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                     headers=gh_h, timeout=10)
    sha = rg.json().get("sha","") if rg.status_code==200 else ""
    payload = {"message":"result: WPCode 애드센스 삽입","content":content}
    if sha: payload["sha"] = sha
    requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                headers=gh_h, json=payload, timeout=15)

print(f"\n{'='*60}")
print(f"✅ 완료 | 성공:{len(results['ok'])} | 실패:{len(results['fail'])}")
if results['ok']:
    print(f"  성공: {results['ok']}")
if results['fail']:
    print(f"  실패: {results['fail']}")
print(f"{'='*60}")
