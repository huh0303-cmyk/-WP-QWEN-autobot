#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
emergency_privacy_lockdown.py
─────────────────────────────────────────────────────────────
비공개로 올라갔어야 할 영상이 실제로 공개/링크공개 상태로 확인됐을 때
즉시 비공개로 되돌리는 1회성 응급 스크립트. curio_upload.py의
get_youtube_service()를 재사용.

사용법:
    python scripts/emergency_privacy_lockdown.py <channel_key> <video_id> [<video_id> ...]
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from curio_upload import get_youtube_service, CHANNEL_SECRET_MAP, log  # noqa: E402


def main():
    channel_key = sys.argv[1]
    video_ids = sys.argv[2:]
    secret_key = CHANNEL_SECRET_MAP.get(channel_key, channel_key.upper())

    youtube = get_youtube_service(secret_key)
    for vid in video_ids:
        try:
            youtube.videos().update(
                part="status",
                body={"id": vid, "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False}},
            ).execute()
            log(f"✅ 비공개 전환 완료: {vid}")
        except Exception as e:
            log(f"❌ 실패: {vid} — {e}")
            raise


if __name__ == "__main__":
    main()
