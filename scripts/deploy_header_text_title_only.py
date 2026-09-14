#!/usr/bin/env python3
"""Deploy the text-title-only header rule to all 27 WordPress sites."""
import os
from pathlib import Path

import requests

try:
    from .site_registry import ACTIVE_SITES
except ImportError:
    from site_registry import ACTIVE_SITES

USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
NAME = "Network header text title only"
SOURCE = Path(__file__).with_name("header_text_title_only.php")


def call(site, password, method, path, **kwargs):
    response = requests.request(method, f"{site}/wp-json/code-snippets/v1/{path}", auth=(USER, password), timeout=30, **kwargs)
    response.raise_for_status()
    return response.json() if response.content else {}


def deploy(site, env_name, code):
    password = os.getenv(env_name, "").strip()
    if not password:
        raise RuntimeError(f"missing secret {env_name}")
    response = call(site, password, "GET", "snippets", params={"per_page": 100})
    snippets = response if isinstance(response, list) else response.get("data", response.get("items", []))
    match = next((s for s in snippets if s.get("name") == NAME or "network-text-title-only-css" in s.get("code", "")), None)
    payload = {"name": NAME, "desc": "Header logo images removed; accessible text site title retained.",
               "code": code, "scope": "global", "active": True, "priority": 10,
               "tags": ["header", "branding", "managed"]}
    target = f"snippets/{match['id']}" if match else "snippets"
    saved = call(site, password, "POST", target, json=payload)
    if not saved.get("active", False):
        raise RuntimeError("snippet inactive after save")


def main():
    if len(ACTIVE_SITES) != 27:
        raise SystemExit("scope guard: expected 27 active WordPress sites")
    code = SOURCE.read_text(encoding="utf-8")
    failures = []
    for index, (site, env_name, _) in enumerate(ACTIVE_SITES, 1):
        try:
            deploy(site, env_name, code)
            print(f"[{index:02d}/27] OK {site}", flush=True)
        except Exception as exc:
            failures.append(f"{site}: {exc}")
            print(f"[{index:02d}/27] FAIL {site}: {exc}", flush=True)
    if failures:
        raise SystemExit("header logo deployment incomplete:\n" + "\n".join(failures))


if __name__ == "__main__":
    main()
