#!/usr/bin/env python3
"""Remove the obsolete [hits] widget and GeneratePress credit residue on k-health365.com."""
import os

import requests

SITE = "https://k-health365.com"
USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
PASSWORD = os.getenv("KHEALTH365COM", "").strip()
SNIPPET_NAME = "K-Health365 clean copyright footer"


def wp(method, path, **kwargs):
    response = requests.request(method, f"{SITE}/wp-json/{path}", auth=(USER, PASSWORD), timeout=30, **kwargs)
    response.raise_for_status()
    return response.json() if response.content else {}


def main():
    if not PASSWORD:
        raise SystemExit("KHEALTH365COM secret missing")

    widgets = wp("GET", "wp/v2/widgets", params={"per_page": 100, "_context": "edit"})
    removed = []
    for widget in widgets:
        raw = str(widget.get("instance", {}).get("raw", ""))
        rendered = str(widget.get("rendered", ""))
        if "[hits]" not in raw and "[hits]" not in rendered:
            continue
        widget_id = widget["id"]
        wp("DELETE", f"wp/v2/widgets/{widget_id}", params={"force": "true"})
        removed.append(widget_id)

    code = """// Managed footer cleanup. Keeps the real daily/total visitor counter intact.
add_filter('generate_copyright', function () {
    return '&copy; ' . wp_date('Y') . ' K-Health365 건강정보';
});
"""
    response = wp("GET", "code-snippets/v1/snippets", params={"per_page": 100})
    snippets = response if isinstance(response, list) else response.get("data", response.get("items", []))
    match = next((s for s in snippets if s.get("name") == SNIPPET_NAME), None)
    payload = {
        "name": SNIPPET_NAME,
        "desc": "Remove the theme credit separator and keep a clean copyright line.",
        "code": code,
        "scope": "global",
        "active": True,
        "priority": 10,
        "tags": ["footer", "cleanup", "managed"],
    }
    target = f"code-snippets/v1/snippets/{match['id']}" if match else "code-snippets/v1/snippets"
    saved = wp("POST", target, json=payload)
    if not saved.get("active", False):
        raise SystemExit("cleanup snippet was not activated")

    html = requests.get(SITE, timeout=30, headers={"User-Agent": "Mozilla/5.0 footer-verifier"}).text
    if "[hits]" in html:
        raise SystemExit("[hits] remains in public HTML after cleanup")
    if "network-daily-visitor-counter" not in html:
        raise SystemExit("real visitor counter disappeared during cleanup")
    print(f"OK removed_widgets={removed}; real visitor counter preserved")


if __name__ == "__main__":
    main()
