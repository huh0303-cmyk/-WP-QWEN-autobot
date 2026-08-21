"""Deploy Koreanews365 home two-column grid as an active Code Snippet."""
from __future__ import annotations
import os
from pathlib import Path
import requests

SITE = "https://koreanews365.com"
NAME = "Koreanews home two-column grid v1"
USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
PASSWORD = os.getenv("KOREANEWS365COM", "").strip()
SOURCE = Path(__file__).with_name("koreanews_home_two_column.php")

def request(method, path, **kwargs):
    response = requests.request(method, f"{SITE}/wp-json/code-snippets/v1/{path}",
        auth=(USER, PASSWORD), timeout=45, **kwargs)
    response.raise_for_status()
    return response.json() if response.content else {}

def main():
    if not PASSWORD: raise SystemExit("Missing KOREANEWS365COM secret")
    code = SOURCE.read_text(encoding="utf-8").removeprefix("<?php").lstrip()
    existing = request("GET", "snippets", params={"search": NAME, "per_page": 20})
    matches = existing if isinstance(existing, list) else existing.get("data", existing.get("items", []))
    payload = {"name": NAME, "desc": "Two-column home cards and 20 published archive posts.",
        "code": code, "scope": "global", "active": True, "priority": 10,
        "tags": ["koreanews", "homepage", "grid"]}
    if matches:
        result = request("POST", f"snippets/{matches[0]['id']}", json=payload); action = "updated"
    else:
        result = request("POST", "snippets", json=payload); action = "created"
    if not result.get("active", False): raise SystemExit(f"Snippet not active: {result}")
    print(f"{action}: {NAME}")

if __name__ == "__main__": main()
