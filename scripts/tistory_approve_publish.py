#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify one signed, single-use Tistory approval token and, only if it
passes, publish exactly the one article it authorizes.

Invoked exclusively by .github/workflows/tistory-approve-publish.yml, which
holds TISTORY_APPROVAL_SIGNING_SECRET and TISTORY_ACCESS_TOKEN as repo
secrets. The review page can only ask GitHub to start that workflow — it
never has these secrets and cannot publish anything by itself.

Exit codes: 0 = PUBLISHED, 1 = FAILED (a real publish attempt was made and
Tistory rejected it or credentials are missing), 2 = REJECTED (the token
itself did not verify — bad signature, expired, wrong job, replay of an
already-published job, or an unknown job_id).
"""
from __future__ import annotations

import argparse
import html as htmllib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
from tistory_approval_tokens import load_state, save_state, verify_token  # noqa: E402
from automation_hub.publishing import PublishJob  # noqa: E402
from automation_hub.tistory_adapter import TistoryPublisher  # noqa: E402


def _patch_review_page(page_path: Path, *, status: str, message: str, public_url: str = "") -> bool:
    if not page_path.exists():
        return False
    text = page_path.read_text(encoding="utf-8")
    if status == "PUBLISHED":
        banner = f'<div class="status-banner status-published">PUBLISHED — <a href="{htmllib.escape(public_url)}" target="_blank" rel="noopener">{htmllib.escape(public_url)}</a></div>'
    elif status == "FAILED":
        banner = f'<div class="status-banner status-failed">FAILED — {htmllib.escape(message)}</div>'
    else:
        return False
    marker_start, marker_end = "<!--STATUS_BANNER_START-->", "<!--STATUS_BANNER_END-->"
    if marker_start not in text or marker_end not in text:
        return False
    pre, rest = text.split(marker_start, 1)
    _, post = rest.split(marker_end, 1)
    text = pre + marker_start + banner + marker_end + post
    # Disable the approve button so a second click cannot re-fire a finished job.
    text = text.replace('onclick="approveAndPublish()"', 'onclick="approveAndPublish()" disabled')
    page_path.write_text(text, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--state-dir", default="state/tistory_approvals")
    parser.add_argument("--public-dir", default="public")
    args = parser.parse_args()

    job_id = args.job_id.strip()
    if ":" not in job_id:
        print(json.dumps({"status": "REJECTED", "reason": "malformed_job_id", "job_id": job_id}))
        return 2
    site_id, date = job_id.split(":", 1)

    ok, _payload, reason = verify_token(args.token, expected_job_id=job_id)
    if not ok:
        print(json.dumps({"status": "REJECTED", "reason": reason, "job_id": job_id}))
        return 2

    state = load_state(args.state_dir, date)
    entry = state.get("jobs", {}).get(job_id)
    if not entry:
        print(json.dumps({"status": "REJECTED", "reason": "unknown_job_id", "job_id": job_id}))
        return 2
    if entry.get("status") == "PUBLISHED":
        print(json.dumps({"status": "REJECTED", "reason": "already_published", "job_id": job_id, "public_url": entry.get("public_url", "")}))
        return 2

    job = PublishJob(
        job_id=job_id,
        site_id=site_id,
        title=entry.get("title", ""),
        content_html=entry.get("content_html", ""),
        labels=entry.get("labels") or [],
    )
    publisher = TistoryPublisher(site_id=site_id, blog_url=entry.get("blog_url", ""))
    result = publisher.publish(job, category=entry.get("category", ""), image_url=entry.get("image_public_url", ""))

    page_path = Path(args.public_dir) / "tistory-review" / date / site_id / "index.html"
    if result.ok:
        entry["status"] = "PUBLISHED"
        entry["public_url"] = result.public_url
        entry["remote_id"] = result.remote_id
        _patch_review_page(page_path, status="PUBLISHED", public_url=result.public_url, message="")
    else:
        entry["status"] = "FAILED"
        entry["error_code"] = result.error_code
        entry["error_message"] = result.message
        _patch_review_page(page_path, status="FAILED", message=f"{result.error_code}: {result.message}")

    state.setdefault("jobs", {})[job_id] = entry
    save_state(args.state_dir, date, state)

    output = {
        "status": entry["status"],
        "job_id": job_id,
        "public_url": entry.get("public_url", ""),
        "error_code": entry.get("error_code", ""),
        "error_message": entry.get("error_message", ""),
    }
    print(json.dumps(output, ensure_ascii=False))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
