#!/usr/bin/env python3
"""koreanews365.com 테마를 원래 상태(newsup)로 되돌린다. 사용자 지시
(2026-08-21) — Mission News 테마 좌우 Latest Posts 위젯이 빈 채로 렌더링되는
문제(category 필터 불일치로 목록 0개)를 못 고쳐서 원복 결정.
activate_koreanews_mission_news_theme.py와 동일한 가드 스니펫 방식."""
from __future__ import annotations
import os
import time

import requests

SITE = "koreanews365.com"
TARGET = "newsup"
USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
PHP = r"""
add_action('init', function () {
    if (get_option('kn26_theme_revert_v1') === 'done') return;
    $slug = 'newsup';
    switch_theme($slug);
    update_option('kn26_theme_revert_v1', get_stylesheet() === $slug ? 'done' : 'revert-error');
}, 1);
"""


def call(method, path, password, data=None, params=None):
    response = requests.request(method, f"https://{SITE}/wp-json/{path}", auth=(USER, password),
        json=data, params=params, headers={"User-Agent": "Koreanews-Theme-Revert/1.0"}, timeout=90)
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
    payload = {"name": "Koreanews365 theme revert v1",
               "desc": "One-time guarded revert back to newsup.",
               "code": PHP, "scope": "global", "active": True, "priority": 1,
               "tags": ["koreanews365", "newsup", "revert"]}
    created = call("POST", "code-snippets/v1/snippets", password, data=payload)
    snippet_id = created.get("id") or created.get("snippet", {}).get("id")
    if not snippet_id:
        raise RuntimeError(f"Snippet id missing: {created}")
    print(f"원복 스니펫 생성됨(id={snippet_id}), init 훅 트리거를 위해 홈페이지 요청...")
    home = requests.get(f"https://{SITE}/?theme-check=1",
                         headers={"User-Agent": "Koreanews-Theme-Revert/1.0"}, timeout=120)
    home.raise_for_status()
    time.sleep(3)
    after = active_theme(password)
    print(f"전환 후 테마: {after}")
    if after != TARGET:
        raise SystemExit(f"원복 실패 — before={before}, after={after}")
    print(f"성공: {SITE} 테마가 {TARGET}(으)로 원복됨")


if __name__ == "__main__":
    main()
