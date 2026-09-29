from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "adsense_revenue_by_domain.json"
KST = timezone(timedelta(hours=9))


def parse_domain_report(payload: dict) -> dict[str, float]:
    domains: dict[str, float] = {}
    for row in payload.get("rows") or []:
        cells = row.get("cells") or []
        if len(cells) < 2:
            continue
        domain = str(cells[0].get("value") or "").strip().lower().removeprefix("www.")
        try:
            amount = round(float(cells[1].get("value")), 2)
        except (TypeError, ValueError):
            continue
        if domain:
            domains[domain] = amount
    return domains


def main() -> None:
    required = (
        "GOOGLE_METRICS_CLIENT_ID",
        "GOOGLE_METRICS_CLIENT_SECRET",
        "GOOGLE_METRICS_REFRESH_TOKEN",
    )
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise SystemExit("Missing Google metrics credentials: " + ", ".join(missing))

    token_response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": os.environ["GOOGLE_METRICS_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_METRICS_CLIENT_SECRET"],
            "refresh_token": os.environ["GOOGLE_METRICS_REFRESH_TOKEN"],
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    token_response.raise_for_status()
    headers = {"Authorization": f"Bearer {token_response.json()['access_token']}"}
    accounts_response = requests.get(
        "https://adsense.googleapis.com/v2/accounts", headers=headers, timeout=30
    )
    accounts_response.raise_for_status()
    accounts = accounts_response.json().get("accounts") or []
    if not accounts:
        raise SystemExit("No AdSense account is available to this credential")

    account = accounts[0]["name"]
    report_response = requests.get(
        f"https://adsense.googleapis.com/v2/{account}/reports:generate",
        headers=headers,
        params=[
            ("dimensions", "OWNED_SITE_DOMAIN_NAME"),
            ("metrics", "ESTIMATED_EARNINGS"),
            ("dateRange", "YEAR_TO_DATE"),
            ("currencyCode", "USD"),
            ("reportingTimeZone", "GOOGLE_TIME_ZONE"),
        ],
        timeout=60,
    )
    report_response.raise_for_status()
    domains = parse_domain_report(report_response.json())
    payload = {
        "checked_at_kst": datetime.now(KST).isoformat(),
        "date_range": "YEAR_TO_DATE",
        "currency": "USD",
        "domains": domains,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved cumulative AdSense revenue for {len(domains)} domains")


if __name__ == "__main__":
    main()
