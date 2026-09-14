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
        if rec.get("status") not in {"draft", "drafted", "✅ DRAFT"} or not rec.get("url"):
            continue
        # New pipeline records carry the exact editor URL. This is required
        # for Blogger, and avoids an unnecessary WordPress API lookup too.
        direct_edit_url = str(rec.get("edit_url") or "").strip()
        platform = str(rec.get("platform") or "").strip().lower()
        if direct_edit_url:
            lines.append({
                "platform": platform or ("blogger" if "blogger.com/blog/post/edit" in direct_edit_url else "wordpress"),
                "site": rec.get("site") or rec.get("site_id") or urlparse(rec.get("url", "")).netloc,
                "title": rec.get("title", "(제목 없음)"),
                "quality_score": rec.get("quality_score"),
                "search_description": rec.get("search_description", ""),
                "search_description_ui_required": bool(rec.get("search_description_ui_required")),
                "edit_url": direct_edit_url,
                "post_url": rec.get("url", direct_edit_url),
            })
            continue
        # Blogger draft URLs are already administrator edit links.
        if "blogger.com/blog/post/edit/" in str(rec.get("url", "")):
            lines.append({
                "platform": "blogger",
                "site": rec.get("site") or rec.get("site_id") or "Blogger",
                "title": rec.get("title", "(제목 없음)"),
                "quality_score": rec.get("quality_score"),
                "edit_url": rec["url"],
                "post_url": rec["url"],
            })
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
        lines.append({
            "platform": "wordpress", "site": urlparse(site_url).netloc,
            "title": title, "quality_score": rec.get("quality_score"),
            "edit_url": edit_url, "post_url": rec["url"],
        })
    return lines


def _score_line(review: dict) -> str:
    score = review.get("quality_score")
    return f"품질점수: {score}/100 (파이프라인 자체 점검)\n" if score not in (None, "") else ""


def _plain_body(base_body: str, reviews: list[dict], fallback_link: str) -> str:
    if not reviews:
        return base_body + f"\n\n작업 기록: {fallback_link}"
    blocks = []
    for review in reviews:
        blocks.append(
            f"{review.get('site', '')}\n"
            f"{review['title']}\n"
            f"{_score_line(review)}"
            + (f"검색 설명({len(review.get('search_description', ''))}자): {review.get('search_description')}\n"
               if review.get("search_description_ui_required") else "")
            + f"검토·발행·예약: {review['edit_url']}"
        )
    return base_body + "\n\n" + "\n\n".join(blocks)


def _html_body(base_body: str, reviews: list[dict], fallback_link: str) -> str:
    import html

    cards = []
    for review in reviews:
        title = html.escape(str(review["title"]))
        site = html.escape(str(review.get("site", "")))
        score = review.get("quality_score")
        score_html = (f'<p style="margin:0 0 12px;color:#52606d">품질점수: <b>{html.escape(str(score))}/100</b> '
                      f'(파이프라인 자체 점검)</p>') if score not in (None, "") else ""
        search_description = str(review.get("search_description") or "")
        meta_html = (f'<p style="margin:0 0 12px;padding:12px;background:#fff7d6;border-radius:8px">'
                     f'<b>검색 설명 {len(search_description)}자</b><br>{html.escape(search_description)}</p>') \
                    if review.get("search_description_ui_required") else ""
        edit_url = html.escape(str(review["edit_url"]), quote=True)
        cards.append(f"""
        <section style="margin:18px 0;padding:20px;border:1px solid #dfe5ec;border-radius:14px;background:#fff">
          <p style="margin:0 0 6px;color:#52606d;font-size:14px">{site}</p>
          <h2 style="margin:0 0 16px;font-size:20px;line-height:1.45;color:#172033">{title}</h2>
          {score_html}
          {meta_html}
          <a href="{edit_url}" style="display:block;margin:8px 0;padding:14px;border-radius:9px;background:#16794b;color:#fff;text-align:center;text-decoration:none;font-weight:800">관리자에서 검토 · 발행 · 예약</a>
        </section>""")
    if not cards:
        return ""
    escaped_base = html.escape(base_body)
    return f"""<html><body style="margin:0;background:#f3f5f7;font-family:Arial,'Noto Sans KR',sans-serif;color:#172033">
    <main style="max-width:640px;margin:auto;padding:24px 14px">
      <h1 style="font-size:24px;margin:0 0 8px">오늘 작성된 글 검토</h1>
      <p style="line-height:1.6;margin:0 0 14px">{escaped_base}<br>링크를 누른 뒤 각 플랫폼 관리자에서 직접 발행하거나 예약하세요.</p>
      {''.join(cards)}
    </main></body></html>"""


def send_email(subject: str, body: str, html_body: str = "") -> bool:
    if os.getenv("NORMAL_COMPLETION_EMAIL_ENABLED", "false").strip().lower() not in {"1", "true", "yes", "on"}:
        print("normal completion email suppressed; review is available in the CEO control room")
        return True
    password = os.getenv("GMAIL_APP_PASSWORD", "").strip()
    recipient = os.getenv("REPORT_EMAIL_TO", "").strip() or "huh0303@gmail.com"
    sender = os.getenv("REPORT_EMAIL_FROM", "").strip() or "huh0303@gmail.com"
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
        "text": f"{str(review['title'])[:100]}\n\n관리자에서 검토 후 직접 발행 또는 예약하세요.",
        "link": {"web_url": link, "mobile_web_url": link},
        "button_title": "관리자에서 검토",
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

    schedule_id = os.getenv("CALENDAR_SCHEDULE_ID", "").strip()
    if schedule_id.startswith(("CAL-", "ROLL-")):
        from scripts.gsheets_direct import get_sheets_service
        service = get_sheets_service()
        sheet_id = os.environ["SHEET_ID"]
        tab = "14일_콘텐츠운영캘린더"
        values = service.spreadsheets().values().get(
            spreadsheetId=sheet_id, range=f"'{tab}'!A1:O2000"
        ).execute().get("values", [])
        matches = [(i, r + [""] * (15 - len(r))) for i, r in enumerate(values, 1)
                   if r and r[0] == schedule_id]
        if len(matches) != 1 or len(reviews) != 1:
            raise RuntimeError("Calendar result must match exactly one schedule and draft")
        index, row = matches[0]
        review = reviews[0]
        if row[2] != "WordPress" or urlparse(row[4]).netloc != urlparse(review["edit_url"]).netloc:
            raise RuntimeError("Draft destination does not match calendar")
        if row[12] not in {"자료수집", "검수중"} or (row[13] and row[13] != review["edit_url"]):
            raise RuntimeError("Calendar changed during generation; refusing to overwrite")
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id, range=f"'{tab}'!M{index}:O{index}", valueInputOption="RAW",
            body={"values": [["검수중", review["edit_url"], row[14] + "\n비공개 초안 저장; 관리자에서 직접 공개"]]},
        ).execute()

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
    # The CEO control room/Sheet is the authoritative review channel. Normal
    # per-item mail and Kakao notices are opt-in to prevent notification floods.
    if os.getenv("NORMAL_COMPLETION_EMAIL_ENABLED", "false").strip().lower() not in {"1", "true", "yes", "on"}:
        print(json.dumps({"email": "suppressed", "kakao": "suppressed", "url": reviews[0]["edit_url"],
                          "draft_links_found": len(reviews), "sheet_synced": sheet_synced,
                          "review_channel": "control.korea365.org"}, ensure_ascii=False))
        return 0
    email_result = send_email(title, body, email_html)
    kakao_results = []
    for review in reviews:
        try:
            kakao_results.append(send_kakao_review(review))
        except Exception as exc:
            print(f"kakao notification failed without affecting email: {exc}")
            kakao_results.append(False)
    # Logs and downstream status use the same real editor link as the email.
    results = {"email": email_result, "kakao": bool(kakao_results) and all(kakao_results),
               "url": reviews[0]["edit_url"], "draft_links_found": len(reviews), "sheet_synced": sheet_synced}
    print(json.dumps(results, ensure_ascii=False))
    return 0 if results["email"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
