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
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

WP_USER = "huh0303@gmail.com"
RESULT_FILE = "newsroom_publish_result.json"
NORMALIZED_RESULT_FILE = "artifacts/automation-room-result.json"


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


def build_draft_reviews() -> list[dict]:
    records = []
    if Path(RESULT_FILE).exists():
        try:
            records = json.loads(Path(RESULT_FILE).read_text(encoding="utf-8")).get("records", [])
        except Exception:
            records = []
    if not records and Path(NORMALIZED_RESULT_FILE).exists():
        try:
            normalized = json.loads(Path(NORMALIZED_RESULT_FILE).read_text(encoding="utf-8"))
            source = normalized.get("source", {})
            draft_url = normalized.get("artifact_url", "")
            if draft_url:
                records = [{
                    "status": source.get("status", "draft"),
                    "url": draft_url,
                    "title": source.get("title", "(제목 없음)"),
                }]
        except Exception:
            records = []

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
        lines.append({"title": title, "edit_url": edit_url, "post_url": rec["url"]})
    return lines


def _plain_body(base_body: str, reviews: list[dict], fallback_link: str) -> str:
    if not reviews:
        return base_body + f"\n\n작업 기록: {fallback_link}"
    blocks = []
    for review in reviews:
        blocks.append(
            f"{review['title']}\n"
            f"글 확인·승인·비승인: {review['edit_url']}"
        )
    return base_body + "\n\n" + "\n\n".join(blocks) + f"\n\n작업 기록: {fallback_link}"


def _html_body(base_body: str, reviews: list[dict], fallback_link: str) -> str:
    import html

    cards = []
    for review in reviews:
        title = html.escape(str(review["title"]))
        edit_url = html.escape(str(review["edit_url"]), quote=True)
        cards.append(f"""
        <section style="margin:18px 0;padding:20px;border:1px solid #dfe5ec;border-radius:14px;background:#fff">
          <h2 style="margin:0 0 16px;font-size:20px;line-height:1.45;color:#172033">{title}</h2>
          <a href="{edit_url}" style="display:block;margin:8px 0;padding:14px;border-radius:9px;background:#eef3f8;color:#172033;text-align:center;text-decoration:none;font-weight:700">글 먼저 보기</a>
          <table role="presentation" width="100%"><tr>
            <td width="50%" style="padding:4px 4px 0 0"><a href="{edit_url}#submitdiv" style="display:block;padding:14px;border-radius:9px;background:#16794b;color:#fff;text-align:center;text-decoration:none;font-weight:800">승인(공개)</a></td>
            <td width="50%" style="padding:4px 0 0 4px"><a href="{edit_url}#delete-action" style="display:block;padding:14px;border-radius:9px;background:#a93333;color:#fff;text-align:center;text-decoration:none;font-weight:800">비승인(보류·삭제)</a></td>
          </tr></table>
        </section>""")
    if not cards:
        return ""
    escaped_base = html.escape(base_body)
    escaped_log = html.escape(fallback_link, quote=True)
    return f"""<html><body style="margin:0;background:#f3f5f7;font-family:Arial,'Noto Sans KR',sans-serif;color:#172033">
    <main style="max-width:640px;margin:auto;padding:24px 14px">
      <h1 style="font-size:24px;margin:0 0 8px">오늘 작성된 글 검토</h1>
      <p style="line-height:1.6;margin:0 0 14px">{escaped_base}<br>아래 글 제목을 눌러 내용을 확인한 뒤 WordPress 화면에서 공개 또는 보류하세요.</p>
      {''.join(cards)}
      <p style="font-size:12px;color:#697386"><a href="{escaped_log}">작업 기록</a></p>
    </main></body></html>"""


def send_email(subject: str, body: str, html_body: str = "") -> bool:
    password = os.getenv("GMAIL_APP_PASSWORD", "").strip()
    recipient = os.getenv("REPORT_EMAIL_TO", "huh0303@gmail.com").strip()
    sender = os.getenv("REPORT_EMAIL_FROM", "huh0303@gmail.com").strip()
    if not password:
        print("email skipped: GMAIL_APP_PASSWORD missing")
        return False
    message = MIMEMultipart("alternative")
    message.attach(MIMEText(body, "plain", "utf-8"))
    if html_body:
        message.attach(MIMEText(html_body, "html", "utf-8"))
    message["Subject"], message["From"], message["To"] = subject, sender, recipient
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
        smtp.login(sender, password)
        smtp.sendmail(sender, [recipient], message.as_string())
    return True


def send_kakao_review(review: dict) -> bool:
    key = os.getenv("KAKAO_REST_API_KEY", "").strip()
    refresh = os.getenv("KAKAO_REFRESH_TOKEN", "").strip()
    if not key or not refresh:
        print("kakao skipped: credentials missing")
        return False
    token = requests.post("https://kauth.kakao.com/oauth/token", data={"grant_type": "refresh_token", "client_id": key, "refresh_token": refresh}, timeout=20)
    token.raise_for_status()
    access = token.json()["access_token"]
    link = review["edit_url"]
    template = {
        "object_type": "text",
        "text": f"{str(review['title'])[:100]}\n\n글을 읽은 뒤 승인(공개) 또는 비승인(보류·삭제)을 선택하세요.",
        "link": {"web_url": link, "mobile_web_url": link},
        "button_title": "글 보기 · 승인/비승인",
    }
    response = requests.post("https://kapi.kakao.com/v2/api/talk/memo/default/send", headers={"Authorization": f"Bearer {access}"}, data={"template_object": json.dumps(template, ensure_ascii=False)}, timeout=20)
    response.raise_for_status()
    return True


def main() -> int:
    title = os.getenv("REPORT_TITLE", "[작성 완료] 글 확인 후 승인 또는 비승인")
    fallback_link = os.getenv("REPORT_URL", "https://github.com/huh0303-cmyk/-WP-QWEN-autobot/actions")
    base_body = os.getenv("REPORT_BODY", "자동발행 결과를 확인하세요.")

    reviews = build_draft_reviews()
    if not reviews:
        # Never send an empty "review" message. A mobile review notice is valid
        # only when it contains at least one real draft editor URL.
        print(json.dumps({
            "email": False, "kakao": False, "url": fallback_link,
            "draft_links_found": 0, "sheet_synced": False,
            "notification_skipped": "no_reviewable_drafts",
        }, ensure_ascii=False))
        return 0

    try:
        from scripts.review_sheet import append_review_rows
        sheet_synced = append_review_rows([
            {"platform": "WordPress", "channel": urlparse(r["post_url"]).netloc,
             "title": r["title"], "review_url": r["edit_url"], "status": "비공개 초안",
             "decision": "검토대기", "run_url": fallback_link}
            for r in reviews
        ])
    except Exception as exc:
        print(f"review sheet sync failed without affecting notifications: {exc}")
        sheet_synced = False
    body = _plain_body(base_body, reviews, fallback_link)
    email_html = _html_body(base_body, reviews, fallback_link)
    kakao_results = [send_kakao_review(review) for review in reviews]
    results = {"email": send_email(title, body, email_html), "kakao": bool(kakao_results) and all(kakao_results),
               "url": fallback_link, "draft_links_found": len(reviews), "sheet_synced": sheet_synced}
    print(json.dumps(results, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
