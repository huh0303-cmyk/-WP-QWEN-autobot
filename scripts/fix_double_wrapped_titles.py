import os, sys, re, json, time, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER, build_diverse_title, pick_best_category

CLICHE_TITLE_PATTERNS = [
    r'\bunlocking\b', r'\bunlock your\b', r'\bunveiling\b', r'\bdiscover the\b',
    r'\bthe ultimate guide\b', r'\bdive into\b', r'\beverything you need to know\b',
    r'\bmaster the art\b', r'\belevate your\b',
]

# 알려진 44개 템플릿 조각 + 옛 클리셰 문구 (제목에서 제거해 핵심 키워드만 추출)
STRIP_PHRASES = [
    r'why does\s+', r'cause problems\?\s*experts explain', r'\d+ mistakes people make with\s+',
    r'unlocking (the (power|secret) of\s+)?', r'unlock your\s+', r'unveiling the secret:?\s*',
    r'top \d+ secrets to\s+', r'secrets to\s+', r'discover the\s+', r'the ultimate guide (to|for)?\s*',
    r'dive into\s+', r'everything you need to know( about)?\s*', r'master the art of\s+',
    r'elevate your\s+', r'warning signs you should never ignore', r'explained in plain english',
    r'with (top \d+ secrets|our complete manual|our complete guide)', r'your ultimate.*?guide( to)?\s*',
    r'\byour glow\b', r'\bwith\b\s*$',
]


def clean_keyword_from_title(title):
    t = re.sub(r'&#8217;', "'", title)
    for pat in STRIP_PHRASES:
        t = re.sub(pat, ' ', t, flags=re.IGNORECASE)
    t = re.sub(r'[?:!]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    # 남은 것 중 가장 긴 유의미한 조각 사용
    if len(t) > 60:
        t = t[:60].rsplit(' ', 1)[0]
    return t


def fix_site(site):
    site_url = site["url"]
    pw = os.getenv(site["wp_pass_env"], "")
    if not pw:
        return {"site": site_url, "error": "no_password"}

    lang = site.get("lang", "en")
    posts, page = [], 1
    while True:
        try:
            r = requests.get(f"{site_url}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                              params={"per_page": 50, "page": page, "status": "publish",
                                      "_fields": "id,title,meta"}, timeout=35)
        except Exception as e:
            return {"site": site_url, "error": str(e)}
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < 50:
            break
        page += 1

    fixed = []
    for p in posts:
        title = p["title"]["rendered"]
        if not any(re.search(pat, title, re.IGNORECASE) for pat in CLICHE_TITLE_PATTERNS):
            continue

        pid = p["id"]
        meta_obj = p.get("meta", {}) or {}
        real_kw = meta_obj.get("rank_math_focus_keyword", "")
        kw = real_kw.split(",")[0].strip() if real_kw else ""
        if not kw or len(kw) < 4:
            kw = clean_keyword_from_title(title)
        if not kw or len(kw) < 4:
            kw = title  # 최후수단

        new_title = build_diverse_title(kw, lang, site_url=site_url)
        new_cat = pick_best_category(site_url, pw, kw, title)
        try:
            pr = requests.patch(f"{site_url}/wp-json/wp/v2/posts/{pid}", auth=(WP_USER, pw),
                                 json={"title": new_title, "categories": [new_cat]}, timeout=25)
            fixed.append({"id": pid, "old": title[:60], "keyword_used": kw, "new": new_title, "status": pr.status_code})
        except Exception as e:
            fixed.append({"id": pid, "old": title[:60], "error": str(e)})
        time.sleep(0.7)

    return {"site": site_url, "fixed_count": len(fixed), "fixed": fixed}


if __name__ == "__main__":
    results = []
    for site in SITES_CONFIG:
        res = fix_site(site)
        results.append(res)
        print(f"{res['site']}: 수정{res.get('fixed_count',0)} / 오류{res.get('error','')}")
        with open("fix_double_wrapped_result.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
