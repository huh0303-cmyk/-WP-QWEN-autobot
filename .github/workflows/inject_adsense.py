#!/usr/bin/env python3
"""
inject_adsense_v2.py
Rank Math Analytics 연동으로 애드센스 코드 삽입
방법: WP Options API 직접 → generate_settings (GeneratePress)
"""
import os, requests, time, sys, json, base64

WP_USER    = "huh0303@gmail.com"
PUB_ID     = "ca-pub-3456727916386941"
GH_TOKEN   = os.getenv("GH_PAT","")
GH_REPO    = os.getenv("GITHUB_REPOSITORY","")

ADSENSE_SCRIPT = f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={PUB_ID}" crossorigin="anonymous"></script>'

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

results = {"ok":[], "fail":[]}

print("="*60)
print("애드센스 Auto Ads 코드 삽입 v2")
print("="*60)
sys.stdout.flush()

for site_url, env_key in SITES:
    pw = os.getenv(env_key,"")
    if not pw:
        results["fail"].append(site_url)
        continue

    domain = site_url.replace("https://","")
    base   = f"{site_url}/wp-json/wp/v2"
    auth   = (WP_USER, pw)
    inserted = False

    print(f"\n🌐 {domain}")
    sys.stdout.flush()

    # ── 방법1: Rank Math Analytics settings에 삽입 ──
    try:
        r = requests.get(f"{site_url}/wp-json/rankmath/v1/settings",
                        auth=auth, timeout=10)
        if r.status_code == 200:
            rm = r.json()
            general = rm.get("general", {})

            # 이미 있는지 확인
            head_code = general.get("head_code","") or ""
            if PUB_ID in head_code:
                print(f"  ✅ 이미 삽입됨 (Rank Math)")
                results["ok"].append(domain)
                inserted = True
            else:
                new_head = (head_code + "\n" + ADSENSE_SCRIPT).strip()
                general["head_code"] = new_head
                r2 = requests.post(
                    f"{site_url}/wp-json/rankmath/v1/settings",
                    auth=auth,
                    json={"general": general},
                    timeout=15
                )
                if r2.status_code == 200:
                    # 확인
                    check = r2.json().get("general",{}).get("head_code","")
                    if PUB_ID in check:
                        print(f"  ✅ Rank Math head_code 삽입 성공")
                        results["ok"].append(domain)
                        inserted = True
                    else:
                        print(f"  ⚠️ Rank Math 저장됐지만 확인 안 됨")
                else:
                    print(f"  ⚠️ Rank Math: HTTP {r2.status_code}")
    except Exception as e:
        print(f"  📍 Rank Math 방법 실패: {e}")

    # ── 방법2: WP 플러그인 옵션 직접 ──
    if not inserted:
        # Insert Headers and Footers 플러그인 (ih_options)
        for plugin_endpoint in [
            f"{site_url}/wp-json/ihaf/v1/code",
            f"{site_url}/wp-json/wpcode/v1/snippets",
        ]:
            try:
                r = requests.get(plugin_endpoint, auth=auth, timeout=5)
                if r.status_code not in (404, 403):
                    print(f"  📍 플러그인 API 발견: {plugin_endpoint}")
            except: pass

    # ── 방법3: GeneratePress hooks ──
    if not inserted:
        try:
            r = requests.get(f"{base}/settings", auth=auth, timeout=10)
            if r.status_code == 200:
                settings = r.json()
                # generate_hooks_data 확인
                for key in settings:
                    if 'generate' in key.lower() and 'hook' in key.lower():
                        current = settings[key]
                        if PUB_ID not in str(current):
                            # 훅에 추가
                            if isinstance(current, dict):
                                current["wp_head"] = ADSENSE_SCRIPT
                            else:
                                current = {"wp_head": ADSENSE_SCRIPT}
                            r2 = requests.post(f"{base}/settings", auth=auth,
                                             json={key: current}, timeout=10)
                            if r2.status_code == 200:
                                print(f"  ✅ GeneratePress hooks 삽입 ({key})")
                                results["ok"].append(domain)
                                inserted = True
                                break
        except Exception as e:
            print(f"  📍 GeneratePress 실패: {e}")

    if not inserted:
        print(f"  ❌ 자동 삽입 불가 → WP 관리자 수동 필요")
        results["fail"].append(domain)

    time.sleep(0.5)

# 결과 저장
if GH_TOKEN:
    content = base64.b64encode(json.dumps(results,ensure_ascii=False,indent=2).encode()).decode()
    gh_h = {"Authorization":f"token {GH_TOKEN}","Content-Type":"application/json"}
    path = "adsense_inject_result.json"
    rg = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                     headers=gh_h, timeout=10)
    sha = rg.json().get("sha","") if rg.status_code==200 else ""
    payload = {"message":"result: 애드센스 삽입 v2","content":content}
    if sha: payload["sha"] = sha
    requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                headers=gh_h, json=payload, timeout=15)

print(f"\n{'='*60}")
print(f"완료 | 성공:{len(results['ok'])} | 수동필요:{len(results['fail'])}")
print(f"{'='*60}")
