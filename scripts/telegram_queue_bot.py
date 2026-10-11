#!/usr/bin/env python3
"""Telegram-to-Google-Sheets queue adapter for the existing London Project hub.

This process only enqueues a post. It does not log in to Naver or publish.
Run it as a persistent service on a trusted VPS/PC with the existing Sheets
OAuth/service-account credentials configured for gsheets_direct.py.
"""
from __future__ import annotations

import logging
import os
import re
import secrets
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if os.path.join(ROOT, "scripts") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "scripts"))

from gsheets_direct import get_sheets_service
from sync_automation_hub_to_sheets import ACCOUNTS_TAB, QUEUE_TAB

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger("telegram-queue")
KST = ZoneInfo("Asia/Seoul")
SHEET_ID = os.getenv("SHEET_ID", "").strip()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    # Optional compatibility with the existing JSON secret bundle.
    import json
    bundle = os.getenv("BLOG_ALL_KEYS", "").strip()
    if bundle:
        try:
            BOT_TOKEN = str(json.loads(bundle).get("TELEGRAM_TOKEN") or "").strip()
        except (ValueError, TypeError):
            raise SystemExit("BLOG_ALL_KEYS is not valid JSON.")
ALLOWED_CHAT_IDS = {
    item.strip() for item in os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "").split(",")
    if item.strip()
}
COMMANDS = {"naver1_365": "huh0303", "naver2_365": "huh3", "naver3_365": "huh4"}
HEADER = [
    "created_at", "job_id", "site_id", "status", "publish_now", "title",
    "content_html", "labels", "source_keyword", "public_url", "remote_id",
    "error_code", "message", "completed_at", "category",
    "search_description", "visibility",
]


def records(values):
    if not values:
        return []
    header = values[0]
    result = []
    for row in values[1:]:
        padded = row + [""] * max(0, len(header) - len(row))
        result.append(dict(zip(header, padded)))
    return result


def authorize(update: Update) -> bool:
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return False
    if ALLOWED_CHAT_IDS and str(chat.id) not in ALLOWED_CHAT_IDS and str(user.id) not in ALLOWED_CHAT_IDS:
        return False
    return True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not authorize(update):
        await update.effective_message.reply_text("⛔ 허용된 텔레그램 계정이 아닙니다.")
        return
    await update.effective_message.reply_text(
        "런던프로젝트 글감 대기열 봇입니다.\n"
        "사용법: /naver1_365 제목 | 본문\n"
        "등록만 하며 직접 발행하지 않습니다. 기본은 검토용 대기열입니다."
    )


async def enqueue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not authorize(update):
        await message.reply_text("⛔ 허용된 텔레그램 계정이 아닙니다.")
        return
    command = (message.text or "").split(maxsplit=1)[0].split("@", 1)[0].lstrip("/")
    destination = COMMANDS.get(command)
    if not destination:
        await message.reply_text("지원하지 않는 명령어입니다.")
        return
    raw = (message.text or "").partition(" ")[2].strip()
    if "|" not in raw:
        await message.reply_text(f"사용법: /{command} 제목 | 본문")
        return
    title, body = (part.strip() for part in raw.split("|", 1))
    if not title or not body:
        await message.reply_text("제목과 본문을 모두 입력해 주세요.")
        return
    if len(title) > 300 or len(body) > 30000:
        await message.reply_text("제목은 300자, 본문은 30,000자 이내로 입력해 주세요.")
        return

    try:
        service = get_sheets_service()
        accounts_values = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID, range=f"'{ACCOUNTS_TAB}'!A1:I"
        ).execute().get("values", [])
        accounts = records(accounts_values)
        account = next((a for a in accounts
                        if a.get("platform", "").lower() == "naver"
                        and a.get("destination_id", "").strip().lower() == destination.lower()
                        and a.get("enabled", "ON").strip().upper() in {"ON", "TRUE", "1"}), None)
        if not account:
            await message.reply_text(
                f"⚠️ {destination} 계정을 활성 네이버 계정 목록에서 찾지 못했습니다. "
                "계정 등록을 확인했으며 글은 등록하지 않았습니다."
            )
            return

        job_id = f"tg-{datetime.now(KST).strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(3)}"
        row = [
            datetime.now(KST).isoformat(timespec="seconds"), job_id, account["site_id"],
            "ready", "FALSE", title, body, "", "telegram", "", "", "", 
            "Telegram에서 등록 · 발행 전 검토 필요", "", "", "", "draft",
        ]
        service.spreadsheets().values().append(
            spreadsheetId=SHEET_ID,
            range=f"'{QUEUE_TAB}'!A:Q",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [row]},
        ).execute()
        await message.reply_text(
            f"📥 대기열 등록 완료\n계정: {destination}\n제목: {title}\n"
            f"작업 ID: {job_id}\n상태: ready (검토용 초안)\n"
            "이 응답은 발행 성공이 아니라 대기열 저장 완료를 뜻합니다."
        )
    except Exception:
        log.exception("Failed to enqueue Telegram post")
        await message.reply_text("❌ 대기열 등록에 실패했습니다. 실행 로그를 확인해 주세요.")


def main():
    if not BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN 환경변수가 필요합니다.")
    if not SHEET_ID:
        raise SystemExit("SHEET_ID 환경변수가 필요합니다.")
    if not ALLOWED_CHAT_IDS:
        raise SystemExit("안전을 위해 TELEGRAM_ALLOWED_CHAT_IDS를 설정해야 합니다.")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    for command in COMMANDS:
        app.add_handler(CommandHandler(command, enqueue))
    log.info("Telegram queue adapter started; publishing is disabled in this process.")
    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
