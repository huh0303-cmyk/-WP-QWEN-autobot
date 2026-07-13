import os, sys, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER, build_diverse_title

site = next(s for s in SITES_CONFIG if s["url"] == "https://jobkoreaglobal.com")
pw = os.getenv(site["wp_pass_env"], "")

r = requests.get(f"{site['url']}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                  params={"per_page": 47, "status": "publish", "_fields": "id,title"}, timeout=30)
posts = r.json()

# 이중으로 꼬인 패턴(제목이 비정상적으로 김) 탐지 후 정리
fixed = 0
for p in posts:
    title = p["title"]["rendered"]
    if len(title) > 90:  # 정상 템플릿은 90자 미만, 이중꼬임만 90자 초과
        # 원래 핵심 키워드만 추출 (알려진 클리셰 접두/접미 제거)
        core = title
        for junk in ["3 Mistakes People Make With ", "A Practical Look at ", "The Real Cost of ",
                     "Cross-Border Trade Korea Careers: ", "The Truth About ", "Behind the Scenes: What ",
                     "How to Actually Handle ", "WTO Korea Representative: "]:
            core = core.replace(junk, "")
        for junk in [" for International Patients", " — What to Expect", " That Most People Get Wrong",
                     " Actually Involves", ": A Specialist&#8217;s Guide", " Warning Signs You Should Never Ignore",
                     " 101: What First-Timers Should Know"]:
            core = core.replace(junk, "")
        # 남은 클리셰 질문형/느낌표 접두 제거
        import re
        core = re.sub(r'^(Are You |Is |Don\'t |Stop )', '', core)
        core = re.split(r'[?:]', core)[0].strip()
        core = re.sub(r'\(.*?\)', '', core).strip()
        if len(core) > 60:
            core = core[:60].rsplit(' ', 1)[0]

        new_title = build_diverse_title(core, "en", site_url=site["url"])
        rr = requests.patch(f"{site['url']}/wp-json/wp/v2/posts/{p['id']}", auth=(WP_USER, pw),
                             json={"title": new_title}, timeout=20)
        print(f"[{p['id']}] {title[:50]}...\n  -> keyword='{core}' -> {new_title} | {rr.status_code}")
        fixed += 1

print(f"\n총 {fixed}개 수정")
