#!/usr/bin/env python3
"""One-off: temporarily deploy a diagnostic snippet on k-trip365.com that
dumps the WordPress/Rank Math options controlling the homepage <title> and
meta description, curl it once, print the result, then delete the snippet."""
import os
import time
import requests

USER = "huh0303@gmail.com"
PW = os.environ["KTRIP365COM"]
BASE = "https://k-trip365.com/wp-json/code-snippets/v1"
SITE = "https://k-trip365.com"

PHP_CODE = r"""
add_action('init', function () {
    if (!isset($_GET['diag_title_v1'])) return;
    header('Content-Type: text/plain; charset=utf-8');
    echo "blogname: " . get_option('blogname') . "\n";
    echo "blogdescription: " . get_option('blogdescription') . "\n";
    $rm_titles = get_option('rank-math-options-titles');
    echo "rank-math-options-titles: " . print_r($rm_titles, true) . "\n";
    $rm_general = get_option('rank-math-options-general');
    echo "rank-math-options-general (truncated): " . substr(print_r($rm_general, true), 0, 2000) . "\n";
    global $post;
    echo "current document_title_parts filters applied to front page:\n";
    echo wp_get_document_title() . "\n";
    exit;
}, 1);
"""

payload = {
    "name": "TEMP diag title source",
    "desc": "temporary diagnostic, safe to delete",
    "code": PHP_CODE,
    "scope": "global",
    "active": True,
    "priority": 1,
}
r = requests.post(f"{BASE}/snippets", auth=(USER, PW), json=payload, timeout=30)
r.raise_for_status()
snippet = r.json()
snippet_id = snippet["id"]
print("created snippet id:", snippet_id)

time.sleep(2)
check = requests.get(f"{SITE}/?diag_title_v1=1", timeout=30)
print("STATUS:", check.status_code)
print(check.text[:4000])

delete = requests.delete(f"{BASE}/snippets/{snippet_id}", auth=(USER, PW), timeout=30)
print("cleanup delete status:", delete.status_code)
