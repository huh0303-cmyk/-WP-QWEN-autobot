#!/usr/bin/env python3
"""One-off: k-trip365.com's Rank Math homepage_title/homepage_description
were mistakenly set to k-health365.com's values ("대한민국 대표 건강정보
연구소"). Fix them to match k-trip365's actual travel-guide identity."""
import os
import time
import requests

USER = "huh0303@gmail.com"
PW = os.environ["KTRIP365COM"]
BASE = "https://k-trip365.com/wp-json/code-snippets/v1"
SITE = "https://k-trip365.com"

NEW_TITLE = "K-Trip365 — Practical Korea Travel Guides & Itineraries"
NEW_DESCRIPTION = ("Friendly, practical guides to traveling in Korea — itineraries, "
                    "hidden gems, transportation tips, and seasonal highlights.")

PHP_CODE = r"""
add_action('init', function () {
    if (!isset($_GET['fix_ktrip_title_v1'])) return;
    header('Content-Type: text/plain; charset=utf-8');
    $titles = get_option('rank-math-options-titles');
    $before_title = $titles['homepage_title'] ?? '';
    $before_desc = $titles['homepage_description'] ?? '';
    $titles['homepage_title'] = '""" + NEW_TITLE + r"""';
    $titles['homepage_description'] = '""" + NEW_DESCRIPTION + r"""';
    update_option('rank-math-options-titles', $titles);
    $after = get_option('rank-math-options-titles');
    echo "before_title: $before_title\n";
    echo "before_description: $before_desc\n";
    echo "after_title: " . $after['homepage_title'] . "\n";
    echo "after_description: " . $after['homepage_description'] . "\n";
    exit;
}, 1);
"""

payload = {
    "name": "TEMP fix ktrip365 homepage title",
    "desc": "temporary one-off fix, safe to delete",
    "code": PHP_CODE,
    "scope": "global",
    "active": True,
    "priority": 1,
}
r = requests.post(f"{BASE}/snippets", auth=(USER, PW), json=payload, timeout=30)
r.raise_for_status()
snippet_id = r.json()["id"]
print("created snippet id:", snippet_id)

time.sleep(2)
check = requests.get(f"{SITE}/?fix_ktrip_title_v1=1", timeout=30)
print("STATUS:", check.status_code)
print(check.text[:2000])

delete = requests.delete(f"{BASE}/snippets/{snippet_id}", auth=(USER, PW), timeout=30)
print("cleanup delete status:", delete.status_code)
