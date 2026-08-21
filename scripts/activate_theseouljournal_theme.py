#!/usr/bin/env python3
"""Guarded install/activation of the free CoverNews theme for The Seoul Journal."""
from __future__ import annotations
import json, os, time
from datetime import datetime, timezone
from pathlib import Path
import requests

SITE = "theseouljournal.com"
TARGET = "covernews"
USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
PHP = r"""
add_action('init', function () {
    if (get_option('sj26_covernews_migration_v1') === 'done') return;
    $slug = 'covernews';
    $theme = wp_get_theme($slug);
    if (!$theme->exists()) {
        require_once ABSPATH . 'wp-admin/includes/theme.php';
        require_once ABSPATH . 'wp-admin/includes/class-wp-upgrader.php';
        require_once ABSPATH . 'wp-admin/includes/theme-install.php';
        $info = themes_api('theme_information', array('slug' => $slug));
        if (is_wp_error($info) || empty($info->download_link)) {
            update_option('sj26_covernews_migration_v1', 'theme-api-error'); return;
        }
        $result = (new Theme_Upgrader(new Automatic_Upgrader_Skin()))->install($info->download_link);
        if (is_wp_error($result) || !$result) {
            update_option('sj26_covernews_migration_v1', 'install-error'); return;
        }
    }
    switch_theme($slug);
    update_option('sj26_covernews_migration_v1', get_stylesheet() === $slug ? 'done' : 'activate-error');
}, 1);
"""

def call(method, path, password, data=None, params=None):
    response = requests.request(method, f"https://{SITE}/wp-json/{path}", auth=(USER, password),
        json=data, params=params, headers={"User-Agent": "SeoulJournal-Theme-Migration/1.0"}, timeout=90)
    if response.status_code >= 400:
        raise RuntimeError(f"{method} {path}: {response.status_code} {response.text[:400]}")
    return response.json() if response.text else {}

def active_theme(password):
    themes = call("GET", "wp/v2/themes", password, params={"status": "active"})
    return themes[0].get("stylesheet") if themes else None

def main():
    password = os.getenv("THESEOULJOURNALCOM", "").strip()
    if not password: raise SystemExit("Missing THESEOULJOURNALCOM")
    before = active_theme(password)
    payload = {"name": "The Seoul Journal CoverNews migration v1", "desc": "One-time guarded CoverNews activation.",
        "code": PHP, "scope": "global", "active": True, "priority": 1,
        "tags": ["theseouljournal", "covernews", "migration"]}
    created = call("POST", "code-snippets/v1/snippets", password, data=payload)
    snippet_id = created.get("id") or created.get("snippet", {}).get("id")
    if not snippet_id: raise RuntimeError(f"Snippet id missing: {created}")
    try:
        home = requests.get(f"https://{SITE}/?theme-check=1", headers={"User-Agent": "SeoulJournal-Theme-Migration/1.0"}, timeout=120)
        home.raise_for_status()
        time.sleep(3)
        after = active_theme(password)
        if after != TARGET: raise RuntimeError(f"Active theme is {after}, expected {TARGET}")
    finally:
        call("DELETE", f"code-snippets/v1/snippets/{snippet_id}", password)
    receipt = {"schema": 1, "applied_at": datetime.now(timezone.utc).isoformat(), "site": SITE,
        "before": before, "after": after, "temporary_snippet_deleted": True}
    Path("theseouljournal_theme_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))

if __name__ == "__main__": main()
