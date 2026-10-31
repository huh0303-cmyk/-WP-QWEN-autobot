import os, re, json, sys, time, html
from pathlib import Path
import requests
from requests.auth import HTTPBasicAuth

BASE = "https://jobkorea365.com"
USER = "huh0303@gmail.com"
PASSWORD = os.getenv("JOBKOREA365COM", "")
ROOT = Path(__file__).resolve().parents[1]
CAPTURES = ROOT / "reports" / "jobkorea365-coupang-portal-captures-2026-10-31.ndjson"
REPORT = ROOT / "reports" / "jobkorea365-all-posts-6to10-report.json"
DISC = "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
TARGET = 8

if not PASSWORD:
    raise SystemExit("Missing GitHub secret JOBKOREA365COM")

products, seen = [], set()
for line in CAPTURES.read_text(encoding="utf-8-sig").splitlines():
    try:
        rec = json.loads(line)
    except Exception:
        continue
    pid = str(rec.get("product_id") or "")
    tag = rec.get("official_blog_html_tag") or ""
    href = re.search(r'href="(https://link\.coupang\.com/a/[^"]+)"', tag)
    img = re.search(r'<img[^>]+src="(https://[^"]+)"', tag)
    if rec.get("status") != "CAPTURED" or not pid or pid in seen or not href or not img:
        continue
    if not re.search(r'/image/affiliate/banner/', img.group(1)):
        continue
    seen.add(pid)
    products.append({
        "id": pid, "title": rec.get("product_title") or rec.get("image_alt") or pid,
        "html": tag, "href": href.group(1), "search": (rec.get("query") or "") + " " + (rec.get("product_title") or "")
    })

if len(products) < 8:
    raise SystemExit(f"Only {len(products)} distinct verified products; refusing mass insertion")

def choose(post):
    text = re.sub(r"<[^>]+>", " ", (post.get("title", {}).get("rendered", "") + " " + post.get("content", {}).get("raw", "")))
    text = html.unescape(text).lower()
    rules = [
        (r"면접|이력서|취업|채용|자기소개|interview|resume|job application", ["1875724251", "7166147985", "6853286088", "9432151903"]),
        (r"한국어|topik|eps.topik|회화|어휘|korean language", ["6460589746", "9751875747"]),
        (r"안전|산업|현장|보호구|공장|ppe|safety|industrial", ["22672148", "9745144579"]),
        (r"피부|화장품|뷰티|미용|보습|선크림|스킨케어|beauty|skin", ["9727536893", "6633183483", "4500298441", "9727610179"]),
        (r"건강|구강|치아|위생|영양|운동|health|oral|tooth", ["6239624318", "2111955991", "7735337888"]),
        (r"생활|기숙사|세탁|정리|청소|가정|living|dorm|laundry", ["6746052927", "9432151903"]),
    ]
    preferred = []
    for pattern, ids in rules:
        if re.search(pattern, text, re.I):
            for p in products:
                if p["id"] in ids and p not in preferred:
                    preferred.append(p)
    chosen = preferred[:2]
    start = (int(post["id"]) * 7) % len(products)
    for offset in range(len(products)):
        p = products[(start + offset) % len(products)]
        if p not in chosen:
            chosen.append(p)
        if len(chosen) == TARGET:
            break
    return chosen

def block(items):
    cards = "".join(
        '<div class="coupang-product-card" style="flex:1 1 140px;max-width:180px;text-align:center;padding:8px;border:1px solid #eee;border-radius:8px">'
        + p["html"] + '<p style="font-size:12px;line-height:1.4">' + html.escape(p["title"]) + "</p></div>"
        for p in items
    )
    return ('<section class="coupang-partners-products" style="margin:24px 0;padding:16px;border:1px solid #eee;border-radius:10px">'
        '<p style="font-size:13px;font-weight:600">' + DISC + '</p>'
        '<p><strong>함께 살펴볼 만한 추천 상품</strong></p>'
        '<div style="display:flex;flex-wrap:wrap;gap:12px">' + cards + '</div></section>')

s = requests.Session()
s.auth = HTTPBasicAuth(USER, PASSWORD)
s.headers.update({"User-Agent": "LondonProject-JobKorea365-Verified-Coupang/2.0"})
results, page = [], 1
while True:
    r = s.get(BASE + "/wp-json/wp/v2/posts", params={
        "status":"publish", "per_page":100, "page":page, "context":"edit",
        "_fields":"id,status,date,featured_media,link,title,content"
    }, timeout=45)
    if r.status_code != 200:
        raise SystemExit(f"LIST_FAILED {r.status_code}: {r.text[:400]}")
    posts = r.json()
    if not posts:
        break
    for post in posts:
        content = post.get("content") or {}
        raw = content.get("raw")
        if not isinstance(raw, str) or not raw:
            results.append({"id":post["id"],"url":post.get("link"),"status":"NO_EDITABLE_RAW"})
            continue
        # Replace only this automation's prior block; preserve all other article content.
        new = re.sub(r'<section\b(?=[^>]*class=["\'][^"\']*coupang-partners-products)[\s\S]*?</section>', '', raw, flags=re.I)
        items = choose(post)
        new_block = block(items)
        # Put the disclosure and product panel near the beginning, after the first paragraph.
        m = re.search(r'</p\s*>', new, flags=re.I)
        if m:
            new = new[:m.end()] + new_block + new[m.end():]
        else:
            new = new_block + new
        u = s.post(BASE + f"/wp-json/wp/v2/posts/{post['id']}", json={"content":new}, timeout=45)
        if u.status_code not in (200, 201):
            results.append({"id":post["id"],"url":post.get("link"),"status":"WRITE_FAILED","http":u.status_code,"detail":u.text[:200]})
            continue
        v = s.get(BASE + f"/wp-json/wp/v2/posts/{post['id']}", params={
            "context":"edit", "_fields":"id,status,date,featured_media,content"
        }, timeout=45)
        if v.status_code != 200:
            results.append({"id":post["id"],"url":post.get("link"),"status":"READBACK_FAILED","http":v.status_code})
            continue
        check = v.json()
        saved = (check.get("content") or {}).get("raw") or ""
        section = re.search(r'<section\b(?=[^>]*class=["\'][^"\']*coupang-partners-products)[\s\S]*?</section>', saved, flags=re.I)
        panel = section.group(0) if section else ""
        links = set(re.findall(r'href="(https://link\.coupang\.com/a/[^"]+)"', panel))
        ok = (len(links) == TARGET and DISC in panel and check.get("status") == post.get("status")
              and check.get("date") == post.get("date")
              and check.get("featured_media") == post.get("featured_media"))
        results.append({"id":post["id"],"url":post.get("link"),"products":len(links),
                        "product_titles":[p["title"] for p in items],
                        "status":"VERIFIED" if ok else "VERIFY_FAILED"})
        time.sleep(0.15)
    if len(posts) < 100:
        break
    page += 1

REPORT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
verified = sum(1 for x in results if x["status"] == "VERIFIED")
failed = [x for x in results if x["status"] != "VERIFIED"]
print(json.dumps({"distinct_verified_products":len(products),"posts_processed":len(results),
                  "verified":verified,"failed":len(failed),"failures":failed[:20],
                  "report":str(REPORT)}, ensure_ascii=False, indent=2))
if failed:
    sys.exit(2)
