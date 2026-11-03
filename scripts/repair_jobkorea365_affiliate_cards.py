
#!/usr/bin/env python3
import os, json, requests, html, re, sys, time
from requests.auth import HTTPBasicAuth

BASE = "https://jobkorea365.com"
USER = "huh0303@gmail.com"
PW = os.environ.get("JOBKOREA365COM", "")
DISC = "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
DATA = "data/affiliate/fleet-placements.json"
REPORT = "reports/jobkorea365-affiliate-repair-2026-11-03.json"
BACKUP = "reports/jobkorea365-affiliate-repair-original-backup-2026-11-03.json"
if not PW:
    raise SystemExit("Missing JOBKOREA365COM secret")

with open(DATA, encoding="utf-8") as f:
    fleet = json.load(f)
rows = fleet["sites"]["jobkorea365.com"]
if len(rows) != 10:
    raise SystemExit("Expected exactly 10 mapped JobKorea365 posts; refusing unexpected batch size")

s = requests.Session()
s.auth = HTTPBasicAuth(USER, PW)
s.headers["User-Agent"] = "LondonProject-JobKorea365-Affiliate-Repair/1.0"
backup = {}
report = []

for row in rows:
    post_id = int(row["post_id"])
    products = row.get("products", [])
    if len(products) != 8:
        raise SystemExit(f"Post {post_id}: expected 8 verified products")
    for p in products:
        if not p.get("verified_account_owned") or p.get("capture_source") != "coupang_partners_portal":
            raise SystemExit(f"Post {post_id}: unverified product {p.get('candidate_id')}")
        if not p.get("affiliate_url", "").startswith("https://link.coupang.com/"):
            raise SystemExit(f"Post {post_id}: invalid affiliate URL")
        if not p.get("official_image_url", "").startswith("https://"):
            raise SystemExit(f"Post {post_id}: invalid official image URL")
        if not p.get("product_title") or "?" in p["product_title"]:
            raise SystemExit(f"Post {post_id}: corrupt product title")

    g = s.get(f"{BASE}/wp-json/wp/v2/posts/{post_id}", params={"context": "edit"}, timeout=40)
    g.raise_for_status()
    old = g.json()
    if old.get("status") != "publish":
        raise SystemExit(f"Post {post_id}: not published; refusing update")
    if old.get("link", "").rstrip("/") != row.get("link", "").rstrip("/"):
        raise SystemExit(f"Post {post_id}: permalink mismatch; refusing update")
    raw = old.get("content", {}).get("raw")
    if not isinstance(raw, str) or not raw:
        raise SystemExit(f"Post {post_id}: editable raw content unavailable")
    backup[str(post_id)] = {
        "link": old.get("link"), "title": old.get("title", {}).get("raw") or old.get("title", {}).get("rendered"),
        "content_raw": raw, "date": old.get("date"), "status": old.get("status"),
        "featured_media": old.get("featured_media")
    }

    os.makedirs("reports", exist_ok=True)
    with open(BACKUP, "w", encoding="utf-8") as f:
        json.dump(backup, f, ensure_ascii=False, indent=2)

    marker = f"<!-- JOBKOREA365_AFFILIATE_REPAIRED:{post_id} -->"
    if marker in raw:
        existing_section = raw.split(marker, 1)[1]
        existing_hrefs = re.findall(r'<a[^>]+href="(https://link\.coupang\.com/[^"]+)"', existing_section)
        existing_imgs = re.findall(r'<img[^>]+src="([^"]+)"', existing_section)
        existing_checks = {
            "eight_cards": existing_section.count('class="jk365-product-card"') == 8,
            "eight_images": len(existing_imgs) == 8,
            "all_images_absolute": all(x.startswith("https://") for x in existing_imgs),
            "eight_distinct_affiliate_links": len(set(existing_hrefs)) == 8,
            "single_disclosure": raw.count(DISC) == 1,
            "no_mojibake_question_marks": "????" not in existing_section
        }
        existing_ok = all(existing_checks.values())
        report.append({"post_id": post_id, "checks": existing_checks, "status": "ALREADY_REPAIRED" if existing_ok else "VERIFY_FAILED"})
        if not existing_ok:
            break
        continue
    if DISC not in raw:
        raise SystemExit(f"Post {post_id}: affiliate disclosure anchor missing; refusing to truncate content")
    editorial = raw.split(DISC, 1)[0].rstrip()

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
            f'<a href="{url}" target="_blank" rel="sponsored nofollow noopener" style="display:inline-block;padding:9px 16px;border-radius:7px;background:#17365d;color:#fff;text-decoration:none;font-size:14px;">쿠팡에서 확인하기</a>'
            '</article>'
        )
    block = (
        f"\n\n{marker}\n"
        '<section class="jk365-affiliate-recommendations" style="margin:32px 0;padding:22px 18px;border:1px solid #e5e7eb;border-radius:14px;">'
        f'<p style="font-size:12px;line-height:1.6;color:#666;margin:0 0 16px;">{DISC}</p>'
        '<h2 style="font-size:22px;line-height:1.4;margin:0 0 18px;">함께 살펴볼 만한 추천 상품</h2>'
        '<div class="jk365-product-grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;">'
        + "".join(cards) +
        '</div></section>'
    )
    new_content = editorial + block
    u = s.post(f"{BASE}/wp-json/wp/v2/posts/{post_id}", json={"content": new_content}, timeout=50)
    u.raise_for_status()

    v = s.get(f"{BASE}/wp-json/wp/v2/posts/{post_id}", params={"context": "edit"}, timeout=40)
    v.raise_for_status()
    check = v.json()
    body = check.get("content", {}).get("raw") or ""
    repaired_section = body.split(marker, 1)[1] if marker in body else ""
    hrefs = re.findall(r'<a[^>]+href="(https://link\.coupang\.com/[^"]+)"', repaired_section)
    imgs = re.findall(r'<img[^>]+src="([^"]+)"', repaired_section)
    checks = {
        "single_marker": body.count(marker) == 1,
        "eight_cards": body.count('class="jk365-product-card"') == 8,
        "eight_images": len(imgs) == 8,
        "all_images_absolute": all(x.startswith("https://") for x in imgs),
        "eight_distinct_affiliate_links": len(set(hrefs)) == 8,
        "single_disclosure": body.count(DISC) == 1,
        "no_mojibake_question_marks": "????" not in body,
        "status_preserved": check.get("status") == old.get("status"),
        "date_preserved": check.get("date") == old.get("date"),
        "featured_media_preserved": check.get("featured_media") == old.get("featured_media")
    }
    ok = all(checks.values())
    report.append({"post_id": post_id, "url": old.get("link"), "product_count": 8, "checks": checks, "status": "VERIFIED" if ok else "VERIFY_FAILED"})
    if not ok:
        break
    time.sleep(0.3)

os.makedirs("reports", exist_ok=True)
with open(BACKUP, "w", encoding="utf-8") as f:
    json.dump(backup, f, ensure_ascii=False, indent=2)
with open(REPORT, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print(json.dumps(report, ensure_ascii=False, indent=2))
if len(report) != 10 or any(x["status"] not in ("VERIFIED", "ALREADY_REPAIRED") for x in report):
    raise SystemExit("REPAIR_BATCH_INCOMPLETE_OR_VERIFICATION_FAILED")

