#!/usr/bin/env python3
"""Build and optionally insert a randomized, relevant 5-10 product card block.

Safety:
- Only the configured K-Health365 post ID may be edited by this workflow.
- Preview is the default; apply requires explicit workflow_dispatch mode=apply.
- Existing post content is preserved; the block is replaced in-place on reruns.
- No post status, title, featured image, metadata, or AdSense settings are changed.
"""
from __future__ import annotations

import html
import json
import os
import random
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SITE = "https://k-health365.com"
ALLOWED_POST_ID = 6148
START = "<!-- KHEALTH365_AFFILIATE_CARDS_START -->"
END = "<!-- KHEALTH365_AFFILIATE_CARDS_END -->"
CATALOG = Path("config/affiliate/k-health365-products.json")
OUT = Path("output")
DISCLOSURE = "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."

def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")

def request(url: str, method: str = "GET", payload: dict | None = None, auth: str | None = None):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if auth:
        headers["Authorization"] = "Basic " + auth
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            raw = response.read()
            return json.loads(raw.decode()) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read(1200).decode("utf-8", "replace")
        fail(f"WordPress API returned HTTP {exc.code}: {detail}")
    except Exception as exc:
        fail(f"Request failed: {exc}")

def resolve_product_image(affiliate_url: str) -> str:
    """Resolve the actual product image from the Coupang affiliate destination page."""
    req = urllib.request.Request(affiliate_url, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml"
    })
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            page_url = response.geturl()
            page = response.read(3_000_000).decode("utf-8", "replace")
    except Exception as exc:
        fail(f"Could not resolve Coupang affiliate destination {affiliate_url}: {exc}")
    candidates = []
    for pattern in (
        r'<meta[^>]+(?:property|name)="og:image"[^>]+content="([^"]+)',
        r'<meta[^>]+content="([^"]+)"[^>]+(?:property|name)="og:image"',
        r'<meta[^>]+(?:name|property)="twitter:image"[^>]+content="([^"]+)',
        r"(https?://[^\\"']+\\.(?:jpg|jpeg|png|webp)(?:\\?[^\\"']*)?)"
    ):        candidates.extend(re.findall(pattern, page, flags=re.I))
    for candidate in candidates:
        if isinstance(candidate, tuple):
            candidate = candidate[-1]
        image_url = html.unescape(candidate).replace("\\/", "/")
        image_url = urllib.parse.urljoin(page_url, image_url)
        parsed = urllib.parse.urlparse(image_url)
        if parsed.scheme != "https" or not any(parsed.path.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp")):
            continue
        try:
            check = urllib.request.Request(image_url, headers={"User-Agent": "Mozilla/5.0"}, method="GET")
            with urllib.request.urlopen(check, timeout=20) as img:
                if img.status == 200 and img.headers.get("Content-Type", "").lower().startswith("image/"):
                    return image_url
        except Exception:
            continue
    fail(f"No verified product image found on Coupang destination: {affiliate_url}")


def main() -> None:
    post_id = int(os.getenv("POST_ID", "6148"))
    if post_id != ALLOWED_POST_ID:
        fail(f"This pilot is locked to post {ALLOWED_POST_ID}; received {post_id}.")
    lo, hi = int(os.getenv("MIN_ITEMS", "5")), int(os.getenv("MAX_ITEMS", "10"))
    if not (5 <= lo <= hi <= 10):
        fail("Choose a valid range: 5 <= min_items <= max_items <= 10.")
    mode = os.getenv("MODE", "preview")
    if mode not in {"preview", "apply"}:
        fail("MODE must be preview or apply.")

    products = json.loads(CATALOG.read_text(encoding="utf-8"))
    eligible = []
    for p in products:
        if not p.get("enabled", False):
            continue
        if not all(p.get(k) for k in ("title", "url", "relevance")):
            continue
        u = urllib.parse.urlparse(p["url"])
        img = urllib.parse.urlparse(p["image_url"])
        if u.scheme != "https" or img.scheme != "https":
            continue
        if not p.get("affiliate_confirmed", False):
            continue
        p["image_url"] = resolve_product_image(p["url"])\n        eligible.append(p)
    if len(eligible) < lo:
        fail(f"Only {len(eligible)} fully verified products are enabled; need at least {lo}. "
             "Each enabled item needs a verified affiliate URL, real product image URL, title, and relevance.")

    # Use the title and body of the target post to rank relevant candidates.
    site = os.getenv("WP_SITE_URL", SITE).rstrip("/")
    user, app_password = os.getenv("WP_USER", ""), os.getenv("WP_APP_PASSWORD", "")
    if not user or not app_password:
        fail("Missing GitHub Secrets KHEALTH365_WP_USER or KHEALTH365_WP_APP_PASSWORD.")
    import base64
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    post = request(f"{site}/wp-json/wp/v2/posts/{post_id}?context=edit", auth=auth)
    title = html.unescape(re.sub("<[^>]+>", " ", post.get("title", {}).get("rendered", "")))
    content = post.get("content", {}).get("raw")
    if content is None:
        fail("WordPress did not return editable raw post content; check application-password permissions.")
    pool = [p for p in eligible if any(w.lower() in (title + " " + p["relevance"]).lower()
            for w in p.get("keywords", []))]
    if len(pool) < lo:
        pool = eligible
    count = random.randint(lo, hi)
    count = min(count, len(pool))
    chosen = random.sample(pool, count)

    cards = [START, '<section class="khealth-affiliate-products" aria-label="관련 상품 추천">',
             '<h2>관련 상품 추천</h2>',
             f'<p class="khealth-affiliate-disclosure">{html.escape(DISCLOSURE)}</p>',
             '<div class="khealth-affiliate-grid">']
    for p in chosen:
        cards.append(
            '<article class="khealth-affiliate-card">'
            f'<a href="{html.escape(p["url"], quote=True)}" target="_blank" rel="sponsored nofollow noopener">'
            f'<img src="{html.escape(p["image_url"], quote=True)}" alt="{html.escape(p["title"], quote=True)}" loading="lazy" />'
            f'<h3>{html.escape(p["title"])}</h3><span class="khealth-affiliate-button">쿠팡에서 상품 확인하기</span></a>'
            '</article>'
        )
    cards += ['</div></section>', END]
    block = "\n".join(cards)
    if START in content and END in content:
        before, remainder = content.split(START, 1)
        # Remove the earlier unmarked pilot block left by the first manual insertion.
        before = re.sub(
            r'\\s*<section class="khealth-affiliate-products" aria-label="관련 상품 추천">.*?</section>\\s*        content = content.rstrip() + "\n\n" + block

    OUT.mkdir(exist_ok=True)
    report = {
        "site": site, "post_id": post_id, "post_title": title, "mode": mode,
        "selected_count": len(chosen),
        "products": [{"title": p["title"], "url": p["url"], "image_url": p["image_url"]} for p in chosen],
        "note": "Preview does not modify WordPress." if mode == "preview" else "WordPress content update requested."
    }
    (OUT / f"khealth365-affiliate-{post_id}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / f"khealth365-affiliate-{post_id}.html").write_text(block, encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if mode == "apply":
        result = request(f"{site}/wp-json/wp/v2/posts/{post_id}", "POST",
                         {"content": content}, auth=auth)
        if result.get("id") != post_id:
            fail("Update response did not confirm the expected post ID.")
        verify = request(f"{site}/wp-json/wp/v2/posts/{post_id}?context=edit", auth=auth)
        raw = verify.get("content", {}).get("raw", "")
        if START not in raw or END not in raw:
            fail("Post update could not be verified after write.")
        print(f"VERIFIED: updated post {post_id}; {len(chosen)} product cards present.")
    else:
        print("PREVIEW ONLY: WordPress was not modified.")

if __name__ == "__main__":
    main()
,
            '',
            before,
            count=1,
            flags=re.S
        )
        content = before + block + remainder.split(END, 1)[1]
    else:
        content = content.rstrip() + "\n\n" + block

    OUT.mkdir(exist_ok=True)
    report = {
        "site": site, "post_id": post_id, "post_title": title, "mode": mode,
        "selected_count": len(chosen),
        "products": [{"title": p["title"], "url": p["url"], "image_url": p["image_url"]} for p in chosen],
        "note": "Preview does not modify WordPress." if mode == "preview" else "WordPress content update requested."
    }
    (OUT / f"khealth365-affiliate-{post_id}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / f"khealth365-affiliate-{post_id}.html").write_text(block, encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if mode == "apply":
        result = request(f"{site}/wp-json/wp/v2/posts/{post_id}", "POST",
                         {"content": content}, auth=auth)
        if result.get("id") != post_id:
            fail("Update response did not confirm the expected post ID.")
        verify = request(f"{site}/wp-json/wp/v2/posts/{post_id}?context=edit", auth=auth)
        raw = verify.get("content", {}).get("raw", "")
        if START not in raw or END not in raw:
            fail("Post update could not be verified after write.")
        print(f"VERIFIED: updated post {post_id}; {len(chosen)} product cards present.")
    else:
        print("PREVIEW ONLY: WordPress was not modified.")

if __name__ == "__main__":
    main()
