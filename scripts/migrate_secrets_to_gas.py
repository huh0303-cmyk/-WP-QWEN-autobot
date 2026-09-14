#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
migrate_secrets_to_gas.py
─────────────────────────────────────────────────────────────
GitHub Actions 실행 중에만 접근 가능한 시크릿 값들을, 사람이 보거나
타이핑하지 않고 Google Apps Script 웹앱으로 직접 전송해서
스크립트 속성(Script Properties)에 저장합니다.
"""

import os
import requests

GAS_WEBAPP_URL = "https://script.google.com/macros/s/AKfycbyyaOJzG6zeu2ICyU9UEaNWIbMwibB4z5s4ZfeUzoZ17KCG3FLHNYF2xfBl6ATVVtHvzg/exec"
MIGRATION_TOKEN = "kuac2026-migrate"

SECRET_NAMES = [
    "KHEALTH365COM", "KOREAMEDICALTOURCOM", "KOREAINVEST365COM", "KIKOREACOM",
    "KOREAINSURANCE365COM", "KFINANCE365COM", "KOREATAXNLAWCOM", "KOREACRYPTO365COM",
    "KREALESTATE365COM", "KTECH365COM", "KSKIN365COM", "OLIVEYOUNGKOREACOM",
    "KWORLD365COM", "KTRIP365COM", "KVISA365COM", "KOREAWEDDING365COM",
    "KSTUDY365COM", "STUDYINKOREA365COM", "KIECAKOREAORG", "KSAKOREAORG",
    "SISKOREACOM", "JOBKOREA365COM", "JOBINKOREA365COM", "JOBKOREAGLOBALCOM",
    "KOREA365ORG", "KOREANEWS365COM", "THESEOULJOURNALCOM",
]


def main():
    secrets = {}
    missing = []
    for name in SECRET_NAMES:
        val = os.getenv(name, "")
        if val:
            secrets[name] = val
        else:
            missing.append(name)

    print(f"전송 대상: {len(secrets)}개 / 누락: {len(missing)}개")
    if missing:
        print("누락된 시크릿:", ", ".join(missing))

    payload = {"token": MIGRATION_TOKEN, "secrets": secrets}
    r = requests.post(GAS_WEBAPP_URL, json=payload, timeout=30)
    print(f"HTTP {r.status_code}")
    print(r.text[:500])


if __name__ == "__main__":
    main()
