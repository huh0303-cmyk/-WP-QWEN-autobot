#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
health_shorts.py
─────────────────────────────────────────────────────────────
"건강 상식" 유튜브 쇼츠(9:16, ~30~45초) 자동 생성기. 매번 주제(수면/수분섭취/
스트레칭/자세/스트레스 관리 등) 하나를 골라, 짧고 실용적인 건강 팁 3가지를
카드 형태로 보여주고 나레이션을 입힌다.

의학적 조언이 아닌 "일반 상식/생활 팁" 수준으로만 다루도록 프롬프트에
명시하고, 설명란에 디스클레이머를 자동으로 붙인다(특정 질병 진단/치료/
복용량 안내 등은 다루지 않음).

사용법:
    python scripts/health_shorts.py ["주제"]
    (또는 HEALTH_TOPIC 환경변수. 비우면 Gemini가 무작위로 고름)

필요 환경변수(Secrets):
    GEMINI_API_KEY              - 팁 생성 + 이미지 생성(나노바나나)
    ELEVENLABS_API_KEY          - TTS 나레이션 (없으면 무음으로 진행)
    ELEVENLABS_VOICE_ID         - (선택) 보이스 ID
    GOOGLE_OAUTH_CLIENT_ID/SECRET/REFRESH_TOKEN, GDRIVE_FOLDER_ID
                                - 업로드용(전부 없으면 로컬 저장만 하고 종료)

필요 시스템 도구: ffmpeg, ffprobe
"""

import os
import sys
import json
import base64
import random
import subprocess
import tempfile as _tempfile

import requests

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_TEXT_MODEL = "gemini-2.5-flash"
GEMINI_IMAGE_MODELS = ["gemini-2.5-flash-image", "gemini-2.5-flash-image-preview"]

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID") or "21m00Tcm4TlvDq8ikWAM"
ELEVENLABS_MODEL = "eleven_multilingual_v2"

GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
GOOGLE_OAUTH_REFRESH_TOKEN = os.environ.get("GOOGLE_OAUTH_REFRESH_TOKEN", "")
GDRIVE_FOLDER_ID = os.environ.get("GDRIVE_FOLDER_ID", "")

BRAND_TEXT = os.environ.get("HEALTH_BRAND_TEXT", "K-Health 365")
DISCLAIMER = ("이 영상은 일반적인 건강 정보 제공 목적이며 의학적 진단·치료 조언이 "
              "아닙니다. 개인 건강 상태에 따라 다를 수 있으니 증상이 있다면 "
              "전문의와 상담하세요.")

WORKDIR = "health_shorts_output"
W, H = 1080, 1920

FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/nanumgothic/NanumGothic-Bold.ttf"
FONT_PATH = os.path.join(_tempfile.gettempdir(), "_health_nanumgothic_bold.ttf")

BG_COLOR = (224, 242, 241, 255)      # 민트/헬스 톤
HEADER_COLOR = (129, 199, 195, 255)
CARD_COLOR = (255, 255, 255, 255)
BLACK = (25, 35, 35, 255)


def log(msg):
    print(msg, flush=True)


def run_ffmpeg(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg 실패: {' '.join(cmd)}\n{proc.stderr[-2000:]}")


def get_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def ensure_font():
    if not os.path.exists(FONT_PATH):
        r = requests.get(FONT_URL, timeout=30)
        r.raise_for_status()
        with open(FONT_PATH, "wb") as f:
            f.write(r.content)
    return FONT_PATH


# ════════════════════════════════════════════════════════════
# Gemini: 건강 팁 생성 + 이미지 생성
# ════════════════════════════════════════════════════════════
def gemini_generate_text(prompt, temperature=0.9):
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{GEMINI_TEXT_MODEL}:generateContent?key={GEMINI_API_KEY}")
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature}}
    r = requests.post(url, json=body, timeout=30)
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


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


def generate_health_tips(topic):
    """Gemini에게 생활 건강 팁 3개를 JSON으로 받아온다. 진단/치료/복용량 안내는
    다루지 않고 누구나 실천할 수 있는 일반 상식 수준으로 제한한다."""
    topic_instr = (f"주제는 '{topic}'로 고정." if topic.strip()
                   else "주제는 수면/수분섭취/스트레칭/바른자세/스트레스관리/식습관/눈건강 "
                        "중 하나를 무작위로 골라라.")
    prompt = f"""건강 유튜브 쇼츠에 쓸 생활 건강 팁 3가지를 만들어줘.
{topic_instr}

조건:
- 특정 질병의 진단/치료/약물 복용량 안내는 절대 금지. 누구나 실천 가능한
  생활 습관 수준의 일반 상식만.
- 각 팁은 한 문장, 12~20자 내외로 짧고 명확하게.
- 각 팁마다 1문장짜리 부연설명(왜 도움되는지)을 추가.
- image_prompt_en은 그 팁을 표현할 간단한 영어 이미지 설명(플랫 아이콘 스타일, 명사구).

JSON만 응답(설명 없이):
{{
  "topic": "주제명(한국어)",
  "tips": [
    {{"tip": "...", "detail": "...", "image_prompt_en": "..."}},
    ...
  ]
}}
"""
    text = gemini_generate_text(prompt, temperature=1.0).strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    data = json.loads(text.strip())
    return data


def generate_social_copy(topic, tips):
    tip_list = " / ".join(t["tip"] for t in tips)
    prompt = f"""너는 건강 정보 유튜브 채널의 SNS 담당자다. 아래 쇼츠 영상 게시글을 써줘.
주제: {topic}. 다루는 팁: {tip_list}.

조건:
- 실제 사람이 캐주얼하게 쓴 것처럼. "당신의 건강을 지켜드립니다!" 같은 상투적
  광고 문구, 이모지 남발, 과장된 감탄사 금지.
- 의학적 효능을 단정짓지 말고 "도움이 될 수 있어요" 정도의 톤 유지.
- youtube_title: 60자 이내
- youtube_description: 2~3문장
- short_caption: 틱톡/인스타/페이스북/쓰레드 공통 캡션 (2~3문장, 100자 내외)
- hashtags: 5~8개, # 없이 단어만

JSON만 응답:
{{"youtube_title": "...", "youtube_description": "...", "short_caption": "...", "hashtags": ["...", "..."]}}
"""
    text = gemini_generate_text(prompt, temperature=0.8).strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


# ════════════════════════════════════════════════════════════
# 카드 이미지 렌더링 (PIL)
# ════════════════════════════════════════════════════════════
def draw_tip_card(icon_path, topic, tip, idx, total, out_path):
    from PIL import Image, ImageDraw, ImageFont

    font_path = ensure_font()

    def F(size):
        return ImageFont.truetype(font_path, size)

    img = Image.new("RGBA", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img, "RGBA")

    draw.rounded_rectangle([90, 60, 990, 230], 40, fill=HEADER_COLOR)
    title = f"건강 상식 · {topic}"
    size = 56
    while size > 28:
        tf = F(size)
        tb = draw.textbbox((0, 0), title, font=tf)
        if tb[2] - tb[0] <= 820:
            break
        size -= 4
    draw.text(((W - (tb[2] - tb[0])) // 2, 145 - (tb[1] + tb[3]) // 2), title,
               font=tf, fill=BLACK)

    cx, cy, r = 940, 145, 42
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 255), outline=BLACK, width=3)
    nf = F(40)
    num = f"{idx+1}/{total}"
    nb = draw.textbbox((0, 0), num, font=nf)
    draw.text((cx - (nb[2] - nb[0]) // 2, cy - (nb[1] + nb[3]) // 2), num, font=nf, fill=BLACK)

    card_box = [110, 310, 970, 760]
    draw.rounded_rectangle(card_box, 40, fill=CARD_COLOR, outline=BLACK, width=5)
    icon = Image.open(icon_path).convert("RGBA")
    max_w, max_h = 650, 360
    scale = min(max_w / icon.width, max_h / icon.height)
    icon = icon.resize((int(icon.width * scale), int(icon.height * scale)), Image.LANCZOS)
    icon_x = (card_box[0] + card_box[2] - icon.width) // 2
    icon_y = (card_box[1] + card_box[3] - icon.height) // 2
    img.alpha_composite(icon, (icon_x, icon_y))

    tip_font = F(64)
    tb = draw.textbbox((0, 0), tip["tip"], font=tip_font)
    draw.text(((W - (tb[2] - tb[0])) // 2, 850 - (tb[1] + tb[3]) // 2), tip["tip"],
               font=tip_font, fill=BLACK)

    detail_font = F(38)
    detail = tip["detail"]
    max_chars = 22
    lines = []
    cur = ""
    for word in detail.replace(",", ", ").split(" "):
        if len(cur) + len(word) + 1 > max_chars:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    if cur:
        lines.append(cur)
    y = 970
    for line in lines[:3]:
        lb = draw.textbbox((0, 0), line, font=detail_font)
        draw.text(((W - (lb[2] - lb[0])) // 2, y), line, font=detail_font, fill=(70, 90, 90, 255))
        y += 55

    bf = F(34)
    bb = draw.textbbox((0, 0), BRAND_TEXT, font=bf)
    draw.text(((W - (bb[2] - bb[0])) // 2, 1840), BRAND_TEXT, font=bf, fill=BLACK)

    img.convert("RGB").save(out_path, "PNG")


# ════════════════════════════════════════════════════════════
# 오디오
# ════════════════════════════════════════════════════════════
def elevenlabs_tts(text, out_path):
    if not ELEVENLABS_API_KEY:
        return False
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {"xi-api-key": ELEVENLABS_API_KEY,
               "Content-Type": "application/json", "Accept": "audio/mpeg"}
    body = {"text": text, "model_id": ELEVENLABS_MODEL,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
    try:
        r = requests.post(url, headers=headers, json=body, timeout=90)
        r.raise_for_status()
        with open(out_path, "wb") as f:
            f.write(r.content)
        return True
    except Exception as e:
        log(f"   ⚠️ TTS 실패: {e}")
        return False


def make_silence(out_path, duration):
    run_ffmpeg(["ffmpeg", "-y", "-f", "lavfi", "-i",
                f"anullsrc=r=44100:cl=stereo:d={duration}", "-c:a", "aac", out_path])


def still_clip(image_path, audio_path, out_path):
    dur = get_duration(audio_path)
    run_ffmpeg(["ffmpeg", "-y", "-loop", "1", "-i", image_path, "-i", audio_path,
                "-t", str(dur), "-vf", f"scale={W}:{H},format=yuv420p",
                "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p",
                "-shortest", out_path])
    return dur


def build_tip_clip(topic, tip, idx, total, workdir):
    icon_path = os.path.join(workdir, f"icon_{idx}.png")
    ok = False
    if GEMINI_API_KEY:
        prompt = (f"A simple flat vector clip-art illustration of "
                  f"{tip['image_prompt_en']}, isolated on plain white background, "
                  f"clean minimalist wellness/health icon style, soft mint and teal "
                  f"accent colors, bold clean outlines, no text, no watermark, no shadow")
        for _ in range(3):
            if gemini_generate_image(prompt, icon_path):
                ok = True
                break
    if not ok:
        from PIL import Image
        Image.new("RGB", (600, 400), (200, 220, 218)).save(icon_path)
        log(f"   ⚠️ 팁{idx+1} 이미지 생성 실패 → 플레이스홀더 대체")

    frame = os.path.join(workdir, f"card_{idx}.png")
    draw_tip_card(icon_path, topic, tip, idx, total, frame)

    audio = os.path.join(workdir, f"audio_{idx}.mp3")
    narration = f"{tip['tip']}. {tip['detail']}"
    if not elevenlabs_tts(narration, audio):
        audio = audio.replace(".mp3", ".m4a")
        make_silence(audio, 3.5)

    clip = os.path.join(workdir, f"clip_{idx}.mp4")
    still_clip(frame, audio, clip)
    return clip


def concat_clips(clip_paths, out_path, workdir):
    list_file = os.path.join(workdir, "concat_list.txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for p in clip_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")
    run_ffmpeg(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
                "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", out_path])


# ════════════════════════════════════════════════════════════
# 구글드라이브 업로드
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


def upload_to_drive(service, file_path, folder_id, name, make_public=False):
    import time as _time
    from googleapiclient.http import MediaFileUpload

    metadata = {"name": name, "parents": [folder_id]}
    media = MediaFileUpload(file_path, resumable=True, chunksize=5 * 1024 * 1024)
    request = service.files().create(body=metadata, media_body=media, fields="id,webViewLink")
    response = None
    retries = 0
    while response is None:
        try:
            _, response = request.next_chunk(num_retries=5)
        except Exception as e:
            retries += 1
            if retries > 8:
                raise
            wait = min(2 ** retries, 60)
            log(f"   ⚠️ 업로드 재시도({retries}/8): {e}")
            _time.sleep(wait)

    file_id = response.get("id")
    if make_public and file_id:
        try:
            service.permissions().create(fileId=file_id, body={"type": "anyone", "role": "reader"}).execute()
        except Exception as e:
            log(f"   ⚠️ 공개 권한 설정 실패(무시): {e}")

    return {
        "id": file_id,
        "webViewLink": response.get("webViewLink"),
        "directLink": f"https://drive.google.com/uc?export=download&id={file_id}" if file_id else None,
    }


# ════════════════════════════════════════════════════════════
# 메인
# ════════════════════════════════════════════════════════════
def main():
    if not GEMINI_API_KEY:
        log("❌ GEMINI_API_KEY 없음")
        raise SystemExit(1)

    topic_input = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("HEALTH_TOPIC", "")

    os.makedirs(WORKDIR, exist_ok=True)

    log(f"1/3 건강 팁 생성 중 (주제: {topic_input or '무작위'})...")
    data = generate_health_tips(topic_input)
    topic = data["topic"]
    tips = data["tips"]
    for t in tips:
        log(f"   - {t['tip']} ({t['detail']})")

    log("2/3 팁별 이미지+나레이션+카드 생성 중...")
    all_clips = []
    for idx, tip in enumerate(tips):
        log(f"   [{idx+1}/{len(tips)}] {tip['tip']}")
        all_clips.append(build_tip_clip(topic, tip, idx, len(tips), WORKDIR))

    log("3/3 최종 영상 이어붙이는 중...")
    final_path = os.path.join(WORKDIR, "final.mp4")
    concat_clips(all_clips, final_path, WORKDIR)
    dur = get_duration(final_path)
    log(f"   ✅ 완성: {final_path} ({dur:.1f}초)")

    log("소셜 게시용 제목/캡션 생성 중...")
    try:
        copy = generate_social_copy(topic, tips)
    except Exception as e:
        log(f"   ⚠️ 소셜 카피 생성 실패(무시): {e}")
        copy = {"youtube_title": f"건강 상식 - {topic}", "youtube_description": "",
                "short_caption": "", "hashtags": ["건강", "건강상식", "헬스팁"]}

    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone(timedelta(hours=9)))

    public_video_url = None
    if all([GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET,
            GOOGLE_OAUTH_REFRESH_TOKEN, GDRIVE_FOLDER_ID]):
        log("업로드 중...")
        service = get_drive_service()
        name = f"health_shorts_{now.strftime('%Y%m%d_%H%M%S')}.mp4"
        drive_info = upload_to_drive(service, final_path, GDRIVE_FOLDER_ID, name, make_public=True)
        public_video_url = drive_info.get("directLink")
        log(f"🎉 드라이브 업로드 완료 — {drive_info.get('webViewLink')}")
    else:
        log("드라이브 업로드 설정 없음 — 로컬 파일만 생성됨")

    description = (copy.get("youtube_description", "") + "\n\n" + DISCLAIMER).strip()

    meta = {
        "topic": topic,
        "created_at": now.isoformat(),
        "video_path": final_path,
        "duration_sec": dur,
        "public_video_url": public_video_url,
        "youtube_title": copy.get("youtube_title", f"건강 상식 - {topic}"),
        "youtube_description": description,
        "short_caption": copy.get("short_caption", ""),
        "hashtags": copy.get("hashtags", []),
    }
    meta_path = os.path.join(WORKDIR, "meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    log(f"🎉 완료 — 메타데이터: {meta_path}")


if __name__ == "__main__":
    main()
