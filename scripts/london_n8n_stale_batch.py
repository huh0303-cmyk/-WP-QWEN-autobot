#!/usr/bin/env python3
"""Sequentially dispatch a reviewed stale-site manifest to the canonical n8n flow."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import secrets
import time
from urllib.parse import urlparse

import requests

KST = timezone(timedelta(hours=9))


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=KST)


def _latest_wordpress(url: str) -> dict:
    response = requests.get(
        url.rstrip("/") + "/wp-json/wp/v2/posts",
        params={"per_page": 1, "orderby": "date", "order": "desc", "status": "publish", "_fields": "id,date,link"},
        timeout=30,
    )
    response.raise_for_status()
    rows = response.json()
    if not rows:
        return {}
    row = rows[0]
    return {"published_at": row.get("date", ""), "url": row.get("link", ""), "post_id": str(row.get("id", ""))}


def _latest_blogger(url: str) -> dict:
    response = requests.get(
        url.rstrip("/") + "/feeds/posts/default",
        params={"alt": "json", "max-results": 1, "orderby": "published"},
        timeout=30,
    )
    response.raise_for_status()
    entries = response.json().get("feed", {}).get("entry", [])
    if not entries:
        return {}
    entry = entries[0]
    link = next((item.get("href", "") for item in entry.get("link", []) if item.get("rel") == "alternate"), "")
    raw_id = str(entry.get("id", {}).get("$t", ""))
    return {"published_at": entry.get("published", {}).get("$t", ""), "url": link, "post_id": raw_id.rsplit("-", 1)[-1]}


def _latest(target: dict) -> dict:
    return _latest_wordpress(target["url"]) if target["platform"] == "wordpress" else _latest_blogger(target["url"])


def _today_receipt(state_dir: Path, site_id: str) -> dict:
    prefix = "lgpt-" + datetime.now(KST).strftime("%Y%m%d") + "-"
    for path in sorted(state_dir.glob(prefix + "*.json"), reverse=True):
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        receipt = state.get("receipt") or {}
        if state.get("site_id") == site_id and state.get("stage_status", {}).get("publish") == "ok" and receipt.get("url"):
            return {"run_id": state.get("run_id"), **receipt}
    return {}


def _write_report(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _run_target(target: dict, cutoff: datetime, webhook: str, state_dir: Path, timeout: int) -> dict:
    site_id = target["site_id"]
    existing = _today_receipt(state_dir, site_id)
    if existing:
        return {"site_id": site_id, "platform": target["platform"], "status": "skipped_today_receipt", "receipt": existing}

    latest = _latest(target)
    if not latest.get("published_at"):
        return {"site_id": site_id, "platform": target["platform"], "status": "precheck_failed", "error": "latest public post unavailable"}
    latest_at = _dt(latest["published_at"]).astimezone(KST)
    baseline = _dt(target["baseline_recent"]).astimezone(KST)
    if latest_at > baseline + timedelta(minutes=2):
        return {"site_id": site_id, "platform": target["platform"], "status": "skipped_changed_since_scan", "latest": latest}
    if latest_at > cutoff:
        return {"site_id": site_id, "platform": target["platform"], "status": "skipped_not_stale", "latest": latest}

    now = datetime.now(KST)
    run_id = f"lgpt-{now.strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(3)}"
    response = requests.post(webhook, json={
        "site_id": site_id,
        "category": target.get("category", ""),
        "publish_mode": "publish",
        "run_id": run_id,
    }, timeout=20)
    if response.status_code >= 400:
        return {"site_id": site_id, "platform": target["platform"], "run_id": run_id,
                "status": "dispatch_failed", "http": response.status_code, "error": response.text[:500]}

    state_path = state_dir / f"{run_id}.json"
    deadline = time.time() + timeout
    last_state = {}
    while time.time() < deadline:
        if state_path.is_file():
            try:
                last_state = json.loads(state_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                time.sleep(2)
                continue
            stages = last_state.get("stage_status") or {}
            receipt = last_state.get("receipt") or {}
            if stages.get("publish") == "ok" and receipt.get("url") and receipt.get("post_id"):
                try:
                    public = requests.get(receipt["url"], timeout=30, allow_redirects=True)
                    verified = public.status_code == 200
                except requests.RequestException:
                    verified = False
                return {"site_id": site_id, "platform": target["platform"], "run_id": run_id,
                        "status": "published" if verified else "receipt_not_public", "receipt": receipt,
                        "keyword": (last_state.get("research") or {}).get("keyword", ""),
                        "title": (last_state.get("article") or {}).get("title", "")}
            if stages.get("publish") == "manual_required":
                return {"site_id": site_id, "platform": target["platform"], "run_id": run_id,
                        "status": "manual_required", "error": (last_state.get("manual_handoff") or {}).get("reason", "")}
            if last_state.get("last_error") or "failed" in stages.values():
                return {"site_id": site_id, "platform": target["platform"], "run_id": run_id,
                        "status": "failed", "error": last_state.get("last_error") or stages}
        time.sleep(2)
    return {"site_id": site_id, "platform": target["platform"], "run_id": run_id,
            "status": "timeout", "last_state": last_state.get("stage_status", {})}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--webhook", default="http://127.0.0.1:5678/webhook/london-content-four-agent")
    parser.add_argument("--state-dir", default="/opt/korea365/data/london-pipeline")
    parser.add_argument("--target-timeout", type=int, default=600)
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    report = {"task_id": manifest["task_id"], "started_at_kst": datetime.now(KST).isoformat(), "results": []}
    output = Path(args.output)
    cutoff = _dt(manifest["cutoff_kst"]).astimezone(KST)
    state_dir = Path(args.state_dir)
    for target in manifest["targets"]:
        try:
            result = _run_target(target, cutoff, args.webhook, state_dir, args.target_timeout)
        except Exception as exc:
            result = {"site_id": target.get("site_id"), "platform": target.get("platform"),
                      "status": "precheck_failed", "error": f"{type(exc).__name__}: {str(exc)[:500]}"}
        report["results"].append(result)
        report["updated_at_kst"] = datetime.now(KST).isoformat()
        _write_report(output, report)
        print("BATCH_RESULT " + json.dumps(result, ensure_ascii=False), flush=True)

    report["completed_at_kst"] = datetime.now(KST).isoformat()
    report["counts"] = {}
    for row in report["results"]:
        status = row["status"]
        report["counts"][status] = report["counts"].get(status, 0) + 1
    _write_report(output, report)
    print("BATCH_SUMMARY " + json.dumps(report["counts"], ensure_ascii=False), flush=True)
    return 0 if all(row["status"] in {"published", "skipped_today_receipt", "skipped_changed_since_scan", "skipped_not_stale"}
                    for row in report["results"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
