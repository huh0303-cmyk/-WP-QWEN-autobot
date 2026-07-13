# -*- coding: utf-8 -*-
"""
27개 사이트(k-health365 포함) 전체에서 실제 rank_math 메타 기준 50점 미만 글을
휴지통으로 이동한다 (영구삭제 아님, WP 관리자에서 복구 가능).
"""
import os, sys, re, json, time, requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER, count_stats, TAG_COUNT

DELETE_THRESHOLD = 50


def real_score(title, body, meta, keyword, tag_count, faq_count):
    score = 0
    kl = (keyword or "").split(",")[0].strip().lower()
    tl = title.lower()
    plain = re.sub(r'<[^>]+>', '', body)
    blen = len(plain.replace(" ", "").replace("\n", ""))
    if kl and kl in tl: score += 10
    if 20 <= len(title) <= 65: score += 3
    if any(c.isdigit() for c in title): score += 2
    if blen >= 3000: score += 20
    elif blen >= 2500: score += 17
    elif blen >= 2000: score += 13
    elif blen >= 1800: score += 9
    elif blen >= 1000: score += 4
    ml = len(meta)
    if 130 <= ml <= 160: score += 10
    elif 100 <= ml < 130: score += 7
    elif 80 <= ml < 100: score += 4
    ic = len(re.findall(r'<img[\s>]', body, re.IGNORECASE))
    if ic >= 3: score += 10
    elif ic == 2: score += 7
    elif ic == 1: score += 4
    il = len(re.findall(r'<a\s+href=["\']https?://[^"\']+["\']', body, re.IGNORECASE))
    if il >= 4: score += 10
    elif il >= 3: score += 7
    elif il >= 2: score += 4
    elif il >= 1: score += 2
    sc = count_stats(body)
    if sc >= 5: score += 10
    elif sc >= 3: score += 8
    elif sc >= 1: score += 4
    cc = len(re.findall(r'\([^)]{3,40},\s*20[0-9]{2}\)', body))
    if cc >= 3: score += 5
    elif cc >= 1: score += 2
    h2 = len(re.findall(r'<h2[\s>]', body, re.IGNORECASE))
    h3 = len(re.findall(r'<h3[\s>]', body, re.IGNORECASE))
    ul = len(re.findall(r'<ul[\s>]', body, re.IGNORECASE))
    tb = len(re.findall(r'<table[\s>]', body, re.IGNORECASE))
    st = 0
    if h2 >= 4: st += 3
    elif h2 >= 2: st += 1
    if h3 >= 3: st += 2
    elif h3 >= 1: st += 1
    if ul >= 2: st += 2
    elif ul >= 1: st += 1
    if tb >= 1: st += 3
    score += min(st, 10)
    if faq_count >= 3: score += 5
    elif faq_count >= 1: score += 2
    if tag_count >= TAG_COUNT: score += 5
    elif tag_count >= 6: score += 2
    return min(score, 100)


def trash_site(site):
    url = site["url"]
    pw = os.getenv(site["wp_pass_env"], "")
    if not pw:
        return {"site": url, "error": "no_password"}

    total_before = 0
    trashed = []
    page = 1
    while True:
        r = None
        for attempt in range(3):
            try:
                r = requests.get(f"{url}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                                  params={"per_page": 20, "page": page, "status": "publish",
                                          "_fields": "id,title,content,tags,link,meta"}, timeout=40)
                break
            except Exception as e:
                if attempt == 2:
                    return {"site": url, "error": str(e), "total_before": total_before, "trashed": trashed}
                time.sleep(5)
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        for p in batch:
            total_before += 1
            title = p.get("title", {}).get("rendered", "")
            body = p.get("content", {}).get("rendered", "")
            meta_obj = p.get("meta", {}) or {}
            keyword = meta_obj.get("rank_math_focus_keyword", "")
            meta_desc = meta_obj.get("rank_math_description", "")
            tag_count = len(p.get("tags", []) or [])
            faq_count = body.count("schema.org/Question")
            sc = real_score(title, body, meta_desc, keyword, tag_count, faq_count)
            if sc < DELETE_THRESHOLD:
                try:
                    dr = requests.delete(f"{url}/wp-json/wp/v2/posts/{p['id']}", auth=(WP_USER, pw),
                                          params={"force": "false"}, timeout=20)
                    ok = dr.status_code in (200, 410)
                    trashed.append({"id": p["id"], "title": title[:50], "score": sc, "ok": ok})
                except Exception as e:
                    trashed.append({"id": p["id"], "title": title[:50], "score": sc, "ok": False, "error": str(e)})
                time.sleep(1.0)
        if len(batch) < 20:
            break
        page += 1
        time.sleep(0.4)

    ok_count = sum(1 for t in trashed if t.get("ok"))
    remaining = total_before - ok_count
    return {"site": url, "total_before": total_before, "trashed_count": ok_count,
            "remaining": remaining, "trashed": trashed}


if __name__ == "__main__":
    results = []
    for site in SITES_CONFIG:
        res = trash_site(site)
        results.append(res)
        print(f"{site['url']}: 발행전{res.get('total_before',0)} 휴지통이동{res.get('trashed_count',0)} 남음{res.get('remaining','?')}")
        with open("trash_result.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
