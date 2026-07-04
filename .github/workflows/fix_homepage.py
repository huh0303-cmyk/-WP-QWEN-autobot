#!/usr/bin/env python3
"""fix_homepage.py - {{post_title}} 문제 긴급 수정"""
import os, requests, time

WP_USER = "huh0303@gmail.com"

SITES = [
    ("https://jobinkorea365.com",  "JOBINKOREA365COM"),
    ("https://jobkorea365.com",    "JOBKOREA365COM"),
    ("https://jobkoreaglobal.com", "JOBKOREAGLOBALCOM"),
]

def fix(url, pw):
    base = f"{url}/wp-json/wp/v2"
    auth = (WP_USER, pw)
    dom = url.replace("https://","")
    done = []

    # 1. 홈페이지 최신글로 강제 설정
    r = requests.post(f"{base}/settings", auth=auth,
                     json={"show_on_front":"posts","page_on_front":0,"page_for_posts":0},
                     timeout=10)
    done.append(f"홈페이지최신글{'✅' if r.status_code in (200,201) else '⚠️'}")

    # 2. Elementor 템플릿 전부 삭제
    removed = 0
    for pt in ["elementor_library","wp_template","wp_template_part"]:
        try:
            r2 = requests.get(f"{base}/{pt}", auth=auth,
                             params={"per_page":100,"status":"any"}, timeout=10)
            if r2.status_code == 200 and isinstance(r2.json(), list):
                for item in r2.json():
                    dr = requests.delete(f"{base}/{pt}/{item['id']}",
                                        auth=auth, params={"force":True}, timeout=8)
                    if dr.status_code in (200,201):
                        removed += 1
        except: pass
    done.append(f"Elementor삭제{removed}개✅")

    # 3. GP Premium 활성화 확인
    try:
        rt = requests.get(f"{base}/themes", auth=auth,
                         params={"status":"active"}, timeout=8)
        if rt.status_code == 200:
            themes = rt.json()
            tlist = themes if isinstance(themes, list) else list(themes.values())
            for t in tlist:
                slug = t.get("stylesheet","")
                if "generatepress" in slug.lower():
                    done.append("GP✅")
                    break
    except: pass

    print(f"  {dom:<30} {' '.join(done)}")

print("="*60)
print("{{post_title}} 긴급 수정")
print("="*60)
for url, env in SITES:
    pw = os.getenv(env,"")
    if not pw:
        print(f"  {url.replace('https://',''):<30} 비번없음")
        continue
    fix(url, pw)
    time.sleep(0.5)
print("완료!")
