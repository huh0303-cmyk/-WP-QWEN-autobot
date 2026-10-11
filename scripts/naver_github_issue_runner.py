#!/usr/bin/env python3
"""Local Naver publisher consuming GitHub Issues queue items.

Use on the trusted PC with a persistent, logged-in Playwright profile:
  python scripts/naver_github_issue_runner.py login --site-id huh0303
  python scripts/naver_github_issue_runner.py run --site-id huh0303
Required env: GH_PAT. This runner does not read Google Sheets.
"""
from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automation_hub.naver_local_adapter import NaverLocalPublisher
from automation_hub.publishing import PublishJob

REPO_OWNER = os.getenv("GITHUB_REPO_OWNER", "huh0303-cmyk").strip()
REPO_NAME = os.getenv("GITHUB_REPO_NAME", "-WP-QWEN-autobot").strip()
API_ROOT = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"
GH_PAT = os.getenv("GH_PAT", "").strip()
STATUS_READY = "queue:ready"
STATUS_PROCESSING = "queue:processing"
STATUS_PUBLISHED = "queue:published"
STATUS_DRAFT_SAVED = "queue:draft-saved"
STATUS_FAILED = "queue:failed"
STATUS_ATTENTION = "queue:attention"
ACCOUNT_PREFIX = "blog:"
BODY_MARKER = "### 📝 블로그 본문 데이터"
TIMEOUT = (5, 30)

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("naver-github-issue-runner")


def api(method: str, path: str, **kwargs: Any) -> requests.Response:
    response = requests.request(
        method, f"{API_ROOT}{path}",
        headers={
            "Authorization": f"Bearer {GH_PAT}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=TIMEOUT,
        **kwargs,
    )
    if not response.ok:
        raise RuntimeError(f"GitHub API HTTP {response.status_code} for {method} {path}: {response.text[:300]}")
    return response


def ensure_label(name: str, color: str, description: str) -> None:
    response = requests.get(
        f"{API_ROOT}/labels/{requests.utils.quote(name, safe='')}",
        headers={
            "Authorization": f"Bearer {GH_PAT}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=TIMEOUT,
    )
    if response.status_code == 200:
        return
    if response.status_code != 404:
        raise RuntimeError(f"GitHub label lookup failed: HTTP {response.status_code}")
    created = requests.post(
        f"{API_ROOT}/labels",
        headers={
            "Authorization": f"Bearer {GH_PAT}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json={"name": name, "color": color, "description": description[:100]},
        timeout=TIMEOUT,
    )
    if created.status_code not in {201, 422}:
        raise RuntimeError(f"GitHub label creation failed: HTTP {created.status_code}")


def ensure_queue_labels(blog_id: str) -> None:
    labels = (
        (STATUS_READY, "1D76DB", "Waiting for local Naver draft save"),
        (STATUS_PROCESSING, "FBCA04", "Claimed by local Naver runner"),
        (STATUS_PUBLISHED, "0E8A16", "Public URL verified"),
        (STATUS_DRAFT_SAVED, "0E8A16", "Naver draft save confirmed"),
        (STATUS_FAILED, "B60205", "Queue processing failed"),
        (STATUS_ATTENTION, "D93F0B", "Human review required"),
        (f"{ACCOUNT_PREFIX}{blog_id}", "5319E7", f"Naver blog account {blog_id}"),
    )
    for name, color, description in labels:
        ensure_label(name, color, description)


def get_ready_issues(blog_id: str, max_jobs: int) -> list[dict[str, Any]]:
    response = api(
        "GET", "/issues",
        params={"state": "open", "labels": f"{STATUS_READY},{ACCOUNT_PREFIX}{blog_id}", "per_page": min(100, max_jobs), "sort": "created", "direction": "asc"},
    )
    issues = response.json()
    return [item for item in issues if "pull_request" not in item][:max_jobs]


def replace_status(issue: dict[str, Any], status: str) -> None:
    labels = [
        item["name"] for item in issue.get("labels", [])
        if not str(item.get("name", "")).startswith("queue:")
    ]
    labels.append(status)
    api("PUT", f"/issues/{issue['number']}/labels", json={"labels": labels})


def add_comment(issue_number: int, text: str) -> None:
    api("POST", f"/issues/{issue_number}/comments", json={"body": text})


def parse_job(issue: dict[str, Any], blog_id: str) -> PublishJob:
    title = re.sub(r"^\[발행대기\](?:\[[^\]]+\])?\s*", "", issue.get("title", "")).strip()
    body = issue.get("body") or ""
    if BODY_MARKER not in body:
        raise ValueError("이슈 본문에 블로그 본문 데이터 표식이 없습니다.")
    content = body.split(BODY_MARKER, 1)[1]
    content = re.split(r"\n\n---\n\n", content, maxsplit=1)[0].strip()
    if not title or not content:
        raise ValueError("제목 또는 본문이 비어 있습니다.")
    return PublishJob(
        job_id=f"github-issue-{issue['number']}",
        site_id=blog_id,
        title=title,
        content_html=content,
        labels=[],
        publish_now=False,
        source_keyword="github-issues-manual",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["login", "run"])
    parser.add_argument("--site-id", required=True, choices=["huh0303", "huh3", "huh4"])
    parser.add_argument("--max-jobs", type=int, default=1)
    parser.add_argument("--profile-root", default=str(ROOT / ".local" / "naver-profiles"))
    args = parser.parse_args()
    if not GH_PAT:
        raise SystemExit("GH_PAT 환경변수가 필요합니다.")

    ensure_queue_labels(args.site_id)
    profile_dir = Path(args.profile_root).resolve() / args.site_id
    profile_dir.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            str(profile_dir), headless=False, locale="ko-KR"
        )
        page = context.pages[0] if context.pages else context.new_page()
        if args.command == "login":
            page.goto("https://blog.naver.com/GoBlogWrite.naver", wait_until="domcontentloaded")
            input("브라우저에서 해당 네이버 계정 로그인을 마친 뒤 Enter를 누르세요: ")
            context.close()
            return 0

        publisher = NaverLocalPublisher(
            args.site_id, "https://blog.naver.com/GoBlogWrite.naver", args.site_id
        )
        issues = get_ready_issues(args.site_id, max(1, min(args.max_jobs, 10)))
        if not issues:
            print("처리할 GitHub queue:ready 이슈가 없습니다.")
            context.close()
            return 0

        for issue in issues:
            try:
                # Claim inside the guarded block so API failures are reported cleanly.
                replace_status(issue, STATUS_PROCESSING)
                job = parse_job(issue, args.site_id)
                result = publisher.publish(page, job)
                if result.ok and result.status == "draft_saved":
                    replace_status(issue, STATUS_DRAFT_SAVED)
                    add_comment(
                        issue["number"],
                        "✅ 네이버 임시저장 완료를 확인했습니다.\n"
                        "공개 발행은 하지 않았습니다. 네이버 블로그 임시저장함에서 확인하세요.",
                    )
                    print(f"#{issue['number']} draft_saved")
                else:
                    replace_status(issue, STATUS_ATTENTION)
                    add_comment(
                        issue["number"],
                        "⚠️ 네이버 임시저장 완료를 확인하지 못했습니다. 수동 확인이 필요합니다.\n\n"
                        f"상태: {result.status}\n오류: {result.error_code or '-'}\n"
                        f"내용: {(result.message or '임시저장 확인 실패')[:800]}",
                    )
                    print(f"#{issue['number']} attention: {result.status}")
                    break
            except Exception as exc:
                try:
                    replace_status(issue, STATUS_FAILED)
                    add_comment(issue["number"], f"❌ 로컬 발행기 오류\\n\\n{str(exc)[:800]}")
                except Exception:
                    log.exception("Could not write failure state for issue #%s", issue.get("number"))
                log.exception("Failed issue #%s", issue.get("number"))
                break
        context.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
