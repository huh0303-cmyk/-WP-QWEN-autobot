#!/usr/bin/env python3
"""
inject_gp_elements.py
GeneratePress Elements (gp_elements) Hook으로
애드센스 코드를 26개 사이트에 삽입
"""
import os, requests, time, sys, json, base64, re

WP_USER  = "huh0303@gmail.com"
GH_TOKEN = os.getenv("GH_PAT","")
GH_REPO  = os.getenv("GITHUB_REPOSITORY","")
PUB_ID   = "ca-pub-3456727916386941"

# k-health365.com에서 실제 Elements 가져오기
SOURCE_SITE = "https://k-health365.com"
SOURCE_PW   = os.getenv("KHEALTH365COM","")

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

ADSENSE_CODE = f'''<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={PUB_ID}" crossorigin="anonymous"></script>
<link rel="preconnect" href="https://pagead2.googlesyndication.com" crossorigin>
<link rel="preconnect" href="https://googleads.g.doubleclick.net" crossorigin>
<link rel="preconnect" href="https://www.googletagmanager.com" crossorigin>
<link rel="preconnect" href="https://www.google-analytics.com" crossorigin>
<style>
ins.adsbygoogle {{ display: block; min-height: 90px; }}
ins.adsbygoogle[data-ad-status="unfilled"],
ins.adsbygoogle:not([data-ad-status]) {{ min-height: 90px !important; background: transparent; }}
.ad-slot, .adsense, .google-auto-placed {{ min-height: 90px; display: block; }}
</style>
<script>
document.addEventListener('DOMContentLoaded', function() {{
  document.querySelectorAll('img:not([width]):not([height])').forEach(function(img) {{
    function setSize() {{
      if (img.naturalWidth && !img.getAttribute('width')) {{
        img.setAttribute('width', img.naturalWidth);
        img.setAttribute('height', img.naturalHeight);
      }}
    }}
    if (img.complete) {{ setSize(); }} else {{ img.addEventListener('load', setSize); }}
  }});
}});
</script>'''

results = {"ok":[], "already":[], "fail":[]}

print("="*60)
print("GeneratePress Elements로 애드센스 삽입 — 26개 사이트")
print("="*60)
sys.stdout.flush()

# ── Step 1: k-health365에서 Elements 구조 확인 ──────────
print("\n[k-health365.com] GP Elements 확인")
if SOURCE_PW:
    src_auth = (WP_USER, SOURCE_PW)
    r = requests.get(
        f"{SOURCE_SITE}/wp-json/wp/v2/gp_elements",
        auth=src_auth,
        params={"per_page":20,"_fields":"id,title,status,content,meta"},
        timeout=15
    )
    print(f"  gp_elements API: HTTP {r.status_code}")
    if r.status_code == 200:
        elements = r.json()
        print(f"  Elements 수: {len(elements)}")
        adsense_element = None
        for el in elements:
            title = el.get("title",{}).get("rendered","") if isinstance(el.get("title"),dict) else ""
            content_raw = el.get("content",{}).get("rendered","") if isinstance(el.get("content"),dict) else ""
            content_raw += str(el.get("meta",{}))
            has_ads = PUB_ID in content_raw or "adsbygoogle" in content_raw
            print(f"    [{el['id']}] {title} | ads:{has_ads}")
            if has_ads:
                adsense_element = el
        if adsense_element:
            print(f"  ✅ 애드센스 Element 발견: [{adsense_element['id']}]")
    else:
        print(f"  응답: {r.text[:200]}")

# ── Step 2: 26개 사이트에 gp_elements로 삽입 ────────────
print(f"\n[26개 사이트 삽입]")

# GP Elements 생성 페이로드
def make_element_payload(site_url):
    return {
        "title":  "AdSense Auto Ads - Header",
        "content": ADSENSE_CODE,
        "status": "publish",
        "meta": {
            "_generate_element_type":     "hook",
            "_generate_hook":             "wp_head",
            "_generate_execute_php":      "",
            "_generate_display_conditions": [],
            "_generate_user_conditions":    [],
            "_generate_element_display":  "all",
            "_generate_priority":         10,
        }
    }

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

    try:
        # 기존 Elements 확인
        r = requests.get(
            f"{site_url}/wp-json/wp/v2/gp_elements",
            auth=auth,
            params={"per_page":20,"_fields":"id,title,content,meta"},
            timeout=12
        )
        print(f"  gp_elements: HTTP {r.status_code}")

        if r.status_code == 200:
            existing = r.json()
            already  = False
            for el in existing:
                c = str(el.get("content",{})) + str(el.get("meta",{}))
                if PUB_ID in c or "adsbygoogle" in c:
                    print(f"  ✅ 이미 존재")
                    results["already"].append(domain)
                    already = True
                    break

            if not already:
                # 새 Element 생성
                payload = make_element_payload(site_url)
                r2 = requests.post(
                    f"{site_url}/wp-json/wp/v2/gp_elements",
                    auth=auth,
                    json=payload,
                    timeout=15
                )
                print(f"  Element 생성: HTTP {r2.status_code}")
                if r2.status_code in (200, 201):
                    eid = r2.json().get("id")
                    print(f"  ✅ 생성 완료! (ID: {eid})")
                    results["ok"].append(domain)
                else:
                    print(f"  ❌ {r2.text[:150]}")
                    results["fail"].append(domain)

        elif r.status_code == 404:
            print(f"  ⚠️ gp_elements 없음 — GP Elements 미활성화")
            results["fail"].append(domain)
        else:
            print(f"  ❌ HTTP {r.status_code}")
            results["fail"].append(domain)

    except Exception as e:
        print(f"  ❌ {e}")
        results["fail"].append(domain)

    time.sleep(0.5)

# 결과 저장
if GH_TOKEN:
    content = base64.b64encode(json.dumps(results,ensure_ascii=False,indent=2).encode()).decode()
    gh_h = {"Authorization":f"token {GH_TOKEN}","Content-Type":"application/json"}
    path = "gp_elements_result.json"
    rg = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                     headers=gh_h,timeout=10)
    sha = rg.json().get("sha","") if rg.status_code==200 else ""
    payload = {"message":"result: GP Elements 애드센스 삽입","content":content}
    if sha: payload["sha"] = sha
    requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                headers=gh_h,json=payload,timeout=15)

print(f"\n{'='*60}")
print(f"✅ 완료")
print(f"   성공:        {len(results['ok'])}개")
print(f"   이미 있음:   {len(results['already'])}개")
print(f"   실패:        {len(results['fail'])}개")
if results['ok']:
    print(f"\n성공: {results['ok']}")
if results['fail']:
    print(f"실패: {results['fail']}")
print(f"{'='*60}")
