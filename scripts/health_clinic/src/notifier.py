"""
5단계: 예약 발행 완료 사실을 huh0303@gmail.com 으로 메일 발송.
Gmail 앱 비밀번호 필요 (구글 계정 > 보안 > 2단계 인증 > 앱 비밀번호).
"""
import os
import smtplib
from email.mime.text import MIMEText

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def send_publish_notification(
    lang: str,
    title: str,
    video_url: str,
    publish_at_iso: str,
    drive_links: dict,
):
    to_addr = os.getenv("NOTIFY_EMAIL_TO", "huh0303@gmail.com")
    from_addr = os.getenv("NOTIFY_EMAIL_FROM", to_addr)
    app_password = os.getenv("GMAIL_APP_PASSWORD")

    body = f"""Health Clinic 자동 파이프라인 - 비공개 업로드 완료 보고 (검수 후 직접 공개해주세요)

■ 채널 언어: {lang.upper()}
■ 영상 제목: {title}
■ 유튜브 링크: {video_url}

■ Drive 저장 위치
  - 대본: {drive_links.get('script', '-')}
  - 영상: {drive_links.get('video', '-')}
  - 썸네일: {drive_links.get('thumbnail', '-')}

이 메일은 자동 발송되었습니다.
"""
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = f"[Health Clinic-{lang.upper()}] 비공개 업로드 완료: {title}"
    msg["From"] = from_addr
    msg["To"] = to_addr

    print("[Notify] 이메일 발송 중...")
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(from_addr, app_password)
        server.sendmail(from_addr, [to_addr], msg.as_string())
    print(f"[Notify] 발송 완료 → {to_addr}")
