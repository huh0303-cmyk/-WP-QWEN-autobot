#!/usr/bin/env python3
"""Send a publishing completion report by Gmail and Kakao Memo when configured.

2026-08-28: the email used to link only to the GitHub Actions run log, which
has no way to actually approve/publish anything. Now it resolves each
review-needed draft's WordPress admin edit screen instead — opening that link
puts a real "Publish" button (and a schedule-date picker) in front of the
user, so tapping it on mobile actually does something.
"""
from __future__ import annotations

import json
import os
import re
import smtplib
import sys
from email.mime.text import MIMEText
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

WP_USER = "huh0303@gmail.com"
RESULT_FILE = "newsroom_publish_result.json"


def _site_key_map() -> dict:
    try:
        from scripts.site_registry import SITES
    except Exception:
        return {}
    return {url.rstrip("/"): key for url, key, _tier in SITES}


def _admin_edit_url(site_url: str, post_id: int) -> str:
    return f"{site_url.rstrip('/')}/wp-admin/post.php?post={post_id}&action=edit"


def _resolve_post_id(site_url: str, post_url: str, wp_pass: str) -> int:
    m = re.search(r"[?&]p=(\d+)", post_url)
    if m:
        return int(m.group(1))
    slug = urlparse(post_url).path.strip("/").split("/")[-1]
    if not slug:
        return 0
    try:
        r = requests.get(
            f"{site_url}/wp-json/wp/v2/posts",
            auth=(WP_USER, wp_pass),
            params={"slug": slug, "status": "draft,pending,private,future",
                    "_fields": "id"},
            timeout=15,
        )
        r.raise_for_status()
        posts = r.json()
        return posts[0]["id"] if posts else 0
    except Exception:
        return 0


def build_draft_review_lines() -> list:
    if not Path(RESULT_FILE).exists():
        return []
    try:
        records = json.loads(Path(RESULT_FILE).read_text(encoding="utf-8")).get("records", [])
    except Exception:
        return []

    key_map = _site_key_map()
    lines = []
    for rec in records:
        if rec.get("status") != "draft" or not rec.get("url"):
            continue
        site_url = "https://" + urlparse(rec["url"]).netloc
        wp_pass = os.environ.get(key_map.get(site_url.rstrip("/"), ""), "")
        if not wp_pass:
            continue
        post_id = _resolve_post_id(site_url, rec["url"], wp_pass)
        if not post_id:
            continue
        edit_url = _admin_edit_url(site_url, post_id)
        title = rec.get("title", "(제목 없음)")
        lines.append(f"- {title}\n  {edit_url}\n  (열어서 '발행' 누르면 즉시 공개, '즉시'를 누르면 예약 시간 지정 가능)")
    return lines


def send_email(subject: str, body: str) -> bool:
    password = os.getenv("GMAIL_APP_PASSWORD", "").strip()
    recipient = os.getenv("REPORT_EMAIL_TO", "huh0303@gmail.com").strip()
    sender = os.getenv("REPORT_EMAIL_FROM", "huh0303@gmail.com").strip()
    if not password:
        print("email skipped: GMAIL_APP_PASSWORD missing")
        return False
    message = MIMEText(body, "plain", "utf-8")
    message["Subject"], message["From"], message["To"] = subject, sender, recipient
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
        smtp.login(sender, password)
        smtp.sendmail(sender, [recipient], message.as_string())
    return True


def send_kakao(text: str, link: str) -> bool:
    key = os.getenv("KAKAO_REST_API_KEY", "").strip()
    refresh = os.getenv("KAKAO_REFRESH_TOKEN", "").strip()
    if not key or not refresh:
        print("kakao skipped: credentials missing")
        return False
    token = requests.post("https://kauth.kakao.com/oauth/token", data={"grant_type": "refresh_token", "client_id": key, "refresh_token": refresh}, timeout=20)
    token.raise_for_status()
    access = token.json()["access_token"]
    template = {"object_type": "text", "text": text[:180], "link": {"web_url": link, "mobile_web_url": link}}
    response = requests.post("https://kapi.kakao.com/v2/api/talk/memo/default/send", headers={"Authorization": f"Bearer {access}"}, data={"template_object": json.dumps(template, ensure_ascii=False)}, timeout=20)
    response.raise_for_status()
    return True


def main() -> int:
    title = os.getenv("REPORT_TITLE", "자동발행 작업 완료")
    fallback_link = os.getenv("REPORT_URL", "https://github.com/huh0303-cmyk/-WP-QWEN-autobot/actions")
    base_body = os.getenv("REPORT_BODY", "자동발행 결과를 확인하세요.")

    draft_lines = build_draft_review_lines()
    if draft_lines:
        body = base_body + "\n\n검수 대기 글 (링크 열어서 바로 발행 또는 예약):\n\n" + "\n\n".join(draft_lines)
        body += f"\n\n실행 로그: {fallback_link}"
    else:
        body = base_body + f"\n\n모바일 확인·업로드: {fallback_link}"

    results = {"email": send_email(title, body), "kakao": send_kakao(body, fallback_link), "url": fallback_link,
               "draft_links_found": len(draft_lines)}
    print(json.dumps(results, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
