#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
import time

WP_USER = "huh0303@gmail.com"
WP_PASS = "Huh522676!"

SITES = [
    "https://k-health365.com",
    "https://koreamedicaltour.com",
    "https://koreainvest365.com",
    "https://ki-korea.com",
    "https://koreainsurance365.com",
    "https://kfinance365.com",
    "https://koreataxnlaw.com",
    "https://koreacrypto365.com",
    "https://krealestate365.com",
    "https://ktech365.com",
    "https://kskin365.com",
    "https://oliveyoungkorea.com",
    "https://kworld365.com",
    "https://k-trip365.com",
    "https://k-visa365.com",
    "https://koreawedding365.com",
    "https://kstudy365.com",
    "https://studyinkorea365.com",
    "https://kieca-korea.org",
    "https://ksa-korea.org",
    "https://sis-korea.com",
    "https://jobkorea365.com",
    "https://jobinkorea365.com",
    "https://jobkoreaglobal.com",
    "https://korea365.org",
    "https://koreanews365.com",
    "https://theseouljournal.com",
]

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

results = []

def process_site(site):
    s = requests.Session()
    s.headers.update(HEADERS)
    try:
        s.get(f"{site}/wp-login.php", timeout=20)
        login_data = {
            "log": WP_USER,
            "pwd": WP_PASS,
            "wp-submit": "Log In",
            "redirect_to": f"{site}/wp-admin/",
            "testcookie": "1",
        }
        s.post(f"{site}/wp-login.php", data=login_data, timeout=20)

        r = s.get(f"{site}/wp-admin/options-discussion.php", timeout=20)
        if r.status_code != 200 or "comments_notify" not in r.text:
            return (site, "FAIL", f"설정페이지 접근 실패 (HTTP {r.status_code}) 또는 로그인 실패")

        soup = BeautifulSoup(r.text, "html.parser")
        forms = soup.find_all("form")
        target = None
        for f in forms:
            if f.find("input", {"name": "comments_notify"}):
                target = f
                break
        if target is None:
            return (site, "FAIL", "설정 폼을 찾을 수 없음")

        payload = {}
        skip_checkboxes = {"comments_notify", "moderation_notify"}  # 이 두 개는 강제로 끔(=폼에서 제외)

        seen_radio_names = set()
        for el in target.find_all(["input", "textarea", "select"]):
            name = el.get("name")
            if not name:
                continue
            tag = el.name
            itype = el.get("type", "text") if tag == "input" else tag

            if itype == "checkbox":
                if name in skip_checkboxes:
                    continue  # 체크 해제 = 폼에서 제외
                if el.has_attr("checked"):
                    payload[name] = el.get("value", "1")
                # 체크 안 된 기존 체크박스는 그대로 제외(유지)
            elif itype == "radio":
                if el.has_attr("checked"):
                    payload[name] = el.get("value", "")
            elif tag == "select":
                selected = el.find("option", selected=True)
                if selected is None:
                    selected = el.find("option")
                if selected is not None:
                    payload[name] = selected.get("value", selected.text.strip())
            elif tag == "textarea":
                payload[name] = el.text
            else:
                payload[name] = el.get("value", "")

        payload["submit"] = "변경 사항 저장"

        r2 = s.post(f"{site}/wp-admin/options.php", data=payload, timeout=20, allow_redirects=True)
        if r2.status_code == 200:
            # 검증: 다시 설정 페이지 열어서 comments_notify가 꺼졌는지 확인
            r3 = s.get(f"{site}/wp-admin/options-discussion.php", timeout=20)
            soup3 = BeautifulSoup(r3.text, "html.parser")
            cn = soup3.find("input", {"name": "comments_notify"})
            mn = soup3.find("input", {"name": "moderation_notify"})
            cn_off = cn is None or not cn.has_attr("checked")
            mn_off = mn is None or not mn.has_attr("checked")
            if cn_off and mn_off:
                return (site, "OK", "댓글 알림 이메일 2개 항목 모두 해제 확인됨")
            else:
                return (site, "PARTIAL", f"저장은 됐으나 확인 실패 (comments_notify off={cn_off}, moderation_notify off={mn_off})")
        else:
            return (site, "FAIL", f"저장 요청 실패 HTTP {r2.status_code}")
    except Exception as e:
        return (site, "ERROR", str(e))

for site in SITES:
    res = process_site(site)
    print(res)
    results.append(res)
    time.sleep(1)

print("\n===== 요약 =====")
ok = [r for r in results if r[1] == "OK"]
fail = [r for r in results if r[1] != "OK"]
print(f"성공: {len(ok)}/{len(results)}")
for r in fail:
    print("  실패:", r)

with open("/home/claude/disable_comment_notify_result.txt", "w", encoding="utf-8") as f:
    for r in results:
        f.write(f"{r[0]} | {r[1]} | {r[2]}\n")
