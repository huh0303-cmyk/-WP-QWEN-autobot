"""Ensure The Seoul Journal uses the same ten editorial desks as Koreanews365."""
from __future__ import annotations
import os
import requests

SITE = "https://theseouljournal.com"
USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
PASSWORD = os.getenv("THESEOULJOURNALCOM", "").strip()
CATEGORIES = [
    ("Politics", "politics"), ("Economy", "economy"), ("Society", "society"),
    ("Culture", "culture"), ("Finance", "finance"), ("Real Estate", "real-estate"),
    ("Military", "military"), ("Art", "art"), ("Sports", "sports"), ("Global", "global"),
]

def request(method, path, **kwargs):
    response = requests.request(method, f"{SITE}/wp-json/wp/v2/{path}", auth=(USER, PASSWORD), timeout=45, **kwargs)
    response.raise_for_status()
    return response.json() if response.content else {}

def main():
    if not PASSWORD: raise SystemExit("Missing THESEOULJOURNALCOM")
    current = request("GET", "categories", params={"per_page": 100, "hide_empty": False})
    by_slug = {item["slug"]: item for item in current}
    for name, slug in CATEGORIES:
        if slug in by_slug:
            print(f"exists {slug}: {by_slug[slug]['id']}")
            continue
        created = request("POST", "categories", json={"name": name, "slug": slug,
            "description": f"The Seoul Journal {name} desk."})
        print(f"created {slug}: {created['id']}")

if __name__ == "__main__": main()
