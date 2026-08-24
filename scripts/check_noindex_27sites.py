#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_noindex_27sites.py
27개 사이트 전체 발행글을 대상으로 Googlebot UA로 직접 접속해서
실제 noindex(X-Robots-Tag / meta robots) 여부를 전수 검사한다.
(khealth_noindex_full_check.json과 동일한 사이트별 포맷: total/checked/noindex/errors)
"""
import os, re, time, json
import requests

WP_USER = "huh0303@gmail.com"
GOOGLEBOT_UA = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"

SITES = [
    ("https://k-health365.com", "KHEALTH365COM"),
    ("https://koreamedicaltour.com", "KOREAMEDICALTOURCOM"),
    ("https://koreainvest365.com", "KOREAINVEST365COM"),
    ("https://ki-korea.com", "KIKOREACOM"),
    ("https://koreainsurance365.com", "KOREAINSURANCE365COM"),
    ("https://kfinance365.com", "KFINANCE365COM"),
    ("https://koreataxnlaw.com", "KOREATAXNLAWCOM"),
    ("https://koreacrypto365.com", "KOREACRYPTO365COM"),
    ("https://krealestate365.com", "KREALESTATE365COM"),
    ("https://ktech365.com", "KTECH365COM"),
    ("https://oliveyoungkorea.com", "OLIVEYOUNGKOREACOM"),
    ("https://kworld365.com", "KWORLD365COM"),
    ("https://k-trip365.com", "KTRIP365COM"),
    ("https://k-visa365.com", "KVISA365COM"),
    ("https://koreawedding365.com", "KOREAWEDDING365COM"),
    ("https://kstudy365.com", "KSTUDY365COM"),
    ("https://studyinkorea365.com", "STUDYINKOREA365COM"),
    ("https://kieca-korea.org", "KIECAKOREAORG"),
    ("https://ksa-korea.org", "KSAKOREAORG"),
    ("https://sis-korea.com", "SISKOREACOM"),
    ("https://jobkorea365.com", "JOBKOREA365COM"),
    ("https://jobinkorea365.com", "JOBINKOREA365COM"),
    ("https://jobkoreaglobal.com", "JOBKOREAGLOBALCOM"),
    ("https://korea365.org", "KOREA365ORG"),
    ("https://koreanews365.com", "KOREANEWS365COM"),
    ("https://theseouljournal.com", "THESEOULJOURNALCOM"),
]


def fetch_all_posts(site_url, pw):
    posts = []
    page = 1
    while True:
        r = requests.get(
            f"{site_url}/wp-json/wp/v2/posts",
            auth=(WP_USER, pw),
            params={"per_page": 100, "page": page, "status": "publish",
                    "_fields": "id,link,title"},
            timeout=25,
        )
        if r.status_code != 200:
            break
        batch = r.json()
        if not isinstance(batch, list) or not batch:
            break
        posts.extend(batch)
        if len(batch) < 100:
            break
        page += 1
        time.sleep(0.2)
    return posts


def check_live_noindex(url):
    try:
        r = requests.get(url, headers={"User-Agent": GOOGLEBOT_UA}, timeout=15, allow_redirects=True)
        xr = r.headers.get("X-Robots-Tag", "")
        is_noindex = "noindex" in xr.lower()
        m = re.search(r'<meta[^>]+name=["\']robots["\'][^>]+content=["\']([^"\']+)["\']', r.text, re.IGNORECASE)
        meta_robots = m.group(1) if m else ""
        if "noindex" in meta_robots.lower():
            is_noindex = True
        return {"status": r.status_code, "is_noindex": is_noindex,
                "x_robots_tag": xr, "meta_robots": meta_robots, "error": None}
    except Exception as e:
        return {"status": None, "is_noindex": False, "x_robots_tag": "",
                "meta_robots": "", "error": str(e)[:150]}


def main():
    all_results = {}
    for site_url, env_key in SITES:
        pw = os.getenv(env_key, "")
        if not pw:
            print(f"⚠️  {site_url} — Secret 없음, 스킵")
            all_results[site_url] = {"total": 0, "checked": 0, "noindex": [], "errors": ["NO_SECRET"]}
            continue

        posts = fetch_all_posts(site_url, pw)
        total = len(posts)
        noindex_list = []
        error_list = []
        checked = 0

        for i, post in enumerate(posts):
            link = post.get("link", "")
            title = re.sub(r'<[^>]+>', '', post.get("title", {}).get("rendered", "")).strip()
            live = check_live_noindex(link)
            checked += 1
            if live["error"]:
                error_list.append({"id": post.get("id"), "title": title, "link": link, "error": live["error"]})
            else:
                if live["is_noindex"]:
                    noindex_list.append({
                        "id": post.get("id"), "title": title, "link": link,
                        "x_robots_tag": live["x_robots_tag"], "meta_robots": live["meta_robots"],
                    })
                if live["status"] and live["status"] != 200:
                    error_list.append({"id": post.get("id"), "title": title, "link": link,
                                        "error": f"HTTP {live['status']}"})
            if (i + 1) % 50 == 0:
                print(f"   ... {site_url} {i+1}/{total}건 확인 중")
            time.sleep(0.15)

        all_results[site_url] = {"total": total, "checked": checked,
                                  "noindex": noindex_list, "errors": error_list}
        print(f"✅ {site_url}: {checked}/{total}건 확인 완료 "
              f"(noindex={len(noindex_list)}, errors={len(error_list)})")

    with open("noindex_check_27sites_result.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("전체 요약")
    print("=" * 60)
    for site_url, r in all_results.items():
        print(f"{site_url}: total={r['total']} checked={r['checked']} "
              f"noindex={len(r['noindex'])} errors={len(r['errors'])}")


if __name__ == "__main__":
    main()
