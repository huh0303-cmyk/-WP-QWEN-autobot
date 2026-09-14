#!/usr/bin/env python3
"""Public, read-only audit of all 27 WordPress footers and visitor counters."""
from __future__ import annotations

import concurrent.futures
import re
import time

import requests

from site_registry import ACTIVE_SITES, SITES

REGULAR_URLS = {row[0].rstrip("/") for row in SITES[:-2]}
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Korea365FooterAudit/1.0"


def inspect_site(row: tuple[str, str, str]) -> dict:
    site = row[0].rstrip("/")
    result = {"site": site, "errors": []}
    for attempt in range(1, 5):
        try:
            response = requests.get(
                f"{site}/?footer_audit={int(time.time())}",
                timeout=25,
                headers={"User-Agent": UA, "Cache-Control": "no-cache"},
            )
            response.raise_for_status()
            html = response.text
            counter_count = html.count('<div class="network-daily-visitor-counter"')
            errors = [] if counter_count == 1 else [f"visitor counter count={counter_count}"]
            if site in REGULAR_URLS:
                footer_count = html.count('<nav class="network-utility-footer"')
                if footer_count != 1:
                    errors.append(f"utility footer count={footer_count}")
                footer_match = re.search(
                    r'<nav class="network-utility-footer".*?</nav>', html, re.I | re.S
                )
                footer_html = footer_match.group(0) if footer_match else ""
                if re.search(r"\\u[0-9a-fA-F]{4}", footer_html):
                    errors.append("literal Unicode escape in utility label")
            stats = requests.get(
                f"{site}/wp-json/site-stats/v1/visitors",
                timeout=25,
                headers={"User-Agent": UA, "Cache-Control": "no-cache"},
            )
            payload = stats.json() if stats.ok else {}
            required = {"count", "yesterday_count", "day_before_yesterday_count", "total"}
            if stats.status_code != 200 or not required.issubset(payload):
                errors.append(f"visitor API HTTP {stats.status_code} or missing fields")
            result.update({
                "counter_count": counter_count,
                "utility_footer_count": html.count('<nav class="network-utility-footer"'),
                "visitor_api_status": stats.status_code,
                "errors": errors,
            })
            if not errors or attempt == 4:
                return result
        except (requests.RequestException, ValueError) as exc:
            result["errors"] = [str(exc)]
            if attempt == 4:
                return result
        time.sleep(5)
    return result


def main() -> int:
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        rows = list(executor.map(inspect_site, ACTIVE_SITES))
    failed = [row for row in rows if row["errors"]]
    for row in rows:
        status = "PASS" if not row["errors"] else "FAIL"
        print(
            f"{status} {row['site']} counter={row.get('counter_count')} "
            f"footer={row.get('utility_footer_count')} api={row.get('visitor_api_status')} "
            f"errors={'; '.join(row['errors'])}"
        )
    if failed:
        raise SystemExit(f"WORDPRESS FOOTER AUDIT FAILED: {len(failed)}/{len(rows)}")
    print(f"WORDPRESS FOOTER AUDIT PASS: {len(rows)}/{len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
