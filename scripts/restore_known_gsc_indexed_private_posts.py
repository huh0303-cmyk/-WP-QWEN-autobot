"""Fast restore: publish only private posts already recorded as GSC indexed."""
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlparse

import requests

from site_registry import SITES

CONFIRM_PHRASE = "RESTORE-KNOWN-INDEXED-PRIVATE-ONLY"
EXCLUDED = {"k-health365.com", "koreanews365.com", "theseouljournal.com"}
SOURCE = Path(__file__).parent / "data" / "protected_indexed_posts.json"
OUTPUT = Path("restore_known_gsc_indexed_private_posts_result.json")


def host(value: str) -> str:
    value = value.strip().lower().rstrip("/")
    if "://" not in value:
        value = "https://" + value
    return (urlparse(value).hostname or "").removeprefix("www.")


def main() -> None:
    if os.getenv("CONFIRM") != CONFIRM_PHRASE:
        raise SystemExit("Confirmation phrase mismatch; no changes made.")

    saved = json.loads(SOURCE.read_text(encoding="utf-8"))
    indexed = {host(site): sorted({int(x) for x in ids}) for site, ids in saved.items()}
    registry = {host(url): (url.rstrip("/"), secret) for url, secret, _ in SITES}
    user = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
    result = {
        "mode": "known_gsc_indexed_ids_only",
        "excluded": sorted(EXCLUDED),
        "totals": {"requested": 0, "published": 0, "already_public": 0, "not_private": 0, "failed": 0},
        "sites": {},
    }

    for domain, ids in sorted(indexed.items()):
        if domain in EXCLUDED:
            continue
        row = {"requested": len(ids), "published": [], "already_public": [], "not_private": [], "failed": []}
        result["sites"][domain] = row
        result["totals"]["requested"] += len(ids)
        if not ids:
            continue
        if domain not in registry:
            row["failed"].append({"error": "site_not_in_registry"})
            result["totals"]["failed"] += len(ids)
            continue
        base, secret_name = registry[domain]
        password = os.getenv(secret_name, "")
        if not password:
            row["failed"].append({"error": f"missing_secret:{secret_name}"})
            result["totals"]["failed"] += len(ids)
            continue
        auth = (user, password)
        for post_id in ids:
            endpoint = f"{base}/wp-json/wp/v2/posts/{post_id}?context=edit"
            try:
                response = requests.get(endpoint, auth=auth, timeout=30)
                response.raise_for_status()
                status = response.json().get("status")
                if status == "publish":
                    row["already_public"].append(post_id)
                    result["totals"]["already_public"] += 1
                elif status == "private":
                    changed = requests.post(endpoint, auth=auth, json={"status": "publish"}, timeout=30)
                    changed.raise_for_status()
                    if changed.json().get("status") != "publish":
                        raise RuntimeError("WordPress did not return publish status")
                    row["published"].append(post_id)
                    result["totals"]["published"] += 1
                else:
                    row["not_private"].append({"id": post_id, "status": status})
                    result["totals"]["not_private"] += 1
            except Exception as exc:
                row["failed"].append({"id": post_id, "error": str(exc)[:500]})
                result["totals"]["failed"] += 1

    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["totals"], ensure_ascii=False))
    if result["totals"]["failed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
