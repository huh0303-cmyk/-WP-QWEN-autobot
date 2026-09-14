"""Create or update the active Koreanews sidebar dashboard Code Snippet."""
from pathlib import Path
import os
import requests

SITE = "https://koreanews365.com"
USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
PASSWORD = os.getenv("KOREANEWS365COM", "").strip()
SOURCE = Path(__file__).with_name("koreanews_sidebar_dashboard.php")
NAME = "Koreanews sidebar dashboard v10"

def call(method, path, **kwargs):
    response = requests.request(method, f"{SITE}/wp-json/code-snippets/v1/{path}",
        auth=(USER, PASSWORD), timeout=45, **kwargs)
    response.raise_for_status()
    return response.json() if response.content else {}

def main():
    if not PASSWORD:
        raise SystemExit("Missing KOREANEWS365COM secret")
    code = SOURCE.read_text(encoding="utf-8").removeprefix("<?php").lstrip()
    response = call("GET", "snippets", params={"per_page": 100})
    snippets = response if isinstance(response, list) else response.get("data", response.get("items", []))
    matches = [s for s in snippets if
        "kn365_kbo_standings_v9" in s.get("code", "") or
        ("koreanews" in s.get("name", "").lower() and "sidebar" in s.get("name", "").lower())]
    payload = {"name": NAME, "desc": "KBO, markets, compact gold conversion, world time and weather.",
        "code": code, "scope": "global", "active": True, "priority": 10,
        "tags": ["koreanews", "sidebar", "markets"]}
    if matches:
        result = call("POST", f"snippets/{matches[0]['id']}", json=payload)
        action = "updated"
    else:
        result = call("POST", "snippets", json=payload)
        action = "created"
    if not result.get("active", False):
        raise SystemExit(f"Snippet not active: {result}")
    print(f"{action}: {NAME}")

if __name__ == "__main__":
    main()
