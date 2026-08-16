#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
curio_longform.py
─────────────────────────────────────────────────────────────
"Curio/Times" 지식채널(NASA_SPACE_TIMES/HISTORY_TODAY_TIMES/SCIENCE_FACTS_TIMES/
CLASSICAL_TIMES/MYTH_LEGEND_TIMES/INVENTION_TIMES) 공용 장편(8분 내외, 16:9)
영상 자동 생성기. health_longform.py를 베이스로 음식/증상 관련 로직만 제거하고
범용 교양 대본 구조로 바꿈 — Veo/이미지/TTS/자막/썸네일 파이프라인은 동일.

사용법:
    python scripts/curio_longform.py "주제" en [재사용할언어] [채널힌트]
    예: python scripts/curio_longform.py "The Voyager Golden Record" en

필요 환경변수: GEMINI_API_KEY, ELEVENLABS_API_KEY
필요 시스템 도구: ffmpeg, ffprobe
"""

import os
import sys
import json
import time
import base64
import random
import shutil
import subprocess

import requests

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class RULES:
    # 2026-08-15: 인트로 영상클립 개수는 시청유지율에 실제로 중요해서 4개로
    # 유지(사용자 확정) — 대신 Veo 하루 10회 한도(Tier 1)에 맞춰 스케줄 쪽을
    # 하루 2채널(Veo 8회, 여유 2회)로 분산해서 무료량을 최대 활용함
    # (curio-longform-daily.yml 참고).
    INTRO_VIDEO_CLIP_COUNT = 4
    INTRO_VIDEO_MODEL = "veo-3.1-lite-generate-preview"
    INTRO_VIDEO_DURATION_SECONDS = 8


def _load_dotenv():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(repo_root, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            if key and key not in os.environ:
                os.environ[key] = value.strip()


_load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_TEXT_MODEL = "gemini-2.5-flash"
GEMINI_IMAGE_MODELS = ["gemini-2.5-flash-image", "gemini-2.5-flash-image-preview"]

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID") or "21m00Tcm4TlvDq8ikWAM"
ELEVENLABS_MODEL = "eleven_multilingual_v2"

W, H = 1920, 1080
TARGET_IMAGE_COUNT = 27

LANG_NAMES = {"ko": "Korean", "en": "English", "ja": "Japanese"}


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


# ════════════════════════════════════════════════════════════
# 1. 대본 생성 (Gemini) — beats 단위 JSON
# ════════════════════════════════════════════════════════════
def _is_billing_exhausted(status_code, body_text):
    """결제/크레딧 고갈 에러는 몇 번을 재시도해도 절대 성공하지 않는다 —
    재시도할수록 시간과 API 요청수만 낭비된다(2026-08-16, 실제로 5회 재시도x
    최대 120초 백오프로 호출 하나당 5분 넘게 낭비되는 게 발견됨). 이런 에러는
    즉시 포기하고 위로 올려서, 호출부가 "이 실행은 크레딧부터 채워야 한다"는
    걸 바로 알 수 있게 한다."""
    if status_code != 429:
        return False
    return "prepayment credits are depleted" in body_text.lower() or "billing" in body_text.lower()


def gemini_generate_text(prompt, temperature=0.9, max_retries=5):
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{GEMINI_TEXT_MODEL}:generateContent?key={GEMINI_API_KEY}")
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature}}
    last_err = None
    for attempt in range(max_retries):
        r = requests.post(url, json=body, timeout=60)
        if r.status_code == 429 or r.status_code >= 500:
            last_err = f"{r.status_code}: {r.text[:200]}"
            if _is_billing_exhausted(r.status_code, r.text):
                raise RuntimeError(f"Gemini 결제/크레딧 고갈 — 재시도 없이 즉시 중단: {last_err}")
            wait = min(15 * (2 ** attempt), 120)
            log(f"   (텍스트 생성 재시도 대기 {wait}초 - {last_err})")
            time.sleep(wait)
            continue
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    raise RuntimeError(f"Gemini 텍스트 생성 최종 실패({max_retries}회 재시도 후): {last_err}")


def _strip_json_fence(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


CHANNEL_TOPICS = {
    "nasa": "space exploration / astronomy / NASA history",
    "history": "on-this-day historical events",
    "science": "surprising science facts ('did you know')",
    "classical": "classical composers and their lives",
    "myth": "world mythology and legends",
    "invention": "the history of inventions and who really invented them",
    # 2026-08-15: 원래 실제 아카이브 영상소스 큐레이션으로 기획됐던 4채널 —
    # 소싱 속도/저작권 리스크 때문에 이 대본+AI이미지 파이프라인으로 편입.
    "american_archive": "American history told through its public archives — "
                         "pivotal moments, presidents, and turning points",
    "silent_era": "the story behind classic silent films and the early days "
                  "of cinema — the stars, the stunts, the studios",
    "retro_reels": "nostalgic retrospectives on 20th-century pop culture — "
                   "fads, fashion, technology, and iconic moments people remember",
    "classic_reads": "the stories and ideas behind beloved classic novels — "
                     "what makes them endure, the authors who wrote them, the "
                     "world that shaped them",
}


def generate_script(topic, lang, channel_key="nasa"):
    lang_name = LANG_NAMES.get(lang, "English")
    n_intro = RULES.INTRO_VIDEO_CLIP_COUNT
    n_images = TARGET_IMAGE_COUNT
    domain = CHANNEL_TOPICS.get(channel_key, "general knowledge")

    prompt = f"""You are writing a narration script for an ~7-minute YouTube educational
video in {lang_name}, about: "{topic}". This channel's domain is: {domain}.

Tone: engaging, documentary-style, factual but conversational — like a good
history/science YouTuber, not a dry lecture. Hook viewers in the first 10 seconds.

The script MUST be broken into "beats" that will each become one video shot:
- The first {n_intro} beats have type "intro_video": short (1-2 sentence) narration
  each, paired with an English text-to-video prompt describing a short cinematic
  visual moment relevant to the topic (archival-style footage feel, or a dramatic
  establishing shot). These are the hook — fast-paced, must grab attention
  immediately, no text overlays needed in the prompt itself.
- The remaining beats have type "image": each pairs one narration chunk (1-3
  sentences, natural spoken pacing, keep individual images from staying on screen
  too long — shorter chunks are better for retention) with an English
  image-generation prompt (realistic/documentary photography style or historical
  illustration style as fits the topic, no text/watermark in the image).
- Total beats (intro_video + image) must be exactly {n_intro + n_images}.
- Structure: hook → context/background → the core interesting facts (the bulk of
  the video) → a surprising twist or lesser-known detail → a memorable closing line.
- Vary pacing: front beats short/punchy, later beats can breathe more.

Also return:
- "thumbnail_lines": {{"line1": "short hook line 1", "line2": "short punchy hook line 2",
  "line3": "short intriguing line", "line4": "short line, e.g. a number or date"}}
  in {lang_name}, YouTube-clickbait-but-honest style, ALL CAPS style ok for English.

Respond with JSON only, no explanation, no markdown fences:
{{
  "topic": "...",
  "thumbnail_lines": {{"line1": "...", "line2": "...", "line3": "...", "line4": "..."}},
  "beats": [
    {{"type": "intro_video", "narration": "...", "video_prompt": "..."}},
    ...,
    {{"type": "image", "narration": "...", "image_prompt": "..."}},
    ...
  ]
}}
"""
    text = gemini_generate_text(prompt, temperature=0.9)
    data = json.loads(_strip_json_fence(text))
    return data


def generate_youtube_metadata(topic, lang, channel_key, beats):
    """실제 대본 내용 기반으로 유튜브 제목/설명(1000자 내외)을 생성한다.
    (2026-08-15: 기존엔 topic 그대로 제목/짧은 고정 템플릿 설명이었는데,
    완전자동 파이프라인이라도 검색 노출을 위해 내용 기반 설명이 필요해서 추가)"""
    lang_name = LANG_NAMES.get(lang, "English")
    domain = CHANNEL_TOPICS.get(channel_key, "general knowledge")
    narration_full = "\n".join(b["narration"] for b in beats)

    prompt = f"""You are writing the YouTube title and description for an educational
video in {lang_name}. Channel domain: {domain}. Video topic: "{topic}".

Here is the actual narration script of the video, so you write about what's
really in it (don't invent facts not in the script):
---
{narration_full[:6000]}
---

Write:
1. "title": a natural, curiosity-driven YouTube title, under 90 characters. No
   clickbait lies, no ALL CAPS spam, no emoji-stuffing. Should read like a real
   channel wrote it, not a template.
2. "description": a YouTube description of roughly 900-1000 characters (not
   bytes) in {lang_name}. Structure it like a real educational channel would:
   - Open with 2-3 sentences expanding on the hook, written in plain natural
     prose (NOT a bullet list, NOT "In this video, we will explore..." /
     "Dive into..." / "Unlock the secrets of..." or any similar generic
     AI-sounding opener — just talk about the actual subject directly).
   - Then a short paragraph or a few bullet lines pulling out 3-5 specific,
     concrete facts/moments that are actually in the script above (not vague
     generalities).
   - Close with one natural sentence inviting people to subscribe for more
     (varied wording, not a robotic CTA).
   - End with 4-6 relevant hashtags on the last line.
   Do not pad with filler just to hit the character count — write naturally
   and let the real content determine the length; 850-1050 characters is fine.

Respond with JSON only, no explanation, no markdown fences:
{{"title": "...", "description": "..."}}
"""
    text = gemini_generate_text(prompt, temperature=0.8)
    data = json.loads(_strip_json_fence(text))
    return data


# ════════════════════════════════════════════════════════════
# 2. 이미지 생성 (Gemini 2.5 Flash Image)
# ════════════════════════════════════════════════════════════
def gemini_generate_image(prompt, out_path, max_retries=5):
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    last_err = None
    for attempt in range(max_retries):
        for model in GEMINI_IMAGE_MODELS:
            url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
                   f"{model}:generateContent?key={GEMINI_API_KEY}")
            try:
                r = requests.post(url, json=body, timeout=90)
                if r.status_code == 429 or r.status_code >= 500:
                    last_err = f"{r.status_code}: {r.text[:200]}"
                    # 결제/크레딧 고갈은 재시도로는 절대 안 풀린다 — 즉시 중단해서
                    # 5회x2모델 재시도 낭비(최대 몇 분)를 막는다(2026-08-16).
                    if _is_billing_exhausted(r.status_code, r.text):
                        raise RuntimeError(f"Gemini 결제/크레딧 고갈 — 재시도 없이 즉시 중단: {last_err}")
                    continue
                if r.status_code != 200:
                    last_err = f"{r.status_code}: {r.text[:200]}"
                    continue
                parts = r.json()["candidates"][0]["content"]["parts"]
                for part in parts:
                    inline = part.get("inlineData") or part.get("inline_data")
                    if inline and inline.get("data"):
                        with open(out_path, "wb") as f:
                            f.write(base64.b64decode(inline["data"]))
                        return True
                last_err = "응답에 이미지 데이터 없음"
            except RuntimeError:
                raise  # 결제 고갈 신호는 그대로 위로 전파 — 재시도 루프에 먹히면 안 됨
            except Exception as e:
                last_err = str(e)
        # 두 모델 다 실패 -> 레이트리밋일 가능성 높으니 지수 백오프 후 재시도
        wait = min(5 * (2 ** attempt), 60)
        log(f"      (이미지 생성 재시도 대기 {wait}초 - 마지막 오류: {last_err})")
        time.sleep(wait)
    log(f"      ⚠️ 최종 실패({max_retries}회 재시도 후): {last_err}")
    return False


# ════════════════════════════════════════════════════════════
# 3. 앞부분 AI 영상 클립 (Veo)
# ════════════════════════════════════════════════════════════
def generate_intro_video(prompt, out_path):
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY)
    operation = client.models.generate_videos(
        model=RULES.INTRO_VIDEO_MODEL,
        prompt=prompt,
        config=types.GenerateVideosConfig(
            number_of_videos=1,
            duration_seconds=RULES.INTRO_VIDEO_DURATION_SECONDS,
        ),
    )
    waited = 0
    while not operation.done:
        time.sleep(10)
        waited += 10
        if waited > 300:
            raise RuntimeError("Veo 영상 생성 타임아웃(5분)")
        operation = client.operations.get(operation)

    if not (operation.response and operation.response.generated_videos):
        raise RuntimeError(f"Veo 영상 생성 실패: {operation}")

    video = operation.response.generated_videos[0]
    client.files.download(file=video.video)
    video.video.save(out_path)


def normalize_intro_clip(raw_path, audio_path, out_path):
    """Veo 클립 자체 오디오는 버리고, 해당 구간 내레이션 오디오로 교체 +
    나머지 이미지 클립과 이어붙일 수 있게 코덱/해상도 통일."""
    audio_dur = get_duration(audio_path)
    video_dur = get_duration(raw_path)
    run_ffmpeg([
        "ffmpeg", "-y", "-i", raw_path, "-i", audio_path,
        "-map", "0:v:0", "-map", "1:a:0",
        "-vf", f"scale={W}:{H},format=yuv420p,fps=30",
        "-c:v", "libx264", "-c:a", "aac",
        "-t", str(max(audio_dur, video_dur)),
        "-shortest" if audio_dur < video_dur else "-y",
        "-map_metadata", "-1", "-fflags", "+bitexact",
        "-flags:v", "+bitexact", "-flags:a", "+bitexact",
        out_path,
    ])
    return max(audio_dur, video_dur)


# ════════════════════════════════════════════════════════════
# 자막(SRT) — 잘 나가는 건강 채널 벤치마킹 결과: 화려한 애니메이션 자막이 아니라
# 유튜브 기본 스타일(흰 글씨 + 반투명 검은 박스, 하단 중앙, 한 줄) 그대로 감.
# 그래서 burn-in 대신 표준 SRT를 만들어 유튜브 자막 업로드로 사용한다 —
# 유튜브가 그 기본 스타일로 알아서 렌더링해준다.
# ════════════════════════════════════════════════════════════
def format_srt_timestamp(seconds):
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def split_narration_for_captions(text, duration, max_chars=32):
    """긴 나레이션 한 덩어리를 문장 단위로 쪼개고, 길이 비례로 구간 시간을 나눈다.
    한 화면에 너무 많은 글자가 몰리지 않게(가독성) max_chars 기준으로 줄바꿈."""
    import re
    sentences = [s.strip() for s in re.split(r"(?<=[.!?。！？])\s+", text.strip()) if s.strip()]
    if not sentences:
        return [(text.strip(), duration)]
    total_len = sum(len(s) for s in sentences) or 1
    return [(s, duration * len(s) / total_len) for s in sentences]


def append_srt_entries(srt_entries, cursor, narration, duration):
    for sentence, seg_dur in split_narration_for_captions(narration, duration):
        srt_entries.append((cursor, cursor + seg_dur, sentence))
        cursor += seg_dur
    return cursor


def write_srt(srt_entries, out_path):
    with open(out_path, "w", encoding="utf-8") as f:
        for i, (start, end, text) in enumerate(srt_entries, 1):
            f.write(f"{i}\n{format_srt_timestamp(start)} --> {format_srt_timestamp(end)}\n{text}\n\n")


# ════════════════════════════════════════════════════════════
# 4. TTS
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
                f"anullsrc=r=44100:cl=stereo:d={duration}", "-c:a", "aac",
                "-map_metadata", "-1", "-fflags", "+bitexact", out_path])


# ════════════════════════════════════════════════════════════
# 5. Ken Burns 정지 이미지 클립
# ════════════════════════════════════════════════════════════
def ken_burns_clip(image_path, audio_path, out_path, zoom_in=True):
    dur = get_duration(audio_path)
    fps = 30
    frames = max(int(dur * fps), fps)
    # zoompan: 서서히 확대(또는 축소)하며 살짝 팬 이동
    if zoom_in:
        zexpr = "min(zoom+0.0007,1.3)"
        xexpr = "iw/2-(iw/zoom/2)"
        yexpr = "ih/2-(ih/zoom/2)"
    else:
        zexpr = "if(eq(on,0),1.3,max(zoom-0.0007,1.0))"
        xexpr = "iw/2-(iw/zoom/2)"
        yexpr = "ih/2-(ih/zoom/2)"
    vf = (
        f"scale=2400:-1,zoompan=z='{zexpr}':x='{xexpr}':y='{yexpr}':"
        f"d={frames}:s={W}x{H}:fps={fps},format=yuv420p"
    )
    run_ffmpeg([
        "ffmpeg", "-y", "-loop", "1", "-i", image_path, "-i", audio_path,
        "-t", str(dur), "-vf", vf,
        "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p",
        "-shortest",
        "-map_metadata", "-1", "-fflags", "+bitexact",
        "-flags:v", "+bitexact", "-flags:a", "+bitexact",
        out_path,
    ])
    return dur


def concat_clips(clip_paths, out_path, workdir):
    list_file = os.path.join(workdir, "concat_list.txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for p in clip_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")
    run_ffmpeg(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
                "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p",
                "-map_metadata", "-1", "-fflags", "+bitexact",
                "-flags:v", "+bitexact", "-flags:a", "+bitexact",
                out_path])


# ════════════════════════════════════════════════════════════
# 6. 썸네일 (음식 이미지 인서트 포함)
# ════════════════════════════════════════════════════════════
_FONT_URLS = {
    "ko": ("NanumGothicExtraBold.ttf",
           "https://raw.githubusercontent.com/google/fonts/main/ofl/nanumgothic/NanumGothic-ExtraBold.ttf"),
    "en": ("AntonRegular.ttf",
           "https://raw.githubusercontent.com/google/fonts/main/ofl/anton/Anton-Regular.ttf"),
    "ja": ("NotoSansJPBlack.ttf",
           "https://raw.githubusercontent.com/google/fonts/main/ofl/notosansjp/NotoSansJP%5Bwght%5D.ttf"),
}


def ensure_thumbnail_font(lang, workdir):
    fname, url = _FONT_URLS.get(lang, _FONT_URLS["ko"])
    cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".font_cache")
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, fname)
    if not os.path.exists(path):
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        with open(path, "wb") as f:
            f.write(r.content)
    return path


def build_thumbnail(topic, lang, thumbnail_lines, channel_key, workdir):
    """MBB 벤치마크 스타일(HALIDONMUSIC) 그대로: 주제 관련 임팩트있는 이미지 +
    화면 꽉 채우는 큼직한 스택형 텍스트. 음식 인서트 없음(건강채널 전용 요소)."""
    from PIL import Image, ImageDraw, ImageFont, ImageEnhance

    def crop_resize(img, w, h):
        ratio = img.width / img.height
        target_ratio = w / h
        if ratio > target_ratio:
            new_h = img.height
            new_w = int(new_h * target_ratio)
            left = (img.width - new_w) // 2
            img = img.crop((left, 0, left + new_w, new_h))
        else:
            new_w = img.width
            new_h = int(new_w / target_ratio)
            top = (img.height - new_h) // 2
            img = img.crop((0, top, new_w, top + new_h))
        return img.resize((w, h), Image.LANCZOS)

    def text_with_outline(draw, cx, y, text, font, fill, outline, ow=12):
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        x = cx - w // 2 - bbox[0]
        if outline is not None:
            for dx in range(-ow, ow + 1, 3):
                for dy in range(-ow, ow + 1, 3):
                    if dx * dx + dy * dy <= ow * ow:
                        draw.text((x + dx, y + dy), text, font=font, fill=outline)
        draw.text((x, y), text, font=font, fill=fill)

    def box_text(draw, cx, y, text, font, box_fill, text_fill, pad_x=28, pad_y=14):
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = cx - w // 2 - bbox[0]
        draw.rectangle([cx - w // 2 - pad_x, y - pad_y, cx + w // 2 + pad_x, y + h + pad_y], fill=box_fill)
        draw.text((x, y), text, font=font, fill=text_fill)

    TW, TH = 1280, 720
    font_path = ensure_thumbnail_font(lang, workdir)

    hero_photo = os.path.join(workdir, "thumb_hero.png")
    hero_prompts = {
        "nasa": f"A dramatic, cinematic photo related to space/astronomy: '{topic}', epic wide shot, no text, no watermark.",
        "history": f"A dramatic, cinematic archival-style photo related to: '{topic}', evocative historical mood, no text, no watermark.",
        "science": f"A striking, curiosity-provoking photo illustrating: '{topic}', vivid colors, no text, no watermark.",
        "classical": f"An elegant, dramatic photo evoking classical music/composer mood related to: '{topic}', no text, no watermark.",
        "myth": f"An epic, mythological fantasy-art style image related to: '{topic}', dramatic lighting, no text, no watermark.",
        "invention": f"A striking photo of an object/scene related to the invention: '{topic}', clean dramatic lighting, no text, no watermark.",
    }
    hero_prompt = hero_prompts.get(channel_key, hero_prompts["science"])
    if not gemini_generate_image(hero_prompt, hero_photo):
        raise RuntimeError("썸네일 히어로 이미지 생성 실패")

    img = crop_resize(Image.open(hero_photo).convert("RGB"), TW, TH)
    img = ImageEnhance.Contrast(img).enhance(1.15)
    canvas = img.copy()
    draw = ImageDraw.Draw(canvas)

    # 하단에 반투명 검정 박스 깔고 그 위에 큼직한 스택 텍스트 (MBB 벤치마크 스타일)
    overlay = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rectangle([0, TH - 260, TW, TH], fill=(0, 0, 0, 160))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(canvas)

    YELLOW, WHITE, BLACK, RED = (255, 255, 0), (255, 255, 255), (0, 0, 0), (255, 0, 0)

    text_with_outline(draw, TW // 2, TH - 250, thumbnail_lines.get("line1", ""), ImageFont.truetype(font_path, 60), WHITE, BLACK, 8)
    text_with_outline(draw, TW // 2, TH - 175, thumbnail_lines.get("line2", ""), ImageFont.truetype(font_path, 78), YELLOW, BLACK, 11)
    text_with_outline(draw, TW // 2, TH - 85, thumbnail_lines.get("line3", ""), ImageFont.truetype(font_path, 50), WHITE, BLACK, 7)
    if thumbnail_lines.get("line4"):
        box_text(draw, TW // 2, TH - 30, thumbnail_lines.get("line4", ""), ImageFont.truetype(font_path, 38), RED, WHITE)

    out_path = os.path.join(workdir, f"thumbnail_{lang}.png")
    canvas.save(out_path, quality=95)
    return out_path


# ════════════════════════════════════════════════════════════
# 7. 메인
# ════════════════════════════════════════════════════════════
def reuse_visuals_from(src_dir, workdir, n_intro, n_images):
    """언어간 이미지/인트로영상클립 재사용, 순서만 셔플. src_dir의 raw Veo 클립과
    이미지 파일을 복사해와서 이 workdir에 채워두면, 이후 생성 루프의
    '이미 있으면 재사용' 체크에 걸려서 Gemini/Veo 재호출 없이 재사용된다
    (TTS/썸네일만 새로 생성됨)."""
    if not os.path.isdir(src_dir):
        log(f"   ⚠️ 재사용 소스 언어 폴더 없음: {src_dir} — 전부 새로 생성함")
        return

    src_raws = [os.path.join(src_dir, f"intro_raw_{i}.mp4") for i in range(n_intro)]
    src_raws = [p for p in src_raws if os.path.exists(p)]
    order = list(range(len(src_raws)))
    random.shuffle(order)
    for new_idx, src_idx in enumerate(order):
        dst = os.path.join(workdir, f"intro_raw_{new_idx}.mp4")
        if not os.path.exists(dst):
            shutil.copyfile(src_raws[src_idx], dst)
    log(f"   {len(src_raws)}개 인트로 영상 클립 재사용 (순서 셔플)")

    src_imgs = [os.path.join(src_dir, f"img_{i}.png") for i in range(n_images)]
    src_imgs = [p for p in src_imgs if os.path.exists(p)]
    order = list(range(len(src_imgs)))
    random.shuffle(order)
    for new_idx, src_idx in enumerate(order):
        dst = os.path.join(workdir, f"img_{new_idx}.png")
        if not os.path.exists(dst):
            shutil.copyfile(src_imgs[src_idx], dst)
    log(f"   {len(src_imgs)}개 본문 이미지 재사용 (순서 셔플)")


def main():
    if not GEMINI_API_KEY:
        log("❌ GEMINI_API_KEY 없음")
        raise SystemExit(1)

    topic = sys.argv[1] if len(sys.argv) > 1 else ""
    lang = (sys.argv[2] if len(sys.argv) > 2 else "en").strip().lower()
    reuse_from = sys.argv[3] if len(sys.argv) > 3 else ""
    channel_key = sys.argv[4] if len(sys.argv) > 4 else "nasa"
    if not topic:
        log("❌ 사용법: python curio_longform.py \"주제\" [en|ko|ja] [재사용할언어] [채널키: nasa/history/science/classical/myth/invention]")
        raise SystemExit(1)

    workdir = os.path.join("curio_longform_output", channel_key, lang)
    os.makedirs(workdir, exist_ok=True)

    if reuse_from:
        reuse_dir = os.path.join("curio_longform_output", channel_key, reuse_from)
        log(f"0/5 {reuse_from} 버전에서 이미지/영상클립 재사용 준비 중...")
        reuse_visuals_from(reuse_dir, workdir, RULES.INTRO_VIDEO_CLIP_COUNT, TARGET_IMAGE_COUNT)

    log(f"1/5 대본 생성 중 (주제: {topic}, 언어: {lang}, 채널: {channel_key})...")
    data = generate_script(topic, lang, channel_key)
    beats = data["beats"]
    with open(os.path.join(workdir, "script.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log(f"   총 {len(beats)}개 비트")

    log("1.5/5 유튜브 제목/설명(1000자 내외) 생성 중...")
    yt_meta = generate_youtube_metadata(topic, lang, channel_key, beats)
    log(f"   제목: {yt_meta['title']}")
    log(f"   설명 길이: {len(yt_meta['description'])}자")

    srt_entries = []
    cursor = 0.0

    log("2/5 앞부분 AI 영상 클립 생성 중 (Veo)...")
    clip_paths = []
    intro_beats = [b for b in beats if b["type"] == "intro_video"]
    for idx, beat in enumerate(intro_beats):
        log(f"   [{idx+1}/{len(intro_beats)}] {beat['video_prompt'][:60]}...")
        raw = os.path.join(workdir, f"intro_raw_{idx}.mp4")
        audio = os.path.join(workdir, f"intro_audio_{idx}.mp3")
        clip = os.path.join(workdir, f"intro_clip_{idx}.mp4")
        if os.path.exists(clip):
            log("      (이미 생성됨, 재사용)")
            clip_paths.append(clip)
            cursor = append_srt_entries(srt_entries, cursor, beat["narration"], get_duration(clip))
            continue
        if not elevenlabs_tts(beat["narration"], audio):
            audio = audio.replace(".mp3", ".m4a")
            make_silence(audio, RULES.INTRO_VIDEO_DURATION_SECONDS)
        if not os.path.exists(raw):
            generate_intro_video(beat["video_prompt"], raw)
        clip_dur = normalize_intro_clip(raw, audio, clip)
        clip_paths.append(clip)
        cursor = append_srt_entries(srt_entries, cursor, beat["narration"], clip_dur)

    log("3/5 나머지 정지 이미지(Ken Burns) 생성 중...")
    image_beats = [b for b in beats if b["type"] == "image"]
    for idx, beat in enumerate(image_beats):
        log(f"   [{idx+1}/{len(image_beats)}] {beat['image_prompt'][:50]}...")
        img_path = os.path.join(workdir, f"img_{idx}.png")
        if os.path.exists(img_path):
            log("      (재사용된 이미지, 생성 스킵)")
        elif not gemini_generate_image(beat["image_prompt"], img_path):
            log(f"   ⚠️ 이미지 생성 실패, 스킵: beat {idx}")
            continue
        audio = os.path.join(workdir, f"img_audio_{idx}.mp3")
        if not elevenlabs_tts(beat["narration"], audio):
            audio = audio.replace(".mp3", ".m4a")
            make_silence(audio, 6.0)
        clip = os.path.join(workdir, f"img_clip_{idx}.mp4")
        clip_dur = ken_burns_clip(img_path, audio, clip, zoom_in=(idx % 2 == 0))
        clip_paths.append(clip)
        cursor = append_srt_entries(srt_entries, cursor, beat["narration"], clip_dur)
        time.sleep(2)  # 이미지 생성 API 레이트리밋 방지용 페이싱

    log("4/5 최종 영상 이어붙이는 중...")
    final_path = os.path.join(workdir, "final.mp4")
    concat_clips(clip_paths, final_path, workdir)
    dur = get_duration(final_path)
    log(f"   ✅ 영상 완성: {final_path} ({dur/60:.1f}분)")

    srt_path = os.path.join(workdir, f"subtitles_{lang}.srt")
    write_srt(srt_entries, srt_path)
    log(f"   ✅ 자막 완성: {srt_path} (유튜브 자막 업로드용 - 잘 나가는 건강채널 벤치마킹한 "
        f"기본 흰글씨/검은박스 스타일로 유튜브가 렌더링함)")

    log("5/5 썸네일 생성 중...")
    thumb_path = build_thumbnail(topic, lang, data.get("thumbnail_lines", {}), channel_key, workdir)
    log(f"   ✅ 썸네일 완성: {thumb_path}")

    meta = {
        "topic": topic,
        "lang": lang,
        "channel_key": channel_key,
        "duration_sec": dur,
        "video_path": final_path,
        "thumbnail_path": thumb_path,
        "subtitle_path": srt_path,
        "title": yt_meta["title"],
        "description": yt_meta["description"],
    }
    with open(os.path.join(workdir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    log(f"🎉 완료 — {workdir}/meta.json")


if __name__ == "__main__":
    main()
