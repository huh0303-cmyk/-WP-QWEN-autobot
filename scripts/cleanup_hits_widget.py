#!/usr/bin/env python3
"""Remove the obsolete [hits] block widget left over from a removed plugin,
network-wide. Only deletes widgets whose content literally contains
"[hits]"; the real daily/total visitor counter (network-daily-visitor-counter)
is a wp_footer hook, not a widget, and is untouched by this script."""
import os

import requests

from site_registry import ACTIVE_SITES

WP_USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"


def wp(site, password, method, path, **kwargs):
    response = requests.request(method, f"{site.rstrip('/')}/wp-json/{path}",
                                 auth=(WP_USER, password), timeout=30, **kwargs)
    response.raise_for_status()
    return response.json() if response.content else {}


def clean_one(site, env_key):
    password = os.environ.get(env_key, "")
    if not password:
        return "skip", "secret missing", []
    widgets = wp(site, password, "GET", "wp/v2/widgets", params={"per_page": 100, "_context": "edit"})
    removed = []
    for widget in widgets:
        raw = str(widget.get("instance", {}).get("raw", ""))
        rendered = str(widget.get("rendered", ""))
        if "[hits]" not in raw and "[hits]" not in rendered:
            continue
        widget_id = widget["id"]
        wp(site, password, "DELETE", f"wp/v2/widgets/{widget_id}", params={"force": "true"})
        removed.append(widget_id)
    html = requests.get(site, timeout=30, headers={"User-Agent": "Mozilla/5.0 hits-widget-cleanup"}).text
    if "[hits]" in html:
        return "fail", "[hits] still present after widget removal", removed
    return ("cleaned" if removed else "already-clean"), None, removed


def main():
    print(f"{'사이트':35s} {'결과':14s} 비고")
    counts = {"cleaned": 0, "already-clean": 0, "skip": 0, "fail": 0}
    failures = []
    for site, env_key, _ in ACTIVE_SITES:
        status, note, removed = clean_one(site, env_key)
        counts[status] = counts.get(status, 0) + 1
        print(f"{site:35s} {status:14s} {note or ''} {removed}")
        if status == "fail":
            failures.append(f"{site}: {note}")
    print(f"\n완료: {counts}")
    if failures:
        raise SystemExit("[hits] 위젯 정리 실패:\n" + "\n".join(failures))


if __name__ == "__main__":
    main()
