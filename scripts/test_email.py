import os
import smtplib
from email.mime.text import MIMEText

WP_USER = "huh0303@gmail.com"
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]

msg = MIMEText("이 메일이 보이시면 GitHub Actions에서 이메일 알림이 정상 작동하는 겁니다.", _charset="utf-8")
msg["Subject"] = "✅ [WP감시] 이메일 알림 테스트 (GitHub Actions)"
msg["From"] = WP_USER
msg["To"] = WP_USER

try:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as s:
        s.login(WP_USER, GMAIL_APP_PASSWORD)
        s.sendmail(WP_USER, [WP_USER], msg.as_string())
    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {e}")
