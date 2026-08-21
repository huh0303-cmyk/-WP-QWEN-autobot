"""Deploy the approved The Seoul Journal newsroom dashboard as a Code Snippet."""
from __future__ import annotations

import os
from pathlib import Path

import requests

SITE = "https://theseouljournal.com"
NAME = "The Seoul Journal newsroom dashboard v1"
USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
PASSWORD = os.getenv("THESEOULJOURNALCOM", "").strip()
SOURCE = Path(__file__).with_name("theseouljournal_newsroom_dashboard.php")


def request(method: str, path: str, **kwargs):
    response = requests.request(
        method,
        f"{SITE}/wp-json/code-snippets/v1/{path}",
        auth=(USER, PASSWORD),
        timeout=45,
        **kwargs,
    )
    response.raise_for_status()
    return response.json() if response.content else {}


def main() -> None:
    if not PASSWORD:
        raise SystemExit("Missing THESEOULJOURNALCOM application-password secret")
    code = SOURCE.read_text(encoding="utf-8").removeprefix("<?php").lstrip()
    existing = request("GET", "snippets", params={"search": NAME, "per_page": 20})
    matches = existing if isinstance(existing, list) else existing.get("data", existing.get("items", []))
    payload = {
        "name": NAME,
        "desc": "Daily MLB, markets, crypto, gold, FX, world time and weather data desk.",
        "code": code,
        "scope": "global",
        "active": True,
        "priority": 10,
        "tags": ["theseouljournal", "newsroom", "dashboard"],
    }
    if matches:
        snippet_id = matches[0]["id"]
        result = request("POST", f"snippets/{snippet_id}", json=payload)
        action = "updated"
    else:
        result = request("POST", "snippets", json=payload)
        snippet_id = result.get("id")
        action = "created"
    if not result.get("active", False):
        raise SystemExit(f"Snippet {snippet_id} was saved but is not active: {result}")
    print(f"{action} active snippet {snippet_id}: {NAME}")


if __name__ == "__main__":
    main()
