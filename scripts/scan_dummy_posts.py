# -*- coding: utf-8 -*-
"""
27개 사이트 전체에서 '더미글'로 의심되는 포스트를 탐지만 한다 (삭제/수정 안 함).
판별 기준:
  1. 제목이 'Post 40', 'Untitled', 'test', '샘플' 등 플레이스홀더 패턴
  2. 본문 실제 텍스트 길이가 매우 짧음 (HTML 태그 제거 후 500자 미만)
  3. 본문에 'lorem ipsum', '더미', 'placeholder', 'sample content' 등 포함
"""
import os, sys, re, json, time, requests
from html import unescape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

DUMMY_TITLE_RE = re.compile(
    r'^(post[\s\-_]?\d+|untitled|test\s*post?|sample|draft|더미|샘플\s*글?|테스트\s*글?|placeholder)\s*\d*\s*$',
    re.IGNORECASE)
DUMMY_CONTENT_MARKERS = ["lorem ipsum", "placeholder text", "sample content", "더미 텍스트", "테스트 본문"]
MIN_TEXT_LEN = 500


def strip_html(html):
    text = re.sub(r'<[^>]+>', ' ', html)
    text = unescape(text)
    return re.sub(r'\s+', ' ', text).strip()


def scan_site(site):
    url = site["url"]
    pw = os.getenv(site["wp_pass_env"], "")
    if not pw:
        return {"site": url, "error": "no_password"}

    total = 0
    suspects = []
    page = 1
    while True:
        r = None
        for attempt in range(3):
            try:
                r = requests.get(f"{url}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                                  params={"per_page": 20, "page": page, "status": "publish",
                                          "_fields": "id,title,content,link,date"}, timeout=40)
                break
            except Exception as e:
                if attempt == 2:
                    return {"site": url, "error": str(e), "total": total, "suspects": suspects}
                time.sleep(5)
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        for p in batch:
            total += 1
            title = p.get("title", {}).get("rendered", "").strip()
            content_html = p.get("content", {}).get("rendered", "")
            text = strip_html(content_html)
            reasons = []
            if DUMMY_TITLE_RE.match(title):
                reasons.append("제목이 더미패턴")
            if len(text) < MIN_TEXT_LEN:
                reasons.append(f"본문 {len(text)}자(500자 미만)")
            low = text.lower()
            for marker in DUMMY_CONTENT_MARKERS:
                if marker in low:
                    reasons.append(f"'{marker}' 포함")
            if reasons:
                suspects.append({"id": p["id"], "title": title, "link": p.get("link"),
                                  "date": p.get("date"), "text_len": len(text), "reasons": reasons})
        if len(batch) < 20:
            break
        page += 1
        time.sleep(0.5)
    return {"site": url, "total": total, "suspect_count": len(suspects), "suspects": suspects}


if __name__ == "__main__":
    results = [scan_site(s) for s in SITES_CONFIG]
    with open("dummy_scan_result.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(json.dumps(results, ensure_ascii=False, indent=2)[:3000])
