#!/usr/bin/env python3
"""Repair recent newsroom posts using their recorded primary source domain."""
import os
import re
import requests

USER = "huh0303@gmail.com"
SITES = (
    ("https://koreanews365.com", "KOREANEWS365COM", {
        "sec.gov": "금융 (FINANCE)", "federalreserve.gov": "금융 (FINANCE)",
        "nasa.gov": "경제 (ECONOMY)", "globalvoices.org": "글로벌 (GLOBAL)",
        "voanews.com": "글로벌 (GLOBAL)", "war.gov": "국방 (MILITARY)",
    }),
    ("https://theseouljournal.com", "THESEOULJOURNALCOM", {
        "sec.gov": "Finance", "federalreserve.gov": "Finance", "nasa.gov": "Economy",
        "globalvoices.org": "Global", "voanews.com": "Global", "war.gov": "Military",
    }),
)


def main():
    target_site = os.getenv("TARGET_SITE_URL", "").rstrip("/")
    for site, secret, routes in SITES:
        if target_site and site != target_site:
            continue
        password = os.getenv(secret, "").strip()
        if not password:
            continue
        auth = (USER, password)
        categories = requests.get(
            f"{site}/wp-json/wp/v2/categories", auth=auth,
            params={"per_page": 100, "_fields": "id,name"}, timeout=20,
        ).json()
        by_name = {c["name"].strip().lower(): c["id"] for c in categories}
        posts = requests.get(
            f"{site}/wp-json/wp/v2/posts", auth=auth,
            params={"per_page": 20, "after": "2026-08-21T00:00:00", "status": "publish",
                    "_fields": "id,title,content,categories"}, timeout=20,
        ).json()
        for post in posts:
            html = post.get("content", {}).get("rendered", "")
            target = next((name for domain, name in routes.items() if domain in html.lower()), None)
            if not target:
                continue
            category_id = by_name.get(target.lower())
            if category_id and post.get("categories") != [category_id]:
                response = requests.post(
                    f"{site}/wp-json/wp/v2/posts/{post['id']}", auth=auth,
                    json={"categories": [category_id]}, timeout=20,
                )
                response.raise_for_status()
                title = re.sub(r"<[^>]+>", "", post.get("title", {}).get("rendered", ""))
                print(f"fixed {site} #{post['id']} -> {target}: {title}")


if __name__ == "__main__":
    main()
