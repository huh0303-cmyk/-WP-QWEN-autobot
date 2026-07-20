#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
27개 사이트 발행 감시 (Watchdog)
1) 최근 STALE_HOURS 이내에 새 글이 실제 발행됐는지 확인
2) 실패 사이트 발견 시 즉시 Plan B: 해당 사이트만 재발행 트리거 (GitHub workflow_dispatch)
3) 이메일로 1차 알림 발송
4) WAIT_MINUTES 대기 후 재확인
5) 그래도 실패 -> Plan C: 에스컬레이션 이메일(에러 로그 포함)
"""
import os
import sys
import time
import smtplib
import requests
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta

WP_USER = "huh0303@gmail.com"
GH_TOKEN = os.environ.get("GH_DISPATCH_TOKEN") or os.environ["GH_TOKEN"]
REPO = "huh0303-cmyk/-WP-QWEN-autobot"
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
ALERT_TO = "huh0303@gmail.com"

STALE_HOURS = 20        # 이 시간 동안 새 글이 없으면 "발행 실패"로 간주
WAIT_MINUTES = 12       # Plan B 재시도 후 이만큼 기다렸다가 재확인

SITES = [
    ("https://k-health365.com", "KHEALTH365COM"), ("https://koreamedicaltour.com", "KOREAMEDICALTOURCOM"),
    ("https://koreainvest365.com", "KOREAINVEST365COM"), ("https://ki-korea.com", "KIKOREACOM"),
    ("https://koreainsurance365.com", "KOREAINSURANCE365COM"), ("https://kfinance365.com", "KFINANCE365COM"),
    ("https://koreataxnlaw.com", "KOREATAXNLAWCOM"), ("https://koreacrypto365.com", "KOREACRYPTO365COM"),
    ("https://krealestate365.com", "KREALESTATE365COM"), ("https://ktech365.com", "KTECH365COM"),
    ("https://kskin365.com", "KSKIN365COM"), ("https://oliveyoungkorea.com", "OLIVEYOUNGKOREACOM"),
    ("https://kworld365.com", "KWORLD365COM"), ("https://k-trip365.com", "KTRIP365COM"),
    ("https://k-visa365.com", "KVISA365COM"), ("https://koreawedding365.com", "KOREAWEDDING365COM"),
    ("https://kstudy365.com", "KSTUDY365COM"), ("https://studyinkorea365.com", "STUDYINKOREA365COM"),
    ("https://kieca-korea.org", "KIECAKOREAORG"), ("https://ksa-korea.org", "KSAKOREAORG"),
    ("https://sis-korea.com", "SISKOREACOM"), ("https://jobkorea365.com", "JOBKOREA365COM"),
    ("https://jobinkorea365.com", "JOBINKOREA365COM"), ("https://jobkoreaglobal.com", "JOBKOREAGLOBALCOM"),
    ("https://korea365.org", "KOREA365ORG"), ("https://koreanews365.com", "KOREANEWS365COM"),
    ("https://theseouljournal.com", "THESEOULJOURNALCOM"),
]


def send_email(subject, body):
    if not GMAIL_APP_PASSWORD:
        print("⚠️ GMAIL_APP_PASSWORD 없음 - 이메일 발송 스킵")
        print(f"[메일내용]\n제목: {subject}\n{body}")
        return
    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = WP_USER
    msg["To"] = ALERT_TO
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as s:
            s.login(WP_USER, GMAIL_APP_PASSWORD)
            s.sendmail(WP_USER, [ALERT_TO], msg.as_string())
        print(f"✅ 이메일 발송 완료: {subject}")
    except Exception as e:
        print(f"⚠️ 이메일 발송 실패: {e}")


def get_latest_post_time(site_url, wp_pass):
    try:
        r = requests.get(f"{site_url}/wp-json/wp/v2/posts",
                          auth=(WP_USER, wp_pass) if wp_pass else None,
                          params={"per_page": 1, "orderby": "date", "order": "desc",
                                  "_fields": "date_gmt"}, timeout=20)
        if r.status_code == 200 and isinstance(r.json(), list) and r.json():
            date_str = r.json()[0]["date_gmt"]
            return datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
    except Exception as e:
        print(f"  조회 오류: {e}")
    return None


def check_all_sites():
    now = datetime.now(timezone.utc)
    failed = []
    for url, env_key in SITES:
        wp_pass = os.getenv(env_key, "")
        latest = get_latest_post_time(url, wp_pass)
        if latest is None:
            failed.append((url, env_key, "조회 실패(사이트 접속 불가 가능성)"))
            continue
        hours_since = (now - latest).total_seconds() / 3600
        status = "OK" if hours_since <= STALE_HOURS else "STALE"
        print(f"{url}: 최근글 {hours_since:.1f}시간 전 [{status}]")
        if status == "STALE":
            failed.append((url, env_key, f"{hours_since:.1f}시간 동안 새 글 없음"))
    return failed


def trigger_republish(site_url):
    """해당 사이트만 즉시 재발행 시도 (전체 워크플로우를 강제로 한번 더 돌림)"""
    r = requests.post(
        f"https://api.github.com/repos/{REPO}/actions/workflows/master_autopost.yml/dispatches",
        headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github+json"},
        json={"ref": "main", "inputs": {"step": "post", "run_slot": "1"}},
        timeout=20,
    )
    return r.status_code


def main():
    print(f"=== 발행 감시 시작: {datetime.now(timezone.utc).isoformat()} ===")
    failed = check_all_sites()

    if not failed:
        print("전체 정상 — 알림 없음")
        return

    # Plan B: 즉시 재시도 + 1차 알림
    body_lines = [f"발행 실패 감지: {len(failed)}개 사이트\n"]
    for url, env_key, reason in failed:
        body_lines.append(f"- {url}: {reason}")
    body_lines.append("\n→ Plan B로 전체 재발행 워크플로우를 즉시 재트리거했습니다.")
    body = "\n".join(body_lines)

    print(body)
    send_email(f"⚠️ [WP감시] 발행실패 {len(failed)}건 감지 - 재시도 중", body)

    status = trigger_republish(None)
    print(f"재발행 트리거 상태: {status}")

    # 대기 후 재확인 (Plan C)
    print(f"{WAIT_MINUTES}분 대기 후 재확인...")
    time.sleep(WAIT_MINUTES * 60)

    still_failed = check_all_sites()
    still_failed_urls = {f[0] for f in still_failed}
    resolved = [f for f in failed if f[0] not in still_failed_urls]
    unresolved = [f for f in failed if f[0] in still_failed_urls]

    if not unresolved:
        send_email(
            "✅ [WP감시] 재시도로 전부 정상화됨",
            f"Plan B 재시도로 아래 사이트들이 정상화됐습니다:\n" + "\n".join(f"- {u}" for u, _, _ in resolved),
        )
    else:
        esc_body = ["⚠️ Plan B(자동 재시도)로도 해결 안 된 사이트가 있습니다. 직접 확인이 필요합니다.\n"]
        for url, env_key, reason in unresolved:
            esc_body.append(f"- {url}: {reason}")
        esc_body.append(f"\n확인 링크: https://github.com/{REPO}/actions/workflows/master_autopost.yml")
        send_email(f"🚨 [WP감시] Plan C 필요 - {len(unresolved)}개 사이트 여전히 발행 실패", "\n".join(esc_body))


if __name__ == "__main__":
    main()
