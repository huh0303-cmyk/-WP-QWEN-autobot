#!/usr/bin/env python3
"""Read-only Facebook Page identity and publishing-task preflight."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
PAGES = (
    ("english", "FB_PAGE_ID_ENGLISH", "FB_PAGE_ACCESS_TOKEN_ENGLISH"),
    ("language", "FB_PAGE_ID_LANGUAGE", "FB_PAGE_ACCESS_TOKEN_LANGUAGE"),
)

def inspect_page(key: str, page_id: str, token: str, api_version: str = "v25.0", session=requests) -> dict:
    row = {
        "page_key": key,
        "page_id_present": bool(page_id),
        "token_present": bool(token),
        "publication_performed": False,
    }
    if not page_id or not token:
        row["status"] = "MISSING_PAGE_ID_OR_ACCESS_TOKEN"
        return row
    try:
        response = session.get(
            f"https://graph.facebook.com/{api_version}/{page_id}",
            params={"fields": "id,name,tasks", "access_token": token},
            timeout=20,
        )
        row["http_status"] = response.status_code
        payload = response.json() if response.content else {}
        if response.status_code != 200 or str(payload.get("id", "")) != page_id:
            error = payload.get("error", {}) if isinstance(payload, dict) else {}
            row["status"] = "INVALID_OR_UNAUTHORIZED_PAGE_TOKEN"
            row["error_code"] = error.get("code")
            return row
        tasks = payload.get("tasks") or []
        row["resolved_page_id"] = str(payload.get("id", ""))
        row["page_name"] = payload.get("name", "")
        row["tasks"] = [str(task) for task in tasks]
        row["create_content_task_present"] = any(
            task in {"CREATE_CONTENT", "MANAGE"} for task in row["tasks"]
        )
        row["status"] = (
            "PAGE_IDENTITY_AND_CREATE_TASK_VERIFIED"
            if row["create_content_task_present"]
            else "PAGE_IDENTITY_VERIFIED_WRITE_TASK_UNCONFIRMED"
        )
        return row
    except (requests.RequestException, ValueError, TypeError):
        row["status"] = "FACEBOOK_GRAPH_API_REQUEST_FAILED"
        return row

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-path", default="reports/facebook_page_preflight.json")
    args = parser.parse_args()
    version = os.getenv("META_GRAPH_API_VERSION", "v25.0").strip() or "v25.0"
    rows = [
        inspect_page(key, os.getenv(id_name, "").strip(), os.getenv(token_name, "").strip(), version)
        for key, id_name, token_name in PAGES
    ]
    verified = sum(row["status"] == "PAGE_IDENTITY_AND_CREATE_TASK_VERIFIED" for row in rows)
    report = {
        "expected_connections": len(PAGES),
        "identity_verified_connections": sum(row["status"].startswith("PAGE_IDENTITY_") for row in rows),
        "create_task_verified_connections": verified,
        "publish_enabled": False,
        "publication_performed": False,
        "connections": rows,
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    path = Path(args.report_path)
    if not path.is_absolute():
        path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["identity_verified_connections"] == len(PAGES) else 1

if __name__ == "__main__":
    raise SystemExit(main())
