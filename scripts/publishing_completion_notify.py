#!/usr/bin/env python3
"""Send a publishing completion report by Gmail and Kakao Memo when configured."""
from __future__ import annotations

import json
import os
import smtplib
from email.mime.text import MIMEText

import requests


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
    link = os.getenv("REPORT_URL", "https://github.com/huh0303-cmyk/-WP-QWEN-autobot/actions")
    body = os.getenv("REPORT_BODY", "자동발행 결과를 확인하세요.") + f"\n\n모바일 확인·업로드: {link}"
    results = {"email": send_email(title, body), "kakao": send_kakao(body, link), "url": link}
    print(json.dumps(results, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
