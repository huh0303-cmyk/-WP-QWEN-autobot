#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""여러 업로드 스크립트가 각자의 성공/실패 결과를 한 곳에 쌓아두는 공용 모듈.
같은 워크플로우 실행(run) 안에서 순차적으로 여러 스크립트가 호출되며 이 파일에
결과를 append 하고, 맨 마지막 스텝(send_report_email.py)이 전체를 읽어 이메일로 보냄."""
import json, os, datetime

REPORT_PATH = "upload_report.json"

def add(platform, lang, status, detail=""):
    """status: 'success' 또는 'fail'"""
    rows = load()
    rows.append({
        "platform": platform, "lang": lang, "status": status, "detail": detail,
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

def load():
    if not os.path.exists(REPORT_PATH):
        return []
    try:
        with open(REPORT_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []
