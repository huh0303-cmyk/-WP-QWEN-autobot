#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
youtube_playlist_maker.py
─────────────────────────────────────────────────────────────
구글드라이브 A폴더(원곡)에서 음악을 무작위로 골라 60~80분 분량으로
이어붙이고, 주제어를 기반으로 감성 라이프스타일풍 AI 이미지 2장(골든아워/주간 톤)을
생성해 15분 간격으로 번갈아 팬줌(Ken Burns) 효과를 넣는다. 1번 이미지 위에 큼직한
"Playlist" 타이틀을 얹어 썸네일로 저장하고, 영상 하단에는 "Playlist | <감성 문구>"
캡션바를 처음부터 끝까지 표시한다. 최종 mp4를 C폴더(최종파일)에
"YYYY_M_D_####.mp4" 형식으로, 썸네일은 별도 PNG로 업로드한다.

주제어를 안 주면(빈 값) B폴더(썸네일창고)에서 이미지를 무작위로 골라
정지 이미지 1장 + 음악으로만 구성하는 기존 방식으로 폴백한다.

곡 파일명에 "일본어", "독일어" 같은 언어 태그가 들어있는 경우, LANGUAGE_KEYWORD로
"Japanese", "French" 등을 주면 해당 언어 태그가 파일명에 포함된 곡들 중에서만
무작위로 고른다. 비어있거나 "Mixed"/"Mix"이면 필터 없이 전체 곡 중에서 고른다.

CAPTION_TEXT를 직접 주면 그 문구를 그대로 캡션바에 쓰고, 비어있으면 주제어 기반으로
Gemini가 짧은 감성 문구를 자동 생성한다.

사용법:
    python scripts/youtube_playlist_maker.py [주제어] [언어 키워드] [캡션 문구]
    (또는 TOPIC_KEYWORD / LANGUAGE_KEYWORD / CAPTION_TEXT 환경변수)

필요 환경변수(Secrets):
    GOOGLE_OAUTH_CLIENT_ID      - 구글드라이브 업로드용 OAuth 클라이언트 ID
    GOOGLE_OAUTH_CLIENT_SECRET  - 구글드라이브 업로드용 OAuth 클라이언트 시크릿
    GOOGLE_OAUTH_REFRESH_TOKEN  - 구글드라이브 업로드용 OAuth 리프레시 토큰
                                  (서비스 계정은 개인 드라이브 업로드 시 저장공간
                                  할당량이 없어 실패하므로 실제 사용자 계정 OAuth 사용)
    GEMINI_API_KEY              - 주제어 기반 이미지 생성(나노바나나). 없으면 B폴더 폴백
    MUSIC_SOURCE_FOLDER_ID      - (선택) 원곡 폴더 ID, 기본값 있음
    THUMBNAIL_FOLDER_ID         - (선택) 썸네일창고 폴더 ID, 기본값 있음(폴백용)
    OUTPUT_FOLDER_ID            - (선택) 최종파일 폴더 ID, 기본값 있음

필요 시스템 도구: ffmpeg, ffprobe
"""

import os
import sys
import json
import random
import base64
import requests
import subprocess

# Windows 로컬 콘솔(cp949 등)에서 이모지/한글 출력 시 죽지 않도록 UTF-8 강제
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
from datetime import datetime, timezone, timedelta

GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
GOOGLE_OAUTH_REFRESH_TOKEN = os.environ.get("GOOGLE_OAUTH_REFRESH_TOKEN", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_IMAGE_MODELS = ["gemini-2.5-flash-image", "gemini-2.5-flash-image-preview"]

# 유튜브 실제 업로드/공개 승인 파이프라인용 — 구글드라이브 업로드용 OAuth와는
# 스코프가 달라서(youtube.upload) 별도로 발급받은 값을 쓴다
YOUTUBE_OAUTH_CLIENT_ID = os.environ.get("YOUTUBE_OAUTH_CLIENT_ID", "")
YOUTUBE_OAUTH_CLIENT_SECRET = os.environ.get("YOUTUBE_OAUTH_CLIENT_SECRET", "")
YOUTUBE_OAUTH_REFRESH_TOKEN = os.environ.get("YOUTUBE_OAUTH_REFRESH_TOKEN", "")

GMAIL_USER = "huh0303@gmail.com"
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

# 플리 채널 5개(2026-08-03 확정): 채널마다 곡 소스/썸네일/출력 폴더와 유튜브
# 업로드 토큰이 전부 달라야 한다 — 안 그러면 언어퀴즈 때처럼 다른 채널로
# 뒤섞여 올라가는 사고가 재발한다. CHANNEL_KEY로 채널을 고르면 그 채널 전용
# *_{KEY} 환경변수(Secrets)를 사용하고, 없으면 기존 공용 기본값으로 폴백한다
# (CHANNEL_KEY를 아예 안 주는 기존 실행 방식과 호환 유지).
PLAYLIST_CHANNELS = ["globalmusic", "healing", "starbucks", "mbb", "kpop"]
# 구독자 50만+ 플리 채널 벤치마킹 공통 포맷("Playlist" 대형 히어로 + 파형) 적용 채널.
# mbb는 예외 — 작곡가 초상화+이름 포맷을 따로 쓴다(아래 build_ai_images/썸네일 호출부 참고).
PLAYLIST_HERO_CHANNELS = {"globalmusic", "healing", "starbucks", "kpop"}
CHANNEL_KEY = (os.environ.get("CHANNEL_KEY") or "").strip().lower()

_DEFAULT_MUSIC_FOLDER = "1RqL44lM5oUSW5_PAZLHHlevrVkr1ibxd"
_DEFAULT_THUMB_FOLDER = "1jVDuCjTVJPnNSIBEXjnU6DPSzZO56d68"
_DEFAULT_OUTPUT_FOLDER = "1srQUiWOk6UruujYSy2S0ogN3FvxVTSBN"


def _channel_env(base_name, fallback):
    if CHANNEL_KEY:
        per_channel = os.environ.get(f"{base_name}_{CHANNEL_KEY.upper()}")
        if per_channel:
            return per_channel
    return os.environ.get(base_name) or fallback


MUSIC_SOURCE_FOLDER_ID = _channel_env("MUSIC_SOURCE_FOLDER_ID", _DEFAULT_MUSIC_FOLDER)
THUMBNAIL_FOLDER_ID = _channel_env("THUMBNAIL_FOLDER_ID", _DEFAULT_THUMB_FOLDER)
OUTPUT_FOLDER_ID = _channel_env("OUTPUT_FOLDER_ID", _DEFAULT_OUTPUT_FOLDER)

# 유튜브 업로드 토큰도 채널 전용 - 없으면 그 채널은 발행을 건너뛰어야 하므로
# youtube_publish_approved.py에서 별도로 검사한다(공용 토큰으로 조용히 폴백 금지).
YOUTUBE_TOKEN_ENV_NAME = (
    f"YOUTUBE_OAUTH_REFRESH_TOKEN_{CHANNEL_KEY.upper()}" if CHANNEL_KEY
    else "YOUTUBE_OAUTH_REFRESH_TOKEN"
)

# 영어 키워드 → 파일명에 박힌 한글 언어 태그 매핑
LANGUAGE_TAG_MAP = {
    "japanese": "일본어", "japan": "일본어",
    "french": "프랑스어", "france": "프랑스어",
    "german": "독일어", "germany": "독일어",
    "english": "영어",
    "korean": "한국어",
    "chinese": "중국어", "china": "중국어",
    "spanish": "스페인어", "spain": "스페인어",
    "italian": "이탈리아어", "italy": "이탈리아어",
    "portuguese": "포르투갈어",
    "russian": "러시아어",
    "vietnamese": "베트남어",
    "thai": "태국어",
}
MIXED_KEYWORDS = {"mixed", "mix", "all", ""}

KST = timezone(timedelta(hours=9))
WORKDIR = "playlist_output"
# 매번 똑같이 60~80분짜리만 나오면 그 자체가 "정형화된 AI 생성물" 티가 나서,
# 실행마다 목표 재생시간 구간 자체를 무작위로 골라 영상 길이가 매번 다르게 한다
DURATION_POOL_MIN_SEC = 30 * 60
DURATION_POOL_MAX_SEC = 100 * 60
# 채널별로 재생시간 구간을 다르게 두고 싶을 때만 여기에 추가 — 없으면 위 기본값 사용.
# starbucks(=카페음악, 2026-08-06부터 연주곡 전용 채널로 재배정): 56~190분 확정.
# globalmusic(=로맨틱글로벌): 2026-08-12부터 64~132분 확정.
CHANNEL_DURATION_POOL_SEC = {
    "starbucks": (56 * 60, 190 * 60),
    "globalmusic": (64 * 60, 132 * 60),
    # healing: 2~3시간짜리 긴 수면/이완용 재생목록으로 고정(2026-08-13 사용자 요청).
    "healing": (120 * 60, 180 * 60),
}
IMAGE_SWAP_SEC = 15 * 60          # AI 이미지 2장 전환 간격
VIDEO_W, VIDEO_H = 1920, 1080
THUMBNAIL_UPSCALE_SIZE = (5120, 2880)  # 썸네일 최종 저장 해상도(5K 기본) — 2026-08-14 사용자 요청
INTRO_DURATION_SEC = 6.0          # 인트로가 쓰는 음악 앞부분 길이 — 본편은 이 지점부터 이어서 재생

AUDIO_EXTS = (".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg")
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp")

import tempfile
_TMPDIR = tempfile.gettempdir()  # "/tmp" 하드코딩은 Windows 로컬 실행에서 항상 깨짐

FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/nanumgothic/NanumGothic-Bold.ttf"
FONT_PATH = os.path.join(_TMPDIR, "_playlist_nanumgothic_bold.ttf")
# 썸네일 "Playlist" 타이틀용 우아한 세리프 폰트 (한글 캡션바는 나눔고딕 유지)
TITLE_FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf"
TITLE_FONT_PATH = os.path.join(_TMPDIR, "_playlist_playfair.ttf")
# 東京/札幌처럼 한자·가나가 섞인 주제어용 — 나눔고딕엔 한자 글리프가 없어서
# Playfair 자리를 대신할 일본어 지원 세리프 폰트가 따로 필요하다
JP_FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/notoserifjp/NotoSerifJP%5Bwght%5D.ttf"
JP_FONT_PATH = os.path.join(_TMPDIR, "_playlist_notoserifjp.ttf")
# healing 채널 전용: 차분하고 얇은 세리프(Cormorant) — Playfair보다 명상적/우아한 느낌
HEALING_TITLE_FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/cormorantgaramond/CormorantGaramond%5Bwght%5D.ttf"
HEALING_TITLE_FONT_PATH = os.path.join(_TMPDIR, "_playlist_cormorant.ttf")


def log(msg):
    print(msg, flush=True)


def run_ffmpeg(cmd):
    # capture_output=True + text=True는 OS 기본 로케일 인코딩(Windows 한글판이면
    # cp949)으로 ffmpeg의 stderr를 디코딩하려다 곡 파일명 등에 섞인 비-cp949
    # 바이트를 만나면 UnicodeDecodeError로 죽는다 — 항상 UTF-8로 강제한다.
    proc = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg 실패: {' '.join(cmd)}\n{proc.stderr[-2000:]}")


def get_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, check=True,
        encoding="utf-8", errors="replace",
    )
    return float(out.stdout.strip())


def ensure_font():
    if not os.path.exists(FONT_PATH):
        r = requests.get(FONT_URL, timeout=30)
        r.raise_for_status()
        with open(FONT_PATH, "wb") as f:
            f.write(r.content)
    return FONT_PATH


def ensure_title_font():
    if not os.path.exists(TITLE_FONT_PATH):
        try:
            r = requests.get(TITLE_FONT_URL, timeout=30)
            r.raise_for_status()
            with open(TITLE_FONT_PATH, "wb") as f:
                f.write(r.content)
        except Exception:
            return ensure_font()  # 실패 시 나눔고딕으로 폴백
    return TITLE_FONT_PATH


def ensure_healing_title_font():
    if not os.path.exists(HEALING_TITLE_FONT_PATH):
        try:
            r = requests.get(HEALING_TITLE_FONT_URL, timeout=30)
            r.raise_for_status()
            with open(HEALING_TITLE_FONT_PATH, "wb") as f:
                f.write(r.content)
        except Exception:
            return ensure_title_font()  # 실패 시 기본 세리프로 폴백
    return HEALING_TITLE_FONT_PATH


def ensure_jp_font():
    if not os.path.exists(JP_FONT_PATH):
        try:
            r = requests.get(JP_FONT_URL, timeout=30)
            r.raise_for_status()
            with open(JP_FONT_PATH, "wb") as f:
                f.write(r.content)
        except Exception:
            return ensure_font()  # 실패 시 나눔고딕으로 폴백(한자는 깨질 수 있음)
    return JP_FONT_PATH


# ════════════════════════════════════════════════════════════
# 구글드라이브
# ════════════════════════════════════════════════════════════
def get_drive_service():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=None,
        refresh_token=GOOGLE_OAUTH_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_OAUTH_CLIENT_ID,
        client_secret=GOOGLE_OAUTH_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    return build("drive", "v3", credentials=creds)


def list_folder_files(service, folder_id, exts, mime_prefix):
    """exts(확장자) 또는 mime_prefix(예: 'audio/','image/')로 매칭되는 파일만 반환.
    다른 종류(예: 오디오 폴더에 섞여 들어간 이미지 파일)는 제외한다."""
    files = []
    page_token = None
    while True:
        resp = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="nextPageToken, files(id, name, mimeType, size)",
            pageToken=page_token,
            pageSize=200,
        ).execute()
        for f in resp.get("files", []):
            name = f.get("name", "")
            mime = f.get("mimeType", "")
            if mime.startswith(mime_prefix) or name.lower().endswith(exts):
                files.append(f)
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return files


def download_drive_file(service, file_id, out_path):
    from googleapiclient.http import MediaIoBaseDownload

    request = service.files().get_media(fileId=file_id)
    with open(out_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


def upload_to_drive(service, file_path, folder_id, name):
    """큰 파일도 안정적으로 올라가도록 청크 단위 업로드 + 재시도 처리.
    (파일 전체를 한 번에 보내면 도중 짧은 네트워크 끊김에도 통째로 실패함)"""
    import time
    from googleapiclient.http import MediaFileUpload

    metadata = {"name": name, "parents": [folder_id]}
    media = MediaFileUpload(file_path, resumable=True, chunksize=5 * 1024 * 1024)
    request = service.files().create(body=metadata, media_body=media,
                                      fields="id,webViewLink")

    response = None
    retries = 0
    while response is None:
        try:
            status, response = request.next_chunk(num_retries=5)
            if status:
                log(f"   업로드 진행률: {int(status.progress() * 100)}%")
        except Exception as e:
            retries += 1
            if retries > 8:
                raise
            wait = min(2 ** retries, 60)
            log(f"   ⚠️ 업로드 청크 오류, {wait}초 후 재시도 ({retries}/8): {e}")
            time.sleep(wait)

    return response.get("webViewLink"), response.get("id")


# ════════════════════════════════════════════════════════════
# 주제어 기반 AI 이미지 생성 (나노바나나)
# ════════════════════════════════════════════════════════════
def gemini_generate_image(prompt, out_path):
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    for model in GEMINI_IMAGE_MODELS:
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{model}:generateContent?key={GEMINI_API_KEY}")
        try:
            r = requests.post(url, json=body, timeout=90)
            if r.status_code != 200:
                continue
            data = r.json()
            parts = data["candidates"][0]["content"]["parts"]
            for part in parts:
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and inline.get("data"):
                    with open(out_path, "wb") as f:
                        f.write(base64.b64decode(inline["data"]))
                    return True
        except Exception:
            continue
    return False


def make_placeholder_image(out_path):
    from PIL import Image
    Image.new("RGB", (VIDEO_W, VIDEO_H), (20, 25, 40)).save(out_path, "PNG")


def gemini_generate_text(prompt, temperature=0.9, max_output_tokens=None):
    if not GEMINI_API_KEY:
        return ""
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}")
    gen_config = {"temperature": temperature}
    if max_output_tokens:
        gen_config["maxOutputTokens"] = max_output_tokens
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": gen_config}
    try:
        r = requests.post(url, json=body, timeout=60)
        r.raise_for_status()
        data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        return ""


def build_caption_text(topic, caption_text):
    if caption_text and caption_text.strip():
        return caption_text.strip()
    prompt = (f"'{topic}' 느낌의 플레이리스트 영상 캡션 한 줄을 써줘. "
              f"조건: 광고 카피처럼 매끈하게 쓰지 말고, 그냥 이 영상을 만든 사람이 "
              f"직접 툭 던지듯 적은 것처럼 자연스럽고 담백하게. 완벽한 문장보다 구어체 느낌으로. "
              f"이모지는 넣어도 1개까지만, 20자 이내. 따옴표나 설명 없이 문구만 출력해줘.")
    text = gemini_generate_text(prompt, temperature=1.0)
    text = text.strip().strip('"').strip("'")
    return text or f"{topic} 들으면서 잠깐 쉬어가기"


# 채널별 설명 톤/컨셉 — Gemini 프롬프트에 채널 정체성을 반영해서 전부 똑같은
# 문구가 나오지 않게 한다 (2026-08-13, 사용자 요청: "이제부터 파이프라인에 박제")
CHANNEL_DESC_CONTEXT = {
    # 2026-08-14 사용자 명시적 지시("확실히"): Cafe_K(=globalmusic 코드키) 채널은
    # 로파이 인스트루멘탈이 아니라 영어/불어/독일어 등 전 세계 모든 언어의
    # 달달한(로맨틱/스위트) 보컬곡 채널로 확정.
    "globalmusic": "a sweet, romantic global music channel featuring vocal love songs in many different languages (English, French, German, and more — warm, tender, feel-good mood)",
    # healing: 빗소리/물소리(시냇물)/새소리 등 자연음 위주, 2~3시간 롱폼(사용자 지시 그대로)
    "healing": "an ambient nature-sounds channel for relaxation and sleep (rain sounds, water/stream sounds, birdsong, temple wind chimes — no lyrics, pure atmosphere, long-form 2-3 hour sessions)",
    # starbucks(=starbucksvibes 채널): 편한 카페 재즈, 보컬 없음(사용자 지시 그대로)
    "starbucks": "a relaxing instrumental cafe jazz channel (no vocals, smooth jazz, warm laid-back cafe mood)",
    "mbb": "a classical music channel centered on Mozart, Bach and Beethoven (and other classical composers)",
    # kpop: 특정 무드로 좁히지 않고 K-pop 전반(사용자 지시: "Kpop음악 전부")
    "kpop": "a K-pop playlist channel featuring all kinds of K-pop music",
}

# 2026-08-14: Gemini 생성이 실패했을 때(쿼터 소진 등, 이날 자주 발생) 쓰던 기존
# 폴백이 너무 dry했고, 주제어가 없는 자동실행에선 raw 파일명까지 제목에 그대로
# 새는 버그가 있었다(예: "Chill Playlist | 2026_8_13_2338.mp4") — 사용자가 직접
# 발견해서 지적함. 이제 채널별로 제목 100자/설명 1000자 가까이 채우는 후킹성
# 정적 템플릿을 갖춰서, Gemini가 죽어도 절대 이런 식으로 올라가지 않게 한다.
PLAYLIST_FALLBACK_HOOKS = {
    "globalmusic": {
        "title_fmt": "{topic} — Sweet Love Songs From Around The World",
        "hook": "A sweet, romantic global mix — love songs in different languages, one warm feeling.",
        "body": (
            "English, French, German, and more — this playlist brings together tender, feel-good vocal love "
            "songs from around the world. Put it on during a date night in, a long drive, or just when you "
            "want the room to feel a little warmer. No sudden drops, no jarring transitions — just a steady, "
            "sweet mood that carries you through the whole thing, no matter what language it's in."
        ),
        "engage": "Which language should the next mix feature? Let us know in the comments.",
        "tags": "#GlobalMusic #LoveSongs #RomanticPlaylist #WorldMusic #ChillMusic #RelaxingMusic",
    },
    "healing": {
        "title_fmt": "{topic} — Pure Nature Sounds For Deep Sleep And Total Relaxation",
        "hook": "Real, layered nature ambience — the kind that quiets a busy mind almost instantly.",
        "body": (
            "No music, no lyrics, no distractions — just rain, flowing water, birdsong, and the kind of quiet "
            "atmosphere that's genuinely hard to find anywhere else. This is built to run for 2-3 hours in the "
            "background while you sleep, study, meditate, or just need the world to feel a little softer for "
            "a while. Put it on, dim the lights, and let it do the work."
        ),
        "engage": "Which soundscape should we record next — rain, a stream, or the ocean? Tell us below.",
        "tags": "#NatureSounds #SleepSounds #RainSounds #WaterSounds #Relaxation #AmbientSounds #WhiteNoise",
    },
    "starbucks": {
        "title_fmt": "{topic} — Relaxing Instrumental Cafe Jazz",
        "hook": "The instrumental cafe jazz mix built to just play in the background while you relax.",
        "body": (
            "No vocals, no lyrics — just warm, smooth jazz that sounds like your favorite coffee shop on a "
            "quiet afternoon. Perfect for unwinding, reading, working, or just needing a steady, unobtrusive "
            "soundtrack in the background. Put it on, get your coffee, and relax."
        ),
        "engage": "What's your go-to way to unwind with this playing? Tell us in the comments.",
        "tags": "#CafeJazz #JazzMusic #InstrumentalMusic #RelaxingMusic #CoffeeShopMusic #ChillJazz",
    },
    "mbb": {
        "title_fmt": "{topic} — Timeless Classical Music From Mozart, Bach And Beethoven",
        "hook": "The classical pieces that have outlasted every trend for over two centuries — and still hit just as hard.",
        "body": (
            "A curated mix of Mozart, Bach, Beethoven, and the composers who defined what music could be. "
            "Whether you're studying, working, or just want something genuinely beautiful playing in the "
            "background, this is music built to last — no algorithm needed, just centuries of proof. Put it "
            "on and hear exactly why it's still being played today."
        ),
        "engage": "Which composer or piece should we feature next? Let us know in the comments.",
        "tags": "#ClassicalMusic #Mozart #Bach #Beethoven #StudyMusic #PianoMusic",
    },
    "kpop": {
        "title_fmt": "{topic} — A K-Pop Playlist Mix To Study, Work Out, Or Drive To",
        "hook": "The K-pop mix built for whatever you're doing right now — studying, driving, or just vibing.",
        "body": (
            "A curated run of K-pop tracks picked for energy and flow, not just what's trending this week. "
            "Whether you're powering through a workout, cruising with the windows down, or just need something "
            "to keep you moving through a study session, this playlist is built to keep the momentum going "
            "from the first track to the last."
        ),
        "engage": "Which group or track should we feature in the next mix? Drop it in the comments.",
        "tags": "#KpopPlaylist #Kpop #StudyMusic #WorkoutMusic #KpopMix #DrivingMusic",
    },
}
_PLAYLIST_DEFAULT_HOOK = {
    "title_fmt": "{topic} — A Playlist Built To Play In The Background All Day",
    "hook": "A playlist built to just play — no skipping, no thinking, just good background sound.",
    "body": (
        "Put this on and let it run — it's built to carry a whole session from start to finish without "
        "pulling your attention away from whatever you're actually doing."
    ),
    "engage": "Let us know what you'd like to hear next in the comments.",
    "tags": "#Playlist #ChillMusic #BackgroundMusic",
}


def _build_fallback_title_and_description(topic, duration_min):
    hook_info = PLAYLIST_FALLBACK_HOOKS.get(CHANNEL_KEY, _PLAYLIST_DEFAULT_HOOK)
    title = hook_info["title_fmt"].format(topic=topic)
    if len(title) > 100:
        title = title[:97].rsplit(" ", 1)[0] + "..."
    description = (
        f"{hook_info['hook']}\n\n"
        f"A {duration_min:.0f}-minute playlist themed around '{topic}'.\n\n"
        f"{hook_info['body']}\n\n"
        f"🔔 Subscribe and turn on notifications — new playlists every week.\n\n"
        f"{hook_info['engage']}\n\n"
        f"{hook_info['tags']}"
    )
    return title, description


def generate_youtube_title_description(topic, caption_text, duration_min):
    """유튜브 업로드용 제목+설명을 Gemini로 생성. 광고 카피처럼 매끈하지 않게,
    실제 채널 운영자가 쓴 것 같은 톤으로("AI 흔적 최소화" 원칙 동일 적용).
    설명은 영어+한국어를 섞어서(약 50:50) 총 5000자 내외의 긴 설명으로 생성한다
    (2026-08-13 사용자 요청 — SEO/시청자 정보성 강화, 모든 채널 공통 적용)."""
    channel_context = CHANNEL_DESC_CONTEXT.get(CHANNEL_KEY, "a curated playlist channel")
    prompt = f"""You are writing the YouTube title and description for a {duration_min:.0f}-minute
playlist video on {channel_context}. The video's mood/topic is "{topic}", one-line caption: "{caption_text}".

Write:
1. TITLE: an emotionally engaging, hooky title close to YouTube's 100-character limit
   (aim for 85-100 characters) — not a dry label, make someone want to click. At most 1 emoji.
2. DESCRIPTION: a long, genuinely useful description of about 5000 characters total,
   written in a natural MIX of English and Korean (roughly 50/50 — alternate by
   paragraph, writing the same content in both languages, not just translating
   word-for-word but writing naturally in each language). Cover: what kind of
   listening experience this is, when/how to use it (studying, sleeping, working,
   relaxing, etc. as fits the topic), why this type of music/sound helps, and a
   warm closing note inviting the listener to subscribe. End with 8-10 relevant
   hashtags (mix of English and Korean tags).
   Sound like a real channel owner wrote it — conversational, not a marketing
   template, no exaggerated claims.

Respond in exactly this format, nothing else:
TITLE: (title)
DESCRIPTION: (the long bilingual description, with blank lines between paragraphs)
"""
    text = gemini_generate_text(prompt, temperature=0.9, max_output_tokens=4096)
    title, description = _build_fallback_title_and_description(topic, duration_min)
    used_fallback = True
    if "TITLE:" in text and "DESCRIPTION:" in text:
        try:
            title_part = text.split("TITLE:")[1].split("DESCRIPTION:")[0].strip()
            desc_part = text.split("DESCRIPTION:")[1].strip()
            if title_part:
                title = title_part
                used_fallback = False
            if desc_part and len(desc_part) > 200:
                description = desc_part
        except Exception:
            pass
    # used_fallback=True는 Gemini 제목생성이 실패해서 기계적인 폴백 문구가 쓰였다는
    # 뜻 — "AI 흔적 없어야 한다"는 원칙상 이런 영상은 자동으로 공개하면 안 되므로
    # publish 단계에서 이 플래그를 보고 비공개로 남겨둔다(youtube_publish_approved.py 참고).
    return title[:100], description, used_fallback




def send_email(subject, body):
    import smtplib
    from email.mime.text import MIMEText

    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = GMAIL_USER
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as s:
        s.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        s.sendmail(GMAIL_USER, [GMAIL_USER], msg.as_string())


THUMBNAIL_BRAND_LABEL = os.environ.get("THUMBNAIL_BRAND_LABEL", "Playlist")

# 워크플로우의 프리셋 드롭다운(한글)을 영문으로 치환 — 썸네일 타이틀 폰트(Playfair
# Display)에 한글 글리프가 없어서, 한글 그대로 넘기면 빈 네모(tofu)로 깨져 보인다.
PRESET_TOPIC_EN_MAP = {
    "봄": "Spring", "여름": "Summer", "가을": "Autumn", "겨울": "Winter",
    "바다": "Ocean", "산": "Mountain", "호수": "Lake",
    "도시 야경": "City Night Lights", "시골 마을": "Countryside Village",
    "카페 감성": "Cozy Cafe",
}

# 썸네일 타이틀은 영문(예: TOKYO)으로 크게, 그 아래 작게 현지어 표기를 곁들인다
# (한자 대신 가타카나처럼, 그 도시/나라에서 실제로 쓰는 표기를 살짝 얹는 감성 포인트)
NATIVE_SUBTITLE_MAP = {
    "Tokyo": "トーキョー",
    "Sapporo": "サッポロ",
    "Seoul": "서울",
}

# 자동 실행(스케줄러 등, 사람이 매번 주제를 골라주지 않는 경우)에서 무작위로
# 뽑을 주제 후보 목록 — 워크플로우 드롭다운 프리셋과 동일한 구성
AUTO_TOPIC_POOL = [
    "봄", "여름", "가을", "겨울", "바다", "산", "호수", "도시 야경", "시골 마을", "카페 감성",
    "Seoul", "London", "Paris", "Tokyo", "New York", "Sapporo", "Miami", "LA", "Prague", "Switzerland",
]
# 주제가 정해지면 그 나라 말 음악을 우선 배치하도록 자동으로 짝지어주는 언어
AUTO_TOPIC_LANGUAGE_HINTS = {
    "Tokyo": "Japanese", "Sapporo": "Japanese",
    "Paris": "French", "Seoul": "Korean",
}

# 채널 성격상 위 여행지/계절 주제풀이 안 맞는 채널은 여기서 전용 주제풀을 쓴다.
# mbb: 작곡가+대표곡 (썸네일에도 그대로 쓰임 — 작곡가 성을 대문자 히어로 텍스트로).
# kpop: 곡 없이도 자연스러운 무드 키워드(플리 콘셉트).
CHANNEL_TOPIC_POOLS = {
    "mbb": [
        "Mozart — Eine kleine Nachtmusik", "Mozart — The Marriage of Figaro Overture",
        "Bach — Air on the G String", "Bach — Brandenburg Concerto No. 3",
        "Beethoven — Moonlight Sonata", "Beethoven — Symphony No. 7",
        "Mozart — Symphony No. 40", "Bach — Cello Suite No. 1",
        "Beethoven — Egmont Overture", "Mozart — Requiem",
        "Bach — Goldberg Variations", "Beethoven — Pathetique Sonata",
    ],
    "kpop": [
        "study playlist", "workout playlist", "driving at night", "chill dance practice",
        "rainy day mix", "morning motivation", "late night vibes", "concert energy",
    ],
}


def _composer_from_topic(topic: str) -> str:
    """'Mozart — Eine kleine Nachtmusik' 형태에서 작곡가 성만 뽑아 썸네일 히어로 텍스트로 쓴다."""
    return (topic or "").split("—")[0].strip() or "Classical"


def make_channel_thumbnail(channel_key: str, image_path: str, out_path: str, topic: str,
                            hero_override: str = None):
    """채널별 썸네일 포맷 분기를 한 곳에 모아둔 공용 헬퍼.
    본 파이프라인(build_playlist)과 주간 썸네일 리프레시 스크립트가 공유해서 쓴다."""
    if hero_override == "playlist_only":
        make_caption_thumbnail(image_path, out_path, topic="Playlist", show_waveform=True)
    elif channel_key == "healing":
        # healing은 다른 4개 히어로 채널과 달리 "사진 썸네일" 포맷 — 큰 타이틀도
        # "Playlist" 문구도 없이 사진이 주인공, 작은 파형 아이콘 하나만 (2026-08-13
        # 사용자 명시적 요청: "썸네일 음파만 작게 하나 Playlist 글씨 없다").
        make_photo_thumbnail(image_path, out_path)
    elif channel_key in PLAYLIST_HERO_CHANNELS:
        make_caption_thumbnail(image_path, out_path, topic="Playlist",
                                subtitle_override=topic, show_waveform=True)
    elif channel_key == "mbb":
        make_caption_thumbnail(image_path, out_path, topic=_composer_from_topic(topic),
                                subtitle_override=topic, show_waveform=False)
    else:
        make_caption_thumbnail(image_path, out_path, topic=topic)
RECENT_TOPICS_FILE = "playlist_recent_topics.json"
RECENT_TOPICS_MEMORY = 8  # 최근 이만큼은 다시 안 뽑히게 피함


def pick_auto_topic():
    """사람이 주제를 안 정해준 자동 실행에서, 최근에 쓴 것과 겹치지 않게
    무작위로 주제를 고르고 상태 파일에 기록해서 다음 실행 때도 반복을 피한다."""
    recent = []
    if os.path.exists(RECENT_TOPICS_FILE):
        try:
            with open(RECENT_TOPICS_FILE, encoding="utf-8") as f:
                recent = json.load(f).get("recent", [])
        except Exception:
            recent = []

    pool = CHANNEL_TOPIC_POOLS.get(CHANNEL_KEY, AUTO_TOPIC_POOL)
    candidates = [t for t in pool if t not in recent] or list(pool)
    topic = random.choice(candidates)

    recent = ([topic] + [t for t in recent if t != topic])[:RECENT_TOPICS_MEMORY]
    try:
        with open(RECENT_TOPICS_FILE, "w", encoding="utf-8") as f:
            json.dump({"recent": recent}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"   ⚠️ 최근 주제 기록 실패(무시하고 진행): {e}")

    return topic, AUTO_TOPIC_LANGUAGE_HINTS.get(topic, "")


def build_ai_images(topic, workdir):
    topic = (topic or "").strip() or "tropical beachside vibe, aesthetic lifestyle"

    if CHANNEL_KEY == "globalmusic":
        # 로맨틱글로벌 채널: 여행지 풍경이 아니라 커플이 주인공인 로맨틱한 장면이 핵심
        style = (
            "real photograph shot on a professional DSLR camera with a warm cinematic "
            "color grade, golden-hour or string-light evening lighting, soft romantic "
            "mood, shallow depth of field, no text, no watermark"
        )
        prompts = [
            f"A romantic couple (their faces not clearly identifiable as any real person) "
            f"sharing an intimate moment — holding hands, dancing, or laughing together — "
            f"in a setting inspired by '{topic}', warm golden hour light, dreamy and tender "
            f"atmosphere, {style}",
            f"A different romantic couple moment inspired by '{topic}', evening string "
            f"lights or sunset backdrop, candid joyful embrace or a quiet close moment, "
            f"{style}",
        ]
    elif CHANNEL_KEY == "healing":
        # 힐링 채널: 안개 낀 숲/시냇물/풍경소리 — 차분한 청록 톤, 사람 없음
        style = (
            "real photograph, cinematic, moody desaturated blue-green color grade, "
            "misty and quiet atmosphere, soft natural light, no people, no text, no watermark"
        )
        prompts = [
            f"A misty forest or mountain stream scene evoking '{topic}', rain droplets on "
            f"leaves or gentle mist between trees, tranquil and meditative, {style}",
            f"A different quiet nature close-up related to '{topic}' — a traditional Korean "
            f"temple's curved roof tile edge (giwa) or wooden eaves (cheoma) against a misty "
            f"forest backdrop, rain falling past the eaves, a flowing creek over rocks, or a "
            f"rainy window looking out at forest, {style}",
        ]
    elif CHANNEL_KEY == "starbucks":
        # 카페음악 채널 (2026-08-13 레트로 컨셉으로 갱신): 빈티지 턴테이블/레코드,
        # 오래된 잡지표지 톤, 오래된 카페 외벽/간판, 꽃집 외부 — 실제 브랜드 로고는 넣지 않음(상표권)
        style = (
            "real photograph shot on a professional DSLR camera, warm nostalgic retro "
            "color grade like an old magazine cover, soft golden afternoon light, "
            "shallow depth of field, no visible brand logos or storefront signage, "
            "no text, no watermark"
        )
        prompts = [
            f"A vintage vinyl record player (turntable) spinning on a cozy wooden shelf "
            f"beside a fresh flower in a vase, inspired by '{topic}', warm retro interior, "
            f"soft afternoon light through a window, {style}",
            f"A charming old-fashioned cafe street corner or flower shop storefront "
            f"related to '{topic}', potted plants and flowers out front, warm string "
            f"lights, cozy retro European alley mood, {style}",
        ]
    elif CHANNEL_KEY == "kpop":
        # K-pop 플리: 실존 아이돌 특정 불가 — 화려한 조명/무대 분위기의 실루엣 컨셉
        style = (
            "real photograph, vibrant neon concert lighting, high energy, dynamic "
            "composition, silhouette figures (no identifiable real person), no text, "
            "no watermark"
        )
        prompts = [
            f"A vibrant K-pop concert stage atmosphere evoking '{topic}', colorful neon "
            f"stage lights, silhouette of a dancer, energetic and glossy mood, {style}",
            f"A different vibrant nightlife/stage scene related to '{topic}', laser lights, "
            f"crowd energy, saturated pink-purple-blue color palette, {style}",
        ]
    elif CHANNEL_KEY == "mbb":
        # 클래식(MBB): 작곡가 유화 초상화 스타일 — 실사진이 아니라 고전 회화 톤
        composer = _composer_from_topic(topic)
        style = (
            "classical oil painting style portrait, museum quality, warm sepia and dark "
            "tones, dramatic chiaroscuro lighting, 18th-19th century European painting "
            "aesthetic, no text, no watermark"
        )
        prompts = [
            f"A classical oil painting portrait of a composer in the style of {composer}'s "
            f"era, formal period clothing, holding sheet music or a quill, dignified "
            f"expression, {style}",
            f"A different classical painting scene evoking {composer}'s music — an ornate "
            f"period concert hall, piano, or manuscript close-up, {style}",
        ]
    else:
        style = (
            "real photograph shot on a professional DSLR camera, not a painting, not "
            "digital art, not an illustration, not 3D-rendered — genuine travel-magazine "
            "photojournalism, ultra sharp focus, cinematic wide 16:9 composition, natural "
            "light, realistic color grading, authentic architectural and environmental "
            "detail, no text, no watermark"
        )
        prompts = [
            f"A breathtaking aerial or street-level travel photo capturing the essence of "
            f"{topic}, golden hour warm lighting, dramatic skyline or landscape composition, "
            f"{style}",
            f"A different iconic view of {topic} from another angle or time of day, "
            f"cooler blue-hour or daylight tone, {style}",
        ]
    paths = []
    for i, prompt in enumerate(prompts, 1):
        path = os.path.join(workdir, f"ai_image_{i}.png")
        ok = False
        if GEMINI_API_KEY:
            for _ in range(3):
                if gemini_generate_image(prompt, path):
                    ok = True
                    break
        if not ok:
            make_placeholder_image(path)
            log(f"   ⚠️ AI 이미지 {i} 생성 실패 → 플레이스홀더 대체")
        else:
            log(f"   ✅ AI 이미지 {i} 생성 완료")
        paths.append(path)
    return paths


def pick_duration_target():
    """실행할 때마다 목표 재생시간 구간 자체를 무작위로 골라서, 영상 길이가
    매번 달라지게 한다(항상 60~80분처럼 똑같으면 그 자체가 AI 생성 티가 남)."""
    pool_min_sec, pool_max_sec = CHANNEL_DURATION_POOL_SEC.get(
        CHANNEL_KEY, (DURATION_POOL_MIN_SEC, DURATION_POOL_MAX_SEC))
    lo_min = random.randint(pool_min_sec // 60, (pool_max_sec - 20 * 60) // 60)
    span_min = random.randint(10, 25)
    hi_min = min(lo_min + span_min, pool_max_sec // 60)
    return lo_min * 60, hi_min * 60


# ════════════════════════════════════════════════════════════
# 오디오 조합 (실행마다 다른 목표 재생시간, 30~100분 범위 내)
# ════════════════════════════════════════════════════════════
def build_playlist_audio(service, tracks_meta, out_path):
    # tracks_meta는 filter_tracks_by_language가 이미 "언어 매칭곡을 앞에,
    # 나머지를 뒤에" 순서로 정렬해서 넘겨준 리스트이므로, 여기서 다시 섞으면
    # 그 우선순위가 깨진다 — 순서 그대로 앞에서부터 채운다.
    shuffled = list(tracks_meta)

    target_min_sec, target_max_sec = pick_duration_target()
    log(f"   이번 목표 재생시간: {target_min_sec/60:.0f}~{target_max_sec/60:.0f}분")

    selected_paths = []
    accumulated = 0.0

    for i, meta in enumerate(shuffled):
        ext = os.path.splitext(meta["name"])[1] or ".mp3"
        local_path = os.path.join(WORKDIR, f"track_{i:03d}{ext}")
        log(f"   다운로드 중: {meta['name']}")
        try:
            download_drive_file(service, meta["id"], local_path)
            dur = get_duration(local_path)
            if dur < 1.0:
                raise ValueError(f"재생시간 {dur:.2f}초 — 오디오 파일이 아닌 것으로 판단")
        except Exception as e:
            log(f"   ⚠️ 스킵({meta['name']}): {e}")
            if os.path.exists(local_path):
                os.remove(local_path)
            continue

        if accumulated >= target_min_sec and accumulated + dur > target_max_sec:
            # 목표 구간 안에 이미 들어와 있고 이 곡을 더하면 넘침 -> 나머지는
            # 안 맞을 때마다 계속 찾아 헤매지 않고 여기서 바로 종료 (다운로드 낭비 방지)
            os.remove(local_path)
            log(f"   (목표 구간 도달 — 나머지 트랙 스캔 중단)")
            break

        selected_paths.append(local_path)
        accumulated += dur
        log(f"   ✅ 추가: {meta['name']} ({dur/60:.1f}분) — 누적 {accumulated/60:.1f}분")

        if accumulated >= target_max_sec:
            break

    if accumulated < target_min_sec:
        log(f"   ⚠️ 보유한 음원을 다 써도 {accumulated/60:.1f}분 (목표 {target_min_sec/60:.0f}분 미만)")

    if not selected_paths:
        raise RuntimeError("사용 가능한 음원이 없습니다")

    # 곡 사이마다 1~3초 랜덤 무음을 끼워넣어 기계적으로 딱딱 붙는 느낌을 없앰
    cmd = ["ffmpeg", "-y"]
    gap_seconds_total = 0.0
    n_inputs = 0
    for i, p in enumerate(selected_paths):
        cmd += ["-i", p]
        n_inputs += 1
        if i < len(selected_paths) - 1:
            gap = round(random.uniform(1.0, 3.0), 2)
            gap_seconds_total += gap
            cmd += ["-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={gap}"]
            n_inputs += 1

    filter_complex = "".join(f"[{i}:a:0]" for i in range(n_inputs)) + \
        f"concat=n={n_inputs}:v=0:a=1[outa]"
    cmd += ["-filter_complex", filter_complex, "-map", "[outa]",
            "-c:a", "aac", "-b:a", "192k", out_path]
    run_ffmpeg(cmd)

    return accumulated + gap_seconds_total


# ════════════════════════════════════════════════════════════
# 영상 조립
# ════════════════════════════════════════════════════════════
def make_kenburns_clip(image_path, out_path, duration, fps=25):
    frames = max(int(duration * fps), 1)
    vf = (f"scale=2560:-1,zoompan=z='min(zoom+0.0006,1.25)':d={frames}:"
          f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={VIDEO_W}x{VIDEO_H}:fps={fps},"
          f"format=yuv420p")
    run_ffmpeg(["ffmpeg", "-y", "-loop", "1", "-i", image_path, "-vf", vf,
                "-r", str(fps), "-t", str(duration), "-c:v", "libx264",
                "-pix_fmt", "yuv420p", out_path])


def make_still_clip(image_path, out_path, duration, fps=25):
    vf = (f"scale={VIDEO_W}:{VIDEO_H}:force_original_aspect_ratio=decrease,"
          f"pad={VIDEO_W}:{VIDEO_H}:(ow-iw)/2:(oh-ih)/2,format=yuv420p")
    run_ffmpeg(["ffmpeg", "-y", "-loop", "1", "-i", image_path, "-vf", vf,
                "-r", str(fps), "-t", str(duration), "-c:v", "libx264",
                "-pix_fmt", "yuv420p", out_path])


def concat_stream_copy(clip_paths, out_path):
    list_file = os.path.join(WORKDIR, "video_concat_list.txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for p in clip_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")
    run_ffmpeg(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
                "-c", "copy", out_path])


def build_alternating_visual(image_paths, total_duration, out_path):
    """image_paths(2장)를 IMAGE_SWAP_SEC 간격으로 번갈아 팬줌 처리 후 이어붙임"""
    clips = []
    t = 0.0
    idx = 0
    i = 0
    while t < total_duration - 0.05:
        dur = min(IMAGE_SWAP_SEC, total_duration - t)
        img = image_paths[idx % len(image_paths)]
        cpath = os.path.join(WORKDIR, f"visual_{i:03d}.mp4")
        make_kenburns_clip(img, cpath, duration=dur)
        clips.append(cpath)
        t += dur
        idx += 1
        i += 1
    concat_stream_copy(clips, out_path)


def _escape_drawtext(text):
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def _ffmpeg_path_escape(path):
    """ffmpeg 필터 문자열(-vf/-filter_complex) 안에 파일 경로를 넣을 때 쓴다.
    Windows 절대경로(C:\\Users\\...)는 드라이브 문자 뒤 콜론이 필터의 key=value
    구분자 콜론과 충돌한다 — `\\:`로 이스케이프해도 이 ffmpeg 빌드의 파서가
    "No option name" 에러를 내며 거부하는 걸 직접 테스트로 확인했다. run_ffmpeg가
    항상 저장소 루트를 cwd로 실행되므로, 그 기준 상대경로로 바꾸면 콜론 자체가
    안 나와서 이 문제를 근본적으로 피할 수 있다."""
    try:
        rel = os.path.relpath(path)
    except ValueError:
        rel = path  # 드라이브가 다르면(cwd와 다른 드라이브) 상대경로 자체가 불가능 — 원본 사용
    return rel.replace("\\", "/")


def add_lower_third_bar(video_path, caption_text, out_path):
    """영상 하단에 반투명 바 + 'Playlist | 캡션' 텍스트를 영상 내내 표시"""
    ensure_font()
    text = _escape_drawtext(f"Playlist | {caption_text}")
    bar_h = 70
    vf = (
        f"drawbox=x=0:y=ih-{bar_h}:w=iw:h={bar_h}:color=black@0.45:t=fill,"
        f"drawtext=fontfile={_ffmpeg_path_escape(FONT_PATH)}:text='{text}':"
        f"fontsize=30:fontcolor=white:x=30:y=h-{bar_h}+({bar_h}-th)/2"
    )
    run_ffmpeg(["ffmpeg", "-y", "-i", video_path, "-vf", vf,
                "-c:a", "copy", "-c:v", "libx264", "-pix_fmt", "yuv420p", out_path])


def _resize_cover(img, w, h):
    """원본 비율을 유지한 채 (w,h)를 꽉 채우고 넘치는 부분만 가운데 기준으로
    잘라낸다 (찌그러짐 없는 썸네일용 크롭)."""
    from PIL import Image

    src_w, src_h = img.size
    scale = max(w / src_w, h / src_h)
    new_w, new_h = int(src_w * scale + 0.5), int(src_h * scale + 0.5)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - w) // 2
    top = (new_h - h) // 2
    return img.crop((left, top, left + w, top + h))


def _gradient_band(w, h, band_h, at_top, max_alpha):
    """상단 또는 하단에 텍스트 가독성을 위한 반투명 검정 그라데이션 밴드 생성"""
    from PIL import Image, ImageDraw

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for i in range(band_h):
        frac = (band_h - i) / band_h if at_top else i / band_h
        alpha = int(max_alpha * frac)
        y = i if at_top else h - band_h + i
        draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))
    return overlay


def _draw_vinyl_icon(draw, cx, cy, r, fill=(20, 20, 20, 230)):
    """레퍼런스의 작은 LP판 아이콘 (검정 원반 + 중앙 홀)"""
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill,
                 outline=(255, 255, 255, 90), width=2)
    inner_r = max(int(r * 0.42), 8)
    draw.ellipse([cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r],
                 fill=(70, 70, 70, 255))
    hole_r = max(int(r * 0.1), 3)
    draw.ellipse([cx - hole_r, cy - hole_r, cx + hole_r, cy + hole_r],
                 fill=(0, 0, 0, 255))


def _draw_waveform(draw, cx, cy, n_bars=17, gap=6, max_h=26, color=(255, 255, 255, 180)):
    """하단 중앙의 작은 오디오 파형 아이콘 (고정 시드로 매번 같은 모양)"""
    rnd = random.Random("thumbnail_waveform")
    heights = [max(3, int(max_h * (0.3 + 0.7 * rnd.random()))) for _ in range(n_bars)]
    total_w = n_bars * gap
    x0 = cx - total_w // 2
    for i, hgt in enumerate(heights):
        x = x0 + i * gap
        draw.line([(x, cy - hgt // 2), (x, cy + hgt // 2)], fill=color, width=2)


def make_vinyl_overlay_png(out_path, r=90):
    """영상 위에 겹칠 투명 배경 LP판 PNG. 완전 대칭이면 회전해도 티가 안 나서
    가장자리에 비대칭 하이라이트 호를 하나 그려 회전이 눈에 보이게 한다."""
    from PIL import Image, ImageDraw

    size = r * 2 + 12
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img, "RGBA")
    cx = cy = size // 2
    _draw_vinyl_icon(draw, cx, cy, r)
    draw.arc([cx - r + 10, cy - r + 10, cx + r - 10, cy + r - 10],
              start=200, end=260, fill=(255, 255, 255, 110), width=3)
    img.save(out_path, "PNG")


def add_spinning_vinyl_and_waveform(visual_path, audio_path, out_path,
                                     vinyl_r=90, rotation_period_sec=4.0):
    """팬줌 영상 위에 (1) 실제로 계속 회전하는 LP판 아이콘과 (2) 재생 중인
    음악 파형을 실시간으로 그려주는 오디오 비주얼라이저를 겹쳐서(overlay),
    영상 내내 화면이 정적이지 않고 살아있는 느낌을 준다. 이 단계에서 오디오도
    함께 입혀서 최종 출력하므로 별도 mux_video_audio 호출이 필요 없다."""
    import math
    vinyl_png = os.path.join(WORKDIR, "vinyl_icon.png")
    make_vinyl_overlay_png(vinyl_png, r=vinyl_r)
    icon_size = vinyl_r * 2 + 12
    rot_canvas = math.ceil(icon_size * 1.4143) + 2  # 회전해도 안 잘리도록 대각선 크기로 캔버스 확보

    wave_w, wave_h = 640, 90
    filter_complex = (
        f"[1:v]format=rgba,rotate=2*PI*t/{rotation_period_sec}:c=none:"
        f"ow={rot_canvas}:oh={rot_canvas}[vinylrot];"
        f"[2:a]volume=3.0,showwaves=s={wave_w}x{wave_h}:mode=cline:colors=white@0.9:rate=25,format=rgba[wave];"
        f"[0:v][vinylrot]overlay=x=(W-w)/2:y=(H-h)/2:shortest=1[v1];"
        f"[v1][wave]overlay=x=(W-w)/2:y=H-h-60[vout]"
    )
    run_ffmpeg([
        "ffmpeg", "-y",
        "-i", visual_path,
        "-loop", "1", "-i", vinyl_png,
        "-i", audio_path,
        "-filter_complex", filter_complex,
        "-map", "[vout]", "-map", "2:a",
        "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p", "-shortest",
        out_path,
    ])


def trim_audio_from(src_path, start_sec, out_path):
    """오디오를 start_sec 지점부터 끝까지 자른다 — 인트로가 곡 앞부분을 쓴 뒤,
    본편이 그 이어지는 지점부터 재생하도록 해서 같은 구간이 겹쳐 들리지 않게 한다."""
    run_ffmpeg(["ffmpeg", "-y", "-i", src_path, "-ss", str(start_sec),
                "-c:a", "aac", out_path])


def make_intro_clip(intro_still_path, audio_path, out_path, duration=INTRO_DURATION_SEC):
    """썸네일과 같은 매거진 표지 디자인(단, 타이틀은 큼직하게 'Playlist')을
    그대로 살려서, 살짝 줌인되고 실제 재생될 음악에 반응하는 파형이 움직이는
    인트로 클립을 만든다. 최종 영상 맨 앞에 붙여서 "이 영상이 플레이리스트"라는
    걸 시청자가 바로 알아보게 한다."""
    intro_audio = os.path.join(WORKDIR, "intro_audio.m4a")
    run_ffmpeg(["ffmpeg", "-y", "-i", audio_path, "-t", str(duration),
                "-c:a", "aac", intro_audio])

    # scale 단계에서 lanczos를 명시해야 AI 초상화 같은 소스가 확대될 때
    # 흐릿해지지 않는다(기본 flags는 bilinear라 4K로 늘렸을 때 뭉개짐 — 2026-08-13
    # 사용자 피드백: "모짜르트 초상화 업스케일 4K" 이후 표준 적용).
    frames = int(duration * 25)
    zoom_vf = (f"scale=2400:-1:flags=lanczos,zoompan=z='min(zoom+0.0015,1.08)':d={frames}:"
               f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={VIDEO_W}x{VIDEO_H}:fps=25,"
               f"format=yuv420p")
    zoomed = os.path.join(WORKDIR, "intro_zoomed.mp4")
    run_ffmpeg(["ffmpeg", "-y", "-loop", "1", "-i", intro_still_path, "-vf", zoom_vf,
                "-t", str(duration), "-c:v", "libx264", "-pix_fmt", "yuv420p", zoomed])

    # 파형: 밋밋한 흰색 오실로스코프 선(cline) 대신, 골드 톤 두꺼운 막대(p2p)로
    # 채널 브랜드 톤과 어울리게 + 은은한 그림자를 한 겹 더 깔아 입체감을 준다
    # (2026-08-13 사용자 피드백: "음파가 넘 멋이없어 - 교체" 이후 표준 적용).
    wave_w, wave_h = 760, 140
    bar_w, bar_h = wave_w + 60, wave_h + 50
    bar_y = VIDEO_H - bar_h - 60
    filter_complex = (
        f"[1:a]volume=3.0,showwaves=s={wave_w}x{wave_h}:mode=p2p:colors=0x000000:rate=25,"
        f"format=rgba,colorchannelmixer=aa=0.35[waveshadow];"
        f"[1:a]volume=3.0,showwaves=s={wave_w}x{wave_h}:mode=p2p:colors=0xF3D27A|0xE0A93E:rate=25,"
        f"format=rgba[wave];"
        f"[0:v]drawbox=x=(iw-{bar_w})/2:y={bar_y}:w={bar_w}:h={bar_h}:"
        f"color=black@0.5:t=fill[bg];"
        f"[bg][waveshadow]overlay=x=(W-w)/2+3:y={bar_y + (bar_h - wave_h) // 2 + 3}[bg2];"
        f"[bg2][wave]overlay=x=(W-w)/2:y={bar_y + (bar_h - wave_h) // 2}[vout]"
    )
    run_ffmpeg([
        "ffmpeg", "-y", "-i", zoomed, "-i", intro_audio,
        "-filter_complex", filter_complex,
        "-map", "[vout]", "-map", "1:a",
        "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", "-shortest",
        out_path,
    ])


def concat_intro_and_main(intro_path, main_path, out_path):
    """서로 다른 단계에서 만들어진 두 영상(인트로/본편)을 안전하게 이어붙인다.
    concat 데먹서는 코덱 파라미터가 조금만 달라도 깨지기 쉬워서, 필터 기반
    concat을 쓴다. 이 함수가 실제 업로드될 최종 파일(final.mp4)을 만드는
    지점이므로, ffmpeg/Lavf 같은 인코더 시그니처가 메타데이터에 안 남게
    지운다("AI 흔적 최소화" 원칙 — [[feedback_minimize_ai_tells]])."""
    run_ffmpeg([
        "ffmpeg", "-y", "-i", intro_path, "-i", main_path,
        "-filter_complex", "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p",
        "-map_metadata", "-1", "-fflags", "+bitexact",
        "-flags:v", "+bitexact", "-flags:a", "+bitexact",
        out_path,
    ])


def _dotted_hline(draw, cx, y, total_w, dash_w=6, gap=8, fill=(255, 255, 255, 220)):
    x = cx - total_w // 2
    end = cx + total_w // 2
    while x < end:
        draw.line([(x, y), (min(x + dash_w, end), y)], fill=fill, width=2)
        x += dash_w + gap


def make_caption_thumbnail(image_path, out_path, topic="", subtitle_override=None,
                            show_waveform=False, w=1280, h=720, title_font_override=None):
    """여행 잡지 표지 스타일 썸네일: 상단 좌우에 작은 브랜드 라벨/볼륨 표기,
    화면 대부분을 채우는 초대형 세리프 주제어 타이틀, 그 아래 얇은 점선 구분선.
    배경 사진만 AI 생성이고 나머지는 전부 PIL로 직접 그려서 무료로 자동 생성된다."""
    from PIL import Image, ImageDraw, ImageFont
    from datetime import datetime as _dt

    title_font_path = title_font_override or ensure_title_font()
    label_font_path = ensure_font()

    def _font(path, size, weight=None):
        f = ImageFont.truetype(path, size)
        if weight is not None:
            try:
                f.set_variation_by_axes([weight])
            except Exception:
                pass
        return f

    img = _resize_cover(Image.open(image_path).convert("RGB"), w, h).convert("RGBA")
    img = Image.alpha_composite(img, _gradient_band(w, h, int(h * 0.30), True, 70))
    img = Image.alpha_composite(img, _gradient_band(w, h, int(h * 0.22), False, 60))
    draw = ImageDraw.Draw(img, "RGBA")

    label_font = _font(label_font_path, 24)

    # 상단: 브랜드 라벨(좌) / VOL. 표기(우) — 잡지 표지 느낌의 작은 캡션
    brand = " ".join(list(THUMBNAIL_BRAND_LABEL.upper()))  # 글자 사이 여백을 둔 스몰캡스 느낌
    draw.text((36, 30), brand, font=label_font, fill=(255, 255, 255, 235))
    vol_text = f"VOL. {_dt.now().timetuple().tm_yday:02d}"
    vol_bbox = draw.textbbox((0, 0), vol_text, font=label_font)
    draw.text((w - 36 - (vol_bbox[2] - vol_bbox[0]), 30), vol_text,
               font=label_font, fill=(255, 255, 255, 235))

    # 중앙: 주제어를 초대형 세리프로 — 폭의 92%를 채우도록 자동 축소
    title = (topic or THUMBNAIL_BRAND_LABEL).strip().upper() or "PLAYLIST"
    # Playfair Display엔 한글/한자 글리프가 없어서, 스크립트에 맞는 폰트로 대체:
    # 한글이 섞이면 나눔고딕, 한자/가나(일본어)가 섞이면 Noto Serif JP
    has_hangul = any('가' <= c <= '힣' for c in title)
    has_cjk = any('一' <= c <= '鿿' or '぀' <= c <= 'ヿ' for c in title)
    if has_hangul:
        title_render_font_path, title_render_weight = label_font_path, None
    elif has_cjk:
        title_render_font_path, title_render_weight = ensure_jp_font(), 700
    else:
        title_render_font_path, title_render_weight = title_font_path, 500
    # 2026-08-14 사용자 요청: "제목과 자막이 커야해.. 이탈자 없어야 하니까" — 시청자
    # 이탈 방지를 위해 타이틀을 화면폭에 최대한 꽉 채운다(5K 기본 해상도와 함께 표준).
    max_w = int(w * 0.97)
    size = 260
    while size > 40:
        font = _font(title_render_font_path, size, title_render_weight)
        bbox = draw.textbbox((0, 0), title, font=font)
        if bbox[2] - bbox[0] <= max_w:
            break
        size -= 6
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    title_y = (h - th) // 2 - int(h * 0.03)
    draw.text(((w - tw) // 2, title_y - bbox[1]), title, font=font,
               fill=(255, 255, 255, 255))
    cursor_y = title_y + th

    # 타이틀 아래 소제목: 명시적으로 지정되면 그걸 쓰고(예: 인트로의 "Playlist"),
    # 아니면 도시별 현지어 소제목(가나/한글 등)이 NATIVE_SUBTITLE_MAP에 있을 때만 표시
    if subtitle_override is not None:
        subtitle = subtitle_override
    else:
        subtitle = NATIVE_SUBTITLE_MAP.get((topic or "").strip(), "")
    if subtitle:
        sub_font_path = ensure_jp_font() if any(
            '぀' <= c <= 'ヿ' or '一' <= c <= '鿿' for c in subtitle) else label_font_path
        sub_font = _font(sub_font_path, 34)
        sub_bbox = draw.textbbox((0, 0), subtitle, font=sub_font)
        sub_y = cursor_y + int(h * 0.02)
        draw.text(((w - (sub_bbox[2] - sub_bbox[0])) // 2, sub_y - sub_bbox[1]),
                   subtitle, font=sub_font, fill=(255, 255, 255, 230))
        cursor_y = sub_y + (sub_bbox[3] - sub_bbox[1])

    # 그 아래: 얇은 점선 구분선
    line_y = cursor_y + int(h * 0.05)
    _dotted_hline(draw, w // 2, line_y, int(w * 0.5))

    # 로맨틱글로벌 등: 감성 강조용으로 구분선 아래 오디오 파형 아이콘 추가
    if show_waveform:
        _draw_waveform(draw, w // 2, line_y + 34, n_bars=27, gap=10, max_h=40,
                        color=(255, 255, 255, 220))

    # 5K로 업스케일해서 저장 (레이아웃 좌표는 1280x720 캔버스에 맞춰져 있어서
    # 그 비율 그대로 유지한 채, 마지막에 해상도만 5K로 끌어올린다 — 유튜브 썸네일
    # 화질 요구사항 대응, Lanczos로 최대한 선명하게).
    final_img = img.convert("RGB")
    if (w, h) != THUMBNAIL_UPSCALE_SIZE:
        final_img = final_img.resize(THUMBNAIL_UPSCALE_SIZE, Image.LANCZOS)
    _save_thumbnail_capped(final_img, out_path)


def _save_thumbnail_capped(img, out_path, max_bytes=2 * 1024 * 1024):
    """유튜브 썸네일 API 2MB 제한 대응. 5K로 올린 뒤로 디테일이 많은 사진(특히
    아카이브 원본 프레임)은 트루컬러 PNG로 저장하면 2MB를 쉽게 넘는다 — 화질
    저하가 거의 안 보이는 adaptive 팔레트 단계부터 순서대로 시도해서 제한 안에
    맞춘다(2026-08-14, 5K 적용 직후 실제로 걸려서 발견)."""
    from PIL import Image

    img.save(out_path, "PNG", optimize=True)
    if os.path.getsize(out_path) <= max_bytes:
        return
    for colors in (256, 192, 128, 96, 64):
        quantized = img.quantize(colors=colors, method=Image.MEDIANCUT, dither=Image.FLOYDSTEINBERG)
        quantized.save(out_path, "PNG", optimize=True)
        if os.path.getsize(out_path) <= max_bytes:
            return
    # 최후 수단: 팔레트로도 안 되면 해상도를 살짝 낮춘다(4K로)
    smaller = img.resize((3840, int(3840 * img.height / img.width)), Image.LANCZOS)
    smaller.save(out_path, "PNG", optimize=True)


def make_photo_thumbnail(image_path, out_path, w=1280, h=720):
    """healing 전용 '사진 썸네일' 포맷 (2026-08-13 사용자 요청): 큰 타이틀/'Playlist'
    문구 없이 사진 자체가 주인공이고, 이 영상이 플레이리스트라는 것만 알아볼 수 있게
    작은 파형 아이콘 하나만 하단 구석에 조용히 얹는다. 나머지 4개 히어로 채널(글로벌뮤직/
    스타벅스/kpop)의 큼직한 매거진 표지 스타일과는 완전히 다른, 조용한 포맷."""
    from PIL import Image, ImageDraw

    img = _resize_cover(Image.open(image_path).convert("RGB"), w, h).convert("RGBA")
    img = Image.alpha_composite(img, _gradient_band(w, h, int(h * 0.16), False, 50))
    draw = ImageDraw.Draw(img, "RGBA")

    # 하단 우측 구석에 작은 파형 아이콘만 — 큰 타이틀도, "Playlist" 문구도 없음
    _draw_waveform(draw, w - 90, h - 40, n_bars=15, gap=6, max_h=22,
                   color=(255, 255, 255, 200))

    final_img = img.convert("RGB")
    if (w, h) != THUMBNAIL_UPSCALE_SIZE:
        final_img = final_img.resize(THUMBNAIL_UPSCALE_SIZE, Image.LANCZOS)
    _save_thumbnail_capped(final_img, out_path)


def mux_video_audio(video_path, audio_path, out_path):
    run_ffmpeg(["ffmpeg", "-y", "-i", video_path, "-i", audio_path,
                "-c:v", "copy", "-c:a", "aac", "-shortest", out_path])


def make_static_video(image_path, audio_path, out_path):
    """주제어 없을 때 폴백: 정지 이미지 1장 + 음악. 이 함수도 최종 업로드
    파일을 직접 만들 수 있는 경로라 인코더 시그니처를 지운다."""
    vf = ("scale=1920:1080:force_original_aspect_ratio=decrease,"
          "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,format=yuv420p")
    run_ffmpeg(["ffmpeg", "-y", "-loop", "1", "-i", image_path, "-i", audio_path,
                "-vf", vf, "-c:v", "libx264", "-tune", "stillimage",
                "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p",
                "-map_metadata", "-1", "-fflags", "+bitexact",
                "-flags:v", "+bitexact", "-flags:a", "+bitexact",
                "-shortest", out_path])


# 파일명에 "프랑스어" 같은 명시적 태그가 없어도, 제목 자체에 그 언어 특유의
# 발음구별기호가 섞여 있으면(예: Suno가 붙인 실제 프랑스어 제목) 같은 언어로 간주
LANGUAGE_HINT_CHARS = {
    "프랑스어": set("éèêëàâçîïôùûüœÉÈÊËÀÂÇÎÏÔÙÛÜŒ"),
    "독일어": set("äöüßÄÖÜ"),
    "스페인어": set("áéíóúñ¿¡ÁÉÍÓÚÑ"),
    "이탈리아어": set("àèéìòùÀÈÉÌÒÙ"),
    "포르투갈어": set("ãõâêôáéíóúçÃÕÂÊÔÁÉÍÓÚÇ"),
}

# 일본어/중국어/한국어처럼 라틴 발음구별기호가 아니라 아예 다른 문자 체계를 쓰는
# 언어는 개별 글자가 아니라 유니코드 스크립트 범위로 판별한다
LANGUAGE_SCRIPT_RANGES = {
    "일본어": [(0x3040, 0x30FF), (0x4E00, 0x9FFF)],   # 히라가나/가타카나 + 한자
    "중국어": [(0x4E00, 0x9FFF)],                       # 한자(간체/번체 공용 대역)
    "한국어": [(0xAC00, 0xD7A3)],                       # 한글 음절
}


def _bring_longest_to_front(items):
    """인트로에서 처음 들리는 곡이 가장 임팩트 있게, 재생시간이 가장 긴 곡을
    맨 앞으로 보낸다(파일 크기를 재생시간 근사치로 사용 — 다운로드 없이 알 수
    있는 값이라 전체 목록을 미리 받아볼 필요가 없다). 나머지는 무작위 순서 유지."""
    if not items:
        return items

    def _size(t):
        try:
            return int(t.get("size", 0) or 0)
        except (TypeError, ValueError):
            return 0

    longest = max(items, key=_size)
    rest = [t for t in items if t is not longest]
    random.shuffle(rest)
    return [longest] + rest


def filter_tracks_by_language(tracks, keyword):
    """keyword가 Mixed/빈값이면 전체를 무작위 순서로 반환.
    아니면 파일명에 해당 언어 태그가 있거나(명시적), 그 언어 특유의 발음구별기호/
    문자 체계가 제목에 섞여 있는(암묵적) 곡을 먼저 앞에 배치하고, 나머지 곡을
    뒤에 이어붙여 돌려준다 — build_playlist_audio가 앞에서부터 채우므로 매칭곡이
    최우선으로 들어가고, 목표 재생시간을 못 채우면 자연스럽게 나머지로 채워진다.
    매칭되는 곡이 하나도 없으면 전체를 무작위 순서로 반환(폴백)."""
    if not keyword or keyword.strip().lower() in MIXED_KEYWORDS:
        log("   (필터 없음 — Mixed, 전체 곡에서 무작위 선택)")
        return _bring_longest_to_front(list(tracks))

    tag = LANGUAGE_TAG_MAP.get(keyword.strip().lower(), keyword.strip())
    hint_chars = LANGUAGE_HINT_CHARS.get(tag, set())
    script_ranges = LANGUAGE_SCRIPT_RANGES.get(tag, [])

    def is_match(name):
        if tag.lower() in name.lower():
            return True
        if hint_chars and any(c in hint_chars for c in name):
            return True
        if script_ranges:
            for c in name:
                cp = ord(c)
                if any(lo <= cp <= hi for lo, hi in script_ranges):
                    return True
        return False

    matched = [t for t in tracks if is_match(t["name"])]
    others = [t for t in tracks if not is_match(t["name"])]

    if not matched:
        log(f"   ⚠️ '{keyword}'({tag}) 태그/제목 매칭 곡이 없어서 전체 곡으로 진행")
        return _bring_longest_to_front(others)
    log(f"   '{keyword}'({tag}) 매칭 {len(matched)}개를 우선 배치, 나머지 {len(others)}개는 뒤에서 채움")
    random.shuffle(others)
    return _bring_longest_to_front(matched) + others


# ════════════════════════════════════════════════════════════
# 메인
# ════════════════════════════════════════════════════════════
def main():
    missing = [k for k, v in {
        "GOOGLE_OAUTH_CLIENT_ID": GOOGLE_OAUTH_CLIENT_ID,
        "GOOGLE_OAUTH_CLIENT_SECRET": GOOGLE_OAUTH_CLIENT_SECRET,
        "GOOGLE_OAUTH_REFRESH_TOKEN": GOOGLE_OAUTH_REFRESH_TOKEN,
    }.items() if not v]
    if missing:
        log(f"❌ 환경변수 누락: {missing}")
        raise SystemExit(1)

    topic_keyword = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TOPIC_KEYWORD", "")
    topic_keyword = PRESET_TOPIC_EN_MAP.get(topic_keyword.strip(), topic_keyword)
    language_keyword = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("LANGUAGE_KEYWORD", "")
    caption_text_input = sys.argv[3] if len(sys.argv) > 3 else os.environ.get("CAPTION_TEXT", "")

    auto_mode = os.environ.get("AUTO_TOPIC", "").strip().lower() == "true"
    if auto_mode and not topic_keyword.strip():
        topic_keyword, auto_lang = pick_auto_topic()
        if not language_keyword.strip():
            language_keyword = auto_lang
        log(f"🤖 자동 선택된 주제: {topic_keyword} (언어: {language_keyword or 'Mixed'})")

    # (2026-08-03에 넣었던 "starbucks 채널은 일본어 기본값" 규칙은 2026-08-06
    # starbucks 채널이 보컬없는 카페 연주곡 전용으로 재배정되면서 더 이상 맞지
    # 않아 제거함 — 연주곡은 언어 태그로 고를 대상이 아니라 항상 Mixed로 둔다.)

    os.makedirs(WORKDIR, exist_ok=True)
    service = get_drive_service()

    log("1/5 원곡 폴더에서 음악 목록 조회 중...")
    tracks = list_folder_files(service, MUSIC_SOURCE_FOLDER_ID, AUDIO_EXTS, "audio/")
    if not tracks:
        log("❌ 원곡 폴더에 음원이 없습니다")
        raise SystemExit(1)
    log(f"   -> {len(tracks)}개 트랙 발견")
    tracks = filter_tracks_by_language(tracks, language_keyword)

    log("2/5 음악 60~80분 분량으로 무작위 이어붙이는 중...")
    audio_path = os.path.join(WORKDIR, "playlist_audio.m4a")
    total_sec = build_playlist_audio(service, tracks, audio_path)
    log(f"   ✅ 총 재생시간: {total_sec/60:.1f}분")

    final_path = os.path.join(WORKDIR, "final.mp4")
    thumbnail_out = os.path.join(WORKDIR, "thumbnail.png")

    if topic_keyword.strip():
        log(f"3/5 주제어 '{topic_keyword}' 기반 AI 이미지 2장 생성 중...")
        image_paths = build_ai_images(topic_keyword, WORKDIR)
        caption_text = build_caption_text(topic_keyword, caption_text_input)
        log(f"   캡션 문구: {caption_text}")
        # 채널별 썸네일 포맷 분기는 make_channel_thumbnail()에 모아둠(구독자 50만+
        # 플리 채널 벤치마킹 공통 포맷 — 주간 썸네일 리프레시 스크립트와 로직 공유)
        make_channel_thumbnail(CHANNEL_KEY, image_paths[0], thumbnail_out, topic_keyword)

        log("4/5 팬줌 영상 조립 + 하단 캡션바 삽입 중...")
        # 인트로가 곡 앞부분(INTRO_DURATION_SEC)을 쓰므로, 본편은 그 이어지는
        # 지점부터 재생해서 같은 구간이 겹쳐 들리지 않고 자연스럽게 이어지게 한다
        body_audio_path = os.path.join(WORKDIR, "body_audio.m4a")
        trim_audio_from(audio_path, INTRO_DURATION_SEC, body_audio_path)
        body_total_sec = total_sec - INTRO_DURATION_SEC

        visual_path = os.path.join(WORKDIR, "visual.mp4")
        build_alternating_visual(image_paths, body_total_sec, visual_path)
        muxed_path = os.path.join(WORKDIR, "muxed.mp4")
        add_spinning_vinyl_and_waveform(visual_path, body_audio_path, muxed_path)
        body_path = os.path.join(WORKDIR, "body.mp4")
        add_lower_third_bar(muxed_path, caption_text, body_path)

        log("   인트로(줌인 + 실시간 파형) 붙이는 중...")
        intro_still = os.path.join(WORKDIR, "intro_still.png")
        make_channel_thumbnail(CHANNEL_KEY, image_paths[0], intro_still, topic_keyword)
        intro_clip = os.path.join(WORKDIR, "intro_clip.mp4")
        make_intro_clip(intro_still, audio_path, intro_clip)
        concat_intro_and_main(intro_clip, body_path, final_path)
    else:
        log("3/5 주제어 없음 — 썸네일창고에서 이미지 무작위 선택(폴백)...")
        thumbs = list_folder_files(service, THUMBNAIL_FOLDER_ID, IMAGE_EXTS, "image/")
        if not thumbs:
            log("❌ 썸네일창고에 이미지가 없습니다")
            raise SystemExit(1)
        thumb_meta = random.choice(thumbs)
        thumb_ext = os.path.splitext(thumb_meta["name"])[1] or ".jpg"
        thumb_path = os.path.join(WORKDIR, f"thumbnail{thumb_ext}")
        download_drive_file(service, thumb_meta["id"], thumb_path)
        log(f"   ✅ 썸네일: {thumb_meta['name']}")

        log("4/5 정지 이미지 + 음악으로 영상 생성 중...")
        make_static_video(thumb_path, audio_path, final_path)
        from PIL import Image
        Image.open(thumb_path).convert("RGB").save(thumbnail_out, "PNG")

    log("5/5 구글드라이브 업로드 중...")
    now = datetime.now(KST)
    rand_suffix = f"{random.randint(0, 9999):04d}"
    filename = f"{now.year}_{now.month}_{now.day}_{rand_suffix}.mp4"
    thumb_filename = f"{now.year}_{now.month}_{now.day}_{rand_suffix}_thumbnail.png"

    link, video_drive_id = upload_to_drive(service, final_path, OUTPUT_FOLDER_ID, filename)
    thumb_link, thumb_drive_id = upload_to_drive(service, thumbnail_out, OUTPUT_FOLDER_ID, thumb_filename)

    log("🎉 완료")
    log(f"   파일명: {filename}")
    log(f"   링크: {link}")
    log(f"   썸네일: {thumb_link}")

    # 유튜브 실제 업로드는 별도 잡(publish)에서 진행하므로, 여기서는 제목/설명만
    # 미리 만들어 다음 잡이 쓸 수 있게 메타데이터로 남겨둔다
    upload_topic = topic_keyword.strip() or "Chill"
    upload_caption = caption_text if topic_keyword.strip() else ""
    yt_title, yt_description, title_is_fallback = generate_youtube_title_description(
        upload_topic, upload_caption, total_sec / 60)
    log(f"   유튜브 제목(예정): {yt_title}" + (" ⚠️ 폴백 제목(Gemini 생성 실패)" if title_is_fallback else ""))

    meta = {
        "video_drive_id": video_drive_id,
        "thumb_drive_id": thumb_drive_id,
        "filename": filename,
        "title": yt_title,
        "description": yt_description,
        "title_is_fallback": title_is_fallback,
        "topic": upload_topic,
        "duration_min": round(total_sec / 60, 1),
    }
    with open(os.path.join(WORKDIR, "upload_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    if GMAIL_APP_PASSWORD:
        try:
            send_email(
                f"[플레이리스트 준비완료] {yt_title[:60]}",
                f"영상이 만들어졌어요. 유튜브 업로드 승인은 곧 이어지는 GitHub 알림 메일에서 "
                f"'Approve and deploy' 버튼 한 번이면 돼요.\n\n"
                f"제목: {yt_title}\n\n설명:\n{yt_description}\n\n"
                f"재생시간: {total_sec/60:.0f}분\n\n"
                f"미리보기(드라이브): {link}\n썸네일: {thumb_link}\n",
            )
        except Exception as e:
            log(f"   ⚠️ 이메일 발송 실패(무시하고 진행): {e}")


if __name__ == "__main__":
    main()
