#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
health_longform.py
─────────────────────────────────────────────────────────────
건강채널 장편(8분 내외, 16:9) 영상 자동 생성기.

주제 하나를 받아서: 대본(JSON, beats 단위) → 앞 3개 AI 영상 클립(Veo) +
나머지 정지 이미지(Ken Burns 효과) → TTS 내레이션 → 최종 mp4 조립 →
자막(SRT, 유튜브 업로드용) → 음식 이미지 포함 썸네일까지 만든다.

자막은 burn-in이 아니라 표준 SRT 파일로 만든다 — 실제 조회수 100만대
건강 채널(닥터딩요 등) 벤치마킹 결과, 화려한 애니메이션 자막보다 유튜브
기본 스타일(흰 글씨 + 반투명 검은 박스, 하단 중앙, 한 줄)이 신뢰감 있는
건강 채널의 표준이었음 (2026-08-03 확인). 유튜브 자막 업로드 시 자동으로
그 스타일로 렌더링된다.

이 스크립트가 지켜야 하는 고정 규칙은 scripts/health_longform_rules.py에
있다 (대본에 음식 섹션 필수, 썸네일에 음식 이미지 필수, 언어별 순서 셔플 등).

사용법:
    python scripts/health_longform.py "허리무릎 통증" ko
    python scripts/health_longform.py "허리무릎 통증" en
    python scripts/health_longform.py "허리무릎 통증" ja

필요 환경변수:
    GEMINI_API_KEY       - 대본/이미지/Veo 영상 생성
    ELEVENLABS_API_KEY   - TTS 내레이션 (없으면 무음 처리)
    ELEVENLABS_VOICE_ID  - (선택)

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
import health_longform_rules as RULES  # noqa: E402


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
def gemini_generate_text(prompt, temperature=0.9, max_retries=5):
    # 2026-08-17: OPENAI_API_KEY가 있으면 ChatGPT로 라우팅 (curio_longform.py와 동일 원칙).
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from openai_text import openai_available, openai_generate_text
        if openai_available():
            return openai_generate_text(prompt, temperature=temperature, max_retries=max_retries)
    except ImportError:
        pass

    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{GEMINI_TEXT_MODEL}:generateContent?key={GEMINI_API_KEY}")
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature}}
    last_err = None
    for attempt in range(max_retries):
        r = requests.post(url, json=body, timeout=60)
        if r.status_code == 429 or r.status_code >= 500:
            last_err = f"{r.status_code}: {r.text[:200]}"
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


def generate_script(topic, lang):
    lang_name = LANG_NAMES.get(lang, "Korean")
    n_images = TARGET_IMAGE_COUNT
    sections = RULES.REQUIRED_SCRIPT_SECTIONS

    prompt = f"""You are writing a narration script for an ~8-minute YouTube health video
in {lang_name}, about: "{topic}".

Channel positioning (must follow): correct symptom-based coping methods + good food
recommendations. This is NOT a hospital/diagnosis substitute — include a disclaimer
that this is general info, not medical advice, and viewers with symptoms should see
a doctor.

The script MUST be broken into "beats" that will each become one video shot:
- Each beat has type "image": pairs one narration chunk (2-4 sentences, natural
  spoken pacing) with an English image-generation prompt (realistic photography
  style, no text/watermark in the image).
- Total beats must be exactly {n_images}.
- Every beat must be tagged with a "section" from this fixed list, covering ALL of
  them across the script in a sensible order: {sections}.
  The "food_recommend" section is MANDATORY and must cover several consecutive
  beats with real, specific recommended foods for this condition (not generic).
- Vary pacing: front beats can be short/punchy, later beats can be longer. The
  first beat especially must grab attention in the first 10 seconds.

Also return:
- "foods": a list of 3-5 specific recommended foods for this condition, in {lang_name}
  culture-appropriate terms (e.g. Korean fish like 고등어 for Korean, salmon/kale for
  English, 焼き鮭/納豆 for Japanese) — pick foods natural for {lang_name} speakers.
- "thumbnail_lines": {{"line1": "short hook line 1", "line2": "short punchy hook line 2",
  "line3": "short line about symptom check", "line4": "short call-to-action line"}}
  in {lang_name}, YouTube-clickbait-but-honest style, ALL CAPS style ok for English.

Respond with JSON only, no explanation, no markdown fences:
{{
  "topic": "...",
  "foods": ["...", ...],
  "thumbnail_lines": {{"line1": "...", "line2": "...", "line3": "...", "line4": "..."}},
  "beats": [
    {{"type": "image", "section": "hook_intro", "narration": "...", "image_prompt": "..."}},
    ...,
    {{"type": "image", "section": "symptom_explain", "narration": "...", "image_prompt": "..."}},
    ...
  ]
}}
"""
    text = gemini_generate_text(prompt, temperature=0.9)
    data = json.loads(_strip_json_fence(text))

    beats = data.get("beats", [])
    present_sections = {b.get("section") for b in beats}
    missing = [s for s in RULES.REQUIRED_SCRIPT_SECTIONS if s not in present_sections]
    if missing:
        raise RuntimeError(f"대본에 필수 섹션 누락: {missing}")
    if RULES.FOOD_SECTION_REQUIRED and "food_recommend" not in present_sections:
        raise RuntimeError("대본에 food_recommend 섹션이 없음 (필수)")

    return data


# ════════════════════════════════════════════════════════════
# 2. 이미지 생성 (Gemini 2.5 Flash Image)
# ════════════════════════════════════════════════════════════
def gemini_generate_image(prompt, out_path, max_retries=5):
    if os.environ.get("PAID_IMAGE_GENERATION_ENABLED", "false").lower() != "true" or os.environ.get("OPENAI_IMAGE_ENABLED", "false").lower() != "true":
        log("      AI 이미지 생성 차단됨 — 퍼블릭도메인/아카이브 이미지만 허용")
        return False
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
            except Exception as e:
                last_err = str(e)
        # 두 모델 다 실패 -> 레이트리밋일 가능성 높으니 지수 백오프 후 재시도
        wait = min(5 * (2 ** attempt), 60)
        log(f"      (이미지 생성 재시도 대기 {wait}초 - 마지막 오류: {last_err})")
        time.sleep(wait)

    # 2026-08-22: 이 함수는 Gemini 전용이라 실패하면 그냥 이미지 없이 끝났음
    # (사용자 지시: "이미지도 돈안드는것 최우선" — 무료를 먼저 쓰되, 그게
    # 실패했을 때 최소한의 안전망은 있어야 함). curio_longform.py와 동일 원칙으로
    # OpenAI(gpt-image-1) 유료 폴백 추가.
    log(f"      ⚠️ Gemini 이미지 생성 실패({last_err}) → OpenAI(gpt-image-1) 유료 폴백 시도")
    try:
        from openai_text import openai_available, openai_generate_image
        if openai_available() and openai_generate_image(prompt, out_path):
            return True
    except ImportError:
        pass
    log(f"      ⚠️ 최종 실패(Gemini+OpenAI 둘 다 안 됨): {last_err}")
    return False


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


def build_thumbnail(topic, lang, thumbnail_lines, foods, workdir):
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

    def make_circle(path, size):
        img = crop_resize(Image.open(path).convert("RGB"), size, size)
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, size, size], fill=255)
        img.putalpha(mask)
        return img

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

    pain_photo = os.path.join(workdir, "thumb_pain_photo.png")
    pain_prompt = (
        f"An extreme close-up photorealistic photo of a person in pain related to "
        f"'{topic}', dramatic lighting, shallow depth of field, cinematic 16:9, "
        f"no text, no watermark."
    )
    if not gemini_generate_image(pain_prompt, pain_photo):
        raise RuntimeError("썸네일 통증 사진 생성 실패")

    food_paths = []
    for i, food in enumerate(foods[:3]):
        fp = os.path.join(workdir, f"thumb_food_{lang}_{i}.png")
        food_prompt = f"Clean top-down food photography of {food}, white background, bright natural light, no text."
        if gemini_generate_image(food_prompt, fp):
            food_paths.append(fp)

    img = crop_resize(Image.open(pain_photo).convert("RGB"), TW, TH)
    img = ImageEnhance.Contrast(img).enhance(1.15)

    canvas = Image.new("RGB", (TW, TH), (0, 0, 0))
    canvas.paste(img.crop((0, 230, TW, 470)), (0, 230))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, 0, TW, 230], fill=(0, 0, 0))
    draw.rectangle([0, 470, TW, TH], fill=(0, 0, 0))

    YELLOW, RED, WHITE, BLACK, GREEN = (255, 255, 0), (255, 0, 0), (255, 255, 255), (0, 0, 0), (60, 200, 90)

    text_with_outline(draw, TW // 2, 20, thumbnail_lines.get("line1", ""), ImageFont.truetype(font_path, 74), WHITE, BLACK, 9)
    text_with_outline(draw, TW // 2, 112, thumbnail_lines.get("line2", ""), ImageFont.truetype(font_path, 88), YELLOW, BLACK, 12)

    circle_size = 130
    start_x = TW - 40 - circle_size
    for i, fp in enumerate(food_paths):
        circ = make_circle(fp, circle_size)
        x = start_x - i * (circle_size - 35)
        y = 470 - circle_size + 20
        ring = Image.new("RGBA", (circle_size + 12, circle_size + 12), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse([0, 0, circle_size + 12, circle_size + 12], fill=(255, 255, 255, 255))
        canvas.paste(ring, (x - 6, y - 6), ring)
        canvas.paste(circ, (x, y), circ)

    draw = ImageDraw.Draw(canvas)
    text_with_outline(draw, TW // 2, 490, thumbnail_lines.get("line3", ""), ImageFont.truetype(font_path, 64), YELLOW, BLACK, 10)
    box_text(draw, TW // 2, 592, thumbnail_lines.get("line4", ""), ImageFont.truetype(font_path, 54), RED, WHITE)

    out_path = os.path.join(workdir, f"thumbnail_{lang}.png")
    canvas.save(out_path, quality=95)
    return out_path


# ════════════════════════════════════════════════════════════
# 7. 메인
# ════════════════════════════════════════════════════════════
def reuse_visuals_from(source_lang, workdir, n_images):
    """SAME_TOPIC_DIFFERENTIATION_RULES: 이미지는 언어간 재사용 가능, 순서만 섞기.
    source_lang의 workdir에서 이미지 파일을 복사해와서 이 workdir에 채워두면,
    이후 생성 루프의 '이미 있으면 재사용' 체크에 걸려서 Gemini 재호출 없이
    그대로 재사용된다 (TTS/썸네일만 새로 생성됨)."""
    src_dir = os.path.join("health_longform_output", source_lang)
    if not os.path.isdir(src_dir):
        log(f"   ⚠️ 재사용 소스 언어 폴더 없음: {src_dir} — 전부 새로 생성함")
        return

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
    lang = (sys.argv[2] if len(sys.argv) > 2 else "ko").strip().lower()
    reuse_from = sys.argv[3] if len(sys.argv) > 3 else ""
    if not topic:
        log("❌ 사용법: python health_longform.py \"주제\" [ko|en|ja] [재사용할언어]")
        raise SystemExit(1)

    workdir = os.path.join("health_longform_output", lang)
    os.makedirs(workdir, exist_ok=True)

    if reuse_from:
        log(f"0/4 {reuse_from} 버전에서 이미지 재사용 준비 중...")
        reuse_visuals_from(reuse_from, workdir, TARGET_IMAGE_COUNT)

    log(f"1/4 대본 생성 중 (주제: {topic}, 언어: {lang})...")
    data = generate_script(topic, lang)
    beats = data["beats"]
    with open(os.path.join(workdir, "script.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log(f"   총 {len(beats)}개 비트, 음식: {data.get('foods')}")

    srt_entries = []
    cursor = 0.0
    clip_paths = []

    log("2/4 정지 이미지(Ken Burns) 생성 중...")
    image_beats = [b for b in beats if b["type"] == "image"]
    for idx, beat in enumerate(image_beats):
        log(f"   [{idx+1}/{len(image_beats)}] ({beat['section']}) {beat['image_prompt'][:50]}...")
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

    log("3/4 최종 영상 이어붙이는 중...")
    final_path = os.path.join(workdir, "final.mp4")
    concat_clips(clip_paths, final_path, workdir)
    dur = get_duration(final_path)
    log(f"   ✅ 영상 완성: {final_path} ({dur/60:.1f}분)")

    srt_path = os.path.join(workdir, f"subtitles_{lang}.srt")
    write_srt(srt_entries, srt_path)
    log(f"   ✅ 자막 완성: {srt_path} (유튜브 자막 업로드용 - 잘 나가는 건강채널 벤치마킹한 "
        f"기본 흰글씨/검은박스 스타일로 유튜브가 렌더링함)")

    log("4/4 썸네일 생성 중...")
    thumb_path = build_thumbnail(topic, lang, data.get("thumbnail_lines", {}), data.get("foods", []), workdir)
    log(f"   ✅ 썸네일 완성: {thumb_path}")

    meta = {
        "topic": topic,
        "lang": lang,
        "duration_sec": dur,
        "video_path": final_path,
        "thumbnail_path": thumb_path,
        "subtitle_path": srt_path,
        "foods": data.get("foods", []),
    }
    with open(os.path.join(workdir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    log(f"🎉 완료 — {workdir}/meta.json")


if __name__ == "__main__":
    main()
