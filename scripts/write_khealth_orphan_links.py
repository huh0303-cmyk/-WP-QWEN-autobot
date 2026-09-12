#!/usr/bin/env python3
"""User-approved, write-only step: the bulk GET to /wp-json/wp/v2/posts on
k-health365.com is blocked by a host WAF specifically for GitHub Actions
runner IPs (confirmed: succeeds from a non-Actions IP, raw HTML 403 from
Actions). The orphan/donor pairing was computed from that same read done
outside Actions; this script only performs the 42 individual POST writes,
each far below whatever triggered the bulk-read block."""
import html
import json
import os
import re
import time
from pathlib import Path
import requests
from requests.auth import HTTPBasicAuth

ROOT = Path(__file__).resolve().parent
USER = "huh0303@gmail.com"
PW = os.environ["KHEALTH365COM"]
BASE = "https://k-health365.com/wp-json/wp/v2"
AUTH = HTTPBasicAuth(USER, PW)
LINK_MARK = "<!-- orphan-fix-2026-09-12 -->"

pairs = json.loads((ROOT / "khealth_orphan_pairs.json").read_text(encoding="utf-8"))
fixed, failed = 0, []
for pair in pairs:
    title = html.unescape(re.sub("<[^>]+>", "", pair["orphan_title"]))
    link_block = (
        f'\n{LINK_MARK}<p style="margin-top:24px;"><strong>함께 보면 좋은 글:</strong> '
        f'<a href="{pair["orphan_link"]}">{title}</a></p>'
    )
    new_content = pair["donor_content"] + link_block
    r = requests.post(f"{BASE}/posts/{pair['donor_id']}", auth=AUTH, json={"content": new_content}, timeout=30)
    ok = r.status_code == 200
    print(f"orphan {pair['orphan_id']} <- donor {pair['donor_id']}: {'OK' if ok else 'FAIL ' + str(r.status_code) + ' ' + r.text[:150]}")
    if ok:
        fixed += 1
    else:
        failed.append(pair["orphan_id"])
    time.sleep(1)

print(f"\nSUMMARY: fixed={fixed} failed={len(failed)} failed_ids={failed}")
