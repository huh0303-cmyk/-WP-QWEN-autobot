#!/usr/bin/env python3
"""Send YouTube upload completion report (Public or Private) to KakaoTalk Memo."""
from __future__ import annotations

import argparse
import json
import os
import sys
import requests


def send_kakao_youtube_alert(channel_name: str, video_title: str, video_id: str, privacy_status: str) -> bool:
    rest_key = os.getenv("KAKAO_REST_API_KEY", "").strip()
    refresh_token = os.getenv("KAKAO_REFRESH_TOKEN", "").strip()
    if not (rest_key and refresh_token):
        print("⚠️ Kakao notification skipped: KAKAO_REST_API_KEY or KAKAO_REFRESH_TOKEN is not configured.")
        return False

    try:
        # 1. Access token 발급
        token_res = requests.post(
            "https://kauth.kakao.com/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": rest_key,
                "refresh_token": refresh_token,
            },
            timeout=20,
        )
        token_res.raise_for_status()
        access_token = token_res.json().get("access_token")
        if not access_token:
            print(f"⚠️ Failed to obtain Kakao access token: {token_res.text}")
            return False

        # 2. 공개/비공개 상태 아이콘 및 문구
        is_private = "private" in privacy_status.lower()
        status_badge = "🔒 [비공개 발행]" if is_private else "🌐 [공개 발행]"
        youtube_url = f"https://youtu.be/{video_id}" if video_id else "https://studio.youtube.com"

        message_text = (
            f"🎬 유튜브 자동 발행 완료 알림\n\n"
            f"• 채널: {channel_name}\n"
            f"• 상태: {status_badge}\n"
            f"• 제목: {video_title[:90]}\n\n"
            f"유튜브 스튜디오 및 영상을 확인하세요."
        )

        template = {
            "object_type": "text",
            "text": message_text,
            "link": {
                "web_url": youtube_url,
                "mobile_web_url": youtube_url,
            },
            "button_title": "영상 보러가기" if video_id else "스튜디오 확인",
        }

        # 3. 카카오톡 나에게 보내기 발송
        headers = {"Authorization": f"Bearer {access_token}"}
        send_res = requests.post(
            "https://kapi.kakao.com/v2/api/talk/memo/default/send",
            headers=headers,
            data={"template_object": json.dumps(template, ensure_ascii=False)},
            timeout=20,
        )
        send_res.raise_for_status()
        print(f"✅ Kakao notification sent successfully: {channel_name} | {status_badge} | {video_title}")
        return True

    except Exception as exc:
        print(f"⚠️ Kakao alert delivery failed: {exc}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Send KakaoTalk memo for YouTube upload completion.")
    parser.add_argument("--channel", default="YouTube Channel", help="Channel name or key")
    parser.add_argument("--title", default="YouTube New Upload", help="Video title")
    parser.add_argument("--video-id", default="", help="Uploaded YouTube Video ID")
    parser.add_argument("--privacy", default="private", help="Privacy status (public / private / unlisted)")
    args = parser.parse_args()

    success = send_kakao_youtube_alert(
        channel_name=args.channel,
        video_title=args.title,
        video_id=args.video_id,
        privacy_status=args.privacy,
    )
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
