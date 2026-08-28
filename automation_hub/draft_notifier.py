from __future__ import annotations

import os
import smtplib
from email.mime.text import MIMEText


def notify_blogger_draft(*, site_id: str, title: str, review_url: str, quality_note: str = "") -> bool:
    """Email a private Blogger review link when Gmail credentials are configured."""
    try:
        from scripts.review_sheet import append_review_rows
        append_review_rows([{
            "platform": "Blogger", "channel": site_id, "title": title,
            "review_url": review_url, "status": "비공개 초안",
            "decision": "검토대기", "note": quality_note,
        }])
    except Exception as exc:
        print(f"Blogger review sheet sync skipped without affecting draft: {exc}")
    password = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
    recipient = os.environ.get("BLOGGER_REVIEW_EMAIL_TO", "huh0303@gmail.com").strip()
    sender = os.environ.get("BLOGGER_REVIEW_EMAIL_FROM", recipient).strip()
    if not all((password, recipient, sender, review_url)):
        print("Blogger draft email skipped: Gmail credential or review URL is missing.")
        return False
    body = f"""Blogger 첫 글 초안이 비공개 상태로 준비되었습니다.

블로그: {site_id}
제목: {title}
검수·편집 링크: {review_url}
품질 기록: {quality_note or '-'}

자동 공개되지 않습니다. 내용을 직접 읽고 확신이 설 때 Blogger에서 게시를 눌러주세요.
"""
    message = MIMEText(body, "plain", "utf-8")
    message["Subject"] = f"[Blogger 초안 검수] {site_id} - {title}"
    message["From"] = sender
    message["To"] = recipient
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, [recipient], message.as_string())
        print(f"Blogger draft review email sent to {recipient}")
        return True
    except (OSError, smtplib.SMTPException) as exc:
        print(f"Blogger draft email failed without affecting the draft: {exc}")
        return False
