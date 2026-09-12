#!/usr/bin/env python3
"""User-approved: k-health365.com has 42 orphan posts (zero incoming
internal links) out of 285. The Code Snippets REST endpoint is blocked by
a host-level WAF (confirmed: raw HTML 403, not a WP permission error), so
instead of a dynamic related-posts filter, directly edit real donor posts'
content to add a permanent link to each orphan - using the standard
/wp-json/wp/v2/posts endpoint, which is not blocked."""
import html
import re
import time
import os
import requests
from requests.auth import HTTPBasicAuth

USER = "huh0303@gmail.com"
PW = os.environ["KHEALTH365COM"]
BASE = "https://k-health365.com/wp-json/wp/v2"
AUTH = HTTPBasicAuth(USER, PW)
LINK_MARK = "<!-- orphan-fix-2026-09-12 -->"


def fetch_all_posts():
    posts, page = [], 1
    while True:
        r = requests.get(f"{BASE}/posts", params={
            "per_page": 100, "page": page, "status": "publish",
            "_fields": "id,link,title,content,categories",
        }, timeout=30)
        if r.status_code == 400:
            break
        batch = r.json()
        if not isinstance(batch, list) or not batch:
            break
        posts.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return posts


def find_orphans(posts):
    permalink_to_id = {p["link"].rstrip("/"): p["id"] for p in posts}
    incoming = {p["id"]: 0 for p in posts}
    for p in posts:
        content = p["content"]["rendered"]
        for href in re.findall(r'href=["\']([^"\']+)["\']', content):
            clean = href.split("?")[0].split("#")[0].rstrip("/")
            target_id = permalink_to_id.get(clean)
            if target_id and target_id != p["id"]:
                incoming[target_id] += 1
    return [p for p in posts if incoming[p["id"]] == 0]


def pick_donor(orphan, posts, used_donor_ids):
    orphan_cats = set(orphan.get("categories", []))
    candidates = [
        p for p in posts
        if p["id"] != orphan["id"]
        and p["id"] not in used_donor_ids
        and LINK_MARK not in p["content"]["rendered"]
        and set(p.get("categories", [])) & orphan_cats
    ]
    if not candidates:
        candidates = [p for p in posts if p["id"] != orphan["id"] and p["id"] not in used_donor_ids
                      and LINK_MARK not in p["content"]["rendered"]]
    return candidates[0] if candidates else None


posts = fetch_all_posts()
print("total posts:", len(posts))
orphans = find_orphans(posts)
print("orphan posts found:", len(orphans))

used_donor_ids = set()
fixed, failed = 0, []
for orphan in orphans:
    donor = pick_donor(orphan, posts, used_donor_ids)
    if not donor:
        failed.append(orphan["id"])
        continue
    used_donor_ids.add(donor["id"])
    title = html.unescape(re.sub("<[^>]+>", "", orphan["title"]["rendered"]))
    link_block = (
        f'\n{LINK_MARK}<p style="margin-top:24px;"><strong>함께 보면 좋은 글:</strong> '
        f'<a href="{orphan["link"]}">{title}</a></p>'
    )
    new_content = donor["content"]["rendered"] + link_block
    r = requests.post(f"{BASE}/posts/{donor['id']}", auth=AUTH, json={"content": new_content}, timeout=30)
    ok = r.status_code == 200
    print(f"orphan {orphan['id']} <- linked from donor {donor['id']}: {'OK' if ok else 'FAIL ' + str(r.status_code)}")
    if ok:
        fixed += 1
    else:
        failed.append(orphan["id"])
    time.sleep(0.3)

print(f"\nSUMMARY: fixed={fixed} failed={len(failed)} failed_ids={failed}")
