#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bulk_fix_code_fences.py
27개 사이트 전체 발행글에서 코드펜스 찌꺼기(```html, "`html 등)만 제거.
콘텐츠 삭제는 하지 않음 — 순수 텍스트 정리(안전한 작업).
"""
import os, re, requests, json

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

def strip_code_fences(text):
    t = text.strip()
    t = re.sub(r'^```[a-zA-Z]*\s*\n?', '', t)
    t = re.sub(r'\n?```\s*$', '', t)
    t = "\n".join(l for l in t.split("\n") if l.strip() not in ("```", "```html", "```HTML"))
    quote_alt = r'(?:[\u201c\u2018"\']|&#8220;|&#8216;|&quot;|&ldquo;|&lsquo;)'
    t = re.sub(rf'<p>\s*{quote_alt}*\s*`{{1,3}}\s*(html)?\s*</p>\s*', '', t, flags=re.IGNORECASE)
    t = re.sub(rf'^{quote_alt}*\s*`{{1,3}}\s*(html)?\s*$', '', t, flags=re.IGNORECASE | re.MULTILINE)
    # 본문 중간에 낀 단독 펜스도 제거(문장 사이)
    t = re.sub(rf'{quote_alt}*\s*`{{2,3}}\s*(html)?(?=\s*<)', '', t, flags=re.IGNORECASE)
    return t.strip()

FENCE_DETECT = [r'```', r'&#8220;`', r'[\u201c\u2018]`']

def has_fence(html_str):
    return any(re.search(pat, html_str) for pat in FENCE_DETECT)

results = {"fixed": 0, "skipped_no_change": 0, "failed": 0, "by_site": {}}

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
                              params={"per_page": 100, "page": page, "status": "publish", "context": "edit",
                                      "_fields": "id,title,link,content"}, timeout=25)
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

    site_fixed = []
    for p in posts:
        raw = p["content"].get("raw") or p["content"]["rendered"]
        if not has_fence(raw):
            continue
        cleaned = strip_code_fences(raw)
        if cleaned.strip() == raw.strip():
            results["skipped_no_change"] += 1
            continue
        ur = requests.post(f"{site_url}/wp-json/wp/v2/posts/{p['id']}", auth=auth,
                            json={"content": cleaned}, timeout=30)
        title = re.sub(r'<[^>]+>', '', p["title"]["rendered"])
        if ur.status_code in (200, 201):
            results["fixed"] += 1
            site_fixed.append(title)
            print(f"  ✅ [{site_url}] {title[:50]}")
        else:
            results["failed"] += 1
            print(f"  ❌ [{site_url}] {title[:50]} — HTTP {ur.status_code}")

    if site_fixed:
        results["by_site"][site_url] = site_fixed
    print(f"=== {site_url}: {len(site_fixed)}건 수정 완료 ===")

print("\n" + "=" * 60)
print(json.dumps({k: v for k, v in results.items() if k != "by_site"}, ensure_ascii=False, indent=2))

with open("bulk_fix_code_fences_result.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
with open("bulk_fix_code_fences_result.txt", "w", encoding="utf-8") as f:
    f.write(f"수정완료: {results['fixed']}건\n실패: {results['failed']}건\n변화없음(재확인): {results['skipped_no_change']}건\n\n")
    for site, titles in results["by_site"].items():
        f.write(f"\n### {site} ({len(titles)}건)\n")
        for t in titles:
            f.write(f"  - {t}\n")
