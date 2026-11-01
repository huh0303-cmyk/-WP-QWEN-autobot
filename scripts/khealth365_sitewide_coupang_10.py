#!/usr/bin/env python3
"""Replace or add exactly ten Coupang Partners cards on published K-Health365 posts."""
import os, re, json, html, argparse, sys
from pathlib import Path
from urllib.parse import urlparse
import requests

SITE = "https://k-health365.com"
START = "<!-- KHEALTH365-COUPANG-START -->"
END = "<!-- KHEALTH365-COUPANG-END -->"
DISCLOSURE = "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
CATALOG = Path("config/affiliate/k-health365-sitewide-10.json")
OUT = Path("output/khealth365-sitewide-10-report.json")
UA = {"User-Agent": "Mozilla/5.0 (compatible; KHealth365AffiliateWorkflow/1.0)"}

def die(msg):
    raise SystemExit("ERROR: " + msg)

def image_from_affiliate(url):
    r = requests.get(url, headers=UA, timeout=35, allow_redirects=True)
    r.raise_for_status()
    page = r.text[:5000000]
    patterns = [
        r"""<meta[^>]+property=["']og:image["'][^>]+content=["']([^"']+)""",
        r"""<meta[^>]+content=["']([^"']+)["'][^>]+property=["']og:image["']""",
        r"""<meta[^>]+name=["']twitter:image["'][^>]+content=["']([^"']+)""",
    ]
    for pat in patterns:
        m = re.search(pat, page, re.I)
        if m:
            candidate = html.unescape(m.group(1))
            if candidate.startswith("https://") and "coupangcdn.com" in urlparse(candidate).netloc:
                check = requests.get(candidate, headers=UA, timeout=25, stream=True)
                ctype = check.headers.get("Content-Type", "").lower()
                check.close()
                if check.ok and ctype.startswith("image/"):
                    return candidate
    die("상품 대표 이미지 확인 실패: " + url)

def load_products():
    items = json.loads(CATALOG.read_text(encoding="utf-8"))
    if len(items) != 10:
        die("상품 카탈로그는 정확히 10개여야 합니다.")
    urls = [p["url"] for p in items]
    if len(set(urls)) != 10:
        die("중복 쿠팡 파트너스 URL이 있습니다.")
    for p in items:
        if not re.fullmatch(r"https://link\.coupang\.com/a/[A-Za-z0-9]+", p["url"]):
            die("쿠팡 파트너스 단축 URL 형식 오류: " + p["id"])
        if not p.get("title"):
            die("상품명 누락: " + p["id"])
        if not p.get("image_url"):
            p["image_url"] = image_from_affiliate(p["url"])
        if not p["image_url"].startswith("https://"):
            die("이미지 URL 검증 실패: " + p["id"])
        check = requests.get(p["image_url"], headers=UA, timeout=25, stream=True)
        ctype = check.headers.get("Content-Type", "").lower()
        check.close()
        if not check.ok or not ctype.startswith("image/"):
            die("상품 이미지 응답 검증 실패: " + p["id"])
    return items

def render_block(products):
    cards = []
    for p in products:
        u = html.escape(p["url"], quote=True)
        img = html.escape(p["image_url"], quote=True)
        title = html.escape(p["title"])
        cards.append(
            '<article class="khealth365-coupang-card">'
            '<a href="' + u + '" target="_blank" rel="sponsored nofollow noopener">'
            '<img src="' + img + '" alt="' + title + '" loading="lazy" decoding="async">'
            '<span class="khealth365-coupang-title">' + title + '</span></a>'
            '<a class="khealth365-coupang-cta" href="' + u + '" target="_blank" rel="sponsored nofollow noopener">쿠팡에서 상품 확인</a>'
            '</article>'
        )
    style = (
        '<style>.khealth365-coupang-wrap{margin:28px 0;padding:18px;border:1px solid #e5e7eb;border-radius:12px}'
        '.khealth365-coupang-wrap h2{font-size:20px;margin:0 0 10px}'
        '.khealth365-coupang-disclosure{font-size:12px;line-height:1.5;margin:0 0 14px}'
        '.khealth365-coupang-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px}'
        '.khealth365-coupang-card{min-width:0;border:1px solid #e5e7eb;border-radius:10px;padding:10px;text-align:center;display:flex;flex-direction:column;align-items:center}'
        '.khealth365-coupang-card img{width:100%;height:150px;object-fit:contain;display:block}'
        '.khealth365-coupang-title{display:block;font-size:13px;line-height:1.45;margin:8px 0;overflow-wrap:anywhere}'
        '.khealth365-coupang-cta{display:block;margin-top:auto;background:#17365d;color:#fff!important;text-decoration:none;padding:8px 10px;border-radius:7px;font-size:12px}'
        '@media(max-width:760px){.khealth365-coupang-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.khealth365-coupang-card img{height:130px}}</style>'
    )
    return (
        START + '\n<section class="khealth365-coupang-wrap" aria-label="쿠팡 파트너스 추천 상품">'
        + style + '<h2>함께 살펴볼 건강관리 상품 10선</h2>'
        + '<p class="khealth365-coupang-disclosure">' + DISCLOSURE + '</p>'
        + '<div class="khealth365-coupang-grid">' + ''.join(cards) + '</div></section>\n' + END
    )

def wp_request(session, method, url, **kwargs):
    r = session.request(method, url, timeout=60, **kwargs)
    if not r.ok:
        die("WordPress API " + str(r.status_code) + ": " + r.text[:500])
    return r

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["preview", "apply"], default=os.getenv("MODE", "preview"))
    ap.add_argument("--limit", type=int, default=0, help="0 means all published posts")
    args = ap.parse_args()
    user = os.getenv("KHEALTH365_WP_USER", "").strip()
    password = os.getenv("KHEALTH365_WP_APP_PASSWORD", "").strip()
    if not user or not password:
        die("GitHub Secrets KHEALTH365_WP_USER / KHEALTH365_WP_APP_PASSWORD 필요")
    products = load_products()
    block = render_block(products)
    session = requests.Session()
    session.auth = (user, password)
    session.headers.update(UA)
    posts, page = [], 1
    while True:
        r = wp_request(session, "GET", SITE + "/wp-json/wp/v2/posts",
            params={"status":"publish","per_page":100,"page":page,"context":"edit","_fields":"id,link,title,content,status"})
        batch = r.json()
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    if args.limit:
        posts = posts[:args.limit]
    report = {"site":SITE,"mode":args.mode,"products":len(products),"posts_found":len(posts),
        "updated":0,"already_current":0,"skipped_legacy":0,"errors":[],"results":[]}
    for post in posts:
        pid = post["id"]
        raw = post.get("content",{}).get("raw")
        if raw is None:
            report["errors"].append({"id":pid,"reason":"raw content unavailable"})
            continue
        if START in raw and END in raw:
            start_at = raw.index(START)
            end_at = raw.index(END, start_at) + len(END)
            before = raw[:start_at]
            after = raw[end_at:]
            # Existing editor content sometimes wraps marker comments in empty paragraph tags.
            if before.rstrip().endswith("<p>"):
                before = before.rstrip()[:-3]
            if after.lstrip().startswith("</p>"):
                after = after.lstrip()[4:]
            new = before.rstrip() + "\n" + block + "\n" + after.lstrip()
        elif "link.coupang.com/" in raw or "쿠팡 파트너스 활동의 일환" in raw:
            report["skipped_legacy"] += 1
            report["results"].append({"id":pid,"url":post.get("link"),"status":"SKIPPED_UNMARKED_LEGACY_BLOCK"})
            continue
        else:
            new = raw.rstrip() + "\n\n" + block + "\n"
        if new == raw:
            report["already_current"] += 1
            continue
        report["results"].append({"id":pid,"url":post.get("link"),"status":"PREVIEW_READY"})
        if args.mode == "apply":
            wp_request(session,"POST",SITE + "/wp-json/wp/v2/posts/" + str(pid),json={"content":new})
            verify = wp_request(session,"GET",SITE + "/wp-json/wp/v2/posts/" + str(pid),
                params={"context":"edit","_fields":"id,link,content,status"}).json()
            check = verify.get("content",{}).get("raw","")
            if START not in check or END not in check or sum(check.count(p["url"]) for p in products) < 20:
                report["errors"].append({"id":pid,"reason":"REST read-back verification failed"})
                continue
            public = wp_request(session,"GET",SITE + "/wp-json/wp/v2/posts/" + str(pid),
                params={"_fields":"id,link,content,status"}).json()
            rendered = public.get("content",{}).get("rendered","")
            distinct = set(re.findall(r"""href=["'](https://link\.coupang\.com/a/[^"']+)""", rendered))
            expected = set(p["url"] for p in products)
            if len(expected.intersection(distinct)) != 10:
                report["errors"].append({"id":pid,"reason":"public page missing one or more affiliate links"})
                continue
            report["updated"] += 1
            report["results"][-1]["status"] = "UPDATED_AND_VERIFIED"
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:report[k] for k in ("mode","products","posts_found","updated","already_current","skipped_legacy","errors")},ensure_ascii=False))
    if report["errors"]:
        sys.exit(2)
    if args.mode == "preview":
        print("PREVIEW ONLY — WordPress content was not changed.")

if __name__ == "__main__":
    main()
