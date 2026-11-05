#!/usr/bin/env python3
"""Pilot the three-partner logo banner on one existing K-Health365 post."""
import os, re, json, sys
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from automation_hub.coupang_partners import (
    render_header, load_header_buttons, HEADER_START, HEADER_END
)

SITE = "https://k-health365.com"
POST_ID = int(os.getenv("POST_ID", "6987"))
USER = os.getenv("WP_USER", "huh0303@gmail.com").strip()
PASSWORD = os.getenv("KHEALTH365COM", "").strip()
MODE = os.getenv("MODE", "apply").strip().lower()
REPORT = ROOT / "reports/khealth365-three-partner-banner-pilot.json"
UA = {"User-Agent": "KHealth365-Affiliate-Banner-Pilot/1.0"}

def req(session, method, url, **kwargs):
    r = session.request(method, url, timeout=45, **kwargs)
    if not r.ok:
        raise RuntimeError(f"HTTP {r.status_code} at {url}: {r.text[:300]}")
    return r

def main():
    if not PASSWORD:
        raise RuntimeError("GitHub Secret KHEALTH365COM is empty.")
    if MODE not in ("preview", "apply"):
        raise RuntimeError("MODE must be preview or apply.")

    header_config = load_header_buttons("wp_khealth365")
    if not header_config:
        raise RuntimeError("Three partner tracking URLs are not eligible for banner rendering.")

    # Check that all three brand image assets are reachable before changing WordPress.
    from automation_hub.coupang_partners import LOGOS
    image_checks = {}
    for provider, url in LOGOS.items():
        r = requests.get(url, headers=UA, timeout=25, allow_redirects=True, stream=True)
        ctype = r.headers.get("Content-Type", "").lower()
        image_checks[provider] = {"status": r.status_code, "content_type": ctype}
        r.close()
        if r.status_code != 200 or not ctype.startswith("image/"):
            raise RuntimeError(f"Logo asset failed validation: {provider} HTTP {image_checks[provider]['status']} {ctype}")

    session = requests.Session()
    session.auth = (USER, PASSWORD)
    session.headers.update(UA)
    me = req(session, "GET", SITE + "/wp-json/wp/v2/users/me", params={"context":"edit","_fields":"id,name"}).json()
    post_url = SITE + f"/wp-json/wp/v2/posts/{POST_ID}"
    post = req(session, "GET", post_url, params={"context":"edit","_fields":"id,link,title,content,status"}).json()
    if post.get("status") != "publish":
        raise RuntimeError(f"Pilot post is not published: status={post.get('status')}")
    raw = post.get("content", {}).get("raw")
    if raw is None:
        raise RuntimeError("WordPress did not return editable raw post content.")

    banner = render_header("wp_khealth365")
    clean = re.sub(re.escape(HEADER_START) + r".*?" + re.escape(HEADER_END), "", raw, flags=re.S).lstrip()
    updated = banner + "\n" + clean
    report = {
        "site": SITE, "post_id": POST_ID, "post_url": post.get("link"),
        "mode": MODE, "wordpress_user_id": me.get("id"),
        "logo_asset_checks": image_checks,
        "tracking_links": [x.get("affiliate_url") for x in header_config.get("buttons", [])],
        "already_had_banner": HEADER_START in raw and HEADER_END in raw,
        "updated": False, "verified": False,
    }
    if MODE == "apply" and updated != raw:
        req(session, "POST", post_url, json={"content": updated})
        check = req(session, "GET", post_url, params={"context":"edit","_fields":"id,link,content,status"}).json()
        verified_raw = check.get("content", {}).get("raw", "")
        if HEADER_START not in verified_raw or HEADER_END not in verified_raw:
            raise RuntimeError("WordPress read-back did not contain banner markers.")
        for link in report["tracking_links"]:
            if link not in verified_raw:
                raise RuntimeError("A partner tracking URL is missing from saved banner.")
        public = req(session, "GET", post_url, params={"_fields":"id,link,content,status"}).json()
        rendered = public.get("content", {}).get("rendered", "")
        if HEADER_START not in rendered or HEADER_END not in rendered:
            raise RuntimeError("Public REST rendering did not contain the banner.")
        report["updated"] = True
        report["verified"] = True
    elif MODE == "preview":
        report["preview_ready"] = True
    else:
        report["already_had_banner"] = True
        report["verified"] = HEADER_START in raw and HEADER_END in raw

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    if MODE == "apply" and not report["verified"]:
        raise RuntimeError("Banner apply did not pass verification.")

if __name__ == "__main__":
    main()
