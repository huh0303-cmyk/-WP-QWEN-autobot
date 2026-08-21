#!/usr/bin/env python3
"""Read-only structural audit for the two newspaper sites."""
from __future__ import annotations
import argparse, json, re
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config" / "newsrooms.json").read_text(encoding="utf-8"))
UA = "WP-Newsroom-Audit/1.0 (+editorial quality audit)"

def get(url: str):
    r = requests.get(url, timeout=25, headers={"User-Agent": UA})
    r.raise_for_status()
    return r

def api(site: str, path: str, **params):
    return get(f"https://{site}/wp-json/wp/v2/{path}?" + requests.compat.urlencode(params)).json()

def audit(site: str) -> dict:
    cfg = CONFIG["sites"][site]
    html = get(f"https://{site}/").text
    cats = api(site, "categories", per_page=100, _fields="name,slug,count")
    posts = api(site, "posts", per_page=10, status="publish", _embed=1)
    pages = api(site, "pages", per_page=100, status="publish", _fields="title,slug,status")
    expected_cats = {x["slug"] for x in cfg["categories"]}
    expected_pages = {x["slug"] for x in cfg["editorial_pages"]}
    cat_slugs = {x["slug"] for x in cats}
    page_slugs = {x["slug"] for x in pages}
    theme = "unknown"
    m = re.search(r"/wp-content/themes/([^/'?]+)", html)
    if m: theme = m.group(1)
    missing_featured, weak_alt = [], []
    for p in posts:
        media = p.get("_embedded", {}).get("wp:featuredmedia", [])
        if not media:
            missing_featured.append(p["link"])
            continue
        alt = (media[0].get("alt_text") or "").strip()
        if len(alt) < 12:
            weak_alt.append({"post": p["link"], "alt": alt})
    checks = {
        "publishing_disabled_in_config": CONFIG["publishing_enabled"] is False,
        "language_matches": f'lang="{cfg["language"]}"' in html,
        "target_theme_active": theme == CONFIG["shared"]["theme_target"],
        "categories_complete": not (expected_cats - cat_slugs),
        "editorial_pages_complete": not (expected_pages - page_slugs),
        "recent_posts_have_featured_image": not missing_featured,
        "recent_featured_images_have_descriptive_alt": not weak_alt,
        "homepage_has_single_h1": len(re.findall(r"<h1\b", html, re.I)) == 1,
        "canonical_present": 'rel="canonical"' in html or "rel='canonical'" in html,
        "indexable": "noindex" not in html.lower(),
    }
    return {
        "site": site, "audited_at": datetime.now(timezone.utc).isoformat(),
        "theme_detected": theme, "checks": checks,
        "missing_categories": sorted(expected_cats-cat_slugs),
        "missing_editorial_pages": sorted(expected_pages-page_slugs),
        "recent_posts_without_featured_image": missing_featured,
        "recent_posts_with_weak_alt": weak_alt,
        "pass": all(checks.values())
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--site", choices=["ALL", *CONFIG["sites"]], default="ALL")
    ap.add_argument("--output", default="newsroom_audit.json")
    args=ap.parse_args()
    sites=list(CONFIG["sites"]) if args.site=="ALL" else [args.site]
    result={"schema":1,"audits":[audit(s) for s in sites]}
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(0 if all(x["pass"] for x in result["audits"]) else 2)

if __name__=="__main__":
    main()
