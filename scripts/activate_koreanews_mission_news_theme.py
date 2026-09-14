#!/usr/bin/env python3
"""Guarded install/activation of Mission News for koreanews365.com — same theme
theseouljournal.com already uses (mission-news, from wordpress.org). User request
2026-08-21: "theseouljournal 깔끔한 신문 느낌 koreanews365에도 입혀줘."
Mirrors activate_theseouljournal_theme.py's approach exactly."""
from __future__ import annotations
import os
import time

import requests

SITE = "koreanews365.com"
TARGET = "mission-news"
USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
PHP = r"""
add_action('init', function () {
    if (get_option('kn26_mission_news_migration_v1') === 'done') return;
    $slug = 'mission-news';
    $theme = wp_get_theme($slug);
    if (!$theme->exists()) {
        require_once ABSPATH . 'wp-admin/includes/theme.php';
        require_once ABSPATH . 'wp-admin/includes/class-wp-upgrader.php';
        require_once ABSPATH . 'wp-admin/includes/theme-install.php';
        $info = themes_api('theme_information', array('slug' => $slug));
        if (is_wp_error($info) || empty($info->download_link)) {
            update_option('kn26_mission_news_migration_v1', 'theme-api-error'); return;
        }
        $result = (new Theme_Upgrader(new Automatic_Upgrader_Skin()))->install($info->download_link);
        if (is_wp_error($result) || !$result) {
            update_option('kn26_mission_news_migration_v1', 'install-error'); return;
        }
    }
    switch_theme($slug);
    update_option('kn26_mission_news_migration_v1', get_stylesheet() === $slug ? 'done' : 'activate-error');
}, 1);
"""


def call(method, path, password, data=None, params=None):
    response = requests.request(method, f"https://{SITE}/wp-json/{path}", auth=(USER, password),
        json=data, params=params, headers={"User-Agent": "Koreanews-Theme-Migration/1.0"}, timeout=90)
    if response.status_code >= 400:
        raise RuntimeError(f"{method} {path}: {response.status_code} {response.text[:400]}")
    return response.json() if response.text else {}


def active_theme(password):
    themes = call("GET", "wp/v2/themes", password, params={"status": "active"})
    return themes[0].get("stylesheet") if themes else None


def main():
    password = os.getenv("KOREANEWS365COM", "").strip()
    if not password:
        raise SystemExit("Missing KOREANEWS365COM")
    before = active_theme(password)
    print(f"현재 테마: {before}")
    payload = {"name": "Koreanews365 Mission News migration v1",
               "desc": "One-time guarded Mission News activation (matches theseouljournal.com).",
               "code": PHP, "scope": "global", "active": True, "priority": 1,
               "tags": ["koreanews365", "mission-news", "migration"]}
    created = call("POST", "code-snippets/v1/snippets", password, data=payload)
    snippet_id = created.get("id") or created.get("snippet", {}).get("id")
    if not snippet_id:
        raise RuntimeError(f"Snippet id missing: {created}")
    print(f"마이그레이션 스니펫 생성됨(id={snippet_id}), init 훅 트리거를 위해 홈페이지 요청...")
    home = requests.get(f"https://{SITE}/?theme-check=1",
                         headers={"User-Agent": "Koreanews-Theme-Migration/1.0"}, timeout=120)
    home.raise_for_status()
    time.sleep(3)
    after = active_theme(password)
    print(f"전환 후 테마: {after}")
    if after != TARGET:
        raise SystemExit(f"테마 전환 실패 또는 미완료 — before={before}, after={after}")
    print(f"성공: {SITE} 테마가 {TARGET}(으)로 전환됨")


if __name__ == "__main__":
    main()
