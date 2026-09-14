#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CEO 종합상황실 최종 승인본 보호 실행기.

2026-08-31 확정:
- 이메일은 KST 기준 하루 1통, schedule 실행에서만 발송.
- WP 일일방문자는 '어제 완료값'을 표시하고 괄호에는 전전일 대비 증감.
- 27개 WP 사이트를 번호로 한눈에 표시.
- 기존 situation_room_daily.py가 이후 수정되어도 이 승인 규칙은 여기서 강제한다.
"""
import json
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

import situation_room_daily as sr

STATE_FILE = Path(sr.REPO_ROOT) / "situation_room_email_state.json"


def approved_visitor_metrics(site_url):
    """최종 승인 기준: 어제 완료값 vs 전전일 완료값."""
    try:
        r = sr.requests.get(
            f"{site_url}/wp-json/site-stats/v1/visitors",
            headers={"User-Agent": "Mozilla/5.0"}, timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            yesterday = int(data.get("yesterday_count", 0))
            day_before = int(data.get("day_before_yesterday_count", 0))
            total = int(data.get("total", yesterday))
            return {
                "today": yesterday,
                "yesterday": day_before,
                "day_before_yesterday": day_before,
                "daily_delta": yesterday - day_before,
                "total": total,
                "total_delta": yesterday,
            }
    except Exception:
        pass
    return None


def approved_email_body(body):
    """최종 승인 이메일 가독성: WP 27개 번호 + 어제 완료 일일방문/증감 표기."""
    body = body.replace("오늘 방문자·증감 리포트", "CEO 종합상황실 일일보고")
    body = body.replace("오늘방문 합계", "일일방문 합계(어제 최종)")
    body = body.replace("오늘방문 ", "일일방문(어제) ")
    body = body.replace("실제방문자 합계(오늘)", "일일방문 합계(어제 최종)")
    body = body.replace("실제방문자(오늘)", "일일방문(어제)")

    lines = body.splitlines()
    in_wp = False
    rank = 0
    out = []
    for line in lines:
        if line.startswith("■ 사이트 "):
            in_wp = True
            rank = 0
            out.append(line)
            continue
        if in_wp and line.startswith("■ 유튜브"):
            in_wp = False
        if in_wp and line.startswith("  - "):
            rank += 1
            line = f"  {rank:02d}. " + line[4:]
        out.append(line)
    return "\n".join(out)


def _load_state():
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def approved_send_email(subject, body):
    """schedule + KST 날짜별 성공 잠금. 수동/재실행/중복 실행은 이메일 금지."""
    event = os.environ.get("GITHUB_EVENT_NAME", "")
    if event != "schedule":
        sr.log(f"📧 CEO 이메일 스킵: schedule 실행이 아님 ({event or 'local'})")
        return

    kst_date = datetime.now(sr.KST).strftime("%Y-%m-%d")
    state = _load_state()
    if state.get("last_success_kst_date") == kst_date:
        sr.log(f"📧 CEO 이메일 중복 차단: {kst_date} 이미 발송 완료")
        return

    if not sr.GMAIL_APP_PASSWORD:
        sr.log("⚠️ GMAIL_APP_PASSWORD 없음 — 이메일 스킵")
        return

    final_subject = f"[CEO 종합상황실] {kst_date} 일일보고"
    final_body = approved_email_body(body)
    msg = MIMEText(final_body, _charset="utf-8")
    msg["Subject"] = final_subject
    msg["From"] = sr.GMAIL_USER
    msg["To"] = sr.GMAIL_USER
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as smtp:
            smtp.login(sr.GMAIL_USER, sr.GMAIL_APP_PASSWORD)
            smtp.sendmail(sr.GMAIL_USER, [sr.GMAIL_USER], msg.as_string())
        STATE_FILE.write_text(json.dumps({
            "last_success_kst_date": kst_date,
            "approved_format": "2026-08-31-final",
            "rule": "one scheduled CEO email per KST day; yesterday vs day-before visitors",
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        sr.log(f"📧 CEO 종합상황실 이메일 발송 완료 + 날짜 잠금: {kst_date}")
    except Exception as exc:
        sr.log(f"⚠️ CEO 이메일 발송 실패(잠금 미기록, 다음 정상 실행 재시도 가능): {exc}")


def main():
    sr.get_visitor_metrics = approved_visitor_metrics
    sr.send_email = approved_send_email
    sr.main()


if __name__ == "__main__":
    main()
