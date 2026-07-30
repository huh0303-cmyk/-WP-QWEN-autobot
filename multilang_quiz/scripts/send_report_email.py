#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
전체 워크플로우가 끝난 뒤, report.py에 쌓인 결과를 취합해서
huh0303@gmail.com 으로 요약 메일을 보냅니다.

Gmail SMTP + 앱 비밀번호(App Password) 방식을 사용합니다 (무료, 별도 API 불필요).
필요 Secrets:
  ML_GMAIL_SENDER            - 보내는 사람 gmail 주소 (예: huh0303@gmail.com)
  ML_GMAIL_APP_PASSWORD      - 그 계정의 앱 비밀번호 (일반 로그인 비밀번호 아님)
선택 env:
  ML_REPORT_TO                - 받는 사람 이메일 (기본값: huh0303@gmail.com)
"""
import os, smtplib, datetime
from email.mime.text import MIMEText
import report
from common import get_secret

DEFAULT_TO = "huh0303@gmail.com"

def build_body(rows):
    if not rows:
        return "이번 실행에서 기록된 업로드 결과가 없습니다 (모든 단계가 건너뛰어졌을 수 있습니다)."

    lines = []
    ok = sum(1 for r in rows if r["status"] == "success")
    fail = sum(1 for r in rows if r["status"] == "fail")
    lines.append(f"총 {len(rows)}건 처리 - 성공 {ok}건 / 실패 {fail}건\n")

    by_platform = {}
    for r in rows:
        by_platform.setdefault(r["platform"], []).append(r)

    for platform, items in by_platform.items():
        lines.append(f"■ {platform}")
        for r in items:
            mark = "✅" if r["status"] == "success" else "❌"
            lines.append(f"  {mark} [{r['lang']}] {r['detail']}")
        lines.append("")

    return "\n".join(lines)

def main():
    rows = report.load()
    body = build_body(rows)

    sender = get_secret("ML_GMAIL_SENDER") or DEFAULT_TO
    password = get_secret("ML_GMAIL_APP_PASSWORD", "GMAIL_APP_PASSWORD")
    to_addr = os.environ.get("ML_REPORT_TO", DEFAULT_TO)

    print("=== 업로드 결과 요약 ===")
    print(body)

    if not sender or not password:
        print("\nML_GMAIL_SENDER / ML_GMAIL_APP_PASSWORD 미설정 - 이메일 발송 건너뜀 (위 로그로 대체 확인)")
        return

    today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = f"[다국어 퀴즈 자동발행 리포트] {today}"
    msg["From"] = sender
    msg["To"] = to_addr

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, [to_addr], msg.as_string())

    print(f"\n리포트 이메일 발송 완료 -> {to_addr}")

if __name__ == "__main__":
    main()
