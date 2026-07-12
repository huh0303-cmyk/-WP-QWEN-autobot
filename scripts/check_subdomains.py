#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""k-health365.com 서브도메인들이 실제로 접속 안 되는지(정리 완료됐는지) 점검"""
import requests

SUBDOMAINS = [
    "beauty.k-health365.com", "chronic-disease.k-health365.com",
    "dental-care.k-health365.com", "dentalcare.k-health365.com",
    "edu.k-health365.com", "functional-nutrition.k-health365.com",
    "health-devices.k-health365.com", "healthinsurance.k-health365.com",
    "medical-checkup.k-health365.com", "mental-health.k-health365.com",
    "money.k-health365.com", "nutrition-supplements.k-health365.com",
    "petcare.k-health365.com", "sleep-health.k-health365.com",
    "telemedicine.k-health365.com",
]

_LOG = []
def log(m=""):
    print(m)
    _LOG.append(str(m))

for sub in SUBDOMAINS:
    url = f"https://{sub}/"
    try:
        r = requests.get(url, timeout=15, allow_redirects=True)
        status = r.status_code
        final_url = r.url
        title_snip = ""
        if "<title>" in r.text.lower():
            try:
                title_snip = r.text.lower().split("<title>")[1].split("</title>")[0][:60]
            except Exception:
                pass
        alive = "❌ 아직 살아있음" if status == 200 else f"⚠️ status={status}"
        log(f"{sub:35s} {alive}  최종URL={final_url[:60]}  제목='{title_snip}'")
    except requests.exceptions.ConnectionError:
        log(f"{sub:35s} ✅ 정리완료 (연결 자체가 안 됨 = DNS 삭제 확인됨)")
    except requests.exceptions.Timeout:
        log(f"{sub:35s} ⚠️ 타임아웃 (판단 애매 — 재확인 필요)")
    except Exception as e:
        log(f"{sub:35s} ⚠️ 기타 오류: {type(e).__name__}: {str(e)[:80]}")

with open("subdomain_check_results.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(_LOG))
