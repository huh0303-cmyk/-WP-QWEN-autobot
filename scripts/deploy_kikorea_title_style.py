#!/usr/bin/env python3
"""Deploy the lighter title/header CSS to ki-korea.com only (owner-reported fix)."""
import os
from pathlib import Path

import requests

SITE = "https://ki-korea.com"
USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
PASSWORD = os.getenv("KIKOREACOM", "").strip()
NAME = "ki-korea title style fix"
SOURCE = Path(__file__).with_name("kikorea_title_style.php")


def call(method, path, **kwargs):
    response = requests.request(method, f"{SITE}/wp-json/code-snippets/v1/{path}", auth=(USER, PASSWORD), timeout=30, **kwargs)
    response.raise_for_status()
    return response.json() if response.content else {}


def main():
    if not PASSWORD:
        raise SystemExit("missing secret KIKOREACOM")
    code = SOURCE.read_text(encoding="utf-8")
    response = call("GET", "snippets", params={"per_page": 100})
    snippets = response if isinstance(response, list) else response.get("data", response.get("items", []))
    match = next((s for s in snippets if s.get("name") == NAME or "kikorea-title-style-fix-css" in s.get("code", "")), None)
    payload = {"name": NAME, "desc": "Lighter entry-title and header site-title font weight per owner request.",
               "code": code, "scope": "global", "active": True, "priority": 20,
               "tags": ["header", "typography", "managed"]}
    target = f"snippets/{match['id']}" if match else "snippets"
    saved = call("POST", target, json=payload)
    if not saved.get("active", False):
        raise RuntimeError("snippet inactive after save")
    print("OK ki-korea.com title style snippet deployed")


if __name__ == "__main__":
    main()
