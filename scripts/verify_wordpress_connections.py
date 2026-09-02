"""Read-only authentication check for every registered WordPress site."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "config" / "automation_hub_sites.json"
WP_USER = os.getenv("WP_USER", "huh0303@gmail.com").strip()


def main() -> int:
    rows = json.loads(REGISTRY.read_text(encoding="utf-8"))
    sites = [row for row in rows if row.get("platform") == "wordpress"]
    results: list[dict] = []

    for site in sites:
        secret_name = str(site.get("secret_name", "")).strip()
        password = os.getenv(secret_name, "").strip()
        result = {
            "site_id": site.get("site_id"),
            "url": site.get("url"),
            "secret_name": secret_name,
            "ok": False,
        }
        if not password:
            result["error"] = "missing_secret"
        else:
            endpoint = str(site["url"]).rstrip("/") + "/wp-json/wp/v2/users/me"
            try:
                response = requests.get(
                    endpoint,
                    auth=(WP_USER, password),
                    params={"context": "edit"},
                    timeout=20,
                    headers={"User-Agent": "Korea365-Connection-Verifier/1.0"},
                )
                result["http_status"] = response.status_code
                result["ok"] = response.status_code == 200
                if result["ok"]:
                    payload = response.json()
                    result["user_id"] = payload.get("id")
                    result["user_name"] = payload.get("name")
                else:
                    result["error"] = "authentication_or_rest_error"
            except requests.RequestException as exc:
                result["error"] = type(exc).__name__
        results.append(result)
        print(f"{'PASS' if result['ok'] else 'FAIL'} {site['site_id']} {site['url']}")

    summary = {
        "expected": 27,
        "checked": len(results),
        "passed": sum(1 for item in results if item["ok"]),
        "failed": sum(1 for item in results if not item["ok"]),
        "results": results,
    }
    output = ROOT / "wordpress_connection_report.json"
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: summary[key] for key in ("expected", "checked", "passed", "failed")}))
    return 0 if summary["checked"] == summary["expected"] and summary["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
