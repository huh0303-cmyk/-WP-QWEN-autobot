"""Upload one generated identity mark and set both WordPress logo and site icon."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import requests


def main() -> int:
    site_url = os.environ["SITE_URL"].rstrip("/")
    site_id = os.environ["SITE_ID"]
    password = os.environ["WP_APP_PASSWORD"].strip()
    user = os.environ.get("WP_USER", "admin")
    path = Path("assets/site_logos/wordpress") / f"{site_id}.png"
    if not password or not path.exists():
        raise RuntimeError(f"Missing credential or logo asset for {site_id}")
    auth = (user, password)
    with path.open("rb") as handle:
        response = requests.post(
            f"{site_url}/wp-json/wp/v2/media", auth=auth, timeout=60,
            headers={"Content-Disposition": f'attachment; filename="{site_id}-logo.png"', "Content-Type": "image/png"},
            data=handle,
        )
    response.raise_for_status()
    media_id = int(response.json()["id"])
    settings = requests.post(
        f"{site_url}/wp-json/wp/v2/settings", auth=auth, timeout=45,
        json={"site_icon": media_id, "site_logo": media_id},
    )
    settings.raise_for_status()
    current = requests.get(f"{site_url}/wp-json/wp/v2/settings", auth=auth, timeout=45).json()
    if int(current.get("site_icon") or 0) != media_id:
        raise RuntimeError(f"Site icon verification failed for {site_id}")
    # Some classic themes do not expose site_logo; site_icon remains the universal identity fallback.
    print({"site_id": site_id, "media_id": media_id, "site_icon": current.get("site_icon"), "site_logo": current.get("site_logo")})
    return 0


if __name__ == "__main__":
    sys.exit(main())
