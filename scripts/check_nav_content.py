import os, sys, re, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

REQUIRED = ["about", "contact", "disclaimer", "privacy-policy"]
MIN_LEN = 600


def check_site(site):
    site_url = site["url"]
    pw = os.getenv(site["wp_pass_env"], "")
    if not pw:
        return {"site": site_url, "error": "no_password"}

    result = {"site": site_url}

    try:
        r = requests.get(site_url, timeout=25)
        home_html = r.text.lower() if r.status_code == 200 else ""
        result["home_fetch_status"] = r.status_code
    except Exception as e:
        home_html = ""
        result["home_fetch_error"] = str(e)

    nav_check = {}
    for slug in REQUIRED:
        pattern = f'/{slug}/'
        nav_check[slug] = pattern in home_html
    result["nav_visible"] = nav_check

    try:
        rc = requests.get(f"{site_url}/wp-json/wp/v2/categories", auth=(WP_USER, pw),
                           params={"per_page": 100}, timeout=20)
        cats = rc.json() if rc.status_code == 200 else []
        result["categories"] = [{"name": c["name"], "count": c["count"]} for c in cats]
        result["has_etc_catchall"] = any(c["name"].strip().lower() in ("etc", "기타") for c in cats)
    except Exception as e:
        result["categories_error"] = str(e)

    try:
        rp = requests.get(f"{site_url}/wp-json/wp/v2/pages", auth=(WP_USER, pw),
                           params={"per_page": 50, "_fields": "id,title,content,slug"}, timeout=25)
        pages = rp.json() if rp.status_code == 200 else []
    except Exception as e:
        pages = []
        result["pages_error"] = str(e)

    page_status = {}
    for slug in REQUIRED:
        matches = [p for p in pages if p.get("slug", "").rstrip("/") == slug or
                   slug.replace("-", " ") in p["title"]["rendered"].strip().lower()]
        if not matches:
            page_status[slug] = "없음"
            continue
        content = matches[0].get("content", {}).get("rendered", "")
        plain = re.sub(r'<[^>]+>', ' ', content); plain = re.sub(r'\s+', ' ', plain).strip()
        issues = []
        if len(plain) < MIN_LEN: issues.append(f"짧음({len(plain)}자)")
        if "lorem ipsum" in content.lower(): issues.append("LOREM")
        if "huh0303@gmail.com" not in content: issues.append("이메일없음")
        page_status[slug] = "정상" if not issues else ",".join(issues)
    result["page_content_status"] = page_status

    return result


if __name__ == "__main__":
    results = [check_site(s) for s in SITES_CONFIG]
    with open("nav_content_check.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    for r in results:
        if "error" in r:
            print(r["site"], "ERROR:", r["error"]); continue
        nav = r.get("nav_visible", {})
        nav_missing = [k for k, v in nav.items() if not v]
        content_issues = [f"{k}:{v}" for k, v in r.get("page_content_status", {}).items() if v != "정상"]
        etc = "Etc있음" if r.get("has_etc_catchall") else "⚠️Etc없음"
        print(f"{r['site']:32s} 메뉴누락:{nav_missing or '없음'} 내용문제:{content_issues or '없음'} {etc}")
