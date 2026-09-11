#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
topik_quiz_longform.py
─────────────────────────────────────────────────────────────
TOPIK 채널용 ~30분 단어 퀴즈 롱폼 자동 생성기.

mbb_work/_build_topik_longform.py 프로토타입(2026-08-13, 실제로 "1시간
롱폼" 결과물을 만들어낸 원본 — topik_basic_500 시트에서 단어를 뽑아 순수
타이포그래피 카드 + TTS로 롱폼을 만드는 방식)을 정식 파이프라인으로
승격한 버전. 사용자 지시(2026-08-17 "VEO나 쓸데없는거 다 막아")에 맞춰
Gemini 이미지 생성은 아예 쓰지 않는다 — topik_quiz_shorts.py의 퀴즈
포맷(질문 카드 → 딩 → 정답 공개 카드)만 그대로 가져오되, 문항 이미지는
Gemini 아이콘 대신 순수 타이포그래피 카드로 대체해서 이미지 생성 비용을
0으로 만들었다.

문항 소스: topik_basic_500 구글시트(500개 단어, D열에 사용여부 기록).
매 실행마다 목표 재생시간(28분)을 채울 만큼 무작위로 뽑아 쓰고, 쓴
단어는 D열에 "Y"로 표시해서 다음 실행엔 겹치지 않게 한다(원본 프로토
타입엔 이 표시 로직이 빠져 있어서 매번 같은 20개만 뽑는 버그가 있었음
— 여기서 수정). 500개를 다 쓰면 자동으로 리셋해서 계속 순환한다.

사용법: python scripts/topik_quiz_longform.py
필요 환경변수:
    ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID          - TTS(없으면 무음 대체)
    GOOGLE_OAUTH_CLIENT_ID/SECRET/REFRESH_TOKEN      - 시트 읽기/쓰기 공용
    YOUTUBE_OAUTH_REFRESH_TOKEN_TOPIK_BROAD          - TOPIK 채널 업로드 전용
    OPENAI_API_KEY                                   - (선택) 제목/설명 생성
필요 시스템 도구: ffmpeg, ffprobe
"""
import os
import sys
import json
import random
import subprocess
from datetime import datetime, timezone, timedelta

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gsheets_direct import get_sheets_service  # noqa: E402
try:
    from openai_text import openai_available, openai_generate_text  # noqa: E402
except Exception:
    def openai_available():
        return False

    def openai_generate_text(*a, **kw):
        raise RuntimeError("openai_text 사용 불가")

SHEET_ID = "1DCGDwvOR2zFpZf3i9J0G5urnGtZm_sMnXZS63z-0RhI"
SHEET_TAB = ""  # 탭 지정 없이 기본 첫 탭 사용(프로토타입과 동일)
SHEET_RANGE = "A2:D520"

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID") or "21m00Tcm4TlvDq8ikWAM"
ELEVENLABS_MODEL = "eleven_multilingual_v2"

YOUTUBE_TOPIK_REFRESH_TOKEN = os.environ.get("YOUTUBE_OAUTH_REFRESH_TOKEN_TOPIK_BROAD", "")
GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")

WORKDIR = "topik_longform_output"
os.makedirs(WORKDIR, exist_ok=True)

VIDEO_W, VIDEO_H = 1920, 1080
TARGET_SEC = 28 * 60      # 최소 목표(28분) — 도달하면 그만 뽑는다
HARD_CAP_SEC = 34 * 60    # 안전상한(과도한 오버슈트 방지)
MAX_WORDS = 400           # 안전상한(무한루프 방지)
THUMBNAIL_UPSCALE = (5120, 2880)  # 5K — 이 세션 공통 기준

FONT_CANDIDATES = [
    "C:/Windows/Fonts/malgunbd.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
]


def log(msg):
    print(msg, flush=True)


def resolve_font():
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def run_ffmpeg(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg 실패: " + " ".join(cmd) + "\n" + proc.stderr[-2000:])


def get_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return float(out.stdout.strip())


def make_silence(out_path, duration):
    run_ffmpeg(["ffmpeg", "-y", "-f", "lavfi", "-i",
                f"anullsrc=r=44100:cl=stereo:d={duration}", "-c:a", "aac", out_path])


def make_ding(out_path):
    run_ffmpeg(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=1046:duration=0.35",
                "-af", "afade=t=out:st=0.15:d=0.2,volume=2.0", "-c:a", "aac", out_path])


def elevenlabs_tts(text, out_path):
    if not ELEVENLABS_API_KEY:
        return False
    import requests
    try:
        r = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
            headers={"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json", "Accept": "audio/mpeg"},
            json={"text": text, "model_id": ELEVENLABS_MODEL,
                  "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}},
            timeout=60,
        )
        r.raise_for_status()
        with open(out_path, "wb") as f:
            f.write(r.content)
        return True
    except Exception as e:
        log(f"   ⚠️ TTS 실패: {e}")
        return False


# ════════════════════════════════════════════════════════════
# 시트: 미사용 단어 확보 + 사용한 만큼만 D열에 "Y" 기록
# ════════════════════════════════════════════════════════════
def fetch_shuffled_unused_pool(svc):
    resp = svc.spreadsheets().values().get(spreadsheetId=SHEET_ID, range=SHEET_RANGE).execute()
    rows = resp.get("values", [])

    def is_unused(r):
        return len(r) < 4 or r[3] != "Y"

    pool = [(i, r[0], r[1], r[2]) for i, r in enumerate(rows) if len(r) >= 3 and is_unused(r)]

    if len(pool) < 40:
        log(f"   ⚠️ 미사용 단어 {len(pool)}개뿐 — 500개 전체 리셋 후 순환")
        clear_rows = len(rows)
        if clear_rows:
            svc.spreadsheets().values().update(
                spreadsheetId=SHEET_ID, range=f"D2:D{1 + clear_rows}",
                valueInputOption="RAW", body={"values": [[""]] * clear_rows}).execute()
        pool = [(i, r[0], r[1], r[2]) for i, r in enumerate(rows) if len(r) >= 3]

    random.shuffle(pool)
    return pool[:MAX_WORDS]


def mark_used(svc, consumed_row_indices):
    if not consumed_row_indices:
        return
    data = [{"range": f"D{i + 2}", "values": [["Y"]]} for i in consumed_row_indices]
    svc.spreadsheets().values().batchUpdate(
        spreadsheetId=SHEET_ID, body={"valueInputOption": "RAW", "data": data}).execute()


# ════════════════════════════════════════════════════════════
# 카드(질문/정답 공개) 렌더링
# ════════════════════════════════════════════════════════════
def draw_card(word, meaning, category, idx, total, reveal, out_path, font_path):
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (VIDEO_W, VIDEO_H), (18, 18, 24))
    draw = ImageDraw.Draw(img)

    def _font(size):
        return ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()

    def centered(text, font, y, fill):
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        draw.text(((VIDEO_W - w) // 2 - bbox[0], y), text, font=font, fill=fill)

    centered(f"TOPIK VOCAB QUIZ · {category}", _font(40), 130, (180, 180, 190))

    wbbox = draw.textbbox((0, 0), word, font=_font(220))
    ww, wh = wbbox[2] - wbbox[0], wbbox[3] - wbbox[1]
    wy = (VIDEO_H - wh) // 2 - 80
    centered(word, _font(220), wy - wbbox[1], (255, 255, 255))

    if reveal:
        centered(f"✅  {meaning}", _font(70), wy + wh + 60, (140, 230, 160))
    else:
        centered("❓  무슨 뜻일까요?", _font(60), wy + wh + 60, (255, 210, 120))

    prog = f"{idx}/{total}"
    pb = draw.textbbox((0, 0), prog, font=_font(32))
    draw.text((VIDEO_W - (pb[2] - pb[0]) - 60, VIDEO_H - 100), prog, font=_font(32), fill=(140, 140, 150))

    img.save(out_path, "PNG")


def still_clip(image_path, audio_path, out_path):
    dur = get_duration(audio_path)
    run_ffmpeg(["ffmpeg", "-y", "-loop", "1", "-i", image_path, "-i", audio_path,
                "-t", str(dur), "-vf", f"scale={VIDEO_W}:{VIDEO_H},format=yuv420p",
                "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p",
                "-shortest", out_path])
    return dur


def build_word_clips(word, meaning, category, idx, total, font_path, ding_path):
    q_frame = os.path.join(WORKDIR, f"q_{idx}.png")
    a_frame = os.path.join(WORKDIR, f"a_{idx}.png")
    draw_card(word, meaning, category, idx, total, reveal=False, out_path=q_frame, font_path=font_path)
    draw_card(word, meaning, category, idx, total, reveal=True, out_path=a_frame, font_path=font_path)

    q_audio = os.path.join(WORKDIR, f"qa_{idx}.mp3")
    a_audio = os.path.join(WORKDIR, f"aa_{idx}.mp3")
    if not elevenlabs_tts(f"{word}... {word}", q_audio):
        q_audio = q_audio.replace(".mp3", ".m4a")
        make_silence(q_audio, 2.0)
    if not elevenlabs_tts(f"{word} means {meaning}.", a_audio):
        a_audio = a_audio.replace(".mp3", ".m4a")
        make_silence(a_audio, 2.0)

    q_clip = os.path.join(WORKDIR, f"clip_q_{idx}.mp4")
    ding_clip = os.path.join(WORKDIR, f"clip_ding_{idx}.mp4")
    a_clip = os.path.join(WORKDIR, f"clip_a_{idx}.mp4")
    q_dur = still_clip(q_frame, q_audio, q_clip)
    still_clip(a_frame, ding_path, ding_clip)
    a_dur = still_clip(a_frame, a_audio, a_clip)

    return [q_clip, ding_clip, a_clip], q_dur + get_duration(ding_path) + a_dur


def concat_clips(clip_paths, out_path):
    list_file = os.path.join(WORKDIR, "concat_list.txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for p in clip_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")
    run_ffmpeg(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
                "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", out_path])


# ════════════════════════════════════════════════════════════
# 5K 썸네일(검증된 JPEG 품질루프 — youtube_playlist_maker.py/curio_longform.py와 동일 방식)
# ════════════════════════════════════════════════════════════
def _save_thumbnail_capped(img, out_path, max_bytes=2 * 1024 * 1024):
    from PIL import Image

    jpg_path = os.path.splitext(out_path)[0] + ".jpg"
    rgb = img.convert("RGB")
    for quality in (95, 90, 85, 80, 75, 70, 60, 50, 40):
        rgb.save(jpg_path, "JPEG", quality=quality, optimize=True)
        if os.path.getsize(jpg_path) <= max_bytes:
            return jpg_path
    for target_w in (3840, 2560, 1920, 1280):
        smaller = rgb.resize((target_w, int(target_w * rgb.height / rgb.width)), Image.LANCZOS)
        smaller.save(jpg_path, "JPEG", quality=70, optimize=True)
        if os.path.getsize(jpg_path) <= max_bytes:
            return jpg_path
    raise RuntimeError(f"썸네일을 {max_bytes}바이트 이하로 못 줄임: {jpg_path}")


def build_thumbnail(word_count, categories, font_path):
    from PIL import Image, ImageDraw, ImageFont

    TW, TH = 1280, 720
    img = Image.new("RGB", (TW, TH), (18, 18, 24))
    draw = ImageDraw.Draw(img)

    def _font(size):
        return ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()

    def centered(text, font, y, fill):
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        draw.text(((TW - w) // 2 - bbox[0], y), text, font=font, fill=fill)

    centered("TOPIK 단어 퀴즈 모음", _font(150), 210, (255, 255, 255))
    centered(f"{word_count} Words · Beginner Level", _font(58), 420, (255, 210, 120))
    top_cats = ", ".join(categories[:4]) if categories else "Vocabulary"
    centered(top_cats, _font(38), 510, (180, 180, 190))

    img = img.resize(THUMBNAIL_UPSCALE, Image.LANCZOS)
    out_path = os.path.join(WORKDIR, "thumbnail.png")
    return _save_thumbnail_capped(img, out_path)


# ════════════════════════════════════════════════════════════
# 유튜브 업로드(비공개)
# ════════════════════════════════════════════════════════════
def upload_private(final_path, thumb_path, title, description, word_count):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    if not YOUTUBE_TOPIK_REFRESH_TOKEN:
        log("   ⚠️ YOUTUBE_OAUTH_REFRESH_TOKEN_TOPIK_BROAD 없음 — 업로드 생략, 로컬 파일만 생성됨")
        return None

    creds = Credentials(
        token=None, refresh_token=YOUTUBE_TOPIK_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_OAUTH_CLIENT_ID, client_secret=GOOGLE_OAUTH_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/youtube"],
    )
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": "27",
            "defaultLanguage": "en",
            "tags": ["topik", "korean vocabulary", "learn korean", "topik test",
                     "korean language", "beginner korean", "korean words quiz"],
        },
        "status": {"selfDeclaredMadeForKids": False, "privacyStatus": "private"},
    }
    media = MediaFileUpload(final_path, resumable=True, chunksize=5 * 1024 * 1024, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            log(f"   업로드 진행률: {int(status.progress() * 100)}%")
    video_id = response["id"]
    log(f"   ✅ 업로드 완료(비공개): https://youtu.be/{video_id}")

    youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumb_path)).execute()
    log("   ✅ 썸네일 설정 완료")
    return video_id


def generate_copy(word_count, categories):
    cat_str = ", ".join(categories[:6]) if categories else "everyday vocabulary"
    if openai_available():
        try:
            prompt = (f"Write a warm, friendly YouTube title (under 100 chars, English) and an "
                      f"around-1000-character English description (SEO keyword-dense but still warm "
                      f"and natural, not robotic) for a TOPIK Korean vocabulary quiz compilation video "
                      f"with {word_count} words covering categories: {cat_str}. Format each word as: "
                      f"Korean word shown, then its English meaning revealed after a short pause — good for "
                      f"listening/pronunciation practice for TOPIK level 1-2 learners. "
                      f"Respond as JSON only: {{\"title\": \"...\", \"description\": \"...\"}}")
            raw = openai_generate_text(prompt, temperature=0.8)
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.strip("`").split("\n", 1)[-1]
            data = json.loads(raw)
            if data.get("title") and data.get("description"):
                return data["title"][:100], data["description"]
        except Exception as e:
            log(f"   ⚠️ GPT 제목/설명 생성 실패(무시, 기본값 사용): {e}")

    title = f"TOPIK Vocabulary Quiz 📚 {word_count} Essential Korean Words for Beginners"
    description = f"""Test yourself on {word_count} essential Korean vocabulary words for TOPIK Level 1-2, covering {cat_str}.

Each word appears on screen first — try to guess the meaning before it's revealed, then listen to the pronunciation twice to practice.

📚 Perfect for:
– TOPIK Level 1-2 exam preparation
– Absolute beginners building their first vocabulary
– Daily listening and pronunciation practice
– Long-form background study sessions

🔔 Subscribe for more TOPIK vocabulary quizzes — new word sets uploaded regularly.

#topik #koreanvocabulary #learnkorean #topiktest #koreanlanguage #beginnerkorean #koreanwords #quiz"""
    return title, description


def main():
    font_path = resolve_font()
    if not font_path:
        log("⚠️ 한글 폰트를 못 찾음 — 기본 폰트로 진행(한글이 깨질 수 있음)")

    log("1/5 topik_basic_500 시트에서 단어 확보 중...")
    svc = get_sheets_service()
    pool = fetch_shuffled_unused_pool(svc)
    log(f"   후보 {len(pool)}개 확보")

    ding_path = os.path.join(WORKDIR, "ding.m4a")
    make_ding(ding_path)

    chosen = []
    total_dur = 0.0
    clip_paths = []
    consumed_row_indices = []
    categories_seen = []

    log("2/5 목표 재생시간(28분)까지 문항 생성 중...")
    for pos, (row_idx, word, meaning, category) in enumerate(pool):
        if total_dur >= TARGET_SEC or len(chosen) >= MAX_WORDS or total_dur >= HARD_CAP_SEC:
            break
        idx = len(chosen) + 1
        group, dur = build_word_clips(word, meaning, category, idx, len(pool), font_path, ding_path)
        clip_paths.extend(group)
        total_dur += dur
        chosen.append((word, meaning, category))
        consumed_row_indices.append(row_idx)
        if category not in categories_seen:
            categories_seen.append(category)
        if idx % 25 == 0:
            log(f"   [{idx}] 누적 {total_dur/60:.1f}분...")

    log(f"   ✅ 문항 {len(chosen)}개, 예상 {total_dur/60:.1f}분")

    log("3/5 전체 이어붙이는 중...")
    final_path = os.path.join(WORKDIR, "final.mp4")
    concat_clips(clip_paths, final_path)
    real_dur = get_duration(final_path)
    log(f"   ✅ 완성: {final_path} ({real_dur/60:.1f}분)")

    log("4/5 시트에 사용 표시 중...")
    mark_used(svc, consumed_row_indices)
    log(f"   ✅ {len(consumed_row_indices)}개 단어 사용 표시 완료")

    log("5/5 썸네일+제목/설명 생성 후 업로드 중...")
    thumb_path = build_thumbnail(len(chosen), categories_seen, font_path)
    title, description = generate_copy(len(chosen), categories_seen)
    video_id = upload_private(final_path, thumb_path, title, description, len(chosen))

    now = datetime.now(timezone(timedelta(hours=9)))
    result = {
        "created_at": now.isoformat(),
        "word_count": len(chosen),
        "duration_min": round(real_dur / 60, 1),
        "categories": categories_seen,
        "video_id": video_id,
        "url": f"https://youtu.be/{video_id}" if video_id else None,
    }
    with open(os.path.join(WORKDIR, "result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    log("완료")


if __name__ == "__main__":
    main()
