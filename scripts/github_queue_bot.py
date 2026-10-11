#!/usr/bin/env python3
"""Telegram intake adapter that stores Naver publishing jobs as GitHub Issues.

Run on the same trusted PC as the local Naver publisher. This process only
creates queue issues; it never logs in to Naver or publishes content.
Required env: TELEGRAM_BOT_TOKEN, GH_PAT, TELEGRAM_ALLOWED_CHAT_IDS.
GH_PAT needs Issues read/write access for this repository only.
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Any

import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

REPO_OWNER = os.getenv("GITHUB_REPO_OWNER", "huh0303-cmyk").strip()
REPO_NAME = os.getenv("GITHUB_REPO_NAME", "-WP-QWEN-autobot").strip()
API_ROOT = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GH_PAT = os.getenv("GH_PAT", "").strip()
ALLOWED_IDS = {
    value.strip() for value in os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "").split(",")
    if value.strip()
}
ACCOUNTS = {
    "naver1_365": "huh0303",
    "naver2_365": "huh3",
    "naver3_365": "huh4",
}
STATUS_LABEL = "queue:ready"
ACCOUNT_LABEL_PREFIX = "blog:"
TIMEOUT = (5, 25)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("github-queue-bot")


class GitHubQueueError(RuntimeError):
    pass


def github_request(method: str, path: str, **kwargs: Any) -> requests.Response:
    headers = {
        "Authorization": f"Bearer {GH_PAT}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    response = requests.request(
        method, f"{API_ROOT}{path}", headers=headers, timeout=TIMEOUT, **kwargs
    )
    if not response.ok:
        # Do not include request headers or secrets in errors/logs.
        raise GitHubQueueError(
            f"GitHub API returned HTTP {response.status_code} for {method} {path}: "
            f"{response.text[:400]}"
        )
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
        raise GitHubQueueError(f"Could not inspect GitHub label (HTTP {response.status_code}).")
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
        raise GitHubQueueError(f"Could not create GitHub label (HTTP {created.status_code}).")


def authorize(update: Update) -> bool:
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat or not ALLOWED_IDS:
        return False
    return str(user.id) in ALLOWED_IDS or str(chat.id) in ALLOWED_IDS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not authorize(update):
        await message.reply_text("⛔ 허용된 텔레그램 계정이 아닙니다.")
        return
    await message.reply_text(
        "런던 프로젝트 GitHub Issues 대기열 봇입니다.\n"
        "사용법: /naver1_365 제목 | 본문\n"
        "이 봇은 글감을 대기열에 등록하며 직접 발행하지 않습니다."
    )


async def enqueue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not authorize(update):
        await message.reply_text("⛔ 허용된 텔레그램 계정이 아닙니다.")
        return

    command = (message.text or "").split(maxsplit=1)[0].split("@", 1)[0].lstrip("/")
    blog_id = ACCOUNTS.get(command)
    raw = (message.text or "").partition(" ")[2].strip()
    if not blog_id or "|" not in raw:
        await message.reply_text(f"사용법: /{command} 제목 | 본문")
        return

    title, content = (part.strip() for part in raw.split("|", 1))
    if not title or not content:
        await message.reply_text("제목과 본문을 모두 입력해 주세요.")
        return
    if len(title) > 250 or len(content) > 30000:
        await message.reply_text("제목은 250자, 본문은 30,000자 이내로 입력해 주세요.")
        return

    try:
        for name, color, description in (
            ("queue:ready", "1D76DB", "Waiting for the local Naver publisher"),
            ("queue:processing", "FBCA04", "Claimed by the local Naver publisher"),
            ("queue:published", "0E8A16", "Public Naver URL verified"),
            ("queue:attention", "D93F0B", "Human review required"),
            ("queue:failed", "B60205", "Queue processing failed"),
            (f"{ACCOUNT_LABEL_PREFIX}{blog_id}", "5319E7", f"Naver blog account {blog_id}"),
        ):
            ensure_label(name, color, description)
        issue_body = (
            f"<!-- london-project-queue:v1 -->\n"
            f"**Target account:** `{blog_id}`\n\n"
            f"### 📝 블로그 본문 데이터\n\n{content}\n\n"
            f"---\n\n"
            f"_접수: Telegram · 실제 발행 전 로컬 실행기 검증 필요_\n"
        )
        response = github_request(
            "POST", "/issues",
            json={
                "title": f"[발행대기][{blog_id}] {title}",
                "body": issue_body,
                "labels": [STATUS_LABEL, f"{ACCOUNT_LABEL_PREFIX}{blog_id}"],
            },
        )
        issue = response.json()
        await message.reply_text(
            f"📥 GitHub 대기열 등록 완료\n계정: {blog_id}\n"
            f"상태: {STATUS_LABEL}\n이슈: {issue.get('html_url', '')}\n"
            "등록 완료는 네이버 발행 성공을 의미하지 않습니다."
        )
    except Exception:
        log.exception("GitHub issue enqueue failed")
        await message.reply_text("❌ 대기열 등록 실패. PC 실행 로그를 확인해 주세요.")


def main() -> None:
    if not BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN 환경변수가 필요합니다.")
    if not GH_PAT:
        raise SystemExit("GH_PAT 환경변수가 필요합니다.")
    if not ALLOWED_IDS:
        raise SystemExit("보안을 위해 TELEGRAM_ALLOWED_CHAT_IDS를 설정해야 합니다.")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    for command in ACCOUNTS:
        app.add_handler(CommandHandler(command, enqueue))
    log.info("GitHub Issues queue bot started; publishing is disabled in this process.")
    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
