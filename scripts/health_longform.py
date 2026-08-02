#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
health_longform.py
─────────────────────────────────────────────────────────────
건강채널 장편(8분 내외, 16:9) 영상 자동 생성기.

주제 하나를 받아서: 대본(JSON, beats 단위) → 앞 3개 AI 영상 클립(Veo) +
나머지 정지 이미지(Ken Burns 효과) → TTS 내레이션 → 최종 mp4 조립 →
음식 이미지 포함 썸네일까지 만든다.

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
import subprocess

import requests

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import health_longform_rules as RULES  # noqa: E402

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
    n_intro = RULES.INTRO_VIDEO_CLIP_COUNT
    n_images = TARGET_IMAGE_COUNT
    sections = RULES.REQUIRED_SCRIPT_SECTIONS

    prompt = f"""You are writing a narration script for an ~8-minute YouTube health video
in {lang_name}, about: "{topic}".

Channel positioning (must follow): correct symptom-based coping methods + good food
recommendations. This is NOT a hospital/diagnosis substitute — include a disclaimer
that this is general info, not medical advice, and viewers with symptoms should see
a doctor.

The script MUST be broken into "beats" that will each become one video shot:
- The first {n_intro} beats have type "intro_video": short (1-2 sentence) narration
  each, paired with an English text-to-video prompt describing realistic natural
  human motion (e.g. a person gently rubbing/pressing the painful area, sitting down
  slowly, walking with slight discomfort). These are the hook — fast-paced, must grab
  attention in the first 10 seconds, no text overlays needed in the prompt itself.
- The remaining beats have type "image": each pairs one narration chunk (2-4
  sentences, natural spoken pacing) with an English image-generation prompt
  (realistic photography style, no text/watermark in the image).
- Total beats (intro_video + image) must be exactly {n_intro + n_images}.
- Every beat must be tagged with a "section" from this fixed list, covering ALL of
  them across the script in a sensible order: {sections}.
  The "food_recommend" section is MANDATORY and must cover several consecutive
  beats with real, specific recommended foods for this condition (not generic).
- Vary pacing: front beats can be short/punchy, later beats can be longer.

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
    {{"type": "intro_video", "section": "hook_intro", "narration": "...", "video_prompt": "..."}},
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
        out_path,
    ])


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
                f"anullsrc=r=44100:cl=stereo:d={duration}", "-c:a", "aac", out_path])


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
        "-shortest", out_path,
    ])
    return dur


def concat_clips(clip_paths, out_path, workdir):
    list_file = os.path.join(workdir, "concat_list.txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for p in clip_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")
    run_ffmpeg(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
                "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", out_path])


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
def main():
    if not GEMINI_API_KEY:
        log("❌ GEMINI_API_KEY 없음")
        raise SystemExit(1)

    topic = sys.argv[1] if len(sys.argv) > 1 else ""
    lang = (sys.argv[2] if len(sys.argv) > 2 else "ko").strip().lower()
    if not topic:
        log("❌ 사용법: python health_longform.py \"주제\" [ko|en|ja]")
        raise SystemExit(1)

    workdir = os.path.join("health_longform_output", lang)
    os.makedirs(workdir, exist_ok=True)

    log(f"1/5 대본 생성 중 (주제: {topic}, 언어: {lang})...")
    data = generate_script(topic, lang)
    beats = data["beats"]
    with open(os.path.join(workdir, "script.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log(f"   총 {len(beats)}개 비트, 음식: {data.get('foods')}")

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
            continue
        if not elevenlabs_tts(beat["narration"], audio):
            audio = audio.replace(".mp3", ".m4a")
            make_silence(audio, RULES.INTRO_VIDEO_DURATION_SECONDS)
        if not os.path.exists(raw):
            generate_intro_video(beat["video_prompt"], raw)
        normalize_intro_clip(raw, audio, clip)
        clip_paths.append(clip)

    log("3/5 나머지 정지 이미지(Ken Burns) 생성 중...")
    image_beats = [b for b in beats if b["type"] == "image"]
    for idx, beat in enumerate(image_beats):
        log(f"   [{idx+1}/{len(image_beats)}] ({beat['section']}) {beat['image_prompt'][:50]}...")
        img_path = os.path.join(workdir, f"img_{idx}.png")
        if not gemini_generate_image(beat["image_prompt"], img_path):
            log(f"   ⚠️ 이미지 생성 실패, 스킵: beat {idx}")
            continue
        audio = os.path.join(workdir, f"img_audio_{idx}.mp3")
        if not elevenlabs_tts(beat["narration"], audio):
            audio = audio.replace(".mp3", ".m4a")
            make_silence(audio, 6.0)
        clip = os.path.join(workdir, f"img_clip_{idx}.mp4")
        ken_burns_clip(img_path, audio, clip, zoom_in=(idx % 2 == 0))
        clip_paths.append(clip)
        time.sleep(2)  # 이미지 생성 API 레이트리밋 방지용 페이싱

    log("4/5 최종 영상 이어붙이는 중...")
    final_path = os.path.join(workdir, "final.mp4")
    concat_clips(clip_paths, final_path, workdir)
    dur = get_duration(final_path)
    log(f"   ✅ 영상 완성: {final_path} ({dur/60:.1f}분)")

    log("5/5 썸네일 생성 중...")
    thumb_path = build_thumbnail(topic, lang, data.get("thumbnail_lines", {}), data.get("foods", []), workdir)
    log(f"   ✅ 썸네일 완성: {thumb_path}")

    meta = {
        "topic": topic,
        "lang": lang,
        "duration_sec": dur,
        "video_path": final_path,
        "thumbnail_path": thumb_path,
        "foods": data.get("foods", []),
    }
    with open(os.path.join(workdir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    log(f"🎉 완료 — {workdir}/meta.json")


if __name__ == "__main__":
    main()
