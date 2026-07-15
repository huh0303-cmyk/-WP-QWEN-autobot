import os, sys, re, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

REQUIRED = ["about", "contact", "disclaimer", "privacy-policy"]
BROKEN_TITLE_RE = re.compile(r'(\bin\s*\?$|\bfor\s*\?$|\bin$|\bfor\s*and\s*beyond$|^\s*◇|^sure,|^certainly!)',
                              re.IGNORECASE)


def check_site(site):
    site_url = site["url"]
    pw = os.getenv(site["wp_pass_env"], "")
    if not pw:
        return {"site": site_url, "error": "no_password"}

    result = {"site": site_url, "issues": []}

    try:
        r = requests.get(site_url, timeout=25)
        home_html = r.text.lower() if r.status_code == 200 else ""
        if r.status_code != 200:
            result["issues"].append(f"홈페이지 응답이상({r.status_code})")
    except Exception as e:
        result["issues"].append(f"홈페이지접속실패:{str(e)[:60]}")
        home_html = ""
    nav_missing = [s for s in REQUIRED if f'/{s}/' not in home_html]
    if nav_missing:
        result["issues"].append(f"메뉴누락:{nav_missing}")

    try:
        ra = requests.get(f"{site_url}/ads.txt", timeout=15)
        if ra.status_code != 200 or "pub-3456727916386941" not in ra.text:
            result["issues"].append("ads.txt이상")
    except Exception:
        result["issues"].append("ads.txt접속실패")
    try:
        rr = requests.get(f"{site_url}/robots.txt", timeout=15)
        if rr.status_code != 200:
            result["issues"].append("robots.txt이상")
    except Exception:
        result["issues"].append("robots.txt접속실패")

    try:
        rp = requests.get(f"{site_url}/wp-json/wp/v2/pages", auth=(WP_USER, pw),
                           params={"per_page": 50, "_fields": "id,title,content,slug"}, timeout=25)
        pages = rp.json() if rp.status_code == 200 else []
    except Exception:
        pages = []
    from collections import Counter
    tc = Counter(p["title"]["rendered"].strip().lower() for p in pages)
    dup = {k: v for k, v in tc.items() if v > 1}
    if dup:
        result["issues"].append(f"중복페이지:{dup}")

    for slug in REQUIRED:
        matches = [p for p in pages if p.get("slug", "").rstrip("/") == slug or
                   slug.replace("-", " ") in p["title"]["rendered"].strip().lower()]
        if not matches:
            result["issues"].append(f"{slug}페이지없음")
            continue
        content = matches[0].get("content", {}).get("rendered", "")
        plain = re.sub(r'<[^>]+>', ' ', content); plain = re.sub(r'\s+', ' ', plain).strip()
        if len(plain) < 400:
            result["issues"].append(f"{slug}너무짧음({len(plain)}자)")
        if "lorem ipsum" in content.lower():
            result["issues"].append(f"{slug}LOREM있음")

    try:
        rpo = requests.get(f"{site_url}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                            params={"per_page": 30, "status": "publish",
                                    "orderby": "date", "order": "desc",
                                    "_fields": "id,title,content"}, timeout=30)
        posts = rpo.json() if rpo.status_code == 200 else []
    except Exception:
        posts = []

    broken = []
    zero_img = 0
    for p in posts:
        title = p["title"]["rendered"].strip()
        if BROKEN_TITLE_RE.search(title):
            broken.append(title[:50])
        content = p.get("content", {}).get("rendered", "")
        if len(re.findall(r'<img[\s>]', content, re.IGNORECASE)) == 0:
            zero_img += 1
    if broken:
        result["issues"].append(f"최근글깨진제목:{broken}")
    if zero_img:
        result["issues"].append(f"최근글이미지없음:{zero_img}개")

    result["ok"] = len(result["issues"]) == 0
    return result


if __name__ == "__main__":
    results = [check_site(s) for s in SITES_CONFIG]
    with open("final_full_audit.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    ok_count = 0
    for r in results:
        if r.get("ok"):
            ok_count += 1
            print(f"✅ {r['site']}")
        else:
            print(f"⚠️ {r['site']}: {r.get('issues', r.get('error',''))}")
    print(f"\n{ok_count}/{len(results)} 완전 정상")
