#!/usr/bin/env python3
"""theseouljournal.com에서 댓글 발생 시 검토요청 이메일이 오는 걸 즉시 중지.
WP 핵심 옵션(comments_notify/moderation_notify)을 끄는 Code Snippet 배포 —
플러그인이든 코어 기본동작이든 이 두 옵션이 이메일 발송 여부를 결정한다."""
import os
import requests

SITE = "https://theseouljournal.com"
USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
PW = os.getenv("THESEOULJOURNALCOM", "").strip()
NAME = "Disable comment notification emails"

PHP = r"""
add_action('init', function () {
    update_option('comments_notify', 0);
    update_option('moderation_notify', 0);
}, 1);
add_filter('notify_post_author', '__return_false');
add_filter('notify_moderator', '__return_false');
"""


def call(method, path, **kwargs):
    r = requests.request(method, f"{SITE}/wp-json/code-snippets/v1/{path}",
                          auth=(USER, PW), timeout=45, **kwargs)
    r.raise_for_status()
    return r.json() if r.content else {}


def main():
    if not PW:
        raise SystemExit("Missing THESEOULJOURNALCOM secret")
    payload = {"name": NAME, "desc": "Stops all comment moderation/notification emails.",
               "code": PHP, "scope": "global", "active": True, "priority": 1,
               "tags": ["comments", "email"]}
    existing = call("GET", "snippets", params={"per_page": 100})
    matches = existing if isinstance(existing, list) else existing.get("data", existing.get("items", []))
    matches = [s for s in matches if s.get("name") == NAME]
    if matches:
        result = call("POST", f"snippets/{matches[0]['id']}", json=payload)
        action = "updated"
    else:
        result = call("POST", "snippets", json=payload)
        action = "created"
    print(f"{action}: {NAME}, active={result.get('active')}")

    # 홈페이지 한 번 요청해서 init 훅 즉시 실행되게(옵션 반영)
    requests.get(SITE, timeout=30)
    print("완료 — comments_notify/moderation_notify 즉시 0으로 설정됨")


if __name__ == "__main__":
    main()
