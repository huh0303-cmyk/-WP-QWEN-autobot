#!/usr/bin/env python3
"""Issue a dedicated read-only OAuth token for GSC and AdSense metrics.

The resulting local file contains secrets and is intentionally stored under
`.local/`, which is excluded from version control.  The script never prints
the refresh token or client secret.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / ".local" / "gsc_adsense_oauth.json"
SCOPES = [
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/adsense.readonly",
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create one read-only refresh token for Search Console and AdSense."
    )
    parser.add_argument("client_secret_json", type=Path)
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()

    flow = InstalledAppFlow.from_client_secrets_file(str(args.client_secret_json), SCOPES)
    credentials = flow.run_local_server(
        host="localhost",
        port=args.port,
        open_browser=True,
        access_type="offline",
        prompt="consent",
        authorization_prompt_message="Open this URL to authorize read-only GSC and AdSense metrics:\n{url}",
        success_message="GSC and AdSense read-only authorization completed. You may close this tab.",
    )
    if not credentials.refresh_token:
        raise RuntimeError("Google did not return a refresh token; revoke the prior grant and retry.")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(
            {
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "refresh_token": credentials.refresh_token,
                "token_uri": credentials.token_uri,
                "scopes": list(credentials.scopes or SCOPES),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Authorization complete. Credentials saved securely to {OUTPUT}")
    print("Scopes: webmasters.readonly, adsense.readonly")


if __name__ == "__main__":
    main()
