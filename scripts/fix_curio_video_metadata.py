#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_curio_video_metadata.py
─────────────────────────────────────────────────────────────
이미 올라간 "지식채널"(Curio/Times) 영상 하나의 제목/설명만 다시 쓸 때 쓰는
1회성 유틸리티. curio_upload.py의 검증된 OAuth 인증 로직(get_youtube_service,
CHANNEL_SECRET_MAP)을 그대로 재사용한다.

fix_video_metadata.py(플리채널 전용, youtube_playlist_maker 기반)와는 별도 —
지식채널은 인증 방식(force-ssl/upload 스코프 순차 시도 + CHANNEL_SECRET_MAP)이
달라서 파일을 분리했다.

사용법:
    python scripts/fix_curio_video_metadata.py <channel_key> <video_id> <title_file> <description_file>
    예: python scripts/fix_curio_video_metadata.py invention zZ-SkcHU3bQ title.txt desc.txt
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from curio_upload import get_youtube_service, CHANNEL_SECRET_MAP, log  # noqa: E402


def main():
    channel_key = sys.argv[1]
    video_id = sys.argv[2]
    title_file = sys.argv[3]
    desc_file = sys.argv[4]

    secret_key = CHANNEL_SECRET_MAP.get(channel_key, channel_key.upper())
    with open(title_file, encoding="utf-8") as f:
        title = f.read().strip()
    with open(desc_file, encoding="utf-8") as f:
        description = f.read().strip()

    log(f"채널: {channel_key} ({secret_key}) / 영상: {video_id}")
    log(f"새 제목({len(title)}자): {title}")
    log(f"새 설명({len(description)}자)")

    youtube = get_youtube_service(secret_key)

    current = youtube.videos().list(part="snippet", id=video_id).execute()
    items = current.get("items", [])
    if not items:
        log(f"❌ 영상을 찾을 수 없음: {video_id}")
        raise SystemExit(1)
    snippet = items[0]["snippet"]
    snippet["title"] = title
    snippet["description"] = description

    youtube.videos().update(part="snippet", body={"id": video_id, "snippet": snippet}).execute()
    log(f"✅ 업데이트 완료: https://youtu.be/{video_id}")


if __name__ == "__main__":
    main()
