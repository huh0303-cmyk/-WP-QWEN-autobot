#!/usr/bin/env python3
"""Verify the dedicated read-only GSC + AdSense OAuth grant."""
from __future__ import annotations

import json
from pathlib import Path

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


ROOT = Path(__file__).resolve().parents[1]
CREDENTIALS_PATH = ROOT / ".local" / "gsc_adsense_oauth.json"
EXPECTED_SCOPES = {
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/adsense.readonly",
}


def main() -> None:
    data = json.loads(CREDENTIALS_PATH.read_text(encoding="utf-8"))
    scopes = set(data.get("scopes") or [])
    if not EXPECTED_SCOPES.issubset(scopes):
        raise RuntimeError(f"Missing expected read-only scopes: {sorted(EXPECTED_SCOPES - scopes)}")

    credentials = Credentials(
        token=None,
        refresh_token=data["refresh_token"],
        token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=data["client_id"],
        client_secret=data["client_secret"],
        scopes=sorted(EXPECTED_SCOPES),
    )
    credentials.refresh(Request())
    headers = {"Authorization": f"Bearer {credentials.token}"}

    gsc = requests.get(
        "https://www.googleapis.com/webmasters/v3/sites", headers=headers, timeout=30
    )
    gsc.raise_for_status()
    gsc_count = len(gsc.json().get("siteEntry", []))

    adsense = requests.get(
        "https://adsense.googleapis.com/v2/accounts", headers=headers, timeout=30
    )
    adsense.raise_for_status()
    adsense_accounts = adsense.json().get("accounts", [])

    print(f"GSC read-only verification: PASS ({gsc_count} accessible properties)")
    print(f"AdSense read-only verification: PASS ({len(adsense_accounts)} accessible accounts)")
    for account in adsense_accounts:
        print(f"AdSense account: {account.get('displayName', 'unnamed')} / state={account.get('state', 'unknown')}")


if __name__ == "__main__":
    main()
