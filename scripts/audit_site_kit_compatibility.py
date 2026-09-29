"""Read-only installed-plugin and public tracking-tag inventory for 27 sites."""
import json
import os
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import requests

try:
    from site_registry import SITES
except ModuleNotFoundError:  # Imported as scripts.audit_site_kit_compatibility in tests.
    from scripts.site_registry import SITES


SAFE_CONNECTION_FIELDS = (
    "connected", "setupCompleted", "hasConnectedAdmins",
    "hasMultipleAdmins", "proxySetup",
)
SAFE_MODULE_FIELDS = (
    "slug", "active", "connected", "setupComplete", "recoverable", "shareable",
)


def safe_sitekit_connection(payload):
    """Keep connection evidence while excluding IDs, tokens and site secrets."""
    if not isinstance(payload, dict):
        return {}
    return {key: payload.get(key) for key in SAFE_CONNECTION_FIELDS if key in payload}


def safe_sitekit_modules(payload):
    modules = payload if isinstance(payload, list) else payload.get("modules", []) if isinstance(payload, dict) else []
    return [
        {key: item.get(key) for key in SAFE_MODULE_FIELDS if key in item}
        for item in modules
        if isinstance(item, dict)
    ]


def audit(site):
    url, key, _ = site
    row = {"site": url}
    try:
        if not os.getenv(key):
            raise ValueError("Missing site credential")
        auth = ("huh0303@gmail.com", os.environ[key])
        result = requests.get(url + "/wp-json/wp/v2/plugins", auth=auth, timeout=30)
        row["plugin_http_status"] = result.status_code
        result.raise_for_status()
        row["plugins"] = [{k: p.get(k) for k in ("plugin", "name", "status", "version", "requires_wp", "requires_php")} for p in result.json()]
        connection = requests.get(
            url + "/wp-json/google-site-kit/v1/core/site/data/connection",
            auth=auth, timeout=30,
        )
        row["sitekit_connection_http_status"] = connection.status_code
        if connection.ok:
            row["sitekit_connection"] = safe_sitekit_connection(connection.json())
        modules = requests.get(
            url + "/wp-json/google-site-kit/v1/core/modules/data/list",
            auth=auth, timeout=30,
        )
        row["sitekit_modules_http_status"] = modules.status_code
        if modules.ok:
            row["sitekit_modules"] = safe_sitekit_modules(modules.json())
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
