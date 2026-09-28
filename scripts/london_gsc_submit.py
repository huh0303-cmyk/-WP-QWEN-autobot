#!/usr/bin/env python3
"""Submit the selected site's sitemap from GitHub Actions, then write a receipt."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import quote, urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.submit_khealth_sitemap import access_token

RUN_PATTERN = re.compile(r"lgpt-[0-9]{8}-[0-9]{6}-[a-f0-9]{6}\Z")


def expected_site(site_id: str) -> tuple[str, str]:
    platform = "wordpress" if site_id.startswith("wp_") else "blogger" if site_id.startswith("blogger_") else ""
    if not platform:
        raise ValueError("invalid site ID")
    site_key = site_id.removeprefix("wp_").removeprefix("blogger_")
    profiles = json.loads((ROOT / "config" / "content_engine_profiles.json").read_text(encoding="utf-8"))["profiles"]
    profile = next((item for item in profiles if item.get("site_key") == site_key), None)
    if not profile:
        raise ValueError("unknown site ID")
    settings = profile["wordpress" if platform == "wordpress" else "blogspot"]
    return platform, str(settings["url"]).rstrip("/")


def validate_url(public_url: str, site_url: str) -> None:
    parsed, expected = urlparse(public_url), urlparse(site_url)
    if (parsed.scheme != "https" or parsed.hostname != expected.hostname or
            parsed.port not in (None, 443) or parsed.username or parsed.password or
            not parsed.path.strip("/")):
        raise ValueError("published URL is outside selected site")


def select_property(entries: list[dict], domain: str) -> str:
    candidates = (f"sc-domain:{domain}", f"https://{domain}/", f"https://www.{domain}/")
    permitted = {row.get("siteUrl") for row in entries if row.get("permissionLevel") not in (None, "siteUnverifiedUser")}
    return next((candidate for candidate in candidates if candidate in permitted), "")


def submit(run_id: str, site_id: str, public_url: str, *, dry_run: bool = False) -> dict:
    if not RUN_PATTERN.fullmatch(run_id):
        raise ValueError("invalid run ID")
    platform, site_url = expected_site(site_id)
    validate_url(public_url, site_url)
    response = requests.get(public_url, timeout=25, allow_redirects=False)
    if response.status_code != 200 or "html" not in response.headers.get("content-type", "").lower():
        raise RuntimeError(f"published page verification HTTP {response.status_code}")
    if "noindex" in response.headers.get("x-robots-tag", "").lower() or re.search(r'<meta[^>]+name=["\']robots["\'][^>]+content=["\'][^"\']*noindex', response.text, re.I):
        raise RuntimeError("published page has noindex")
    sitemap = f"{site_url}/{'sitemap_index.xml' if platform == 'wordpress' else 'sitemap.xml'}"
    sitemap_response = requests.get(sitemap, timeout=25, allow_redirects=True)
    if sitemap_response.status_code != 200:
        raise RuntimeError(f"sitemap HTTP {sitemap_response.status_code}")
    raw = os.environ.get("GSC_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw:
        raise RuntimeError("GSC_SERVICE_ACCOUNT_JSON is missing")
    token = access_token(json.loads(raw))
    headers = {"Authorization": f"Bearer {token}"}
    base = "https://www.googleapis.com/webmasters/v3"
    sites = requests.get(f"{base}/sites", headers=headers, timeout=30)
    sites.raise_for_status()
    domain = urlparse(site_url).hostname or ""
    prop = select_property(sites.json().get("siteEntry", []), domain)
    if not prop:
        raise RuntimeError(f"GSC service account has no verified property for {domain}")
    if dry_run:
        return {"status": "ready", "property": prop, "sitemap_url": sitemap}
    endpoint = f"{base}/sites/{quote(prop, safe='')}/sitemaps/{quote(sitemap, safe='')}"
    submitted = requests.put(endpoint, headers=headers, timeout=30)
    if submitted.status_code not in (200, 204):
        raise RuntimeError(f"GSC sitemap submit HTTP {submitted.status_code}: {submitted.text[:180]}")
    checked = requests.get(endpoint, headers=headers, timeout=30)
    checked.raise_for_status()
    return {"status": "submitted", "property": prop, "sitemap_url": sitemap,
            "last_submitted": checked.json().get("lastSubmitted")}


def main() -> int:
    run_id = os.environ.get("LONDON_RUN_ID", "")
    if not RUN_PATTERN.fullmatch(run_id):
        raise SystemExit("invalid run ID")
    output = ROOT / "artifacts" / "london-gsc-receipts"
    output.mkdir(parents=True, exist_ok=True)
    result = {"run_id": run_id, "site_id": os.environ.get("LONDON_SITE_ID", ""),
              "url": os.environ.get("LONDON_PUBLIC_URL", ""), "at": datetime.now(timezone.utc).isoformat()}
    try:
        result.update(submit(run_id, result["site_id"], result["url"],
                             dry_run=os.environ.get("LONDON_GSC_DRY_RUN") == "true"))
    except Exception as exc:
        result.update(status="failed", error=f"{type(exc).__name__}: {exc}"[:300])
    (output / f"{run_id}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "url"}, ensure_ascii=False))
    return 0 if result["status"] in {"submitted", "ready"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
