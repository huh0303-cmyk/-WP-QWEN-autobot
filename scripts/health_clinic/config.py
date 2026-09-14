"""
Health Clinic 채널별 설정.
kr / en / jp 세 언어 채널의 공통 설정과 언어별 차이점을 여기서 관리합니다.
"""
import os
from dotenv import load_dotenv

load_dotenv()

CHANNEL_NAME = "Health Clinic"

# 대본 길이 (RT 15분 기준, 1분당 한국어 약 280자 / 영어 약 150단어 / 일본어 약 300자 기준 역산)
TARGET_SCRIPT_MINUTES = (14, 16)

LANGUAGES = {
    "kr": {
        "code": "ko",
        "label": "한국어",
        "voice_id_a_env": "ELEVENLABS_VOICE_ID_KR_A",
        "voice_id_b_env": "ELEVENLABS_VOICE_ID_KR_B",
        "channel_id_env": "YOUTUBE_CHANNEL_ID_KR",
        "youtube_category_id": "27",  # Education
        "default_locale": "ko-KR",
    },
    "en": {
        "code": "en",
        "label": "English",
        "voice_id_a_env": "ELEVENLABS_VOICE_ID_EN_A",   # Rachel
        "voice_id_b_env": "ELEVENLABS_VOICE_ID_EN_B",   # Bella
        "channel_id_env": "YOUTUBE_CHANNEL_ID_EN",
        "youtube_category_id": "27",
        "default_locale": "en-US",
    },
    "jp": {
        "code": "ja",
        "label": "日本語",
        "voice_id_a_env": "ELEVENLABS_VOICE_ID_JP_A",
        "voice_id_b_env": "ELEVENLABS_VOICE_ID_JP_B",
        "channel_id_env": "YOUTUBE_CHANNEL_ID_JP",
        "youtube_category_id": "27",
        "default_locale": "ja-JP",
    },
}

# 채널 톤 & 타겟 — 대본 생성 프롬프트에 그대로 들어갑니다
AUDIENCE_PROFILE = {
    "kr": "50~70대 한국 시니어. 손주, 건강검진, 관절/혈압/혈당 걱정이 많고, "
          "과장광고에 지쳐있어 진솔하고 담백한 화법을 선호함.",
    "en": "Adults 50+ in the US/UK/Canada who are proactive about healthy aging, "
          "skeptical of hype, and prefer a warm, trustworthy, slightly informal tone "
          "(like a knowledgeable friend, not a lecture).",
    "jp": "50代以上の日本のシニア層。丁寧で落ち着いたトーンを好み、"
          "誇張表現を嫌い、実用的で具体的なアドバイスを重視する。",
}

DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

# 하위 폴더 구조 (Drive 안에 자동 생성)
DRIVE_SUBFOLDERS = {
    "scripts": "01_scripts",
    "videos": "02_videos",
    "thumbnails": "03_thumbnails",
}
