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

# 마크다운 코드펜스 잔존물 제거 — audit_27sites_ai_tells.py의 FENCE_PATTERNS와 짝을 이루는 규칙.
# 펜스 마커만 벗겨내고 안의 실제 본문은 그대로 남긴다 (콘텐츠 삭제 아님, 래핑만 제거).
FENCE_CLEANUP_RULES = [
    (re.compile(r'<p>\s*```[a-zA-Z]*\s*</p>', re.IGNORECASE), ''),   # <p>```html</p> 형태
    (re.compile(r'```[a-zA-Z]*\n?', re.IGNORECASE), ''),              # 오프닝 펜스 (```html, ```markdown 등)
    (re.compile(r'```'), ''),                                          # 잔여 백틱 3연속 (클로징 펜스 포함)
    (re.compile(r'[“‘]`'), ''),                              # 스마트따옴표+백틱 조합 잔재
    (re.compile(r'&#8220;`'), ''),                                     # 엔티티화된 스마트따옴표+백틱 잔재
]


def clean_content(html):
    for pat, repl in CLEANUP_RULES:
        html = pat.sub(repl, html)
    for pat, repl in FENCE_CLEANUP_RULES:
        html = pat.sub(repl, html)
    # 문장 시작 대문자 정리 (치환으로 소문자 시작된 경우 보정은 스킵 - 리스크 최소화)
    return html


def fix_site(site, dry_run=False):
    site_url = site["url"]
    pw = os.getenv(site["wp_pass_env"], "")
    if not pw:
        return {"site": site_url, "error": "no_password"}

    lang = site.get("lang", "en")
    log = {"site": site_url, "title_fixed": [], "content_cleaned": [], "failed": [], "dry_run": dry_run}

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

        if dry_run:
            entry = {"id": pid, "link": p.get("link", ""), "old_title": title[:60]}
            if title_broken:
                entry["new_title"] = payload.get("title", "")[:60]
                log["title_fixed"].append(entry)
            if content_changed:
                log["content_cleaned"].append({"id": pid, "link": p.get("link", "")})
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
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="")
    ap.add_argument("--dry-run", action="store_true",
                    help="실제 PATCH 없이 무엇이 바뀔지만 리포트 (사이트 수정 없음)")
    args = ap.parse_args()

    targets = [s for s in SITES_CONFIG if (not args.site or s["url"] == args.site)]
    results = []
    out_file = "cleanup_ai_tells_dryrun.json" if args.dry_run else "cleanup_ai_tells_result.json"
    for site in targets:
        res = fix_site(site, dry_run=args.dry_run)
        results.append(res)
        tag = "[DRY-RUN] " if args.dry_run else ""
        print(f"{tag}{res['site']}: 제목수정{len(res.get('title_fixed',[]))} / 본문정리{len(res.get('content_cleaned',[]))} / 실패{len(res.get('failed',[]))} / 오류{res.get('error','')}")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
