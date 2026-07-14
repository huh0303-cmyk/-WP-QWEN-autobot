# -*- coding: utf-8 -*-
import os, sys, re, json, time, random, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER, build_diverse_title, pick_best_category

BROKEN_TITLE_RE = re.compile(r'(\bin\s*\?$|\bfor\s*\?$|\bin$|\bfor\s*and\s*beyond$|^\s*◇|^sure,|^certainly!)',
                              re.IGNORECASE)

# (검색패턴, 치환문자열) - 문장 자체를 자연스럽게 다듬음
CLEANUP_RULES = [
    (re.compile(r'<p>\s*◇\s*By\s+[A-Za-z\s]+</p>', re.IGNORECASE), ''),
    (re.compile(r'◇\s*By\s+[A-Za-z\s]+', re.IGNORECASE), ''),
    (re.compile(r'\bNavigating the (complex|dynamic)\s+', re.IGNORECASE), 'Understanding the '),
    (re.compile(r'\bin conclusion,\s*', re.IGNORECASE), ''),
    (re.compile(r'현대\s*사회에서\s*', re.IGNORECASE), ''),
    (re.compile(r'\bin the ever-evolving\s+', re.IGNORECASE), 'in the changing '),
]


def clean_content(html):
    for pat, repl in CLEANUP_RULES:
        html = pat.sub(repl, html)
    # 문장 시작 대문자 정리 (치환으로 소문자 시작된 경우 보정은 스킵 - 리스크 최소화)
    return html


def fix_site(site):
    site_url = site["url"]
    pw = os.getenv(site["wp_pass_env"], "")
    if not pw:
        return {"site": site_url, "error": "no_password"}

    lang = site.get("lang", "en")
    log = {"site": site_url, "title_fixed": [], "content_cleaned": [], "failed": []}

    posts, page = [], 1
    while True:
        try:
            r = requests.get(f"{site_url}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                              params={"per_page": 50, "page": page, "status": "publish",
                                      "_fields": "id,title,content,meta"}, timeout=35)
        except Exception as e:
            log["error"] = str(e)
            return log
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < 50:
            break
        page += 1

    for p in posts:
        pid = p["id"]
        title = p["title"]["rendered"]
        content = p.get("content", {}).get("rendered", "")
        meta_obj = p.get("meta", {}) or {}

        payload = {}
        title_broken = bool(BROKEN_TITLE_RE.search(title.strip()))
        if title_broken:
            keyword = meta_obj.get("rank_math_focus_keyword", "") or title
            kw = keyword.split(",")[0].strip()
            if len(kw) < 4 or re.match(r'^[◇\s]*By\s', kw, re.IGNORECASE):
                plain = re.sub(r'<[^>]+>', ' ', content)
                kw = re.sub(r'\s+', ' ', plain).strip()[:40] or title
            new_title = build_diverse_title(kw, lang, site_url=site_url)
            payload["title"] = new_title

        new_content = clean_content(content)
        content_changed = new_content != content
        if content_changed:
            payload["content"] = new_content

        if not payload:
            continue

        try:
            pr = requests.patch(f"{site_url}/wp-json/wp/v2/posts/{pid}", auth=(WP_USER, pw),
                                 json=payload, timeout=25)
            entry = {"id": pid, "old_title": title[:40], "status": pr.status_code}
            if title_broken:
                entry["new_title"] = payload.get("title", "")[:40]
                log["title_fixed"].append(entry)
            if content_changed:
                log["content_cleaned"].append({"id": pid, "status": pr.status_code})
        except Exception as e:
            log["failed"].append({"id": pid, "error": str(e)})

        time.sleep(random.uniform(0.6, 1.2))

    return log


if __name__ == "__main__":
    results = []
    for site in SITES_CONFIG:
        res = fix_site(site)
        results.append(res)
        print(f"{res['site']}: 제목수정{len(res.get('title_fixed',[]))} / 본문정리{len(res.get('content_cleaned',[]))} / 실패{len(res.get('failed',[]))} / 오류{res.get('error','')}")
        with open("cleanup_ai_tells_result.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
