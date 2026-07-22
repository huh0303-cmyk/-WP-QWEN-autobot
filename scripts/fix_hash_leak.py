#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_hash_leak.py
load_keyword()가 keywords_*.txt의 '#카테고리명' 주석 줄을 실제 키워드로 오인해서
발행해버린 글들을 찾아서 고친다.

방식:
  - 각 사이트의 keywords_*.txt에서 '#'로 시작하는 주석 줄(진짜 카테고리명/플레이스홀더)을 읽는다.
  - 해당 사이트의 최근 발행글들의 title.raw / content.raw 안에서
    "# {comment}" 형태(주석 문구가 '#' 접두어를 단 채로 그대로 노출된 경우)를 찾는다.
  - 찾으면 "# {comment}" -> "{comment}" 로 전역 치환해서 제목/본문을 업데이트.
  - 같은 이름의 태그가 '#'를 포함해서 생성돼 있으면 태그 이름도 정리.
  - '추가' 같은 순수 플레이스홀더(실제 카테고리명이 아닌 것)는 REVIEW 대상으로만 표시하고
    본문 치환은 하되, 자동 삭제/재발행은 하지 않는다 (사람 검토 필요).
"""
import os, re, json, requests

SITES = [
    {"url":"https://k-health365.com","keywords_file":"data/keywords/keywords_khealth.txt","wp_pass_env":"KHEALTH365COM"},
    {"url":"https://koreamedicaltour.com","keywords_file":"data/keywords/keywords_medicaltour.txt","wp_pass_env":"KOREAMEDICALTOURCOM"},
    {"url":"https://koreainvest365.com","keywords_file":"data/keywords/keywords_kinvest.txt","wp_pass_env":"KOREAINVEST365COM"},
    {"url":"https://ki-korea.com","keywords_file":"data/keywords/keywords_kikorea.txt","wp_pass_env":"KIKOREACOM"},
    {"url":"https://koreainsurance365.com","keywords_file":"data/keywords/keywords_kinsurance.txt","wp_pass_env":"KOREAINSURANCE365COM"},
    {"url":"https://kfinance365.com","keywords_file":"data/keywords/keywords_kfinance.txt","wp_pass_env":"KFINANCE365COM"},
    {"url":"https://koreataxnlaw.com","keywords_file":"data/keywords/keywords_ktax.txt","wp_pass_env":"KOREATAXNLAWCOM"},
    {"url":"https://koreacrypto365.com","keywords_file":"data/keywords/keywords_kcrypto.txt","wp_pass_env":"KOREACRYPTO365COM"},
    {"url":"https://krealestate365.com","keywords_file":"data/keywords/keywords_krealestate.txt","wp_pass_env":"KREALESTATE365COM"},
    {"url":"https://ktech365.com","keywords_file":"data/keywords/keywords_ktech.txt","wp_pass_env":"KTECH365COM"},
    {"url":"https://kskin365.com","keywords_file":"data/keywords/keywords_kskin.txt","wp_pass_env":"KSKIN365COM"},
    {"url":"https://oliveyoungkorea.com","keywords_file":"data/keywords/keywords_oliveyoung.txt","wp_pass_env":"OLIVEYOUNGKOREACOM"},
    {"url":"https://kworld365.com","keywords_file":"data/keywords/keywords_kworld.txt","wp_pass_env":"KWORLD365COM"},
    {"url":"https://k-trip365.com","keywords_file":"data/keywords/keywords_ktrip.txt","wp_pass_env":"KTRIP365COM"},
    {"url":"https://k-visa365.com","keywords_file":"data/keywords/keywords_kvisa.txt","wp_pass_env":"KVISA365COM"},
    {"url":"https://koreawedding365.com","keywords_file":"data/keywords/keywords_kwedding.txt","wp_pass_env":"KOREAWEDDING365COM"},
    {"url":"https://kstudy365.com","keywords_file":"data/keywords/keywords_kstudy365.txt","wp_pass_env":"KSTUDY365COM"},
    {"url":"https://studyinkorea365.com","keywords_file":"data/keywords/keywords_studyinkorea365.txt","wp_pass_env":"STUDYINKOREA365COM"},
    {"url":"https://kieca-korea.org","keywords_file":"data/keywords/keywords_kieca.txt","wp_pass_env":"KIECAKOREAORG"},
    {"url":"https://ksa-korea.org","keywords_file":"data/keywords/keywords_ksaKorea.txt","wp_pass_env":"KSAKOREAORG"},
    {"url":"https://sis-korea.com","keywords_file":"data/keywords/keywords_sisKorea.txt","wp_pass_env":"SISKOREACOM"},
    {"url":"https://jobkorea365.com","keywords_file":"data/keywords/keywords_jobkorea365.txt","wp_pass_env":"JOBKOREA365COM"},
    {"url":"https://jobinkorea365.com","keywords_file":"data/keywords/keywords_jobinkorea365.txt","wp_pass_env":"JOBINKOREA365COM"},
    {"url":"https://jobkoreaglobal.com","keywords_file":"data/keywords/keywords_jobkoreaglobal.txt","wp_pass_env":"JOBKOREAGLOBALCOM"},
    {"url":"https://korea365.org","keywords_file":"data/keywords/keywords_korea365.txt","wp_pass_env":"KOREA365ORG"},
    {"url":"https://koreanews365.com","keywords_file":"data/keywords/keywords_koreanews.txt","wp_pass_env":"KOREANEWS365COM"},
    {"url":"https://theseouljournal.com","keywords_file":"data/keywords/keywords_seouljournal.txt","wp_pass_env":"THESEOULJOURNALCOM"},
]

WP_USER = "huh0303@gmail.com"
PLACEHOLDER_WORDS = {"추가", "add", "tbd", "todo"}

_LOG = []
def log(m=""):
    print(m)
    _LOG.append(str(m))

def load_comments(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [l.strip()[1:].strip() for l in f if l.strip().startswith("#")]

def fetch_all_posts(site_url, auth, max_pages=10):
    posts = []
    page = 1
    while page <= max_pages:
        try:
            r = requests.get(f"{site_url}/wp-json/wp/v2/posts", auth=auth,
                              params={"per_page": 50, "page": page, "status": "publish",
                                      "context": "edit",
                                      "_fields": "id,title,link,slug,content,tags"}, timeout=25)
        except Exception as e:
            log(f"  ⚠️ 목록 조회 오류: {e}")
            break
        if r.status_code != 200:
            break
        batch = r.json()
        if not isinstance(batch, list) or not batch:
            break
        posts.extend(batch)
        if len(batch) < 50:
            break
        page += 1
    return posts

def fix_tag(site_url, auth, leaked_comment):
    """'# 카테고리명' 형태로 생성된 태그가 있으면 이름 정리"""
    try:
        r = requests.get(f"{site_url}/wp-json/wp/v2/tags", auth=auth,
                          params={"search": leaked_comment, "per_page": 20}, timeout=15)
        if r.status_code != 200:
            return
        for t in r.json():
            name = t.get("name", "")
            if name.strip().startswith("#"):
                clean = name.lstrip("#").strip()
                requests.post(f"{site_url}/wp-json/wp/v2/tags/{t['id']}", auth=auth,
                              json={"name": clean}, timeout=15)
                log(f"    🏷️ 태그 정리: '{name}' -> '{clean}'")
    except Exception as e:
        log(f"    ⚠️ 태그 정리 오류: {e}")

def process_site(site):
    site_url = site["url"]
    pass_env = site["wp_pass_env"]
    wp_pass = os.environ.get(pass_env)
    if not wp_pass:
        log(f"⏭️  {site_url}: 비밀번호 환경변수 {pass_env} 없음, 건너뜀")
        return {"site": site_url, "fixed": 0, "reviewed": 0}

    auth = requests.auth.HTTPBasicAuth(WP_USER, wp_pass)
    comments = load_comments(site["keywords_file"])
    if not comments:
        log(f"⏭️  {site_url}: 주석 키워드 없음")
        return {"site": site_url, "fixed": 0, "reviewed": 0}

    log(f"\n=== {site_url} (주석 {len(comments)}개: {comments}) ===")
    posts = fetch_all_posts(site_url, auth)
    log(f"  발행글 {len(posts)}건 로드")

    fixed = 0
    reviewed = 0

    for p in posts:
        title_raw = p["title"].get("raw") or p["title"].get("rendered", "")
        content_raw = p["content"].get("raw") or p["content"].get("rendered", "")

        matched_comment = None
        for c in comments:
            if not c:
                continue
            needle_variants = [f"# {c}", f"#{c}"]
            if any(v in title_raw for v in needle_variants) or any(v in content_raw for v in needle_variants):
                matched_comment = c
                break

        if not matched_comment:
            continue

        is_placeholder = matched_comment.strip().lower() in PLACEHOLDER_WORDS

        new_title = title_raw
        new_content = content_raw
        for v in [f"# {matched_comment}", f"#{matched_comment}"]:
            new_title = new_title.replace(v, matched_comment)
            new_content = new_content.replace(v, matched_comment)

        if new_title == title_raw and new_content == content_raw:
            continue

        payload = {}
        if new_title != title_raw:
            payload["title"] = new_title
        if new_content != content_raw:
            payload["content"] = new_content

        try:
            r = requests.post(f"{site_url}/wp-json/wp/v2/posts/{p['id']}", auth=auth,
                               json=payload, timeout=30)
            ok = r.status_code in (200, 201)
        except Exception as e:
            ok = False
            log(f"  ❌ 업데이트 오류: {e}")

        tag_str = ", ".join(f"'{c}'" for c in [matched_comment])
        if ok:
            fix_tag(site_url, auth, matched_comment)
            if is_placeholder:
                reviewed += 1
                log(f"  🟡 REVIEW(플레이스홀더 '{matched_comment}'): {p['link']}")
            else:
                fixed += 1
                log(f"  ✅ 수정완료 ({tag_str}): {p['link']}")
        else:
            log(f"  ❌ 수정 실패: {p['link']} (status={r.status_code if 'r' in dir() else '?'})")

    return {"site": site_url, "fixed": fixed, "reviewed": reviewed}

def main():
    summary = []
    for site in SITES:
        summary.append(process_site(site))

    log("\n\n========== 최종 요약 ==========")
    total_fixed = sum(s["fixed"] for s in summary)
    total_review = sum(s["reviewed"] for s in summary)
    for s in summary:
        if s["fixed"] or s["reviewed"]:
            log(f"  {s['site']}: 수정 {s['fixed']}건, 검토필요 {s['reviewed']}건")
    log(f"\n총 수정: {total_fixed}건 / 검토필요(플레이스홀더): {total_review}건")

    with open("fix_hash_leak_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(_LOG))
    with open("fix_hash_leak_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
