"""Read-only installed-plugin and public tracking-tag inventory for 27 sites."""
import json
import os
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import requests
from site_registry import SITES


def audit(site):
    url, key, _ = site
    row = {"site": url}
    try:
        if not os.getenv(key):
            raise ValueError("Missing site credential")
        result = requests.get(url + "/wp-json/wp/v2/plugins", auth=("huh0303@gmail.com", os.environ[key]), timeout=30)
        row["plugin_http_status"] = result.status_code
        result.raise_for_status()
        row["plugins"] = [{k: p.get(k) for k in ("plugin", "name", "status", "version", "requires_wp", "requires_php")} for p in result.json()]
        result = requests.get(url, timeout=30)
        row["homepage_http_status"] = result.status_code
        row["tracking_ids"] = sorted(set(re.findall(r"\b(?:G-[A-Z0-9]{6,}|GTM-[A-Z0-9]+|ca-pub-\d+)\b", result.text)))
        row["sitekit_public_marker"] = "google-site-kit" in result.text or "Google Site Kit" in result.text
        row["rankmath_public_marker"] = "Rank Math" in result.text
        row["status"] = "audited"
    except (requests.RequestException, ValueError, TypeError) as exc:
        row.update(status="needs_access_check", error=type(exc).__name__)
    print(json.dumps({k:v for k,v in row.items() if k != "plugins"}), flush=True)
    return row


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(audit, SITES))
    output = Path("artifacts/site-kit-audit")
    output.mkdir(parents=True, exist_ok=True)
    (output / "results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
