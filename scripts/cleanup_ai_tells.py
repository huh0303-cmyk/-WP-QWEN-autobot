# -*- coding: utf-8 -*-
import os, sys, re, json, time, random, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER, build_diverse_title, pick_best_category

BROKEN_TITLE_RE = re.compile(r'(\bin\s*\?$|\bfor\s*\?$|\bin$|\bfor\s*and\s*beyond$|^\s*◇|^sure,|^certainly!)',
                              re.IGNORECASE)

# ★ 2026-07-28: audit_27sites_ai_tells.py가 찾아낸 3개 카테고리(진부제목/연도포함/
#   중복제목)를 이 스크립트도 그대로 잡아서 고치도록 확장. 감사 스크립트와 패턴을
#   동일하게 유지해야 "감사에서 몇 건 → 정리 후 0건"이 정확히 맞아떨어진다.
CLICHE_TITLE_PATTERNS = [
    r'complete guide to', r'ultimate guide', r'your complete guide',
    r'everything you need to know', r'a to z', r'a-to-z',
    r'총정리', r'완벽\s*가이드', r'모든\s*것을\s*알아',
    r'top \d+ (?:reasons|tips|ways|things)',
    r'\d+ essential (?:tips|insights|reasons|things)',
    r'the essential guide', r'your essential guide', r'\*\*',
]
YEAR_TITLE_PATTERNS = [r'\b202[0-5]\b', r'202[0-5]년']

# (검색패턴, 치환문자열) - 문장 자체를 자연스럽게 다듬음
CLEANUP_RULES = [
    (re.compile(r'<p>\s*◇\s*By\s+[A-Za-z\s]+</p>', re.IGNORECASE), ''),
    (re.compile(r'◇\s*By\s+[A-Za-z\s]+', re.IGNORECASE), ''),
    (re.compile(r'\bNavigating the (complex|dynamic)\s+', re.IGNORECASE), 'Understanding the '),
    (re.compile(r'\bin conclusion,\s*', re.IGNORECASE), ''),
    (re.compile(r'현대\s*사회에서\s*', re.IGNORECASE), ''),
    (re.compile(r'\bin the ever-evolving\s+', re.IGNORECASE), 'in the changing '),
    # 2026-08-19: 루테인 글(젬스→복붙, 파이프라인 미경유) 검토에서 발견 —
    # 내부링크로 치환됐어야 할 대괄호 자리표시자가 그대로 발행된 사례.
    # 자동화 파이프라인은 SITE_INTERNAL_LINKS의 실제 URL을 바로 삽입하므로
    # 원래 이런 게 안 생기지만, 사람이 다른 경로로 올린 글까지 이 스크립트가
    # 훑으므로 안전망으로 추가. 실제 링크로 무엇을 넣을지는 모르므로 통째로
    # 제거만 한다(임의 URL을 지어내 채워 넣지 않음).
    (re.compile(r'\[내부링크[^\]]*\]\s*', re.IGNORECASE), ''),
    (re.compile(r'\[TODO[^\]]*\]\s*', re.IGNORECASE), ''),
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

    # ★ 2026-07-28: audit_27sites_ai_tells.py와 동일한 방식(제목 앞 20자, 공백제거,
    #   소문자 정규화)으로 같은 사이트 내 중복 제목을 먼저 한 번에 찾아둔다.
    #   API 기본 정렬(date desc)이 감사 스크립트와 동일하므로 "가장 최근 글이
    #   원제목 유지, 그 이전 중복글들만 재작성" 기준도 감사 결과와 정확히 일치한다.
    title_prefix_seen = set()
    dup_ids = set()
    for p in posts:
        t = p["title"]["rendered"]
        key = re.sub(r'\s+', '', t[:20].lower())
        if key in title_prefix_seen:
            dup_ids.add(p["id"])
        else:
            title_prefix_seen.add(key)

    for p in posts:
        pid = p["id"]
        title = p["title"]["rendered"]
        content = p.get("content", {}).get("rendered", "")
        meta_obj = p.get("meta", {}) or {}

        payload = {}
        tl = title.strip().lower()
        title_broken = bool(BROKEN_TITLE_RE.search(title.strip()))
        title_cliche = any(re.search(pat, tl, re.IGNORECASE) for pat in CLICHE_TITLE_PATTERNS)
        title_year   = any(re.search(pat, title, re.IGNORECASE) for pat in YEAR_TITLE_PATTERNS)
        title_dup    = pid in dup_ids
        needs_retitle = title_broken or title_cliche or title_year or title_dup
        if needs_retitle:
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
            if needs_retitle:
                reasons = [r for r, flag in [("broken", title_broken), ("cliche", title_cliche),
                                              ("year", title_year), ("dup", title_dup)] if flag]
                entry["reason"] = ",".join(reasons)
                entry["new_title"] = payload.get("title", "")[:60]
                log["title_fixed"].append(entry)
            if content_changed:
                log["content_cleaned"].append({"id": pid, "link": p.get("link", "")})
            continue

        try:
            pr = requests.patch(f"{site_url}/wp-json/wp/v2/posts/{pid}", auth=(WP_USER, pw),
                                 json=payload, timeout=25)
            entry = {"id": pid, "old_title": title[:40], "status": pr.status_code}
            if needs_retitle:
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
    ap.add_argument("--exclude", default="",
                    help="쉼표로 구분된 제외할 사이트 URL 목록 (예: 이미 애드센스 승인된 사이트는 안 건드리고 싶을 때)")
    ap.add_argument("--dry-run", action="store_true",
                    help="실제 PATCH 없이 무엇이 바뀔지만 리포트 (사이트 수정 없음)")
    args = ap.parse_args()

    exclude_set = {u.strip().rstrip("/") for u in args.exclude.split(",") if u.strip()}
    targets = [s for s in SITES_CONFIG
               if (not args.site or s["url"] == args.site)
               and s["url"].rstrip("/") not in exclude_set]
    if exclude_set:
        print(f"⏭  제외: {', '.join(exclude_set)}")
    results = []
    out_file = "cleanup_ai_tells_dryrun.json" if args.dry_run else "cleanup_ai_tells_result.json"
    for site in targets:
        res = fix_site(site, dry_run=args.dry_run)
        results.append(res)
        tag = "[DRY-RUN] " if args.dry_run else ""
        print(f"{tag}{res['site']}: 제목수정{len(res.get('title_fixed',[]))} / 본문정리{len(res.get('content_cleaned',[]))} / 실패{len(res.get('failed',[]))} / 오류{res.get('error','')}")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
