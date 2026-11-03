#!/usr/bin/env python3
import os, json, requests, html, re, time
from requests.auth import HTTPBasicAuth

BASE = "https://k-trip365.com"
USER = "huh0303@gmail.com"
PW = os.environ.get("KTRIP365COM", "")
DATA = "data/affiliate/ktrip365-products.json"
REPORT = "reports/ktrip365-coupang-all-posts-repair-2026-11-03.json"
BACKUP = "reports/ktrip365-coupang-all-posts-backup-2026-11-03.json"
DISC = "\uc774 \ud3ec\uc2a4\ud305\uc740 \ucfe0\ud321 \ud30c\ud2b8\ub108\uc2a4 \ud65c\ub3d9\uc758 \uc77c\ud658\uc73c\ub85c, \uc774\uc5d0 \ub530\ub978 \uc77c\uc815\uc561\uc758 \uc218\uc218\ub8cc\ub97c \uc81c\uacf5\ubc1b\uc2b5\ub2c8\ub2e4."
HEADING = "\ud568\uaed8 \uc0b4\ud3b4\ubcfc \ub9cc\ud55c \ucd94\ucc9c \uc0c1\ud488"
CTA = "\ucfe0\ud321\uc5d0\uc11c \ud655\uc778\ud558\uae30"
if not PW:
    raise SystemExit("Missing KTRIP365COM secret")

catalog = json.load(open(DATA, encoding="utf-8"))
products = catalog.get("products", [])
if catalog.get("site", "").rstrip("/") != "https://k-trip365.com" or len(products) != 10:
    raise SystemExit("K-Trip365 product catalog mismatch or not exactly 10 products")
if len({p.get("affiliate_url") for p in products}) != 10:
    raise SystemExit("Product affiliate URLs are not unique")
for p in products:
    if not p.get("verified_account_owned") or not p.get("affiliate_confirmed"):
        raise SystemExit(f"Product not verified as account-generated: {p.get('id')}")
    if p.get("capture_source") != "coupang_partners_portal" or p.get("status") != "VERIFIED_ACCOUNT_GENERATED":
        raise SystemExit(f"Invalid capture status: {p.get('id')}")
    if not p.get("affiliate_url", "").startswith("https://link.coupang.com/"):
        raise SystemExit(f"Invalid Coupang affiliate URL: {p.get('id')}")
    if not p.get("official_image_url", "").startswith("https://"):
        raise SystemExit(f"Invalid image URL: {p.get('id')}")
    if not p.get("title_ko") or "?" in p["title_ko"]:
        raise SystemExit(f"Corrupt product title: {p.get('id')}")

s = requests.Session()
s.auth = HTTPBasicAuth(USER, PW)
s.headers["User-Agent"] = "LondonProject-KTrip365-Coupang-AllPosts-Repair/1.0"

# Retrieve every published post with editable raw content.
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
if len(posts) < 1:
    raise SystemExit("No published K-Trip365 posts returned; refusing to continue")

# Remove only known previous affiliate blocks; all unrelated article HTML is retained.
def strip_old_affiliate_blocks(raw):
    before = raw
    # Remove any element carrying the legacy CTA/banner class, regardless of wrapper paragraphs or Gutenberg comments.
    raw = re.sub(
        r'<(?:section|div)\b(?=[^>]*\bclass=["\'][^"\']*\bcoupang-partners-(?:cta|banner)\b)[^>]*>.*?</(?:section|div)>',
        '', raw, flags=re.I | re.S
    )
    raw = re.sub(r'<!--\s*coupang-partners-generic-cta-20261103\s*-->', '', raw, flags=re.I)
    raw = re.sub(
        r'<!--\s*KTRIP365_COUPANG_[^>]*-->\s*<section\b[^>]*>.*?</section>',
        '', raw, flags=re.I | re.S
    )
    # Remove empty paragraphs left behind by the old marker.
    raw = re.sub(r'<p>\s*</p>', '', raw, flags=re.I)
    return raw, raw != before

cards = []
for p in products:
    title = html.escape(p["title_ko"], quote=True)
    url = html.escape(p["affiliate_url"], quote=True)
    img = html.escape(p["official_image_url"], quote=True)
    cards.append(
        '<article class="ktrip365-coupang-card" style="box-sizing:border-box;min-width:0;display:flex;flex-direction:column;align-items:center;border:1px solid #e5e7eb;border-radius:12px;padding:14px;text-align:center;background:#fff;">'
        f'<a href="{url}" target="_blank" rel="sponsored nofollow noopener" style="display:block;width:100%;">'
        f'<img src="{img}" alt="{title}" loading="lazy" decoding="async" referrerpolicy="unsafe-url" style="display:block;width:100%;height:170px;max-width:190px;object-fit:contain;margin:0 auto 12px;">'
        '</a>'
        f'<h3 style="font-size:14px;line-height:1.5;font-weight:600;margin:8px 0 12px;color:#222;overflow-wrap:anywhere;">{title}</h3>'
        f'<a href="{url}" target="_blank" rel="sponsored nofollow noopener" style="display:inline-block;margin-top:auto;padding:9px 16px;border-radius:7px;background:#17365d;color:#fff;text-decoration:none;font-size:14px;">{CTA}</a>'
        '</article>'
    )
block = (
    '<section class="ktrip365-coupang-recommendations" style="clear:both;display:block;width:100%;box-sizing:border-box;margin:34px 0 20px;padding:22px 18px;border:1px solid #e5e7eb;border-radius:14px;background:#fff;">'
    f'<p style="font-size:12px;line-height:1.6;color:#666;margin:0 0 16px;">{DISC}</p>'
    f'<h2 style="font-size:22px;line-height:1.4;margin:0 0 18px;">{HEADING}</h2>'
    '<div class="ktrip365-coupang-grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,145px),1fr));gap:14px;align-items:stretch;">'
    + "".join(cards) +
    '</div></section>'
)

backup = {}
plans = []
already = []
for post in posts:
    pid = int(post["id"])
    raw = post.get("content", {}).get("raw")
    if not isinstance(raw, str):
        raise SystemExit(f"Post {pid}: editable raw content missing")
    marker = f"<!-- KTRIP365_COUPANG_ALL_POSTS_V1:{pid} -->"
    backup[str(pid)] = {
        "link": post.get("link"),
        "title": post.get("title", {}).get("raw") or post.get("title", {}).get("rendered"),
        "content_raw": raw,
        "date": post.get("date"),
        "status": post.get("status"),
        "featured_media": post.get("featured_media")
    }
    if marker in raw:
        section = raw.split(marker, 1)[1]
        links = re.findall(r'<a[^>]+href="(https://link\.coupang\.com/[^"]+)"', section)
        imgs = re.findall(r'<img[^>]+src="([^"]+)"', section)
        ok = (
            section.count('class="ktrip365-coupang-card"') == 10 and
            len(imgs) == 10 and all(x.startswith("https://") for x in imgs) and
            len(set(links)) == 10 and raw.count(DISC) == 1
        )
        if not ok:
            raise SystemExit(f"Post {pid}: existing V1 marker but block fails validation")
        already.append({"post_id": pid, "status": "ALREADY_REPAIRED"})
        continue

    editorial, changed = strip_old_affiliate_blocks(raw)
    # Any remaining affiliate URL after known block removal is unexpected; do not erase editorial material.
    if "link.coupang.com/" in editorial or "coupang-partners-" in editorial:
        raise SystemExit(f"Post {pid}: unrecognized legacy affiliate markup remains; refusing unsafe overwrite")
    plans.append((post, editorial, changed))

# Save the complete original content for all posts before the first write.
os.makedirs("reports", exist_ok=True)
with open(BACKUP, "w", encoding="utf-8") as f:
    json.dump(backup, f, ensure_ascii=False, indent=2)

report = list(already)
for post, editorial, removed_old in plans:
    pid = int(post["id"])
    marker = f"<!-- KTRIP365_COUPANG_ALL_POSTS_V1:{pid} -->"
    new_content = editorial.rstrip() + "\n\n" + marker + "\n" + block
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
        "ten_cards": section.count('class="ktrip365-coupang-card"') == 10,
        "ten_images": len(imgs) == 10,
        "all_images_absolute": all(x.startswith("https://") for x in imgs),
        "ten_distinct_coupang_links": len(set(hrefs)) == 10,
        "single_disclosure": body.count(DISC) == 1,
        "only_coupang_provider": all(x.startswith("https://link.coupang.com/") for x in hrefs),
        "no_corrupt_titles": "????" not in section,
        "status_preserved": q.get("status") == post.get("status"),
        "date_preserved": q.get("date") == post.get("date"),
        "featured_media_preserved": q.get("featured_media") == post.get("featured_media")
    }
    public = s.get(post["link"], timeout=45)
    public_html = public.content
    public_section = public_html.split(marker.encode("utf-8"), 1)[-1]
    checks["public_http_200"] = public.status_code == 200
    checks["public_ten_cards"] = public_section.count(b'class="ktrip365-coupang-card"') == 10
    checks["public_ten_absolute_images"] = len(re.findall(rb'<img[^>]+src="https://', public_section, re.I)) == 10
    checks["public_ten_coupang_links"] = len(set(re.findall(rb'href="(https://link\.coupang\.com/[^"]+)"', public_section, re.I))) == 10
    checks["old_block_removed"] = "coupang-partners-cta" not in body and "coupang-partners-banner" not in body
    ok = all(checks.values())
    report.append({
        "post_id": pid, "url": post.get("link"), "removed_old_block": removed_old,
        "checks": checks, "status": "VERIFIED" if ok else "VERIFY_FAILED"
    })
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    if not ok:
        break
    time.sleep(0.15)

with open(REPORT, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print(json.dumps({
    "published_posts": len(posts), "updated_posts": len(plans),
    "already_repaired": len(already), "verified": sum(x["status"] in ("VERIFIED", "ALREADY_REPAIRED") for x in report),
    "report": report
}, ensure_ascii=True, indent=2))
if len(report) != len(posts) or any(x["status"] not in ("VERIFIED", "ALREADY_REPAIRED") for x in report):
    raise SystemExit("KTRIP365_ALL_POSTS_REPAIR_INCOMPLETE_OR_VERIFICATION_FAILED")
