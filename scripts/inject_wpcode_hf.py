#!/usr/bin/env python3
import os, requests, json, base64

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

ADSENSE = f'''<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-{PUB_ID}" crossorigin="anonymous"></script>'''

results = {"ok":[], "already":[], "fail":[]}

print("WPCode Header & Footer 옵션 확인 및 삽입")

for site_url, env_key in SITES:
    pw = os.getenv(env_key,"")
    if not pw:
        results["fail"].append(site_url.replace("https://",""))
        continue

    domain = site_url.replace("https://","")
    auth   = ("huh0303@gmail.com", pw)
    base   = f"{site_url}/wp-json/wp/v2"

    print(f"\n🌐 {domain}")

    # WPCode Header & Footer 옵션 키들
    # wpcode_header_scripts = Header 코드
    # wpcode_footer_scripts = Footer 코드
    wpcode_keys = [
        "wpcode_header_scripts",
        "wpcode_footer_scripts", 
        "wpcode_header_body_scripts",
        "wpcodeHeader",
        "ihaf_opt",  # Insert Headers and Footers 호환
    ]

    try:
        r = requests.get(f"{base}/settings", auth=auth, timeout=10)
        if r.status_code == 200:
            settings = r.json()
            # 모든 키 중 wpcode 관련 찾기
            found_keys = {k:v for k,v in settings.items()
                         if any(x in k.lower() for x in ["wpcode","header_script","footer_script","head_code"])}
            print(f"  WPCode 관련 키: {list(found_keys.keys())}")

            # 이미 있는지
            for k,v in found_keys.items():
                if PUB_ID in str(v):
                    print(f"  ✅ 이미 있음 ({k})")
                    results["already"].append(domain)
                    break
            else:
                # wpcode_header_scripts에 삽입 시도
                for key in ["wpcode_header_scripts"] + list(found_keys.keys()):
                    current = settings.get(key, "")
                    if PUB_ID in str(current):
                        break
                    new_val = (str(current) + "\n" + ADSENSE).strip() if current else ADSENSE
                    r2 = requests.post(f"{base}/settings", auth=auth,
                                      json={key: new_val}, timeout=10)
                    if r2.status_code == 200:
                        saved = r2.json().get(key,"")
                        if PUB_ID in str(saved):
                            print(f"  ✅ 삽입 완료! ({key})")
                            results["ok"].append(domain)
                            break
                        else:
                            print(f"  저장됐지만 확인 안됨 ({key})")
                    else:
                        print(f"  {key}: HTTP {r2.status_code}")
                else:
                    # wpcode_header_scripts 직접 생성
                    r3 = requests.post(f"{base}/settings", auth=auth,
                                      json={"wpcode_header_scripts": ADSENSE}, timeout=10)
                    if r3.status_code == 200 and PUB_ID in str(r3.json().get("wpcode_header_scripts","")):
                        print(f"  ✅ wpcode_header_scripts 직접 삽입!")
                        results["ok"].append(domain)
                    else:
                        print(f"  ❌ 자동 삽입 불가")
                        results["fail"].append(domain)
        else:
            print(f"  ❌ HTTP {r.status_code}")
            results["fail"].append(domain)
    except Exception as e:
        print(f"  ❌ {e}")
        results["fail"].append(domain)

    import time; time.sleep(0.3)

if GH_TOKEN:
    content = base64.b64encode(json.dumps(results,ensure_ascii=False,indent=2).encode()).decode()
    gh_h = {"Authorization":f"token {GH_TOKEN}","Content-Type":"application/json"}
    path = "wpcode_hf_result.json"
    rg = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",headers=gh_h,timeout=10)
    sha = rg.json().get("sha","") if rg.status_code==200 else ""
    payload = {"message":"result: WPCode HF 삽입","content":content}
    if sha: payload["sha"] = sha
    requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",headers=gh_h,json=payload,timeout=15)

print(f"\n완료 | 성공:{len(results['ok'])} | 이미:{len(results['already'])} | 실패:{len(results['fail'])}")
