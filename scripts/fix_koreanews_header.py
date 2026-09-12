#!/usr/bin/env python3
"""One-off: koreanews365.com header — remove the duplicate top site-title text
and the gray/navy overlay band behind the branding block."""
import os
import requests

SITE = "https://koreanews365.com"
USER = "huh0303@gmail.com"
PASS = os.environ["KOREANEWS365COM"]
AUTH = (USER, PASS)
NAME = "Header: single title, white band"

CODE = """add_action('wp_footer', function () {
    if (is_admin()) {
        return;
    }
    ?>
    <style id="kn365-header-cleanup-style">
      .mg-nav-widget-area .inner { background-color: #ffffff !important; background-image: none !important; }
      .navbar-header .site-logo .network-text-site-title { display: none !important; }
    </style>
    <?php
}, 60);
"""


def call(method, path, **kwargs):
    r = requests.request(method, f"{SITE}/wp-json/code-snippets/v1/{path}", auth=AUTH, timeout=30, **kwargs)
    r.raise_for_status()
    return r.json() if r.content else {}


def main():
    existing = call("GET", "snippets", params={"per_page": 100})
    snippets = existing if isinstance(existing, list) else existing.get("data", existing.get("items", []))
    match = next((s for s in snippets if s.get("name") == NAME), None)
    payload = {"name": NAME, "desc": "Remove duplicate small site-title above the main heading; make the branding band white instead of navy overlay.",
               "code": CODE, "scope": "global", "active": True, "priority": 10, "tags": ["header", "branding", "one-off"]}
    target = f"snippets/{match['id']}" if match else "snippets"
    saved = call("POST", target, json=payload)
    print("saved:", saved.get("id"), "active:", saved.get("active"))


if __name__ == "__main__":
    main()
