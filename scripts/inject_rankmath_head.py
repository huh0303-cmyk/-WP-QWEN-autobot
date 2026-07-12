#!/usr/bin/env python3
"""
inject_rankmath_head.py
Rank Math general.head_code 에 애드센스 코드 26개 사이트 삽입
"""
import os, requests, time, sys, json, base64

WP_USER  = "huh0303@gmail.com"
GH_TOKEN = os.getenv("GH_PAT","")
GH_REPO  = os.getenv("GITHUB_REPOSITORY","")

# k-health365.com과 동일한 헤더 코드
HEAD_CODE = '''<meta name="google-site-verification" content="dWTlat-p9ttxJTOdFgD7bMDoIvTsgL7DRJf_kTw4Gac" />
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-3456727916386941" crossorigin="anonymous"></script>
<link rel="preconnect" href="https://fonts.googleapis.com" crossorigin>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preconnect" href="https://pagead2.googlesyndication.com" crossorigin>
<link rel="preconnect" href="https://googleads.g.doubleclick.net" crossorigin>
<link rel="preconnect" href="https://www.googletagmanager.com" crossorigin>
<link rel="preconnect" href="https://www.google-analytics.com" crossorigin>
<style>
ins.adsbygoogle { display: block; min-height: 90px; }
ins.adsbygoogle[data-ad-status="unfilled"],
ins.adsbygoogle:not([data-ad-status]) { min-height: 90px !important; background: transparent; }
.ad-slot, .adsense, .google-auto-placed { min-height: 90px; display: block; }
</style>
<script>
document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('img:not([width]):not([height])').forEach(function(img) {
    function setSize() {
      if (img.naturalWidth && !img.getAttribute('width')) {
        img.setAttribute('width', img.naturalWidth);
        img.setAttribute('height', img.naturalHeight);
      }
    }
    if (img.complete) { setSize(); } else { img.addEventListener('load', setSize); }
  });
});
</script>'''

# 애드센스만 (google-site-verification 제외 — 사이트마다 다름)
ADSENSE_ONLY = '''<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-3456727916386941" crossorigin="anonymous"></script>
<link rel="preconnect" href="https://pagead2.googlesyndication.com" crossorigin>
<link rel="preconnect" href="https://googleads.g.doubleclick.net" crossorigin>
<link rel="preconnect" href="https://www.googletagmanager.com" crossorigin>
<link rel="preconnect" href="https://www.google-analytics.com" crossorigin>
<style>
ins.adsbygoogle { display: block; min-height: 90px; }
ins.adsbygoogle[data-ad-status="unfilled"],
ins.adsbygoogle:not([data-ad-status]) { min-height: 90px !important; background: transparent; }
.ad-slot, .adsense, .google-auto-placed { min-height: 90px; display: block; }
</style>
<script>
document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('img:not([width]):not([height])').forEach(function(img) {
    function setSize() {
      if (img.naturalWidth && !img.getAttribute('width')) {
        img.setAttribute('width', img.naturalWidth);
        img.setAttribute('height', img.naturalHeight);
      }
    }
    if (img.complete) { setSize(); } else { img.addEventListener('load', setSize); }
  });
});
</script>'''

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

results = {"ok":[], "already":[], "fail":[]}

print("="*60)
print("Rank Math head_code 애드센스 삽입 — 26개 사이트")
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

    try:
        # Rank Math 현재 설정 읽기
        r = requests.get(f"{site_url}/wp-json/rankmath/v1/settings",
                        auth=auth, timeout=12)

        if r.status_code != 200:
            print(f"  ❌ Rank Math REST: HTTP {r.status_code}")
            results["fail"].append(domain)
            continue

        rm = r.json()
        general = rm.get("general", {})
        current_head = general.get("head_code","") or ""

        # 이미 있는지 확인
        if "ca-pub-3456727916386941" in current_head:
            print(f"  ✅ 이미 삽입됨")
            results["already"].append(domain)
            continue

        # 삽입
        general["head_code"] = current_head + "\n" + ADSENSE_ONLY if current_head.strip() else ADSENSE_ONLY

        r2 = requests.post(
            f"{site_url}/wp-json/rankmath/v1/settings",
            auth=auth,
            json={"general": general},
            timeout=15
        )

        if r2.status_code == 200:
            # 검증
            saved = r2.json().get("general",{}).get("head_code","")
            if "ca-pub-3456727916386941" in saved:
                print(f"  ✅ 삽입 완료!")
                results["ok"].append(domain)
            else:
                print(f"  ⚠️ 저장됐지만 코드 없음")
                results["fail"].append(domain)
        else:
            print(f"  ❌ HTTP {r2.status_code}: {r2.text[:100]}")
            results["fail"].append(domain)

    except Exception as e:
        print(f"  ❌ {e}")
        results["fail"].append(domain)

    time.sleep(0.5)

# 결과 저장
if GH_TOKEN:
    content = base64.b64encode(json.dumps(results,ensure_ascii=False,indent=2).encode()).decode()
    gh_h = {"Authorization":f"token {GH_TOKEN}","Content-Type":"application/json"}
    path = "rankmath_adsense_result.json"
    rg = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                     headers=gh_h,timeout=10)
    sha = rg.json().get("sha","") if rg.status_code==200 else ""
    payload = {"message":"result: Rank Math 애드센스 삽입","content":content}
    if sha: payload["sha"] = sha
    requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                headers=gh_h,json=payload,timeout=15)

print(f"\n{'='*60}")
print(f"✅ 완료")
print(f"   삽입 성공:  {len(results['ok'])}개")
print(f"   이미 있음:  {len(results['already'])}개")
print(f"   실패:       {len(results['fail'])}개")
if results['ok']:
    print(f"\n성공: {results['ok']}")
if results['fail']:
    print(f"실패: {results['fail']}")
print(f"{'='*60}")
