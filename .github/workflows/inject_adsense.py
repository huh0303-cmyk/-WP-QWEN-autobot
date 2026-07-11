#!/usr/bin/env python3
"""
inject_adsense.py
27개 사이트 애드센스 광고 코드 자동 삽입
- <head>에 auto ads 코드 삽입
- GeneratePress header hook 활용
"""
import os, requests, time, sys, json, base64

WP_USER    = "huh0303@gmail.com"
ADSENSE_ID = "pub-3456727916386941"
GH_TOKEN   = os.getenv("GH_PAT","")
GH_REPO    = os.getenv("GITHUB_REPOSITORY","")

# 애드센스 Auto Ads 코드
ADSENSE_CODE = f'''<!-- Google AdSense Auto Ads -->
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-{ADSENSE_ID}" crossorigin="anonymous"></script>'''

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

results = {"ok":[],"fail":[],"already":[]}

print("="*60)
print(f"27개 사이트 애드센스 코드 삽입")
print(f"Publisher ID: ca-{ADSENSE_ID}")
print("="*60)
sys.stdout.flush()

for site_url, env_key in SITES:
    pw = os.getenv(env_key,"")
    if not pw:
        print(f"\n⚠️  {site_url} — Secret없음")
        results["fail"].append(site_url)
        continue

    domain = site_url.replace("https://","")
    base   = f"{site_url}/wp-json/wp/v2"
    auth   = (WP_USER, pw)

    print(f"\n🌐 {domain}")
    sys.stdout.flush()

    # ── 방법 1: WP Custom HTML Widget or Theme Header ──
    # GeneratePress: wp_head 훅으로 삽입
    # WP REST API Settings에 head_scripts 없으면
    # → wp_options에 직접 저장

    # 현재 head 설정 확인
    try:
        r = requests.get(f"{base}/settings", auth=auth, timeout=10)
        settings = r.json() if r.status_code==200 else {}

        # GeneratePress 설정에서 header scripts 확인
        gp_settings_keys = [k for k in settings if 'generate' in k.lower() or 'header' in k.lower() or 'script' in k.lower()]
        if gp_settings_keys:
            print(f"  GeneratePress 키: {gp_settings_keys[:3]}")
    except: settings = {}

    # ── 방법 2: WP insert_headers_and_footers 플러그인 ──
    # 또는 Code Snippets 플러그인
    # REST API로 옵션 직접 저장

    # ── 방법 3: theme.json / functions.php 수정 ──
    # → WP File Manager로 직접

    # ── 방법 4: Rank Math Schema에 삽입 ──
    # → 지원 안 함

    # ── 방법 5: WP Options API로 직접 저장 ──
    # insert_headers_and_footers 플러그인 옵션 키:
    # wpcode_header_scripts (WPCode 플러그인)
    # ih_header_code (Insert Headers and Footers)
    # generate_hooks (GeneratePress)

    inserted = False

    # WPCode 플러그인 확인 + 저장
    for option_key in [
        "wpcode_header_scripts",
        "ih_header_code",
        "wp_head_scripts",
        "header_scripts",
        "generate_hooks",
    ]:
        try:
            # WP REST에서 이 옵션이 노출되는지 확인
            test_url = f"{site_url}/wp-json/wp/v2/settings"
            r = requests.get(test_url, auth=auth, timeout=8)
            if r.status_code == 200:
                opts = r.json()
                if option_key in opts:
                    current = opts.get(option_key, "")
                    if ADSENSE_ID in str(current):
                        print(f"  ✅ 이미 삽입됨 ({option_key})")
                        results["already"].append(domain)
                        inserted = True
                        break
                    # 삽입
                    new_val = str(current) + "\n" + ADSENSE_CODE if current else ADSENSE_CODE
                    r2 = requests.post(test_url, auth=auth,
                                      json={option_key: new_val}, timeout=10)
                    if r2.status_code == 200:
                        print(f"  ✅ 삽입 완료 ({option_key})")
                        results["ok"].append(domain)
                        inserted = True
                        break
        except: pass

    if not inserted:
        # ── 방법 6: WP Customizer Additional CSS/JS ──
        # theme_mods에 저장
        try:
            # GeneratePress hooks 직접 저장
            r = requests.post(
                f"{base}/settings",
                auth=auth,
                json={"generate_hooks": {
                    "wp_head": ADSENSE_CODE
                }},
                timeout=10
            )
            if r.status_code == 200 and "generate_hooks" in r.json():
                print(f"  ✅ GeneratePress hook 삽입")
                results["ok"].append(domain)
                inserted = True
        except: pass

    if not inserted:
        # ── 최후 수단: 광고 코드를 functions.php에 추가 ──
        # WP Filesystem API로
        try:
            # 플러그인 생성으로 삽입
            plugin_code = f'''<?php
/**
 * Plugin Name: AdSense Auto Ads
 * Description: Google AdSense Auto Ads
 */
function add_adsense_head() {{
    echo '{ADSENSE_CODE}';
}}
add_action('wp_head', 'add_adsense_head', 1);
'''
            # WP REST로 플러그인 파일 생성은 불가
            # → 대신 wp_options에 직접 저장
            r = requests.post(
                f"{site_url}/wp-json/wp/v2/settings",
                auth=auth,
                json={"page_on_front": None},  # 테스트
                timeout=8
            )
            print(f"  ⚠️  자동 삽입 실패 → 수동 필요")
            results["fail"].append(domain)
        except:
            print(f"  ❌ 완전 실패")
            results["fail"].append(domain)

    time.sleep(0.5)

# 결과 저장
final = results
if GH_TOKEN:
    content = base64.b64encode(json.dumps(final,ensure_ascii=False,indent=2).encode()).decode()
    gh_h = {"Authorization":f"token {GH_TOKEN}","Content-Type":"application/json"}
    path = "adsense_inject_result.json"
    rg = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                     headers=gh_h, timeout=10)
    sha = rg.json().get("sha","") if rg.status_code==200 else ""
    payload = {"message":"result: 애드센스 코드 삽입","content":content}
    if sha: payload["sha"] = sha
    requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                headers=gh_h, json=payload, timeout=15)

print(f"\n{'='*60}")
print(f"✅ 완료")
print(f"  삽입 성공: {len(results['ok'])}개")
print(f"  이미 있음: {len(results['already'])}개")
print(f"  수동 필요: {len(results['fail'])}개")
if results['fail']:
    print(f"\n수동 삽입 필요 사이트:")
    for s in results['fail']:
        print(f"  - {s}")
print(f"{'='*60}")
