#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_27sites_ai_tells.py
27개 사이트 전체 발행글을 대상으로 (삭제는 하지 않고) 아래 항목만 감사/리포트:
  1) 코드펜스 찌꺼기(```html 등) 잔존 글
  2) 본문이 지나치게 짧은(더미 의심) 글 — 500자 미만
  3) 제목에 진부한 AI 패턴(complete guide, 총정리, 연도(2024/2025) 등) 남은 글
  4) 같은 사이트 내 제목 앞 20자 중복 글
"""
import os, re, requests, html as _html, json

WP_USER = "huh0303@gmail.com"

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
    ("https://kskin365.com", "KSKIN365COM"),
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

CLICHE_PATTERNS = [
    r'complete guide to', r'ultimate guide', r'your complete guide',
    r'everything you need to know', r'a to z', r'a-to-z',
    r'총정리', r'완벽\s*가이드', r'모든\s*것을\s*알아',
    r'top \d+ (?:reasons|tips|ways|things)',
    r'\d+ essential (?:tips|insights|reasons|things)',
    r'the essential guide', r'your essential guide', r'\*\*',
]
YEAR_PATTERNS = [r'\b202[0-5]\b', r'202[0-5]년']
FENCE_PATTERNS = [r'```', r'&#8220;`', r'[\u201c\u2018]`']

MIN_CONTENT_LEN = 500

def strip_tags(html_str):
    return re.sub(r'<[^>]+>', '', html_str or '').strip()

results = {}
grand = {"fence": 0, "short": 0, "cliche_title": 0, "year_title": 0, "dup_title": 0, "total": 0}

for site_url, env_key in SITES:
    pw = os.getenv(env_key, "")
    if not pw:
        print(f"⚠️  {site_url} — Secret 없음, 스킵")
        continue

    auth = (WP_USER, pw)
    posts = []
    page = 1
    while True:
        try:
            r = requests.get(f"{site_url}/wp-json/wp/v2/posts", auth=auth,
                              params={"per_page": 100, "page": page, "status": "publish",
                                      "_fields": "id,title,link,date,content,slug"}, timeout=25)
        except Exception as e:
            print(f"⚠️  {site_url} 요청 실패: {e}")
            break
        if r.status_code != 200:
            break
        batch = r.json()
        if not isinstance(batch, list) or not batch:
            break
        posts.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    site_issues = {"fence": [], "short": [], "cliche_title": [], "year_title": [], "dup_title": []}
    title_seen = {}

    for p in posts:
        title = _html.unescape(strip_tags(p.get("title", {}).get("rendered", "")))
        content_html = p.get("content", {}).get("rendered", "")
        plain = strip_tags(content_html)
        clen = len(plain.replace(" ", "").replace("\n", ""))
        link = p.get("link", "")

        if any(re.search(pat, content_html) for pat in FENCE_PATTERNS):
            site_issues["fence"].append((title, link))
        if clen < MIN_CONTENT_LEN:
            site_issues["short"].append((title, link, clen))
        tl = title.lower()
        if any(re.search(pat, tl, re.IGNORECASE) for pat in CLICHE_PATTERNS):
            site_issues["cliche_title"].append((title, link))
        if any(re.search(pat, title, re.IGNORECASE) for pat in YEAR_PATTERNS):
            site_issues["year_title"].append((title, link))
        key = re.sub(r'\s+', '', title[:20].lower())
        if key in title_seen:
            site_issues["dup_title"].append((title, link))
        else:
            title_seen[key] = link

    grand["total"] += len(posts)
    for k in ("fence", "short", "cliche_title", "year_title", "dup_title"):
        grand[k] += len(site_issues[k])

    if any(site_issues.values()):
        results[site_url] = {"post_count": len(posts), "issues": site_issues}
    print(f"✅ {site_url}: {len(posts)}건 검사 완료 "
          f"(펜스={len(site_issues['fence'])}, 단문={len(site_issues['short'])}, "
          f"진부제목={len(site_issues['cliche_title'])}, 연도포함={len(site_issues['year_title'])}, "
          f"중복제목={len(site_issues['dup_title'])})")

print("\n" + "=" * 60)
print("전체 요약")
print("=" * 60)
print(json.dumps(grand, ensure_ascii=False, indent=2))

with open("audit_27sites_ai_tells_result.json", "w", encoding="utf-8") as f:
    json.dump({"summary": grand, "by_site": results}, f, ensure_ascii=False, indent=2)

# 사람이 읽기 쉬운 텍스트 요약도 별도 저장
with open("audit_27sites_ai_tells_result.txt", "w", encoding="utf-8") as f:
    f.write(f"전체 {grand['total']}건 검사\n")
    f.write(f"코드펜스 찌꺼기: {grand['fence']}건\n")
    f.write(f"단문(500자 미만): {grand['short']}건\n")
    f.write(f"진부한 제목 패턴: {grand['cliche_title']}건\n")
    f.write(f"제목에 연도(2020~2025) 포함: {grand['year_title']}건\n")
    f.write(f"중복 제목(앞 20자 기준): {grand['dup_title']}건\n\n")
    for site_url, data in results.items():
        f.write(f"\n### {site_url} (전체 {data['post_count']}건)\n")
        for cat, label in [("fence", "코드펜스"), ("short", "단문"),
                            ("cliche_title", "진부제목"), ("year_title", "연도포함"),
                            ("dup_title", "중복제목")]:
            items = data["issues"][cat]
            if items:
                f.write(f"  [{label}] {len(items)}건\n")
                for it in items[:15]:
                    f.write(f"    - {it}\n")
