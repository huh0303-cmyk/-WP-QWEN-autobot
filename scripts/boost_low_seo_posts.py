# -*- coding: utf-8 -*-
"""
26개 사이트(k-health365 제외 여부는 TARGET_SITES로 제어) 전체를 스캔해서
0~49점짜리 글에 부족한 요소(통계/출처인용/FAQ/표/메타디스크립션)를
AI로 보강 생성해 기존 본문 끝(관련글 블록 앞)에 삽입한다.
- 기존 본문·제목·URL은 절대 건드리지 않음 (색인 이력 보존)
- 보강 콘텐츠만 추가(append), 실패해도 원본 그대로 유지
"""
import os, sys, re, json, time, random, requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import (
    SITES_CONFIG, WP_USER, count_stats, TAG_COUNT, generate_content_gemini,
    get_multiple_images, build_img_html, get_authority_links
)

LOW_THRESHOLD = 50  # 이 점수 미만인 글만 보강 대상


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


def build_supplement_prompt(keyword, title, lang):
    if lang == "ko":
        return f"""이미 발행된 블로그 글 "{title}" (주제: {keyword})에 추가로 삽입할
보충 콘텐츠를 작성하라. HTML만 사용, 마크다운 금지.

요구사항:
0. 심층 분석 단락 3~4개 추가 작성 (배경/원인/실제 사례/전문가 조언 등, 총 1500자 이상)
1. 실제 통계 수치 5개 이상 (%, 만 명, 원 등 구체적 숫자)
2. 출처 인용 3회 이상: "(기관명, 2026)" 형식 (연도는 반드시 2026만, 과거연도 절대 금지)
3. <table> 1개 이상 (관련 비교/데이터 표, thead/tbody 완전 구조)
4. FAQ 3개 이상, 각각 정확히 이 형식:
   <div itemscope itemprop="mainEntity" itemtype="https://schema.org/Question"><h3 itemprop="name">질문</h3><div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer"><p itemprop="text">답변</p></div></div>
   전체를 <div itemscope itemtype="https://schema.org/FAQPage"><h2>자주 묻는 질문 (FAQ)</h2>...</div>로 감쌀 것
5. <h2>, <h3> 소제목으로 구조화, 전문적이고 깊이 있는 내용

출력 형식 (정확히):
SUPPLEMENT_HTML: (위 내용 HTML)
META_DESC: (130~155자 한글, '{keyword}' 포함, 요약형)"""
    else:
        return f"""Write supplemental content to append to an already-published blog post
titled "{title}" (topic: {keyword}). HTML only, no markdown.

Requirements:
0. Add 3-4 in-depth analysis paragraphs (background/causes/real cases/expert advice, 1500+ characters total)
1. At least 5 real statistics (%, numbers, figures)
2. At least 3 source citations: "(Organization, 2026)" format (year MUST be 2026 only, never past years)
3. At least 1 <table> (comparison/data table, full thead/tbody structure)
4. At least 3 FAQs, each in exactly this format:
   <div itemscope itemprop="mainEntity" itemtype="https://schema.org/Question"><h3 itemprop="name">Question</h3><div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer"><p itemprop="text">Answer</p></div></div>
   Wrap all in <div itemscope itemtype="https://schema.org/FAQPage"><h2>Frequently Asked Questions</h2>...</div>
5. Use <h2>/<h3> subheadings, professional and in-depth content

Output format (exactly):
SUPPLEMENT_HTML: (the HTML above)
META_DESC: (130-155 English chars, include '{keyword}', summary style)"""


def parse_supplement(raw):
    m1 = re.search(r'SUPPLEMENT_HTML:\s*(.*?)(?=META_DESC:|$)', raw, re.DOTALL)
    m2 = re.search(r'META_DESC:\s*(.*)', raw, re.DOTALL)
    html = m1.group(1).strip() if m1 else ""
    meta = m2.group(1).strip() if m2 else ""
    html = re.sub(r'\b(2023|2024|2025)\b', '2026', html)
    meta = re.sub(r'\b(2023|2024|2025)\b', '2026', meta)
    return html, meta


def boost_site(site):
    url = site["url"]
    pw = os.getenv(site["wp_pass_env"], "")
    if not pw:
        return {"site": url, "error": "no_password"}

    lang = site.get("lang", "ko")
    boosted = failed = skipped = 0
    log = []
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
                    return {"site": url, "error": str(e), "boosted": boosted, "log": log}
                time.sleep(5)
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break

        for p in batch:
            title = p.get("title", {}).get("rendered", "")
            body = p.get("content", {}).get("rendered", "")
            meta_obj = p.get("meta", {}) or {}
            keyword = meta_obj.get("rank_math_focus_keyword", "")
            tag_count = len(p.get("tags", []) or [])
            faq_count = body.count("schema.org/Question")
            meta_desc = meta_obj.get("rank_math_description", "")

            score_before = real_score(title, body, meta_desc, keyword, tag_count, faq_count)
            if score_before >= LOW_THRESHOLD:
                skipped += 1
                continue

            try:
                prompt_keyword = (keyword.split(",")[0].strip() if keyword else title)
                prompt = build_supplement_prompt(prompt_keyword, title, lang)
                raw = generate_content_gemini(prompt)
                sup_html, sup_meta = parse_supplement(raw)
                if not sup_html:
                    failed += 1
                    log.append({"id": p["id"], "title": title, "error": "빈 응답"})
                    continue

                marker = 'class="related-links"'

                # 이미지 2장 + 권위기관 링크 2개 추가 (이미지/링크 배점 보강)
                extra_html = ""
                try:
                    imgs = get_multiple_images(prompt_keyword, count=2, theme=site.get("theme", ""))
                    if imgs:
                        extra_html += build_img_html(imgs, prompt_keyword)
                except Exception:
                    pass
                try:
                    auth = get_authority_links(site.get("theme", ""))
                    if auth:
                        label = "참고 자료" if lang == "ko" else "References"
                        items = "".join(f'<li><a href="{u}" target="_blank" rel="noopener">{n}</a></li>' for n, u in auth[:3])
                        extra_html += f'<div style="margin:20px 0;"><h3>{label}</h3><ul>{items}</ul></div>'
                except Exception:
                    pass
                sup_html = sup_html + extra_html

                if marker in body:
                    idx = body.find('<div class="related-links"')
                    new_body = body[:idx] + sup_html + body[idx:]
                else:
                    new_body = body + sup_html

                new_meta_desc = sup_meta if len(sup_meta) >= 80 else meta_desc
                payload = {"content": new_body}
                if new_meta_desc:
                    payload["meta"] = {"rank_math_description": new_meta_desc}

                pr = requests.patch(f"{url}/wp-json/wp/v2/posts/{p['id']}", auth=(WP_USER, pw),
                                     json=payload, timeout=25)
                new_faq_count = new_body.count("schema.org/Question")
                score_after = real_score(title, new_body, new_meta_desc or meta_desc, keyword, tag_count, new_faq_count)

                if pr.status_code in (200, 201):
                    boosted += 1
                    log.append({"id": p["id"], "title": title[:40], "before": score_before, "after": score_after})
                else:
                    failed += 1
                    log.append({"id": p["id"], "title": title[:40], "error": f"HTTP {pr.status_code}"})
            except Exception as e:
                failed += 1
                log.append({"id": p["id"], "title": title[:40], "error": str(e)})

            time.sleep(random.uniform(2, 4))

        if len(batch) < 20:
            break
        page += 1

    return {"site": url, "boosted": boosted, "failed": failed, "skipped": skipped, "log": log}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="")
    args = ap.parse_args()

    targets = [s for s in SITES_CONFIG if s["url"] != "https://k-health365.com"
               and (not args.site or s["url"] == args.site)]

    results = []
    for site in targets:
        res = boost_site(site)
        results.append(res)
        print(f"{site['url']}: boosted={res.get('boosted',0)} failed={res.get('failed',0)} skipped={res.get('skipped',0)}")
        with open("boost_result.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
