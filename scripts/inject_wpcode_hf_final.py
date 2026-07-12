#!/usr/bin/env python3
import os, requests, time, sys, json, base64

WP_USER  = "huh0303@gmail.com"
PUB_ID   = "ca-pub-3456727916386941"
GH_TOKEN = os.getenv("GH_PAT","")
GH_REPO  = os.getenv("GITHUB_REPOSITORY","")

HEADER_CODE = '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-3456727916386941" crossorigin="anonymous"></script>\n<link rel="preconnect" href="https://fonts.googleapis.com" crossorigin>\n<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n<link rel="preconnect" href="https://pagead2.googlesyndication.com" crossorigin>\n<link rel="preconnect" href="https://googleads.g.doubleclick.net" crossorigin>\n<link rel="preconnect" href="https://www.googletagmanager.com" crossorigin>\n<link rel="preconnect" href="https://www.google-analytics.com" crossorigin>\n<style>\nins.adsbygoogle { display: block; min-height: 90px; }\nins.adsbygoogle[data-ad-status="unfilled"],\nins.adsbygoogle:not([data-ad-status]) { min-height: 90px !important; background: transparent; }\n.ad-slot, .adsense, .google-auto-placed { min-height: 90px; display: block; }\n</style>\n<script>\ndocument.addEventListener(\'DOMContentLoaded\', function() {\n  document.querySelectorAll(\'img:not([width]):not([height])\').forEach(function(img) {\n    function setSize() {\n      if (img.naturalWidth && !img.getAttribute(\'width\')) {\n        img.setAttribute(\'width\', img.naturalWidth);\n        img.setAttribute(\'height\', img.naturalHeight);\n      }\n    }\n    if (img.complete) { setSize(); } else { img.addEventListener(\'load\', setSize); }\n  });\n});\n</script>'

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
print("="*55)
print("WPCode Header & Footer 26개 사이트 애드센스 삽입")
print("="*55)
sys.stdout.flush()

for site_url, env_key in SITES:
    pw = os.getenv(env_key,"")
    if not pw:
        results["fail"].append(site_url.replace("https://",""))
        continue

    domain = site_url.replace("https://","")
    auth   = (WP_USER, pw)
    print(f"\n🌐 {domain}")
    sys.stdout.flush()
    inserted = False

    # WPCode admin-ajax로 저장
    # nonce 먼저 가져오기
    try:
        # nonce 획득
        r_nonce = requests.get(
            f"{site_url}/wp-json/wpcode/v1/headers-footers",
            auth=auth, timeout=8
        )
        if r_nonce.status_code == 200:
            data = r_nonce.json()
            header = data.get("header","") or data.get("head_scripts","") or ""
            if PUB_ID in str(header):
                print(f"  ✅ 이미 있음")
                results["already"].append(domain)
                inserted = True
            else:
                new_h = (header + "\n" + HEADER_CODE).strip() if header else HEADER_CODE
                r2 = requests.post(
                    f"{site_url}/wp-json/wpcode/v1/headers-footers",
                    auth=auth,
                    json={"header": new_h, "body": "", "footer": ""},
                    timeout=12
                )
                if r2.status_code in (200,201):
                    print(f"  ✅ REST API 삽입 성공!")
                    results["ok"].append(domain)
                    inserted = True
                else:
                    print(f"  REST: HTTP {r2.status_code} {r2.text[:80]}")
        else:
            print(f"  REST: HTTP {r_nonce.status_code}")
    except Exception as e:
        print(f"  REST 오류: {e}")

    # WP REST Settings로 wpcode 옵션 직접 저장
    if not inserted:
        try:
            # WPCode가 register_setting으로 노출하는 키 직접 시도
            for opt_key in ["wpcode_header_scripts","wpcode_head","wpcodeheader"]:
                r = requests.post(
                    f"{site_url}/wp-json/wp/v2/settings",
                    auth=auth,
                    json={opt_key: HEADER_CODE},
                    timeout=10
                )
                if r.status_code == 200:
                    val = r.json().get(opt_key,"")
                    if PUB_ID in str(val):
                        print(f"  ✅ WP Settings 삽입 ({opt_key})!")
                        results["ok"].append(domain)
                        inserted = True
                        break
        except: pass

    # admin-ajax 직접 시도
    if not inserted:
        try:
            # WPCode nonce 없이 시도
            r = requests.post(
                f"{site_url}/wp-admin/admin-ajax.php",
                auth=auth,
                data={
                    "action": "wpcode_update_headers_footers",
                    "header": HEADER_CODE,
                    "body":   "",
                    "footer": "",
                },
                timeout=10
            )
            print(f"  ajax: {r.status_code} {r.text[:60]}")
            if "success" in r.text.lower() or r.status_code == 200:
                print(f"  ✅ ajax 성공 가능성")
                results["ok"].append(domain)
                inserted = True
        except Exception as e:
            print(f"  ajax 오류: {e}")

    if not inserted and domain not in [x for lst in results.values() for x in lst]:
        results["fail"].append(domain)
    time.sleep(0.5)

if GH_TOKEN:
    content = base64.b64encode(json.dumps(results,ensure_ascii=False,indent=2).encode()).decode()
    gh_h = {"Authorization":f"token {GH_TOKEN}","Content-Type":"application/json"}
    path = "wpcode_hf_final_result.json"
    rg = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",headers=gh_h,timeout=10)
    sha = rg.json().get("sha","") if rg.status_code==200 else ""
    payload = {"message":"result: WPCode HF 최종","content":content}
    if sha: payload["sha"] = sha
    requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",headers=gh_h,json=payload,timeout=15)

print(f"\n성공:{len(results['ok'])} 이미:{len(results['already'])} 실패:{len(results['fail'])}")
