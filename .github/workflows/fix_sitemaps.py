#!/usr/bin/env python3
"""sitemap 오류 사이트 긴급 수정 - 퍼머링크 재저장"""
import os, requests, time

WP_USER = "huh0303@gmail.com"

PROBLEM_SITES = [
    ("https://ki-korea.com",        "KIKOREACOM"),
    ("https://kfinance365.com",     "KFINANCE365COM"),
    ("https://kskin365.com",        "KSKIN365COM"),
    ("https://oliveyoungkorea.com", "OLIVEYOUNGKOREACOM"),
    ("https://k-trip365.com",       "KTRIP365COM"),
    ("https://kstudy365.com",       "KSTUDY365COM"),
    ("https://kieca-korea.org",     "KIECAKOREAORG"),
    ("https://ksa-korea.org",       "KSAKOREAORG"),
]

def fix_sitemap(url, pw):
    dom  = url.replace("https://","")
    base = f"{url}/wp-json/wp/v2"
    auth = (WP_USER, pw)
    done = []

    # 1. 퍼머링크 재저장 (가장 중요 — sitemap 살리는 핵심)
    for struct in ["/%postname%/", "/%year%/%postname%/", "/%postname%/"]:
        r = requests.post(f"{base}/settings", auth=auth,
                         json={"permalink_structure": struct}, timeout=10)
        if r.status_code in (200,201):
            done.append(f"퍼머링크✅")
            break
    else:
        done.append("퍼머링크❌")

    time.sleep(1)

    # 2. Rank Math sitemap 강제 활성화
    try:
        r2 = requests.post(
            f"{url}/wp-json/rankmath/v1/updateSettings",
            auth=auth,
            json={"sitemap": {"enable": 1}},
            timeout=10)
        done.append(f"RankMath{'✅' if r2.status_code in (200,201) else '⚠️'}")
    except:
        done.append("RankMath⚠️")

    # 3. LiteSpeed 캐시 삭제 (캐시가 sitemap 막는 경우)
    try:
        requests.get(f"{url}/?litespeed=purge_all", auth=auth, timeout=5)
        requests.post(f"{url}/wp-admin/admin-ajax.php",
                     data={"action":"litespeed_purge_all"},
                     auth=auth, timeout=5)
        done.append("캐시삭제✅")
    except:
        done.append("캐시삭제⚠️")

    time.sleep(2)

    # 4. sitemap 접근 확인
    for sm_path in ["/sitemap_index.xml", "/sitemap.xml"]:
        try:
            r3 = requests.get(f"{url}{sm_path}", timeout=8,
                             headers={"User-Agent":"Googlebot/2.1"},
                             allow_redirects=True)
            if r3.status_code == 200 and ("sitemap" in r3.text.lower() or "xml" in r3.text.lower()):
                done.append(f"sitemap✅({r3.status_code})")
                break
            else:
                done.append(f"sitemap❌({r3.status_code})")
        except Exception as e:
            done.append(f"sitemap❌")

    # 5. Google ping
    try:
        sm = requests.utils.quote(f"{url}/sitemap_index.xml")
        rg = requests.get(f"https://www.google.com/ping?sitemap={sm}", timeout=6)
        done.append(f"Gping{'✅' if rg.status_code==200 else '⚠️'}")
    except:
        done.append("Gping⚠️")

    print(f"  {dom:<28} {' | '.join(done)}")

print("="*65)
print("sitemap 오류 사이트 긴급 수정")
print("="*65)

ok = skip = 0
for url, env in PROBLEM_SITES:
    pw = os.getenv(env, "")
    if not pw:
        print(f"  {url.replace('https://',''):<28} ⏭️ 비번없음")
        skip += 1
        continue
    fix_sitemap(url, pw)
    ok += 1
    time.sleep(0.5)

print("="*65)
print(f"✅ 처리:{ok} | ⏭️:{skip}")
print()
print("📌 완료 후 Search Console에서:")
print("   각 사이트 → Sitemaps → 기존 삭제 → sitemap_index.xml 재제출")
