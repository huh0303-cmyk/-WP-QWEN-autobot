#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
refresh_playlist_thumbnails.py
─────────────────────────────────────────────────────────────
플리 5개 채널(globalmusic/healing/starbucks/mbb/kpop) 각각에 대해, 채널별로
이미 정해둔 벤치마킹 포맷(youtube_playlist_maker.make_channel_thumbnail)으로
새 썸네일을 5장씩 생성한다.

- 각 채널의 구글드라이브 "썸네일" 폴더에 업로드
- 로컬 thumbnail_bank/<채널>/ 에도 저장해서 GitHub에 커밋(백업/버전관리 겸용)

매주 수요일 자동 실행(.github/workflows/refresh-playlist-thumbnails.yml).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import youtube_playlist_maker as pm

THUMBNAILS_PER_CHANNEL = 5
BANK_DIR = "thumbnail_bank"


def refresh_channel(channel_key: str):
    pm.CHANNEL_KEY = channel_key
    pm.log(f"\n{'='*50}\n[{channel_key}] 썸네일 {THUMBNAILS_PER_CHANNEL}장 리프레시 시작\n{'='*50}")

    thumb_folder_id = pm._channel_env("THUMBNAIL_FOLDER_ID", pm._DEFAULT_THUMB_FOLDER)
    drive = pm.get_drive_service()

    out_dir = os.path.join(BANK_DIR, channel_key)
    os.makedirs(out_dir, exist_ok=True)

    for i in range(THUMBNAILS_PER_CHANNEL):
        topic, _ = pm.pick_auto_topic()
        pm.log(f"[{channel_key}] {i+1}/{THUMBNAILS_PER_CHANNEL} 주제: {topic}")

        workdir = f"/tmp/thumb_refresh_{channel_key}_{i}"
        os.makedirs(workdir, exist_ok=True)
        try:
            image_paths = pm.build_ai_images(topic, workdir)
        except Exception as e:
            pm.log(f"   ⚠️ 이미지 생성 실패, 건너뜀: {e}")
            continue

        out_path = os.path.join(out_dir, f"{i+1:02d}.png")
        out_path = pm.make_channel_thumbnail(channel_key, image_paths[0], out_path, topic)

        try:
            thumb_ext = os.path.splitext(out_path)[1] or ".png"
            pm.upload_to_drive(drive, out_path, thumb_folder_id, f"refresh_{i+1:02d}{thumb_ext}")
            pm.log(f"   ✅ 드라이브 업로드 완료")
        except Exception as e:
            pm.log(f"   ⚠️ 드라이브 업로드 실패(로컬 파일은 유지됨): {e}")


def main():
    for channel_key in pm.PLAYLIST_CHANNELS:
        try:
            refresh_channel(channel_key)
        except Exception as e:
            pm.log(f"❌ [{channel_key}] 처리 중 오류(다음 채널로 계속): {e}")


if __name__ == "__main__":
    main()
