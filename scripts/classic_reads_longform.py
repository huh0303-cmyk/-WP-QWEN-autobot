#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
classic_reads_longform.py
─────────────────────────────────────────────────────────────
CLASSIC_READS_JOURNAL 채널 전용 파이프라인. "고전 100선"(동서양,
scripts/data/classic_reads_100.json)을 한 권씩 순서대로 ~10분 영상으로
압축한다. 나머지 9개 Curio/Times 채널(curio_longform.py)과 다른 점:

- Veo 없음 — 전부 정지이미지 Ken Burns 컷 (인트로 영상클립 생략)
- 이미지 컷은 나레이션 문장 길이와 무관하게 고정 ~4초 간격으로 전환
  (책마다 18장 내외의 고유 이미지를 생성해서 순환 재생, 반복될 때마다
  줌/팬 방향을 바꿔 단조로움을 줄임)
- 자막은 사이드카 SRT가 아니라 영상에 직접 큼직하게 번인
  (health_longform 채널 벤치마킹 규칙과 동일한 원칙 적용)
- 목소리는 ElevenLabs Adam(차분하고 깊은 남성 내레이터 — 문학 다큐 톤)
- 썸네일은 책 제목을 가장 크게, 저자/발간연도를 작게 표시

"하버드대학 추천"은 채널 브랜딩용 후킹 문구이지 실제 하버드의 공식 100선이
존재하는 게 아니므로, 나레이션 안에서 이를 사실인 것처럼 구체적으로
서술하지 않는다(generate_script 프롬프트에 명시).

사용법:
    python scripts/classic_reads_longform.py
"""
import os
import sys
import re
import json
import time
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from curio_longform import (  # noqa: E402
    gemini_generate_text, gemini_generate_image, make_silence, get_duration,
    run_ffmpeg, _strip_json_fence, format_srt_timestamp, log,
    GEMINI_API_KEY, ELEVENLABS_API_KEY, ELEVENLABS_MODEL,
)

import requests  # noqa: E402

CHANNEL_KEY = "classic_reads"
W, H = 1920, 1080
IMAGE_SLIDE_SECONDS = 4.0
N_UNIQUE_IMAGES = 18
TARGET_WORD_COUNT = 1400  # ~9-10분 분량(영어 낭독 기준 ~150wpm)

# 2026-08-23: 예전엔 Adam 목소리 하나로 고정이라, classic_reads/nasa/아카이브
# 영상 채널(american_archive/history/invention/silent_era/retro_reels) 전부가
# 항상 똑같은 목소리로 나갔음(사용자 지시로 다양성을 위해 3개 중 매 영상마다
# 랜덤 하나로 변경). CLASSIC_READS_ELEVENLABS_VOICE_ID를 명시적으로 지정하면
# 그 목소리로 강제 고정(기존 동작 유지), 안 지정하면 아래 3개 중 랜덤.
NARRATOR_VOICE_IDS = [
    "pNInz6obpgDQGcFmaJgB",  # Adam — 깊고 차분한 남성
    "ErXwobaYiN019PkySvjV",  # Antoni — 밸런스 잡힌 남성
    "EXAVITQu4vr4xnSDxMaL",  # Bella — 부드러운 여성
]
VOICE_ID = os.environ.get("CLASSIC_READS_ELEVENLABS_VOICE_ID") or random.choice(NARRATOR_VOICE_IDS)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
BOOKS_PATH = os.path.join(DATA_DIR, "classic_reads_100.json")
STATE_PATH = os.path.join(DATA_DIR, "classic_reads_state.json")

CAPTION_STYLE = (
    "FontName=DejaVu Sans,Fontsize=20,Bold=1,"
    "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
    "BorderStyle=3,Outline=3,Shadow=0,MarginV=80,Alignment=2"
)


# ════════════════════════════════════════════════════════════
# 0. 책 선정 (100권 순환, 반복 없이 anti-repeat)
# ════════════════════════════════════════════════════════════
def load_books():
    with open(BOOKS_PATH, encoding="utf-8") as f:
        return json.load(f)


def pick_next_book():
    books = load_books()
    state = {"last_rank": 0}
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, encoding="utf-8") as f:
            state = json.load(f)
    next_rank = (state.get("last_rank", 0) % len(books)) + 1
    book = next(b for b in books if b["rank"] == next_rank)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump({"last_rank": next_rank}, f)
    return book


# ════════════════════════════════════════════════════════════
# 1. 대본 + 이미지 프롬프트 (Gemini)
# ════════════════════════════════════════════════════════════
def generate_script(book):
    prompt = f"""You are writing a narration script for a ~10-minute YouTube video
that compresses one classic book into an engaging audio-visual summary, for a
channel called "Classic Reads Journal" that covers 100 great books of world
literature (East and West).

Book: "{book['title']}" by {book['author']} ({book['year']}, {book['region']}).

Write:
1. "narration": a single continuous narration script, approximately
   {TARGET_WORD_COUNT} words, in English, spoken-documentary tone (like a
   thoughtful literary YouTuber, not a dry Wikipedia summary). Cover: what the
   book is about (plot/core ideas, without needing to spoil every twist),
   who the author was and why they wrote it, the world/historical context
   that shaped it, and why it still resonates with readers today. Hook the
   listener in the first two sentences. Do NOT claim Harvard University
   officially endorses or ranks this book — just talk about the book itself.
   Do not quote more than a short phrase (under 15 words) directly from the
   original text at any point — describe and summarize in your own words
   instead of reproducing passages.
2. "image_prompts": exactly {N_UNIQUE_IMAGES} English image-generation prompts,
   each describing one distinct visual scene, setting, symbol, or mood evoked
   by the book (NOT a literal reproduction of any real book cover design —
   original artistic interpretations only). Vary composition: some wide
   establishing scenes, some intimate/symbolic close-ups. Painterly or
   cinematic-illustration style fitting the book's era and culture, warm and
   inviting book-club mood, no text, no watermark, no readable letters in
   the image.
3. "title_hint": a short natural phrase capturing the book's essence, used to
   help write the YouTube title later (not the final title itself).

Respond with JSON only, no explanation, no markdown fences:
{{"narration": "...", "image_prompts": ["...", ...], "title_hint": "..."}}
"""
    text = gemini_generate_text(prompt, temperature=0.85)
    data = json.loads(_strip_json_fence(text))
    if len(data.get("image_prompts", [])) != N_UNIQUE_IMAGES:
        data["image_prompts"] = (data.get("image_prompts", []) + [""] * N_UNIQUE_IMAGES)[:N_UNIQUE_IMAGES]
    return data


def generate_youtube_metadata(book, narration):
    prompt = f"""You are writing the YouTube title and description for a video that
summarizes the classic book "{book['title']}" by {book['author']} ({book['year']})
on a literary channel called "Classic Reads Journal".

Here is the actual narration script, so you write about what's really in it:
---
{narration[:6000]}
---

Write:
1. "title": a warm, friendly, curiosity-driven YouTube title, under 100
   characters, that naturally includes the book title — like a real person
   who loves this book sharing it with you, not a clickbait template. No ALL
   CAPS spam, no emoji-stuffing, no lies.
2. "description": around 1000 characters (not bytes), always in English.
   - Open with 2-3 sentences on why this book matters, plain natural prose
     (no "In this video, we will explore..." or similar generic AI opener).
   - A short paragraph pulling out 3-5 concrete, specific points actually in
     the script (not vague generalities).
   - One natural sentence inviting people to subscribe for more classic books.
   - End with 4-6 relevant hashtags on the last line (include the book title
     and author as hashtags where natural).
   Do not quote long passages from the original book text.

Respond with JSON only, no explanation, no markdown fences:
{{"title": "...", "description": "..."}}
"""
    text = gemini_generate_text(prompt, temperature=0.8)
    return json.loads(_strip_json_fence(text))


# ════════════════════════════════════════════════════════════
# 2. TTS (Adam 보이스) + 문장 단위 캡션
# ════════════════════════════════════════════════════════════
def elevenlabs_tts_voice(text, out_path, voice_id, max_retries=5):
    """2026-08-17: 문장 단위로 수십~수백 번 호출되다 보니(archive_footage_longform.py
    등 7분 내레이션이면 문장 70개 이상) ElevenLabs 429(레이트리밋)를 실제로 맞는
    걸 확인함 — 이전엔 429가 나면 그냥 그 문장만 무음으로 대체하고 넘어갔는데,
    재시도 없이 그러면 나레이션 전체가 뭉텅뭉텅 무음으로 나갈 수 있다(healing
    채널 검은화면 사고와 같은 유형 — 다른 이유로 조용히 콘텐츠가 빠지는 것).
    429만 지수백오프로 재시도하고, 그 외 에러는 기존처럼 즉시 무음 폴백."""
    if not ELEVENLABS_API_KEY:
        return False
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"xi-api-key": ELEVENLABS_API_KEY,
               "Content-Type": "application/json", "Accept": "audio/mpeg"}
    body = {"text": text, "model_id": ELEVENLABS_MODEL,
            "voice_settings": {"stability": 0.55, "similarity_boost": 0.75}}
    for attempt in range(max_retries):
        try:
            r = requests.post(url, headers=headers, json=body, timeout=90)
            if r.status_code == 429:
                wait = 5 * (attempt + 1)
                log(f"   ⚠️ TTS 429(레이트리밋) — {wait}초 대기 후 재시도({attempt + 1}/{max_retries})")
                time.sleep(wait)
                continue
            r.raise_for_status()
            with open(out_path, "wb") as f:
                f.write(r.content)
            return True
        except Exception as e:
            if attempt == max_retries - 1:
                log(f"   ⚠️ TTS 실패: {e}")
                return False
            time.sleep(3)
    log("   ⚠️ TTS 실패: 429 재시도 소진")
    return False


def _normalize_audio(in_path, out_path):
    run_ffmpeg(["ffmpeg", "-y", "-i", in_path, "-c:a", "aac", "-ar", "44100", "-ac", "2",
                "-map_metadata", "-1", "-fflags", "+bitexact", out_path])


def build_narration_track(narration_text, workdir):
    """나레이션을 문장 단위로 쪼개 각각 TTS -> 정규화된 오디오로 저장하고,
    실제 오디오 길이 기준으로 SRT 캡션 타이밍을 만든 뒤, 전부 이어붙여
    하나의 연속 오디오 트랙으로 합친다.

    2026-08-18 사고: Invention 영상(zZ-SkcHU3bQ 아님, _scG62MN0PE)이 문장
    전부(70개+) ElevenLabs 400을 맞아서 8.1분 전체가 무음으로 업로드됨 —
    문장당 5회 재시도는 이미 하고 있었지만(429 대응으로 8/17에 추가), 그날
    ElevenLabs 쪽이 지속적으로 막혀있어서 재시도로도 못 뚫었음. 재시도만으론
    부족하다는 게 드러나서, 무음으로 대체된 비율이 너무 높으면(30% 이상)
    "일부만 조용히 무음 처리"가 아니라 파이프라인 자체를 중단시켜 무음
    영상이 업로드되는 사고를 원천 차단한다."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", narration_text.strip()) if s.strip()]
    norm_paths = []
    srt_entries = []
    cursor = 0.0
    silent_count = 0
    for i, sent in enumerate(sentences):
        raw = os.path.join(workdir, f"narr_raw_{i}.mp3")
        norm = os.path.join(workdir, f"narr_{i}.m4a")
        if not os.path.exists(norm):
            ok = elevenlabs_tts_voice(sent, raw, VOICE_ID)
            if ok:
                _normalize_audio(raw, norm)
            else:
                silent_count += 1
                make_silence(norm, max(2.0, len(sent) / 15))
        dur = get_duration(norm)
        norm_paths.append(norm)
        srt_entries.append((cursor, cursor + dur, sent))
        cursor += dur
        # 2026-08-17: 5문장마다 몰아서 1초씩 쉬는 버스트 패턴이 오히려 429를
        # 유발하는 걸 확인 — 매 호출마다 고르게 짧은 간격을 두는 게 더 안전.
        time.sleep(0.6)

    silent_ratio = silent_count / len(sentences) if sentences else 0
    if silent_ratio > 0.3:
        raise RuntimeError(
            f"TTS 실패율이 너무 높음({silent_count}/{len(sentences)}, {silent_ratio:.0%}) — "
            f"ElevenLabs 쪽 문제로 보이며, 이대로 진행하면 대부분 무음인 영상이 나간다. "
            f"업로드 직전까지 안 가고 여기서 중단."
        )

    list_file = os.path.join(workdir, "audio_concat_list.txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for p in norm_paths:
            f.write(f"file '{os.path.basename(p)}'\n")
    audio_out = os.path.join(workdir, "narration_full.m4a")
    cwd = os.getcwd()
    os.chdir(workdir)
    try:
        run_ffmpeg(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i",
                    "audio_concat_list.txt", "-c", "copy", "narration_full.m4a"])
    finally:
        os.chdir(cwd)
    return audio_out, srt_entries, cursor


def write_srt(srt_entries, out_path):
    with open(out_path, "w", encoding="utf-8") as f:
        for i, (start, end, text) in enumerate(srt_entries, 1):
            f.write(f"{i}\n{format_srt_timestamp(start)} --> {format_srt_timestamp(end)}\n{text}\n\n")


# ════════════════════════════════════════════════════════════
# 3. 이미지 생성 + 고정 4초 Ken Burns 컷 순환
# ════════════════════════════════════════════════════════════
N_MUSEUM_IMAGES = 12  # N_UNIQUE_IMAGES(18) 중 실제 박물관 소장품으로 채우는 목표치
# 2026-08-16: 시카고미술관(키불필요, 13만+점)+Met(키불필요)+스미소니언(CC0) 3소스
# 통합으로 성공률이 크게 올라가서 6→12로 상향(사용자 지시: "콘텐츠 많고 받기 쉬운 것").


def generate_book_images(book, image_prompts, workdir):
    """가능하면 실제 미술관 소장품 사진(퍼블릭도메인/CC0, 시카고미술관+Met+스미소니언
    통합 검색)을 우선 섞어 넣고, 부족한 만큼만 Gemini AI 이미지로 채운다 — AI 흔적을
    줄이고 진짜 유물/미술품을 보여주는 게 문학/역사 채널에 더 어울린다는 사용자
    지시(2026-08-16)."""
    from museum_sources import fetch_museum_images

    paths = []
    query = f"{book['author']} {book['region']} art"
    museum_paths = fetch_museum_images(query, workdir, N_MUSEUM_IMAGES, prefix="museum")
    if museum_paths:
        log(f"   실제 미술관 소장품 이미지 {len(museum_paths)}장 확보 (검색어: {query!r})")
    paths.extend(museum_paths)

    remaining_prompts = image_prompts[:max(0, N_UNIQUE_IMAGES - len(paths))]
    for idx, prompt in enumerate(remaining_prompts):
        img_path = os.path.join(workdir, f"img_{idx}.png")
        if os.path.exists(img_path):
            paths.append(img_path)
            continue
        if gemini_generate_image(prompt, img_path):
            paths.append(img_path)
        time.sleep(2)
    if not paths:
        raise RuntimeError("이미지가 하나도 생성되지 않음")
    return paths


_KB_VARIANTS = [
    ("min(zoom+0.0015,1.25)", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),   # 중앙 줌인
    ("if(eq(on,0),1.25,max(zoom-0.0015,1.0))", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),  # 중앙 줌아웃
    ("min(zoom+0.0015,1.22)", "0", "0"),                                  # 좌상단에서 줌인
    ("min(zoom+0.0015,1.22)", "iw-iw/zoom", "ih-ih/zoom"),                # 우하단에서 줌인
]


def ken_burns_fixed(image_path, out_path, duration, variant_idx):
    fps = 30
    frames = max(int(duration * fps), fps)
    zexpr, xexpr, yexpr = _KB_VARIANTS[variant_idx % len(_KB_VARIANTS)]
    vf = (f"scale=2400:-1,zoompan=z='{zexpr}':x='{xexpr}':y='{yexpr}':"
          f"d={frames}:s={W}x{H}:fps={fps},format=yuv420p")
    run_ffmpeg([
        "ffmpeg", "-y", "-loop", "1", "-i", image_path, "-t", str(duration),
        "-vf", vf, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an",
        "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:v", "+bitexact",
        out_path,
    ])


def build_visual_track(image_paths, total_duration, workdir):
    import math
    n_clips = max(1, math.ceil(total_duration / IMAGE_SLIDE_SECONDS))
    clip_paths = []
    for i in range(n_clips):
        remaining = total_duration - i * IMAGE_SLIDE_SECONDS
        dur = min(IMAGE_SLIDE_SECONDS, remaining)
        if dur <= 0:
            break
        img = image_paths[i % len(image_paths)]
        clip = os.path.join(workdir, f"visual_clip_{i}.mp4")
        if not os.path.exists(clip):
            ken_burns_fixed(img, clip, dur, variant_idx=i)
        clip_paths.append(clip)

    list_file = os.path.join(workdir, "visual_concat_list.txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for p in clip_paths:
            f.write(f"file '{os.path.basename(p)}'\n")
    out_path = os.path.join(workdir, "visual_full.mp4")
    cwd = os.getcwd()
    os.chdir(workdir)
    try:
        run_ffmpeg(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i",
                    "visual_concat_list.txt", "-c", "copy", "visual_full.mp4"])
    finally:
        os.chdir(cwd)
    return out_path


def mux_final(visual_path, audio_path, srt_path, out_path, workdir):
    """나레이션 오디오를 영상에 입힌다.

    2026-08-18 사용자 지적("유튜브 자동자막 있는데 굳이 넣을 필요있나?
    그리고 이러니까 화면을 보기가 힘들어") — 예전엔 여기서 SRT를 화면에
    번인(subtitles 필터 + 불투명 박스, BorderStyle=3)해서, 유튜브 자체
    자동생성 자막(끄고 켤 수 있음)과 중복인 데다 항상 화면 하단을 가려서
    끌 수도 없었음. 번인 완전히 제거 — srt_path는 호출부 캡션 타이밍
    계산용으로만 남겨두고(파일 자체는 만들어지되 화면엔 안 들어감),
    영상은 순수 비디오+오디오만 합성한다."""
    cwd = os.getcwd()
    os.chdir(workdir)
    try:
        run_ffmpeg([
            "ffmpeg", "-y", "-i", os.path.basename(visual_path), "-i", os.path.basename(audio_path),
            "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-c:a", "aac", "-shortest",
            "-map_metadata", "-1", "-fflags", "+bitexact",
            "-flags:v", "+bitexact", "-flags:a", "+bitexact",
            os.path.basename(out_path),
        ])
    finally:
        os.chdir(cwd)
    return out_path


# ════════════════════════════════════════════════════════════
# 4. 썸네일 — 책 제목 크게 + 저자/발간연도
# ════════════════════════════════════════════════════════════
def ensure_font():
    from curio_longform import ensure_thumbnail_font
    return ensure_thumbnail_font("en", DATA_DIR)


def _save_thumbnail_capped(img, out_path, max_bytes=2 * 1024 * 1024):
    """유튜브 썸네일 API 2MB 제한 대응(youtube_playlist_maker.py와 동일 원칙 —
    5K 트루컬러 PNG는 쉽게 2MB를 넘어서 품질을 낮춰가며 실제로 검증한다).
    반환값은 실제 저장된 경로(.jpg로 바뀔 수 있음) — 호출부는 이 값을 써야 한다."""
    from PIL import Image
    rgb = img.convert("RGB")
    jpg_path = os.path.splitext(out_path)[0] + ".jpg"
    for quality in (95, 90, 85, 80, 75, 70, 60, 50, 40):
        rgb.save(jpg_path, "JPEG", quality=quality, optimize=True)
        if os.path.getsize(jpg_path) <= max_bytes:
            if jpg_path != out_path and os.path.exists(out_path):
                os.remove(out_path)
            return jpg_path
    for target_w in (3840, 2560, 1920, 1280):
        smaller = rgb.resize((target_w, int(target_w * rgb.height / rgb.width)), Image.LANCZOS)
        smaller.save(jpg_path, "JPEG", quality=70, optimize=True)
        if os.path.getsize(jpg_path) <= max_bytes:
            if jpg_path != out_path and os.path.exists(out_path):
                os.remove(out_path)
            return jpg_path
    raise RuntimeError(f"썸네일을 {max_bytes}바이트 이하로 못 줄임: {jpg_path}")


def build_thumbnail(book, hero_image_path, workdir):
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

    def wrap_title(draw, text, font, max_width):
        words = text.split()
        lines, cur = [], ""
        for w in words:
            trial = (cur + " " + w).strip()
            if draw.textbbox((0, 0), trial, font=font)[2] <= max_width:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines[:3]

    def text_with_outline(draw, cx, y, text, font, fill, outline, ow=10):
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        x = cx - w // 2 - bbox[0]
        for dx in range(-ow, ow + 1, 3):
            for dy in range(-ow, ow + 1, 3):
                if dx * dx + dy * dy <= ow * ow:
                    draw.text((x + dx, y + dy), text, font=font, fill=outline)
        draw.text((x, y), text, font=font, fill=fill)

    TW, TH = 1280, 720
    UPSCALE = (5120, 2880)
    font_path = ensure_font()

    img = crop_resize(Image.open(hero_image_path).convert("RGB"), TW, TH)
    img = ImageEnhance.Contrast(img).enhance(1.1)
    img = ImageEnhance.Brightness(img).enhance(0.85)  # 텍스트 대비를 위해 살짝 어둡게
    canvas = img.copy()

    overlay = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rectangle([0, 0, TW, 130], fill=(0, 0, 0, 150))
    ImageDraw.Draw(overlay).rectangle([0, TH - 150, TW, TH], fill=(0, 0, 0, 170))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(canvas)

    WHITE, YELLOW, BLACK = (255, 255, 255), (255, 214, 0), (0, 0, 0)

    # 상단: 시리즈 브랜드 라벨
    brand_font = ImageFont.truetype(font_path, 34)
    text_with_outline(draw, TW // 2, 20, "CLASSIC READS JOURNAL", brand_font, WHITE, BLACK, 4)

    # 중앙: 책 제목 (가장 크게, 최대 3줄)
    title_font_size = 96 if len(book["title"]) <= 20 else (76 if len(book["title"]) <= 32 else 60)
    title_font = ImageFont.truetype(font_path, title_font_size)
    lines = wrap_title(draw, book["title"].upper(), title_font, TW - 120)
    total_h = len(lines) * (title_font_size + 14)
    start_y = max(140, (TH - 150 - total_h) // 2)
    for i, line in enumerate(lines):
        text_with_outline(draw, TW // 2, start_y + i * (title_font_size + 14), line, title_font, YELLOW, BLACK, 12)

    # 하단: 저자 · 발간연도
    meta_font = ImageFont.truetype(font_path, 40)
    meta_text = f"{book['author']}  •  {book['year']}"
    text_with_outline(draw, TW // 2, TH - 110, meta_text, meta_font, WHITE, BLACK, 6)

    canvas = canvas.resize(UPSCALE, Image.LANCZOS)
    out_path = os.path.join(workdir, "thumbnail.png")
    canvas.save(out_path, quality=95)

    return _save_thumbnail_capped(canvas, out_path)


# ════════════════════════════════════════════════════════════
# 5. 메인
# ════════════════════════════════════════════════════════════
def main():
    if not GEMINI_API_KEY:
        log("❌ GEMINI_API_KEY 없음")
        raise SystemExit(1)

    lang = "en"
    book = pick_next_book()
    workdir = os.path.join("curio_longform_output", CHANNEL_KEY, lang)
    os.makedirs(workdir, exist_ok=True)

    log(f"1/6 [{book['rank']}/100] 대본+이미지프롬프트 생성 중: {book['title']} ({book['author']}, {book['year']})...")
    data = generate_script(book)
    narration = data["narration"]
    with open(os.path.join(workdir, "script.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log(f"   나레이션 {len(narration.split())}단어")

    log("1.5/6 유튜브 제목/설명 생성 중...")
    yt_meta = generate_youtube_metadata(book, narration)
    log(f"   제목: {yt_meta['title']}")

    log(f"2/6 나레이션 TTS + 캡션 타이밍 생성 중 (ElevenLabs voice_id={VOICE_ID})...")
    audio_path, srt_entries, total_dur = build_narration_track(narration, workdir)
    log(f"   총 나레이션 길이: {total_dur/60:.1f}분")

    srt_path = os.path.join(workdir, "captions.srt")
    write_srt(srt_entries, srt_path)

    log(f"3/6 책 삽화 이미지 {N_UNIQUE_IMAGES}장 생성 중 (Gemini, Veo 미사용)...")
    image_paths = generate_book_images(book, data["image_prompts"], workdir)
    log(f"   {len(image_paths)}장 생성 완료")

    log(f"4/6 {IMAGE_SLIDE_SECONDS:.0f}초 간격 Ken Burns 컷 순환 영상 조립 중...")
    visual_path = build_visual_track(image_paths, total_dur, workdir)

    log("5/6 영상+오디오 합성 중...")
    final_path = os.path.join(workdir, "final.mp4")
    mux_final(visual_path, audio_path, srt_path, final_path, workdir)
    dur = get_duration(final_path)
    log(f"   ✅ 영상 완성: {final_path} ({dur/60:.1f}분)")

    log("6/6 썸네일 생성 중 (책 제목 강조)...")
    thumb_path = build_thumbnail(book, image_paths[0], workdir)
    log(f"   ✅ 썸네일 완성: {thumb_path}")

    meta = {
        "topic": book["title"],
        "book": book,
        "lang": lang,
        "channel_key": CHANNEL_KEY,
        "duration_sec": dur,
        "video_path": final_path,
        "thumbnail_path": thumb_path,
        "subtitle_path": None,  # 번인이라 유튜브 자막 트랙 업로드 불필요
        "title": yt_meta["title"],
        "description": yt_meta["description"],
    }
    with open(os.path.join(workdir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    log(f"🎉 완료 — {workdir}/meta.json")


if __name__ == "__main__":
    main()
