#!/usr/bin/env python3
"""Expose Rank Math post metadata in KWorld365 REST, then verify it."""
from __future__ import annotations

import json
import os

import requests

SITE = "https://kworld365.com"
USER = "huh0303@gmail.com"
NAME = "REST: expose Rank Math editorial metadata"
CODE = """add_action('init', function () {
    foreach (array('rank_math_focus_keyword', 'rank_math_description', 'rank_math_seo_score') as $key) {
        register_post_meta('post', $key, array(
            'show_in_rest' => true,
            'single' => true,
            'type' => 'string',
            'auth_callback' => function () { return current_user_can('edit_posts'); },
        ));
    }
});"""


def main() -> int:
    password = os.environ.get("KWORLD365COM", "").strip()
    if not password:
        raise SystemExit("KWORLD365COM missing")
    auth = (USER, password)
    endpoint = f"{SITE}/wp-json/code-snippets/v1/snippets"
    response = requests.get(endpoint, auth=auth, params={"per_page": 100}, timeout=30)
    response.raise_for_status()
    payload = response.json()
    items = payload if isinstance(payload, list) else payload.get("data", payload.get("items", []))
    existing = next((row for row in items if row.get("name") == NAME), None)
    body = {"name": NAME, "desc": "Allow authenticated automation to save and verify Rank Math metadata.", "code": CODE, "scope": "global", "active": True}
    if existing:
        saved = requests.post(f"{endpoint}/{existing['id']}", auth=auth, json=body, timeout=30)
        action = "updated"
    else:
        saved = requests.post(endpoint, auth=auth, json=body, timeout=30)
        action = "created"
    saved.raise_for_status()
    check = requests.get(f"{SITE}/wp-json/wp/v2/posts", auth=auth, params={"status": "publish", "context": "edit", "per_page": 1, "_fields": "id,meta"}, timeout=30)
    check.raise_for_status()
    meta = (check.json()[0].get("meta") or {}) if check.json() else {}
    ok = "rank_math_focus_keyword" in meta
    result = {"ok": ok, "action": action, "focus_keyword_exposed": ok}
    with open("kworld_rankmath_rest_result.json", "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
