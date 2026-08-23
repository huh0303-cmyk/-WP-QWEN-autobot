#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nasa_archive_longform.py
─────────────────────────────────────────────────────────────
NASA_SPACE_JOURNAL 채널 전용 파이프라인. 나머지 Curio/Times 채널과 달리
AI로 이미지/영상을 만들지 않는다 — NASA 공식 이미지/영상 API
(images-api.nasa.gov, 전량 퍼블릭도메인 — 미국 연방정부 저작물이라 원칙적으로
저작권 없음)에서 실제 아카이브 영상을 검색+다운로드해 짜깁기하고, 그 위에
Gemini가 쓴 사실기반 나레이션(ElevenLabs TTS) + 큰 번인자막을 입힌다.
썸네일도 AI생성 이미지가 아니라 실제 다운로드한 NASA 사진을 사용한다.

Library of Congress(loc.gov)도 후보 소스로 검토했으나, National Screening
Room 항목별로 재사용 권리(rights statement)가 제각각이라 항목마다 개별
확인이 필요함 — 1단계는 NASA API만으로 구현하고, LOC는 rights 필터링
로직을 추가해서 다음 단계로 확장 가능하도록 소스 함수를 분리해뒀다.

사용법:
    python scripts/nasa_archive_longform.py
"""
import os
import re
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests  # noqa: E402

from curio_longform import (  # noqa: E402
    gemini_generate_text, get_duration, run_ffmpeg, _strip_json_fence,
    log, GEMINI_API_KEY, ensure_thumbnail_font,
)
from classic_reads_longform import (  # noqa: E402
    build_narration_track, write_srt, mux_final, CAPTION_STYLE, _save_thumbnail_capped,
)

CHANNEL_KEY = "nasa"
W, H = 1920, 1080
NASA_API = "https://images-api.nasa.gov"
CLIP_TRIM_SECONDS = 22.0      # 클립 하나당 최대 사용 길이(너무 길게 늘어지지 않게)
N_CLIPS_TARGET = 12           # 검색 결과에서 확보 시도할 실제 클립 수

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
STATE_PATH = os.path.join(DATA_DIR, "nasa_archive_state.json")

# 기존 curio_longform.py의 nasa 주제풀과 동일 계열 — 전부 NASA 아카이브에
# 실제 영상 소스가 존재할 만한 잘 알려진 미션/사건 위주로 구성.
TOPICS = [
    "Apollo 11 moon landing",
    "Voyager Golden Record",
    "Artemis program Moon",
    "Hubble Space Telescope",
    "James Webb Space Telescope",
    "International Space Station",
    "Mars Perseverance rover landing",
    "Cassini Saturn mission",
    "Space Shuttle launch",
    "Voyager Jupiter flyby",
    "Apollo 13",
    "Curiosity rover Mars",
]


def pick_topic():
    state = {"last_idx": -1}
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, encoding="utf-8") as f:
            state = json.load(f)
    idx = (state.get("last_idx", -1) + 1) % len(TOPICS)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump({"last_idx": idx}, f)
    return TOPICS[idx]


# ════════════════════════════════════════════════════════════
# 1. NASA 실제 아카이브 영상 검색 + 다운로드
# ════════════════════════════════════════════════════════════
def search_nasa_videos(query, count):
    r = requests.get(f"{NASA_API}/search", params={"q": query, "media_type": "video"}, timeout=30)
    r.raise_for_status()
    return r.json()["collection"]["items"][:count]


def _best_asset_url(files):
    """orig(용량 큼)보다 medium/mobile/small 순으로 선호 — CI 다운로드 속도용."""
    for suffix in ("~medium.mp4", "~mobile.mp4", "~small.mp4", "~orig.mp4"):
        for f in files:
            if f.endswith(suffix):
                return f
    for f in files:
        if f.endswith(".mp4"):
            return f
    return None


def download_file(url, out_path, timeout=120):
    r = requests.get(url, stream=True, timeout=timeout)
    r.raise_for_status()
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=1 << 16):
            f.write(chunk)


def fetch_nasa_clips(query, workdir, n_target=N_CLIPS_TARGET):
    items = search_nasa_videos(query, n_target * 2)
    clips = []
    for item in items:
        if len(clips) >= n_target:
            break
        data = item["data"][0]
        nasa_id = data.get("nasa_id", "unknown")
        href = item.get("href")
        if not href:
            continue
        try:
            files = requests.get(href, timeout=30).json()
        except Exception:
            continue
        asset_url = _best_asset_url(files)
        if not asset_url:
            continue
        safe_name = re.sub(r"[^A-Za-z0-9_-]", "_", nasa_id)[:60]
        raw_path = os.path.join(workdir, f"raw_{safe_name}.mp4")
        try:
            if not os.path.exists(raw_path):
                download_file(asset_url, raw_path)
            dur = get_duration(raw_path)
            if dur < 2:
                continue
            clips.append({
                "path": raw_path, "title": data.get("title", ""), "duration": dur,
                "nasa_id": nasa_id, "date": data.get("date_created", ""),
                "description": (data.get("description") or "")[:300],
            })
        except Exception as e:
            log(f"   ⚠️ 다운로드 실패({nasa_id}): {e}")
            continue
    return clips


# ════════════════════════════════════════════════════════════
# 2. 대본 (실제 확보된 클립 정보를 근거로, 사실기반)
# ════════════════════════════════════════════════════════════
def generate_script(topic, clips):
    clip_notes = "\n".join(
        f"- {c['title']} ({c['date'][:10] if c['date'] else 'date unknown'}): {c['description']}"
        for c in clips
    )
    prompt = f"""You are writing a narration script for a ~7-minute YouTube documentary
video about: "{topic}", for a channel that uses real NASA archival footage
(not AI-generated visuals).

Here are the actual NASA archive clips that will play under this narration, IN
THE EXACT ORDER they will appear on screen (clip 1 plays first, then clip 2,
and so on, looping back to clip 1 if the narration runs longer than the clips):
---
{clip_notes[:3000]}
---

Write "narration": a single continuous narration script, approximately 950-1050
words, in English, engaging documentary tone (like a good space/science
YouTuber — factual, vivid, not a dry lecture). CRITICAL: structure the
narration to move through the clips in the SAME ORDER listed above — write
roughly one section per clip (proportional to how many clips there are), and
make each section actually be about what that clip shows/depicts (use its
title/date/description), so a viewer watching clip N on screen hears narration
about clip N at that moment. Open the first section with a hook in its first
two sentences. Close the final section with a memorable closing line. Do not
fabricate quotes or invent specific technical details/statistics that aren't
well-established public knowledge about NASA history.

Also write "title_hint": a short natural phrase capturing the video's angle.

Respond with JSON only, no explanation, no markdown fences:
{{"narration": "...", "title_hint": "..."}}
"""
    text = gemini_generate_text(prompt, temperature=0.85)
    return json.loads(_strip_json_fence(text))


def generate_youtube_metadata(topic, narration):
    prompt = f"""You are writing the YouTube title and description for a documentary
video about "{topic}", on a channel that uses real NASA archival footage.

Narration script:
---
{narration[:6000]}
---

Write:
1. "title": a warm, friendly, curiosity-driven YouTube title, under 100
   characters — like a real person who loves this topic sharing it with you,
   not a clickbait template. No ALL CAPS spam, no emoji-stuffing, no lies.
2. "description": around 1000 characters (not bytes), always in English.
   - Open with 2-3 sentences on why this moment/topic matters, plain natural
     prose (no "In this video, we will explore..." or similar AI-sounding
     opener).
   - A short paragraph pulling out 3-5 concrete facts actually in the script.
   - Mention that the footage is real NASA archival footage (public domain).
   - One natural sentence inviting people to subscribe for more space history.
   - End with 4-6 relevant hashtags on the last line.
3. "tags": a JSON array of 10-15 YouTube search tags (not hashtags) —
   specific mission/spacecraft/people names from this topic plus a few
   broader category terms (e.g. "nasa", "space", "documentary"), each a
   short lowercase phrase, no # symbol.

Respond with JSON only, no explanation, no markdown fences:
{{"title": "...", "description": "...", "tags": ["...", "..."]}}
"""
    text = gemini_generate_text(prompt, temperature=0.8)
    return json.loads(_strip_json_fence(text))


# ════════════════════════════════════════════════════════════
# 3. 실제 클립을 트림/정규화해서 나레이션 길이만큼 순환 이어붙이기
# ════════════════════════════════════════════════════════════
def normalize_clip(raw_path, out_path, max_dur):
    dur = min(get_duration(raw_path), max_dur)
    vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},format=yuv420p,fps=30"
    run_ffmpeg([
        "ffmpeg", "-y", "-i", raw_path, "-t", str(dur), "-vf", vf,
        "-c:v", "libx264", "-an", "-pix_fmt", "yuv420p",
        "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:v", "+bitexact",
        out_path,
    ])
    return dur


def build_visual_track(clips, total_duration, workdir):
    norm_clips = []
    for i, c in enumerate(clips):
        norm_path = os.path.join(workdir, f"norm_{i}.mp4")
        if not os.path.exists(norm_path):
            normalize_clip(c["path"], norm_path, CLIP_TRIM_SECONDS)
        norm_clips.append(norm_path)

    # 2026-08-23: 예전엔 한 바퀴 다 쓸 때마다 클립 순서를 무작위로 섞었는데,
    # generate_script()가 이제 나레이션을 clips 리스트 순서 그대로(클립1 얘기 ->
    # 클립2 얘기 -> ...) 쓰도록 바뀌었으므로, 화면도 반드시 같은 순서로 재생돼야
    # 나레이션 내용과 화면이 맞는다(사용자 지적: "화면과 나레이션 전혀 안 맞아").
    # 무작위 셔플을 없애고 clips 원래 순서를 그대로 반복 재생한다 — 한 바퀴를 다
    # 돌면 다시 처음(클립0)부터, 인접 반복(마지막 클립 바로 다음에 또 그 클립)은
    # 애초에 발생하지 않는다(다음 바퀴 시작은 항상 클립0).
    segments = []
    covered = 0.0
    pos = 0
    while covered < total_duration:
        if pos >= len(norm_clips):
            pos = 0
        clip = norm_clips[pos]
        pos += 1
        seg_dur = min(get_duration(clip), total_duration - covered)
        segments.append((clip, seg_dur))
        covered += seg_dur

    list_file = os.path.join(workdir, "visual_concat_list.txt")
    trimmed_paths = []
    for idx, (clip, seg_dur) in enumerate(segments):
        full_dur = get_duration(clip)
        if seg_dur >= full_dur - 0.05:
            trimmed_paths.append(clip)
        else:
            trimmed = os.path.join(workdir, f"seg_{idx}.mp4")
            if not os.path.exists(trimmed):
                run_ffmpeg(["ffmpeg", "-y", "-i", clip, "-t", str(seg_dur),
                            "-c", "copy", trimmed])
            trimmed_paths.append(trimmed)

    with open(list_file, "w", encoding="utf-8") as f:
        for p in trimmed_paths:
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


# ════════════════════════════════════════════════════════════
# 4. 썸네일 — AI생성이 아니라 실제 다운로드한 NASA 클립의 한 프레임 사용
# ════════════════════════════════════════════════════════════
def extract_hero_frame(clip_path, out_path, at_sec=1.0):
    run_ffmpeg(["ffmpeg", "-y", "-ss", str(at_sec), "-i", clip_path,
                "-frames:v", "1", "-q:v", "2", out_path])
    return out_path


def build_thumbnail(topic, hero_frame_path, workdir):
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

    def text_with_outline(draw, cx, y, text, font, fill, outline, ow=10):
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        x = cx - w // 2 - bbox[0]
        for dx in range(-ow, ow + 1, 3):
            for dy in range(-ow, ow + 1, 3):
                if dx * dx + dy * dy <= ow * ow:
                    draw.text((x + dx, y + dy), text, font=font, fill=outline)
        draw.text((x, y), text, font=font, fill=fill)

    def wrap(draw, text, font, max_width, max_lines=2):
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
        return lines[:max_lines]

    TW, TH = 1280, 720
    UPSCALE = (5120, 2880)
    font_path = ensure_thumbnail_font("en", DATA_DIR)

    img = crop_resize(Image.open(hero_frame_path).convert("RGB"), TW, TH)
    img = ImageEnhance.Contrast(img).enhance(1.15)
    canvas = img.copy()

    overlay = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rectangle([0, TH - 260, TW, TH], fill=(0, 0, 0, 165))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(canvas)

    WHITE, YELLOW, BLACK = (255, 255, 255), (255, 214, 0), (0, 0, 0)
    title_font = ImageFont.truetype(font_path, 66)
    lines = wrap(draw, topic.upper(), title_font, TW - 100)
    y = TH - 240
    for line in lines:
        text_with_outline(draw, TW // 2, y, line, title_font, YELLOW, BLACK, 10)
        y += 76

    tag_font = ImageFont.truetype(font_path, 32)
    text_with_outline(draw, TW // 2, TH - 45, "REAL NASA ARCHIVE FOOTAGE", tag_font, WHITE, BLACK, 5)

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
    topic = pick_topic()
    workdir = os.path.join("curio_longform_output", CHANNEL_KEY, lang)
    os.makedirs(workdir, exist_ok=True)

    log(f"1/6 NASA 아카이브에서 실제 영상 클립 검색+다운로드 중 (주제: {topic})...")
    clips = fetch_nasa_clips(topic, workdir)
    if not clips:
        log("❌ 이 주제로 사용 가능한 NASA 클립을 하나도 못 찾음")
        raise SystemExit(1)
    log(f"   {len(clips)}개 클립 확보")

    log("2/6 사실기반 대본 생성 중 (실제 확보한 클립 정보 근거)...")
    data = generate_script(topic, clips)
    narration = data["narration"]
    with open(os.path.join(workdir, "script.json"), "w", encoding="utf-8") as f:
        json.dump({"topic": topic, "clips": clips, **data}, f, ensure_ascii=False, indent=2)
    log(f"   나레이션 {len(narration.split())}단어")

    log("2.5/6 유튜브 제목/설명 생성 중...")
    yt_meta = generate_youtube_metadata(topic, narration)
    log(f"   제목: {yt_meta['title']}")

    log("3/6 나레이션 TTS + 캡션 타이밍 생성 중...")
    audio_path, srt_entries, total_dur = build_narration_track(narration, workdir)
    log(f"   총 나레이션 길이: {total_dur/60:.1f}분")
    srt_path = os.path.join(workdir, "captions.srt")
    write_srt(srt_entries, srt_path)

    log("4/6 실제 NASA 클립으로 영상 트랙 조립 중 (트림+정규화+순환)...")
    visual_path = build_visual_track(clips, total_dur, workdir)

    log("5/6 영상+오디오 합성 중...")
    final_path = os.path.join(workdir, "final.mp4")
    mux_final(visual_path, audio_path, srt_path, final_path, workdir)
    dur = get_duration(final_path)
    log(f"   ✅ 영상 완성: {final_path} ({dur/60:.1f}분)")

    log("6/6 썸네일 생성 중 (실제 NASA 프레임 사용)...")
    hero_frame = os.path.join(workdir, "hero_frame.jpg")
    extract_hero_frame(clips[0]["path"], hero_frame, at_sec=min(1.0, clips[0]["duration"] / 3))
    thumb_path = build_thumbnail(topic, hero_frame, workdir)
    log(f"   ✅ 썸네일 완성: {thumb_path}")

    meta = {
        "topic": topic,
        "lang": lang,
        "channel_key": CHANNEL_KEY,
        "duration_sec": dur,
        "video_path": final_path,
        "thumbnail_path": thumb_path,
        "title": yt_meta["title"],
        "description": yt_meta["description"],
        "tags": yt_meta.get("tags", []),
        "source_clips": [{"nasa_id": c["nasa_id"], "title": c["title"]} for c in clips],
    }
    with open(os.path.join(workdir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    log(f"🎉 완료 — {workdir}/meta.json")


if __name__ == "__main__":
    main()
