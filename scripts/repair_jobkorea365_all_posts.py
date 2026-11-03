#!/usr/bin/env python3
import os, json, requests, html, re, sys, time
from requests.auth import HTTPBasicAuth

BASE = "https://jobkorea365.com"
USER = "huh0303@gmail.com"
PW = os.environ.get("JOBKOREA365COM", "")
DISC = "\uc774 \ud3ec\uc2a4\ud305\uc740 \ucfe0\ud321 \ud30c\ud2b8\ub108\uc2a4 \ud65c\ub3d9\uc758 \uc77c\ud658\uc73c\ub85c, \uc774\uc5d0 \ub530\ub978 \uc77c\uc815\uc561\uc758 \uc218\uc218\ub8cc\ub97c \uc81c\uacf5\ubc1b\uc2b5\ub2c8\ub2e4."
HEADING = "\ud568\uaed8 \uc0b4\ud3b4\ubcfc \ub9cc\ud55c \ucd94\ucc9c \uc0c1\ud488"
CTA = "\ucfe0\ud321\uc5d0\uc11c \ud655\uc778\ud558\uae30"
DATA = "data/affiliate/fleet-placements.json"
CAPTURES = "reports/jobkorea365-coupang-portal-captures-2026-10-31.ndjson"
REPORT = "reports/jobkorea365-all-posts-repair-2026-11-03.json"
BACKUP = "reports/jobkorea365-all-posts-original-backup-2026-11-03.json"
if not PW:
    raise SystemExit("Missing JOBKOREA365COM secret")

fleet = json.load(open(DATA, encoding="utf-8"))
products = list(fleet["sites"]["jobkorea365.com"][0]["products"])
captures = [json.loads(x) for x in open(CAPTURES, encoding="utf-8") if x.strip()]
for cid in ("jk03", "jk04"):
    products.append(next(x for x in captures if x["candidate_id"] == cid))
if len(products) != 10 or len({p["affiliate_url"] for p in products}) != 10:
    raise SystemExit("Product pool must contain exactly 10 unique affiliate products")
for p in products:
    if not p.get("affiliate_url", "").startswith("https://link.coupang.com/"):
        raise SystemExit("Invalid affiliate URL")
    if not p.get("official_image_url", "").startswith("https://"):
        raise SystemExit("Invalid official image URL")
    if not p.get("product_title") or "?" in p["product_title"]:
        raise SystemExit("Corrupt or missing product title")
    if p.get("status") != "CAPTURED":
        raise SystemExit("Product capture status is not CAPTURED")

s = requests.Session()
s.auth = HTTPBasicAuth(USER, PW)
s.headers["User-Agent"] = "LondonProject-JobKorea365-AllPosts-Affiliate-Repair/2.0"

# Read every published post using the authenticated edit context.
posts = []
page = 1
while True:
    r = s.get(BASE + "/wp-json/wp/v2/posts", params={
        "status": "publish", "per_page": 100, "page": page, "context": "edit",
        "_fields": "id,status,date,featured_media,link,title,content"
    }, timeout=50)
    if r.status_code == 400 and "rest_post_invalid_page_number" in r.text:
        break
    r.raise_for_status()
    batch = r.json()
    if not batch:
        break
    posts.extend(batch)
    if len(batch) < 100:
        break
    page += 1

if len(posts) < 50:
    raise SystemExit(f"Unexpectedly low published post count: {len(posts)}")

backup = {}
plans = []
already = []
for p in posts:
    raw = p.get("content", {}).get("raw")
    if not isinstance(raw, str):
        raise SystemExit(f"Post {p.get('id')}: editable content missing")
    pid = int(p["id"])
    marker = f"<!-- JOBKOREA365_AFFILIATE_REPAIRED_V2:{pid} -->"
    backup[str(pid)] = {
        "link": p.get("link"), "title": p.get("title", {}).get("raw") or p.get("title", {}).get("rendered"),
        "content_raw": raw, "date": p.get("date"), "status": p.get("status"),
        "featured_media": p.get("featured_media")
    }
    if marker in raw:
        section = raw.split(marker, 1)[1]
        h = re.findall(r'<a[^>]+href="(https://link\.coupang\.com/[^"]+)"', section)
        im = re.findall(r'<img[^>]+src="([^"]+)"', section)
        if section.count('class="jk365-product-card"') == 10 and len(im) == 10 and len(set(h)) == 10 and raw.count(DISC) == 1:
            already.append({"post_id": pid, "status": "ALREADY_REPAIRED"})
            continue
        raise SystemExit(f"Post {pid}: V2 marker exists but current block fails validation")
    has_affiliate = "link.coupang.com/" in raw
    if has_affiliate:
        if DISC in raw:
            editorial = raw.split(DISC, 1)[0].rstrip()
        else:
            m = re.search(r'<(?:div|section)[^>]+class="[^"]*(?:coupang|affiliate)', raw, re.I)
            if not m:
                raise SystemExit(f"Post {pid}: affiliate links found but no safe block boundary")
            editorial = raw[:m.start()].rstrip()
    else:
        # New posts without any affiliate block receive one at the end.
        editorial = raw.rstrip()
    plans.append((p, editorial))

# Persist a complete original-content backup before the first write.
os.makedirs("reports", exist_ok=True)
with open(BACKUP, "w", encoding="utf-8") as f:
    json.dump(backup, f, ensure_ascii=False, indent=2)

cards = []
for p in products:
    title = html.escape(p["product_title"], quote=True)
    url = html.escape(p["affiliate_url"], quote=True)
    img = html.escape(p["official_image_url"], quote=True)
    cards.append(
        '<article class="jk365-product-card" style="box-sizing:border-box;min-width:0;border:1px solid #e5e7eb;border-radius:12px;padding:14px;text-align:center;background:#fff;">'
        f'<a href="{url}" target="_blank" rel="sponsored nofollow noopener" style="display:block;">'
        f'<img src="{img}" alt="{title}" loading="lazy" decoding="async" style="display:block;width:100%;height:170px;max-width:180px;object-fit:contain;margin:0 auto 12px;">'
        '</a>'
        f'<h3 style="font-size:15px;line-height:1.5;font-weight:600;margin:8px 0 12px;color:#222;">{title}</h3>'
        f'<a href="{url}" target="_blank" rel="sponsored nofollow noopener" style="display:inline-block;padding:9px 16px;border-radius:7px;background:#17365d;color:#fff;text-decoration:none;font-size:14px;">{CTA}</a>'
        '</article>'
    )
block_template = (
    '<section class="jk365-affiliate-recommendations" style="margin:32px 0;padding:22px 18px;border:1px solid #e5e7eb;border-radius:14px;">'
    f'<p style="font-size:12px;line-height:1.6;color:#666;margin:0 0 16px;">{DISC}</p>'
    f'<h2 style="font-size:22px;line-height:1.4;margin:0 0 18px;">{HEADING}</h2>'
    '<div class="jk365-product-grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;">'
    + "".join(cards) + '</div></section>'
)

report = list(already)
for p, editorial in plans:
    pid = int(p["id"])
    marker = f"<!-- JOBKOREA365_AFFILIATE_REPAIRED_V2:{pid} -->"
    new_content = editorial + "\n\n" + marker + "\n" + block_template
    u = s.post(BASE + f"/wp-json/wp/v2/posts/{pid}", json={"content": new_content}, timeout=55)
    u.raise_for_status()
    v = s.get(BASE + f"/wp-json/wp/v2/posts/{pid}", params={"context": "edit"}, timeout=45)
    v.raise_for_status()
    q = v.json()
    body = q.get("content", {}).get("raw") or ""
    section = body.split(marker, 1)[1] if marker in body else ""
    hrefs = re.findall(r'<a[^>]+href="(https://link\.coupang\.com/[^"]+)"', section)
    imgs = re.findall(r'<img[^>]+src="([^"]+)"', section)
    checks = {
        "ten_cards": section.count('class="jk365-product-card"') == 10,
        "ten_images": len(imgs) == 10,
        "all_images_absolute": all(x.startswith("https://") for x in imgs),
        "ten_distinct_affiliate_links": len(set(hrefs)) == 10,
        "single_disclosure": body.count(DISC) == 1,
        "no_corrupt_titles": "????" not in section,
        "status_preserved": q.get("status") == p.get("status"),
        "date_preserved": q.get("date") == p.get("date"),
        "featured_media_preserved": q.get("featured_media") == p.get("featured_media")
    }
    public = s.get(p["link"], params={"affiliate_repair_verify": pid}, timeout=45)
    public_html = public.content
    public_section = public_html.split(marker.encode("utf-8"), 1)[-1]
    checks["public_http_200"] = public.status_code == 200
    checks["public_ten_cards"] = public_section.count(b'class="jk365-product-card"') == 10
    checks["public_ten_absolute_images"] = len(re.findall(rb'<img[^>]+src="https://', public_section, re.I)) == 10
    checks["public_ten_affiliate_links"] = len(set(re.findall(rb'href="(https://link\.coupang\.com/[^"]+)"', public_section, re.I))) == 10
    ok = all(checks.values())
    report.append({"post_id": pid, "url": p.get("link"), "checks": checks, "status": "VERIFIED" if ok else "VERIFY_FAILED"})
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    if not ok:
        break
    time.sleep(0.15)

with open(REPORT, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print(json.dumps({"published_posts": len(posts), "updated_posts": len(plans), "already_repaired": len(already), "report": report}, ensure_ascii=True, indent=2))
if len(report) != len(posts) or any(x["status"] not in ("VERIFIED", "ALREADY_REPAIRED") for x in report):
    raise SystemExit("ALL_POSTS_REPAIR_INCOMPLETE_OR_VERIFICATION_FAILED")
