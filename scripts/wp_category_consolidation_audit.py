#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wp_category_consolidation_audit.py
─────────────────────────────────────────────────────────────
General-purpose (reusable across all 25 regular WP sites) audit for the
"1 site = 1 core topic = 1 representative category" cleanup.

For one target domain, this script:
  1. Backs up every published WordPress Post (id, url, title, status,
     categories) BEFORE anything else runs.
  2. Backs up the current category list (id, name, slug, count).
  3. Loads the GSC-indexed-URL snapshot for that domain from
     config/gsc_indexed_snapshot/gsc_indexed_master_60.csv (the ONLY
     accepted ground truth for "is this actually indexed by Google" —
     never inferred, never called live from this script).
  4. Classifies every indexed URL into POST / PAGE / HOME / CATEGORY /
     TAG / AUTHOR / PAGINATION / ARCHIVE / OTHER.
  5. Matches indexed POST URLs to WordPress post IDs -> PROTECTED_INDEXED_POSTS.
  6. Computes PRIVATE_CANDIDATES = published posts NOT in that protected set.
  7. Computes a category-consolidation *recommendation only* (no category is
     created, deleted, renamed, or moved by this script).

Hard safety invariants (do not remove or weaken these):
  - DRY_RUN defaults to "true". In DRY_RUN mode this script NEVER sends a
    POST/PUT/PATCH/DELETE request to WordPress. Read-only GET calls only.
  - This script contains NO delete functionality for posts, ever.
  - Any domain in DENYLIST is refused outright, before any network call,
    regardless of DRY_RUN.
  - If even one GSC-classified POST URL fails to match a WordPress post ID,
    `safe_for_real_run` is set to False in the summary and the script will
    refuse to proceed to any write step even if DRY_RUN is later set false.
  - On any WordPress/API error while fetching posts/pages/categories, the
    run aborts immediately with status=API_ERROR and performs no writes.
  - Secrets (application passwords) are read from environment variables and
    are never printed or written to any output file.

Run only from GitHub Actions (or another runner not blocked by the
Hostinger WAF) — never call this against production from a local machine
whose IP the WAF blocks.
"""
from __future__ import annotations

import csv
import json
import os
import re
import socket
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit

import requests

# ── IPv4-forced DNS (mirrors scripts/prune_unindexed_all_sites_safe.py; some
#    Hostinger endpoints behave inconsistently over IPv6 from GH runners) ──
_original_getaddrinfo = socket.getaddrinfo


def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)


socket.getaddrinfo = _ipv4_getaddrinfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_registry import SITES  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GSC_SNAPSHOT_PATH = os.path.join(
    REPO_ROOT, "config", "gsc_indexed_snapshot", "gsc_indexed_master_60.csv"
)

# Domains this workflow may NEVER touch, in any mode.
DENYLIST = {"koreanews365.com", "theseouljournal.com"}

DEFAULT_REQUIRED_PAGE_SLUGS = {
    "about", "about-us",
    "contact", "contact-us",
    "privacy-policy", "privacy",
    "terms", "terms-of-service", "terms-and-conditions", "terms-conditions",
    "disclaimer",
}

UA = {"User-Agent": "Mozilla/5.0 (GitHubActions; WP-Category-Consolidation-Audit/1.0)"}
WP_USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"


def log(msg):
    print(msg, flush=True)


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def site_secret_key(domain):
    for site_url, env_key, _lifecycle in SITES:
        if site_url.replace("https://", "").rstrip("/") == domain:
            return env_key
    return None


def normalize_url(url):
    """Scheme+host lowercased, trailing slash stripped, query/fragment dropped."""
    if not url:
        return ""
    parts = urlsplit(url.strip())
    path = parts.path.rstrip("/")
    return f"{parts.scheme.lower()}://{parts.netloc.lower()}{path}"


def wp_get(url, params=None, auth=None, timeout=35):
    return requests.get(url, params=params or {}, auth=auth, headers=UA, timeout=timeout)


def fetch_all(site_url, endpoint, fields, auth=None, extra_params=None):
    """Paginate a WP REST collection endpoint until exhausted."""
    out = []
    page = 1
    params = {"per_page": 100, "_fields": ",".join(fields)}
    if extra_params:
        params.update(extra_params)
    while True:
        params["page"] = page
        r = wp_get(f"{site_url}/wp-json/wp/v2/{endpoint}", params=params, auth=auth)
        if r.status_code == 400 and "rest_post_invalid_page_number" in r.text:
            break
        if r.status_code != 200:
            raise RuntimeError(f"{endpoint} HTTP {r.status_code}: {r.text[:200]}")
        batch = r.json()
        if not batch:
            break
        out.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return out


def title_of(post):
    t = post.get("title") or ""
    return t.get("rendered", "") if isinstance(t, dict) else str(t)


def load_gsc_rows(domain):
    if not os.path.exists(GSC_SNAPSHOT_PATH):
        raise RuntimeError(f"GSC snapshot missing at {GSC_SNAPSHOT_PATH}")
    rows = []
    with open(GSC_SNAPSHOT_PATH, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("site", "").strip().lower() == domain:
                rows.append(row)
    return rows


def classify_url(url, domain, page_slugs):
    path = urlsplit(url).path.rstrip("/")
    if path == "":
        return "HOME"
    if re.match(r"^/page/\d+$", path):
        return "PAGINATION"
    if path.startswith("/category/"):
        return "CATEGORY"
    if path.startswith("/tag/"):
        return "TAG"
    if path.startswith("/author/"):
        return "AUTHOR"
    if re.match(r"^/\d{4}(/\d{2}(/\d{2})?)?$", path):
        return "ARCHIVE"
    slug = path.lstrip("/")
    if "/" not in slug and slug in page_slugs:
        return "PAGE"
    if "/" in slug:
        return "OTHER"
    return "POST"


TARGET_CATEGORY_ALIASES = {
    "korea jobs": ("korea-jobs", "korea jobs"),
}


def recommend_category(categories, target_name):
    """Return (recommendation dict). Never creates/renames anything."""
    target_lc = target_name.strip().lower()
    aliases = TARGET_CATEGORY_ALIASES.get(target_lc, (target_lc.replace(" ", "-"), target_lc))
    generic_job_words = ("job", "career", "employment", "korea-jobs")

    exact = [c for c in categories if c["slug"].lower() in aliases or c["name"].lower() in aliases]
    if exact:
        best = max(exact, key=lambda c: c.get("count", 0))
        return {
            "action": "KEEP_EXISTING",
            "name": best["name"],
            "slug": best["slug"],
            "id": best["id"],
            "reason": "exact name/slug match for target topic",
        }

    fuzzy = [
        c for c in categories
        if any(w in c["slug"].lower() or w in c["name"].lower() for w in generic_job_words)
        and c["slug"].lower() != "uncategorized"
    ]
    if fuzzy:
        best = max(fuzzy, key=lambda c: c.get("count", 0))
        return {
            "action": "KEEP_EXISTING",
            "name": best["name"],
            "slug": best["slug"],
            "id": best["id"],
            "reason": "fuzzy topical match — reuse instead of creating a new category",
        }

    return {
        "action": "WOULD_CREATE_NEW",
        "name": target_name,
        "slug": target_name.lower().replace(" ", "-"),
        "id": None,
        "reason": "no existing category represents this topic; NOT created in this run",
    }


def write_csv(path, rows, fieldnames):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def main():
    domain = os.getenv("SITE_DOMAIN", "").strip().lower()
    dry_run = os.getenv("DRY_RUN", "true").strip().lower() != "false"
    target_category_name = os.getenv("TARGET_CATEGORY_NAME", "Korea Jobs").strip()
    out_dir = os.getenv("OUTPUT_DIR", ".").strip() or "."
    run_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    summary = {
        "domain": domain,
        "dry_run": dry_run,
        "generated_at": now_iso(),
        "status": "STARTED",
        "api_errors": [],
    }

    def abort(status, message):
        summary["status"] = status
        summary["message"] = message
        summary_path = os.path.join(out_dir, f"summary_{domain or 'unknown'}.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        log(f"[ABORT] {status}: {message}")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        sys.exit(1)

    if not domain:
        abort("BAD_INPUT", "SITE_DOMAIN env var is required")

    if domain in DENYLIST:
        abort("DENYLISTED", f"{domain} is on the permanent denylist — refusing to run")

    if not dry_run:
        abort("REFUSED", "This script only supports DRY_RUN=true right now; real Private "
                          "conversion is intentionally not implemented yet")

    secret_key = site_secret_key(domain)
    if not secret_key:
        abort("BAD_INPUT", f"{domain} not found in scripts/site_registry.py")

    app_password = os.getenv(secret_key, "").strip()
    if not app_password:
        abort("SKIP_NO_SECRET", f"secret {secret_key} not set in this run's environment")

    site_url = f"https://{domain}"
    auth = (WP_USER, app_password)

    # 1) Fetch + immediately back up published posts.
    try:
        posts = fetch_all(
            site_url, "posts",
            fields=["id", "link", "title", "status", "categories"],
            auth=auth, extra_params={"status": "publish"},
        )
    except Exception as e:
        summary["api_errors"].append(f"posts fetch failed: {e}")
        abort("API_ERROR", f"failed to fetch posts for {domain}: {e}")

    backup_posts = [
        {
            "id": p["id"],
            "url": p.get("link"),
            "title": title_of(p),
            "status": p.get("status"),
            "categories": p.get("categories", []),
        }
        for p in posts
    ]
    backup_path = os.path.join(out_dir, f"backup_posts_{domain}_{run_stamp}.json")
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(backup_posts, f, ensure_ascii=False, indent=2)
    log(f"Backed up {len(backup_posts)} published posts -> {backup_path}")

    # 2) Fetch pages (to know real required-page slugs) and categories.
    try:
        pages = fetch_all(
            site_url, "pages", fields=["id", "link", "slug", "title", "status"],
            auth=auth, extra_params={"status": "publish"},
        )
    except Exception as e:
        summary["api_errors"].append(f"pages fetch failed: {e}")
        abort("API_ERROR", f"failed to fetch pages for {domain}: {e}")

    page_slugs = set(DEFAULT_REQUIRED_PAGE_SLUGS)
    page_slugs.update(p.get("slug", "").lower() for p in pages if p.get("slug"))

    try:
        categories = fetch_all(
            site_url, "categories", fields=["id", "name", "slug", "count"],
        )
    except Exception as e:
        summary["api_errors"].append(f"categories fetch failed: {e}")
        abort("API_ERROR", f"failed to fetch categories for {domain}: {e}")

    categories_backup_path = os.path.join(out_dir, f"backup_categories_{domain}_{run_stamp}.json")
    with open(categories_backup_path, "w", encoding="utf-8") as f:
        json.dump(categories, f, ensure_ascii=False, indent=2)

    # 3) Load GSC-indexed snapshot (sole ground truth) for this domain.
    gsc_rows = load_gsc_rows(domain)
    if not gsc_rows:
        abort("NO_GSC_DATA", f"no rows for site=={domain} in {GSC_SNAPSHOT_PATH}")

    # 4) Classify every indexed URL.
    buckets = {
        "HOME": [], "PAGE": [], "CATEGORY": [], "TAG": [], "AUTHOR": [],
        "PAGINATION": [], "ARCHIVE": [], "OTHER": [], "POST": [],
    }
    for row in gsc_rows:
        cls = classify_url(row["url"], domain, page_slugs)
        buckets[cls].append(row["url"])

    # 5) Match POST-classified URLs to WordPress post IDs.
    posts_by_norm_url = {normalize_url(p["url"]): p for p in backup_posts}
    protected = []
    unmatched = []
    for url in buckets["POST"]:
        match = posts_by_norm_url.get(normalize_url(url))
        if match:
            protected.append(match)
        else:
            unmatched.append(url)

    protected_ids = {p["id"] for p in protected}
    safe_for_real_run = len(unmatched) == 0

    # 6) Private candidates = published posts not in the protected set.
    private_candidates = [p for p in backup_posts if p["id"] not in protected_ids]

    # 7) Category recommendation (calculation only).
    recommendation = recommend_category(categories, target_category_name)
    target_cat_id = recommendation.get("id")

    protected_categories_ids = set()
    for p in protected:
        protected_categories_ids.update(p.get("categories", []))
    would_move_count = 0
    if target_cat_id is not None:
        for p in protected:
            if target_cat_id not in (p.get("categories") or []):
                would_move_count += 1
    other_categories_to_consolidate = max(0, len(categories) - 1)

    # ── write output artifacts ──
    protected_csv = os.path.join(out_dir, f"protected_indexed_posts_{domain}.csv")
    private_csv = os.path.join(out_dir, f"private_candidates_{domain}.csv")
    write_csv(
        protected_csv,
        [{"id": p["id"], "url": p["url"], "title": p["title"], "categories": p["categories"]} for p in protected],
        fieldnames=["id", "url", "title", "categories"],
    )
    write_csv(
        private_csv,
        [{"id": p["id"], "url": p["url"], "title": p["title"], "status": p["status"], "categories": p["categories"]}
         for p in private_candidates],
        fieldnames=["id", "url", "title", "status", "categories"],
    )

    system_url_count = sum(len(v) for k, v in buckets.items() if k != "POST")

    summary.update({
        "status": "DRY_RUN_OK",
        "total_publish_posts": len(backup_posts),
        "gsc_indexed_url_count": len(gsc_rows),
        "gsc_url_breakdown": {k: len(v) for k, v in buckets.items()},
        "actual_post_url_count": len(buckets["POST"]),
        "post_id_match_success_count": len(protected),
        "system_page_archive_url_count": system_url_count,
        "protected_indexed_posts_count": len(protected),
        "private_candidates_count": len(private_candidates),
        "current_category_count": len(categories),
        "categories": [{"id": c["id"], "name": c["name"], "slug": c["slug"], "count": c.get("count", 0)} for c in categories],
        "category_recommendation": recommendation,
        "categories_pending_consolidation_count": other_categories_to_consolidate,
        "protected_posts_that_would_move_to_target_category": would_move_count,
        "unmatched_gsc_post_urls": unmatched,
        "safe_for_real_run": safe_for_real_run,
        "backup_posts_file": backup_path,
        "backup_categories_file": categories_backup_path,
        "protected_csv": protected_csv,
        "private_csv": private_csv,
        "delete_performed": False,
        "wp_write_requests_sent": 0,
    })

    summary_path = os.path.join(out_dir, f"summary_{domain}.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not safe_for_real_run:
        log(f"[WARNING] {len(unmatched)} GSC POST URL(s) did not match a WordPress post ID. "
            f"Any future real (non-dry-run) run for {domain} must stay blocked until this is resolved.")


if __name__ == "__main__":
    main()
