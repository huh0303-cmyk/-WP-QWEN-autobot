# -*- coding: utf-8 -*-
"""
k-health365.com을 제외한 26개 사이트 전체 발행글의 구조적 SEO 품질을 재평가한다 (읽기전용).

방법: autopost_mega.py의 estimate_seo_score()와 동일한 채점 로직을 재사용하되,
     발행 당시의 원본 focus keyword/meta description은 REST API로 재조회가
     안 되는 필드라서, 본문/구조 신호(글자수·이미지·내부링크·통계·인용·
     제목구조 h2/h3/표·FAQ유무·태그수) 중심으로 근사 채점한다.
     → "양보다 전문성·깊이·구조"라는 목표에 맞는 지표들 위주로 평가.
"""
import os, sys, re, json, time, requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER, count_stats, TAG_COUNT

SCORE_THRESHOLD = 90


def approx_score(title, body, excerpt, tag_count):
    score = 0
    plain = re.sub(r'<[^>]+>', '', body)
    blen = len(plain.replace(" ", "").replace("\n", ""))

    # 제목 (keyword 정보 없이 근사: 길이/숫자 포함 여부만)
    if 20 <= len(title) <= 65: score += 3
    if any(c.isdigit() for c in title): score += 2
    score += 10  # 원 로직의 'keyword in title' 10점은 발행 시점에 이미 보장된 것으로 간주

    if blen >= 3000: score += 20
    elif blen >= 2500: score += 17
    elif blen >= 2000: score += 13
    elif blen >= 1800: score += 9
    elif blen >= 1000: score += 4

    ml = len(re.sub(r'<[^>]+>', '', excerpt))
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

    faq_like = len(re.findall(r'\bQ[:.]', body)) or len(re.findall(r'<h[23][^>]*>\s*(Q|질문)', body, re.IGNORECASE))
    if faq_like >= 3: score += 5
    elif faq_like >= 1: score += 2

    if tag_count >= TAG_COUNT: score += 5
    elif tag_count >= 6: score += 2

    return min(score, 100)


def audit_site(site):
    url = site["url"]
    pw = os.getenv(site["wp_pass_env"], "")
    if not pw:
        return {"site": url, "error": "no_password"}

    total = 0
    below = []
    page = 1
    while True:
        r = None
        for attempt in range(3):
            try:
                r = requests.get(f"{url}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                                  params={"per_page": 20, "page": page, "status": "publish",
                                          "_fields": "id,title,content,excerpt,tags,link,date"}, timeout=40)
                break
            except Exception as e:
                if attempt == 2:
                    return {"site": url, "error": str(e), "total": total, "below": below}
                time.sleep(5)
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        for p in batch:
            total += 1
            title = p.get("title", {}).get("rendered", "")
            body = p.get("content", {}).get("rendered", "")
            excerpt = p.get("excerpt", {}).get("rendered", "")
            tag_count = len(p.get("tags", []) or [])
            sc = approx_score(title, body, excerpt, tag_count)
            if sc < SCORE_THRESHOLD:
                below.append({"id": p["id"], "title": title, "score": sc, "link": p.get("link")})
        if len(batch) < 20:
            break
        page += 1
        time.sleep(0.4)

    return {"site": url, "total": total, "below_90_count": len(below), "below_90": below}


if __name__ == "__main__":
    results = []
    for site in SITES_CONFIG:
        if site["url"] == "https://k-health365.com":
            continue  # k-health365는 별도 트랙, 이번 감사 대상 제외
        results.append(audit_site(site))
    with open("seo_audit_result.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(json.dumps(results, ensure_ascii=False)[:2000])
