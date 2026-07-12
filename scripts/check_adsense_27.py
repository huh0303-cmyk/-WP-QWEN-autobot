#!/usr/bin/env python3
"""GitHub Actions에서 실행 — 27개 사이트 애드센스 코드 확인"""
import os, requests, re, json, base64

WP_USER  = "huh0303@gmail.com"
PUB_ID   = "ca-pub-3456727916386941"
GH_TOKEN = os.getenv("GH_PAT","")
GH_REPO  = os.getenv("GITHUB_REPOSITORY","")

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

ok = []; no_ads = []; error = []

print("="*60)
print("27개 사이트 애드센스 코드 전수 확인")
print("="*60)

for site_url, env_key in SITES:
    pw = os.getenv(env_key,"")
    domain = site_url.replace("https://","")

    # 방법1: 실제 사이트 HTML 확인
    try:
        r = requests.get(site_url, timeout=12,
                        headers={"User-Agent":"Mozilla/5.0 Chrome/120"},
                        allow_redirects=True)
        html = r.text
        count = html.count(PUB_ID)
        if count >= 1:
            status = "⚠️ 중복" if count > 1 else "✅"
            print(f"  {status} {domain} (코드 {count}개)")
            ok.append({"domain":domain,"count":count})
            continue
    except: pass

    # 방법2: WP REST로 WPCode 설정 확인
    if pw:
        try:
            r2 = requests.get(
                f"{site_url}/wp-json/wp/v2/settings",
                auth=(WP_USER, pw), timeout=10
            )
            if r2.status_code == 200:
                settings = r2.json()
                # WPCode 헤더 옵션 확인
                for k,v in settings.items():
                    if PUB_ID in str(v):
                        print(f"  ✅ {domain} (WP Settings: {k})")
                        ok.append({"domain":domain,"count":1})
                        break
                else:
                    print(f"  ❌ {domain} ← 애드센스 없음")
                    no_ads.append(domain)
                continue
        except: pass

    print(f"  ❓ {domain} ← 확인 불가")
    error.append(domain)

# 결과 저장
result = {"ok":ok,"no_ads":no_ads,"error":error}
if GH_TOKEN:
    content = base64.b64encode(json.dumps(result,ensure_ascii=False,indent=2).encode()).decode()
    gh_h = {"Authorization":f"token {GH_TOKEN}","Content-Type":"application/json"}
    path = "adsense_check_result.json"
    rg = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",headers=gh_h,timeout=10)
    sha = rg.json().get("sha","") if rg.status_code==200 else ""
    payload = {"message":"check: 27개 애드센스 전수확인","content":content}
    if sha: payload["sha"] = sha
    requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",headers=gh_h,json=payload,timeout=15)

print(f"\n✅ 정상: {len(ok)}개")
print(f"❌ 없음: {len(no_ads)}개 → {no_ads}")
print(f"❓ 불확실: {len(error)}개 → {error}")
