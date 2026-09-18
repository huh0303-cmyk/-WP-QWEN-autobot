#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wp_consolidate_categories.py
1-site-1-category focus strategy execution script, generalized via env vars
so it can target any site (generalizes the k-health365.com-only pattern in
reorganize_categories.py).

Behavior:
  1) Validate that WP_KEEP_CATEGORY_SLUG, every slug in WP_MERGE_CATEGORY_SLUGS,
     and every id in WP_PRIVATE_POST_IDS actually exist on the site. Abort
     before changing anything if any of them do not.
  2) Move every post in the merge categories into the keep category.
  3) Delete a merge category ONLY if every post in it was moved successfully
     with zero API errors. If even one move fails, that category (and
     everything after it) is left untouched and the run ends in failure.
  4) If WP_PRIVATE_POST_IDS is set and no error occurred above, flip those
     posts to status=private (never deletes, always reversible).
  5) Print final category list and a verification summary.

WP_DRY_RUN=true (default): does every read/validation step above and prints
exactly what it WOULD change, but issues no POST/DELETE request at all.

Safety:
  - Never deletes a post. Only ever deletes an emptied category term.
  - Any missing slug/post id aborts before any write.
  - A single API failure during the move phase stops all further
    destructive steps (no more category deletes, no status changes) for
    the rest of the run.
  - WP_APP_PASSWORD is never logged or printed anywhere, including in
    request-error text (only status codes and short reason snippets are
    logged, and those are scrubbed for the word "password" defensively).
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
DRY_RUN = os.environ.get("WP_DRY_RUN", "true").strip().lower() not in ("false", "0", "no")

AUTH = requests.auth.HTTPBasicAuth(WP_USER, WP_PASS)
ALL_STATUSES = ["publish", "private", "draft", "pending", "future"]


def log(m=""):
    text = str(m)
    if WP_PASS and WP_PASS in text:
        text = text.replace(WP_PASS, "***REDACTED***")
    print(text)


def get_categories():
    r = requests.get(f"{SITE_URL}/wp-json/wp/v2/categories",
                      auth=AUTH, params={"per_page": 100}, timeout=20)
    r.raise_for_status()
    return {c["slug"]: c for c in r.json()}


def get_posts_in_category(cat_id):
    def _fetch(status_param):
        out, page = [], 1
        while True:
            r = requests.get(f"{SITE_URL}/wp-json/wp/v2/posts", auth=AUTH,
                              params={"categories": cat_id, "per_page": 100, "page": page,
                                      "status": status_param,
                                      "_fields": "id,categories,title,status"},
                              timeout=20)
            if r.status_code == 400 and "rest_post_invalid_page_number" in r.text:
                break
            if r.status_code == 400:
                return None
            r.raise_for_status()
            batch = r.json()
            if not batch:
                break
            out.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        return out

    combined = _fetch(",".join(ALL_STATUSES))
    if combined is not None:
        return combined

    log(f"  note: combined status filter rejected (HTTP 400) for category {cat_id}; "
        f"falling back to per-status queries")
    merged, seen_ids = [], set()
    for status in ALL_STATUSES:
        rows = _fetch(status) or []
        for row in rows:
            if row["id"] not in seen_ids:
                seen_ids.add(row["id"])
                merged.append(row)
    return merged


def get_post(post_id):
    r = requests.get(f"{SITE_URL}/wp-json/wp/v2/posts/{post_id}", auth=AUTH,
                      params={"_fields": "id,categories,title,status", "context": "edit"},
                      timeout=20)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


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
    log(f"mode: {'DRY RUN (no changes will be made)' if DRY_RUN else 'LIVE RUN'}")
    log(f"keep category: {KEEP_SLUG}")
    log(f"merge categories: {MERGE_SLUGS}")
    log(f"private posts: {PRIVATE_IDS or 'none'}")

    cats = get_categories()
    missing_cats = [s for s in [KEEP_SLUG] + MERGE_SLUGS if s not in cats]
    if missing_cats:
        log(f"\nABORT: unknown category slug(s)={missing_cats}. No changes made.")
        sys.exit(1)

    missing_posts = []
    post_rows = {}
    for pid in PRIVATE_IDS:
        row = get_post(pid)
        if row is None:
            missing_posts.append(pid)
        else:
            post_rows[pid] = row
    if missing_posts:
        log(f"\nABORT: post id(s) not found on this site={missing_posts}. No changes made.")
        sys.exit(1)

    keep_id = cats[KEEP_SLUG]["id"]
    log(f"\nverified OK: keep category id={keep_id} ({cats[KEEP_SLUG]['name']})")
    for slug in MERGE_SLUGS:
        log(f"verified OK: merge category '{slug}' id={cats[slug]['id']} count={cats[slug].get('count')}")
    for pid, row in post_rows.items():
        title = row.get("title", {})
        title = title.get("rendered", title) if isinstance(title, dict) else title
        log(f"verified OK: post {pid} exists, status={row.get('status')}, title={title!r}")

    had_error = False
    total_moved = 0
    categories_to_delete = []

    for slug in MERGE_SLUGS:
        merge_id = cats[slug]["id"]
        posts = get_posts_in_category(merge_id)
        log(f"\n-- {slug} (id={merge_id}): {len(posts)} post(s) currently in this category --")
        if had_error:
            log(f"  skipped: an earlier error already stopped destructive steps this run")
            continue
        category_ok = True
        for p in posts:
            new_cats = sorted(set(p.get("categories", [])) - {merge_id} | {keep_id})
            if DRY_RUN:
                log(f"  DRY RUN: would move post {p['id']} ({p.get('status')}) -> categories={new_cats}")
                total_moved += 1
            else:
                if set_post_categories(p["id"], new_cats):
                    total_moved += 1
                else:
                    category_ok = False
                    had_error = True
        if DRY_RUN:
            log(f"  DRY RUN: would then delete now-empty category '{slug}' (id={merge_id})")
            categories_to_delete.append((slug, merge_id))
        elif category_ok:
            remaining = get_posts_in_category(merge_id)
            if remaining:
                log(f"  WARNING: {slug} still has {len(remaining)} post(s) after moving -> category NOT deleted")
            else:
                categories_to_delete.append((slug, merge_id))
        else:
            log(f"  {slug}: one or more posts failed to move -> category NOT deleted, stopping further destructive steps")

    if not DRY_RUN and not had_error:
        for slug, merge_id in categories_to_delete:
            delete_category(merge_id)

    if PRIVATE_IDS:
        if had_error:
            log(f"\nskipped private-status step for {PRIVATE_IDS}: an earlier error stopped destructive steps this run")
        elif DRY_RUN:
            log(f"\nDRY RUN: would set {len(PRIVATE_IDS)} post(s) to private: {PRIVATE_IDS}")
        else:
            log(f"\n-- setting {len(PRIVATE_IDS)} post(s) to private --")
            for pid in PRIVATE_IDS:
                if not set_post_status(pid, "private"):
                    had_error = True

    final_cats = get_categories()
    log("\n=== category list (current live state) ===")
    for slug, c in sorted(final_cats.items(), key=lambda kv: -kv[1].get("count", 0)):
        log(f"  {c['name']} (slug={slug}, count={c.get('count')})")

    if DRY_RUN:
        log(f"\nDRY RUN DONE: would move {total_moved} post(s), "
            f"would delete {len(categories_to_delete)} empty categor(y/ies), "
            f"would set private {len(PRIVATE_IDS)} post(s). Nothing was changed.")
    else:
        log(f"\nDONE: moved {total_moved} post(s), "
            f"deleted {len(categories_to_delete) if not had_error else 0} categor(y/ies), "
            f"set private {0 if had_error else len(PRIVATE_IDS)} post(s).")
        if had_error:
            log("RESULT: FAILED partway -- see FAIL lines above. Re-run only after the underlying "
                "API error is understood; already-moved posts stay moved (safe/reversible), "
                "nothing else was force-changed.")
            sys.exit(1)


if __name__ == "__main__":
    main()
