#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wp_consolidate_categories.py
1-site-1-category focus strategy execution script, generalized via env vars
so it can target any site (generalizes the k-health365.com-only pattern in
reorganize_categories.py).

Behavior:
  1) Move every post in WP_MERGE_CATEGORY_SLUGS (comma-separated) into
     WP_KEEP_CATEGORY_SLUG.
  2) Delete the now-empty merged categories.
  3) If WP_PRIVATE_POST_IDS (comma-separated, optional) is set, flip those
     posts to status=private (never deletes, always reversible).
  4) Print final category list and verification summary.

Safety: never deletes a post (only empty category terms). If any given slug
does not exist, abort before making any change.
"""
import os
import sys
import requests

SITE_URL = os.environ["WP_SITE_URL"].rstrip("/")
WP_USER = os.environ.get("WP_USER", "huh0303@gmail.com")
WP_PASS = os.environ["WP_APP_PASSWORD"]
KEEP_SLUG = os.environ["WP_KEEP_CATEGORY_SLUG"].strip()
MERGE_SLUGS = [s.strip() for s in os.environ.get("WP_MERGE_CATEGORY_SLUGS", "").split(",") if s.strip()]
PRIVATE_IDS = [int(x) for x in os.environ.get("WP_PRIVATE_POST_IDS", "").split(",") if x.strip()]

AUTH = requests.auth.HTTPBasicAuth(WP_USER, WP_PASS)
_LOG = []


def log(m=""):
    print(m)
    _LOG.append(str(m))


def get_categories():
    r = requests.get(f"{SITE_URL}/wp-json/wp/v2/categories",
                      auth=AUTH, params={"per_page": 100}, timeout=20)
    r.raise_for_status()
    return {c["slug"]: c for c in r.json()}


def get_posts_in_category(cat_id):
    out = []
    page = 1
    while True:
        r = requests.get(f"{SITE_URL}/wp-json/wp/v2/posts", auth=AUTH,
                          params={"categories": cat_id, "per_page": 100, "page": page,
                                  "status": "publish,private,draft,pending,future",
                                  "_fields": "id,categories,title"},
                          timeout=20)
        if r.status_code == 400 and "rest_post_invalid_page_number" in r.text:
            break
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        out.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return out


def set_post_categories(post_id, cat_ids):
    r = requests.post(f"{SITE_URL}/wp-json/wp/v2/posts/{post_id}", auth=AUTH,
                       json={"categories": cat_ids}, timeout=20)
    ok = r.status_code in (200, 201)
    log(f"  {'OK' if ok else 'FAIL'} post {post_id} -> categories={cat_ids} (status={r.status_code})")
    return ok


def set_post_status(post_id, status):
    r = requests.post(f"{SITE_URL}/wp-json/wp/v2/posts/{post_id}", auth=AUTH,
                       json={"status": status}, timeout=20)
    ok = r.status_code in (200, 201)
    log(f"  {'OK' if ok else 'FAIL'} post {post_id} -> status={status} (status_code={r.status_code})")
    return ok


def delete_category(cat_id):
    r = requests.delete(f"{SITE_URL}/wp-json/wp/v2/categories/{cat_id}", auth=AUTH,
                         params={"force": "true"}, timeout=20)
    ok = r.status_code in (200, 201)
    log(f"  {'OK' if ok else 'FAIL'} delete empty category {cat_id} (status={r.status_code})")
    return ok


def main():
    log(f"=== {SITE_URL} category consolidation ===")
    log(f"keep category: {KEEP_SLUG}")
    log(f"merge categories: {MERGE_SLUGS}")
    log(f"private posts: {PRIVATE_IDS or 'none'}")

    cats = get_categories()
    missing = [s for s in [KEEP_SLUG] + MERGE_SLUGS if s not in cats]
    if missing:
        log(f"ABORT: unknown category slug(s)={missing}")
        sys.exit(1)

    keep_id = cats[KEEP_SLUG]["id"]
    log(f"\nkeep category id={keep_id} ({cats[KEEP_SLUG]['name']})")

    total_moved = 0
    for slug in MERGE_SLUGS:
        merge_id = cats[slug]["id"]
        posts = get_posts_in_category(merge_id)
        log(f"\n-- {slug} (id={merge_id}): moving {len(posts)} post(s) --")
        for p in posts:
            new_cats = sorted(set(p.get("categories", [])) - {merge_id} | {keep_id})
            if set_post_categories(p["id"], new_cats):
                total_moved += 1
        remaining = get_posts_in_category(merge_id)
        if remaining:
            log(f"  WARNING: {slug} still has {len(remaining)} post(s) -> category NOT deleted")
        else:
            delete_category(merge_id)

    if PRIVATE_IDS:
        log(f"\n-- setting {len(PRIVATE_IDS)} post(s) to private --")
        for pid in PRIVATE_IDS:
            set_post_status(pid, "private")

    final_cats = get_categories()
    log("\n=== final category list ===")
    for slug, c in sorted(final_cats.items(), key=lambda kv: -kv[1].get("count", 0)):
        log(f"  {c['name']} (slug={slug}, count={c.get('count')})")

    log(f"\nDONE: moved {total_moved} post(s), set private {len(PRIVATE_IDS)} post(s)")


if __name__ == "__main__":
    main()
