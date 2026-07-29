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
    GOOGLE_CREDENTIALS_JSON - 구글드라이브 서비스계정 JSON(문자열 그대로)
    GEMINI_API_KEY          - 주제어 기반 이미지 생성(나노바나나). 없으면 B폴더 폴백
    MUSIC_SOURCE_FOLDER_ID  - (선택) 원곡 폴더 ID, 기본값 있음
    THUMBNAIL_FOLDER_ID     - (선택) 썸네일창고 폴더 ID, 기본값 있음(폴백용)
    OUTPUT_FOLDER_ID        - (선택) 최종파일 폴더 ID, 기본값 있음

필요 시스템 도구: ffmpeg, ffprobe
"""

import os
import sys
import json
import random
import base64
import requests
import subprocess
from datetime import datetime, timezone, timedelta

GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_IMAGE_MODELS = ["gemini-2.5-flash-image", "gemini-2.5-flash-image-preview"]

MUSIC_SOURCE_FOLDER_ID = os.environ.get("MUSIC_SOURCE_FOLDER_ID") or "1RqL44lM5oUSW5_PAZLHHlevrVkr1ibxd"
THUMBNAIL_FOLDER_ID = os.environ.get("THUMBNAIL_FOLDER_ID") or "1jVDuCjTVJPnNSIBEXjnU6DPSzZO56d68"
OUTPUT_FOLDER_ID = os.environ.get("OUTPUT_FOLDER_ID") or "1srQUiWOk6UruujYSy2S0ogN3FvxVTSBN"

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
TARGET_MIN_SEC = 60 * 60
TARGET_MAX_SEC = 80 * 60
IMAGE_SWAP_SEC = 15 * 60          # AI 이미지 2장 전환 간격
VIDEO_W, VIDEO_H = 1920, 1080

AUDIO_EXTS = (".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg")
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp")

FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/nanumgothic/NanumGothic-Bold.ttf"
FONT_PATH = "/tmp/_playlist_nanumgothic_bold.ttf"


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
# 구글드라이브
# ════════════════════════════════════════════════════════════
def get_drive_service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    sa_info = json.loads(GOOGLE_CREDENTIALS_JSON)
    creds = service_account.Credentials.from_service_account_info(
        sa_info, scopes=["https://www.googleapis.com/auth/drive"])
    return build("drive", "v3", credentials=creds)


def list_folder_files(service, folder_id, exts):
    files = []
    page_token = None
    while True:
        resp = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="nextPageToken, files(id, name, mimeType)",
            pageToken=page_token,
            pageSize=200,
        ).execute()
        for f in resp.get("files", []):
            name = f.get("name", "")
            mime = f.get("mimeType", "")
            if mime.startswith("audio/") or mime.startswith("image/") or \
               name.lower().endswith(exts):
                files.append(f)
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return [f for f in files if f.get("name", "").lower().endswith(exts)
            or f.get("mimeType", "").startswith(("audio/", "image/"))]


def download_drive_file(service, file_id, out_path):
    from googleapiclient.http import MediaIoBaseDownload

    request = service.files().get_media(fileId=file_id)
    with open(out_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


def upload_to_drive(service, file_path, folder_id, name):
    from googleapiclient.http import MediaFileUpload

    metadata = {"name": name, "parents": [folder_id]}
    media = MediaFileUpload(file_path, resumable=True)
    f = service.files().create(body=metadata, media_body=media,
                                fields="id,webViewLink").execute()
    return f.get("webViewLink"), f.get("id")


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


def gemini_generate_text(prompt, temperature=0.9):
    if not GEMINI_API_KEY:
        return ""
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}")
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature}}
    try:
        r = requests.post(url, json=body, timeout=30)
        r.raise_for_status()
        data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        return ""


def build_caption_text(topic, caption_text):
    if caption_text and caption_text.strip():
        return caption_text.strip()
    prompt = (f"'{topic}' 분위기의 감성 음악 플레이리스트 유튜브 영상에 어울리는 "
              f"짧은 한글 소개 문구를 20자 이내로 하나만 만들어줘. "
              f"이모지 1개 포함, 따옴표나 설명 없이 문구만 출력해줘.")
    text = gemini_generate_text(prompt)
    text = text.strip().strip('"').strip("'")
    return text or f"{topic} 감성 플레이리스트"


def build_ai_images(topic, workdir):
    topic = (topic or "").strip() or "tropical beachside vibe, aesthetic lifestyle"
    prompts = [
        f"Aesthetic lifestyle photo of a joyful young woman with arms raised, "
        f"candid pose, background: {topic}, golden hour sunset lighting, "
        f"cinematic photorealistic, vibrant colors, high quality influencer photo, "
        f"no text, no watermark, 16:9",
        f"Aesthetic lifestyle photo of a joyful young woman, candid pose, "
        f"background: {topic}, bright daylight, cinematic photorealistic, "
        f"vibrant colors, high quality influencer photo, no text, no watermark, 16:9",
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


# ════════════════════════════════════════════════════════════
# 오디오 조합 (무작위 60~80분)
# ════════════════════════════════════════════════════════════
def build_playlist_audio(service, tracks_meta, out_path):
    shuffled = list(tracks_meta)
    random.shuffle(shuffled)

    selected_paths = []
    accumulated = 0.0

    for i, meta in enumerate(shuffled):
        ext = os.path.splitext(meta["name"])[1] or ".mp3"
        local_path = os.path.join(WORKDIR, f"track_{i:03d}{ext}")
        log(f"   다운로드 중: {meta['name']}")
        try:
            download_drive_file(service, meta["id"], local_path)
            dur = get_duration(local_path)
        except Exception as e:
            log(f"   ⚠️ 스킵({meta['name']}): {e}")
            if os.path.exists(local_path):
                os.remove(local_path)
            continue

        if accumulated >= TARGET_MIN_SEC and accumulated + dur > TARGET_MAX_SEC:
            os.remove(local_path)
            continue

        selected_paths.append(local_path)
        accumulated += dur
        log(f"   ✅ 추가: {meta['name']} ({dur/60:.1f}분) — 누적 {accumulated/60:.1f}분")

        if accumulated >= TARGET_MAX_SEC:
            break

    if accumulated < TARGET_MIN_SEC:
        log(f"   ⚠️ 보유한 음원을 다 써도 {accumulated/60:.1f}분 (목표 60분 미만)")

    if not selected_paths:
        raise RuntimeError("사용 가능한 음원이 없습니다")

    cmd = ["ffmpeg", "-y"]
    for p in selected_paths:
        cmd += ["-i", p]
    n = len(selected_paths)
    filter_complex = "".join(f"[{i}:a:0]" for i in range(n)) + f"concat=n={n}:v=0:a=1[outa]"
    cmd += ["-filter_complex", filter_complex, "-map", "[outa]",
            "-c:a", "aac", "-b:a", "192k", out_path]
    run_ffmpeg(cmd)

    return accumulated


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


def add_lower_third_bar(video_path, caption_text, out_path):
    """영상 하단에 반투명 바 + 'Playlist | 캡션' 텍스트를 영상 내내 표시"""
    ensure_font()
    text = _escape_drawtext(f"Playlist | {caption_text}")
    bar_h = 70
    vf = (
        f"drawbox=x=0:y=ih-{bar_h}:w=iw:h={bar_h}:color=black@0.45:t=fill,"
        f"drawtext=fontfile={FONT_PATH}:text='{text}':"
        f"fontsize=30:fontcolor=white:x=30:y=h-{bar_h}+({bar_h}-th)/2"
    )
    run_ffmpeg(["ffmpeg", "-y", "-i", video_path, "-vf", vf,
                "-c:a", "copy", "-c:v", "libx264", "-pix_fmt", "yuv420p", out_path])


def make_caption_thumbnail(image_path, out_path, w=1280, h=720):
    """레퍼런스처럼 이미지 위에 큼직한 'Playlist' 타이틀을 얹은 썸네일 생성"""
    from PIL import Image, ImageDraw, ImageFont

    ensure_font()
    img = Image.open(image_path).convert("RGB").resize((w, h))
    draw = ImageDraw.Draw(img, "RGBA")
    font = ImageFont.truetype(FONT_PATH, 140)
    title = "Playlist"

    bbox = draw.textbbox((0, 0), title, font=font, stroke_width=6)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (w - tw) // 2
    y = int(h * 0.62)
    draw.text((x, y), title, font=font, fill=(255, 255, 255, 255),
               stroke_width=6, stroke_fill=(0, 0, 0, 160))
    img.save(out_path, "PNG")


def mux_video_audio(video_path, audio_path, out_path):
    run_ffmpeg(["ffmpeg", "-y", "-i", video_path, "-i", audio_path,
                "-c:v", "copy", "-c:a", "aac", "-shortest", out_path])


def make_static_video(image_path, audio_path, out_path):
    """주제어 없을 때 폴백: 정지 이미지 1장 + 음악"""
    vf = ("scale=1920:1080:force_original_aspect_ratio=decrease,"
          "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,format=yuv420p")
    run_ffmpeg(["ffmpeg", "-y", "-loop", "1", "-i", image_path, "-i", audio_path,
                "-vf", vf, "-c:v", "libx264", "-tune", "stillimage",
                "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p",
                "-shortest", out_path])


def filter_tracks_by_language(tracks, keyword):
    """keyword가 Mixed/빈값이면 전체 반환, 아니면 파일명에 해당 언어 태그가
    포함된 곡만 골라 반환. 매칭되는 곡이 하나도 없으면 전체로 폴백."""
    if not keyword or keyword.strip().lower() in MIXED_KEYWORDS:
        log("   (필터 없음 — Mixed, 전체 곡에서 무작위 선택)")
        return tracks

    tag = LANGUAGE_TAG_MAP.get(keyword.strip().lower(), keyword.strip())
    matched = [t for t in tracks if tag.lower() in t["name"].lower()]
    if not matched:
        log(f"   ⚠️ '{keyword}'({tag}) 태그가 포함된 곡이 없어서 전체 곡으로 진행")
        return tracks
    log(f"   '{keyword}'({tag}) 태그 매칭: {len(matched)}개")
    return matched


# ════════════════════════════════════════════════════════════
# 메인
# ════════════════════════════════════════════════════════════
def main():
    if not GOOGLE_CREDENTIALS_JSON:
        log("❌ GOOGLE_CREDENTIALS_JSON 없음")
        raise SystemExit(1)

    topic_keyword = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TOPIC_KEYWORD", "")
    language_keyword = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("LANGUAGE_KEYWORD", "")
    caption_text_input = sys.argv[3] if len(sys.argv) > 3 else os.environ.get("CAPTION_TEXT", "")

    os.makedirs(WORKDIR, exist_ok=True)
    service = get_drive_service()

    log("1/5 원곡 폴더에서 음악 목록 조회 중...")
    tracks = list_folder_files(service, MUSIC_SOURCE_FOLDER_ID, AUDIO_EXTS)
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
        make_caption_thumbnail(image_paths[0], thumbnail_out)

        log("4/5 팬줌 영상 조립 + 하단 캡션바 삽입 중...")
        visual_path = os.path.join(WORKDIR, "visual.mp4")
        build_alternating_visual(image_paths, total_sec, visual_path)
        muxed_path = os.path.join(WORKDIR, "muxed.mp4")
        mux_video_audio(visual_path, audio_path, muxed_path)
        add_lower_third_bar(muxed_path, caption_text, final_path)
    else:
        log("3/5 주제어 없음 — 썸네일창고에서 이미지 무작위 선택(폴백)...")
        thumbs = list_folder_files(service, THUMBNAIL_FOLDER_ID, IMAGE_EXTS)
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

    link, _ = upload_to_drive(service, final_path, OUTPUT_FOLDER_ID, filename)
    thumb_link, _ = upload_to_drive(service, thumbnail_out, OUTPUT_FOLDER_ID, thumb_filename)

    log("🎉 완료")
    log(f"   파일명: {filename}")
    log(f"   링크: {link}")
    log(f"   썸네일: {thumb_link}")


if __name__ == "__main__":
    main()
