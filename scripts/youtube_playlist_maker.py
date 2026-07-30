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
# 썸네일 "Playlist" 타이틀용 우아한 세리프 폰트 (한글 캡션바는 나눔고딕 유지)
TITLE_FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf"
TITLE_FONT_PATH = "/tmp/_playlist_playfair.ttf"


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
            fields="nextPageToken, files(id, name, mimeType)",
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
    prompt = (f"'{topic}' 느낌의 플레이리스트 영상 캡션 한 줄을 써줘. "
              f"조건: 광고 카피처럼 매끈하게 쓰지 말고, 그냥 이 영상을 만든 사람이 "
              f"직접 툭 던지듯 적은 것처럼 자연스럽고 담백하게. 완벽한 문장보다 구어체 느낌으로. "
              f"이모지는 넣어도 1개까지만, 20자 이내. 따옴표나 설명 없이 문구만 출력해줘.")
    text = gemini_generate_text(prompt, temperature=1.0)
    text = text.strip().strip('"').strip("'")
    return text or f"{topic} 들으면서 잠깐 쉬어가기"


THUMBNAIL_BRAND_LABEL = os.environ.get("THUMBNAIL_BRAND_LABEL", "Playlist")


def build_ai_images(topic, workdir):
    topic = (topic or "").strip() or "tropical beachside vibe, aesthetic lifestyle"
    style = (
        "professional travel-magazine photography, ultra sharp, cinematic wide 16:9 "
        "composition, natural light, vivid but realistic color grading, no text, "
        "no watermark, no illustration or 3D-render look"
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
            if dur < 1.0:
                raise ValueError(f"재생시간 {dur:.2f}초 — 오디오 파일이 아닌 것으로 판단")
        except Exception as e:
            log(f"   ⚠️ 스킵({meta['name']}): {e}")
            if os.path.exists(local_path):
                os.remove(local_path)
            continue

        if accumulated >= TARGET_MIN_SEC and accumulated + dur > TARGET_MAX_SEC:
            # 목표 구간 안에 이미 들어와 있고 이 곡을 더하면 넘침 -> 나머지는
            # 안 맞을 때마다 계속 찾아 헤매지 않고 여기서 바로 종료 (다운로드 낭비 방지)
            os.remove(local_path)
            log(f"   (목표 구간 도달 — 나머지 트랙 스캔 중단)")
            break

        selected_paths.append(local_path)
        accumulated += dur
        log(f"   ✅ 추가: {meta['name']} ({dur/60:.1f}분) — 누적 {accumulated/60:.1f}분")

        if accumulated >= TARGET_MAX_SEC:
            break

    if accumulated < TARGET_MIN_SEC:
        log(f"   ⚠️ 보유한 음원을 다 써도 {accumulated/60:.1f}분 (목표 60분 미만)")

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
        f"[2:a]showwaves=s={wave_w}x{wave_h}:mode=cline:colors=white@0.8:rate=25,format=rgba[wave];"
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


def _dotted_hline(draw, cx, y, total_w, dash_w=6, gap=8, fill=(255, 255, 255, 220)):
    x = cx - total_w // 2
    end = cx + total_w // 2
    while x < end:
        draw.line([(x, y), (min(x + dash_w, end), y)], fill=fill, width=2)
        x += dash_w + gap


def make_caption_thumbnail(image_path, out_path, topic="", w=1280, h=720):
    """여행 잡지 표지 스타일 썸네일: 상단 좌우에 작은 브랜드 라벨/볼륨 표기,
    화면 대부분을 채우는 초대형 세리프 주제어 타이틀, 그 아래 얇은 점선 구분선.
    배경 사진만 AI 생성이고 나머지는 전부 PIL로 직접 그려서 무료로 자동 생성된다."""
    from PIL import Image, ImageDraw, ImageFont
    from datetime import datetime as _dt

    title_font_path = ensure_title_font()
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
    max_w = int(w * 0.92)
    size = 220
    while size > 40:
        font = _font(title_font_path, size, 500)
        bbox = draw.textbbox((0, 0), title, font=font)
        if bbox[2] - bbox[0] <= max_w:
            break
        size -= 6
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    title_y = (h - th) // 2 - int(h * 0.03)
    draw.text(((w - tw) // 2, title_y - bbox[1]), title, font=font,
               fill=(255, 255, 255, 255))

    # 타이틀 바로 아래: 얇은 점선 구분선
    _dotted_hline(draw, w // 2, title_y + th + int(h * 0.05), int(w * 0.5))

    img.convert("RGB").save(out_path, "PNG")


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
    missing = [k for k, v in {
        "GOOGLE_OAUTH_CLIENT_ID": GOOGLE_OAUTH_CLIENT_ID,
        "GOOGLE_OAUTH_CLIENT_SECRET": GOOGLE_OAUTH_CLIENT_SECRET,
        "GOOGLE_OAUTH_REFRESH_TOKEN": GOOGLE_OAUTH_REFRESH_TOKEN,
    }.items() if not v]
    if missing:
        log(f"❌ 환경변수 누락: {missing}")
        raise SystemExit(1)

    topic_keyword = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TOPIC_KEYWORD", "")
    language_keyword = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("LANGUAGE_KEYWORD", "")
    caption_text_input = sys.argv[3] if len(sys.argv) > 3 else os.environ.get("CAPTION_TEXT", "")

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
        make_caption_thumbnail(image_paths[0], thumbnail_out, topic=topic_keyword)

        log("4/5 팬줌 영상 조립 + 하단 캡션바 삽입 중...")
        visual_path = os.path.join(WORKDIR, "visual.mp4")
        build_alternating_visual(image_paths, total_sec, visual_path)
        muxed_path = os.path.join(WORKDIR, "muxed.mp4")
        add_spinning_vinyl_and_waveform(visual_path, audio_path, muxed_path)
        add_lower_third_bar(muxed_path, caption_text, final_path)
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

    link, _ = upload_to_drive(service, final_path, OUTPUT_FOLDER_ID, filename)
    thumb_link, _ = upload_to_drive(service, thumbnail_out, OUTPUT_FOLDER_ID, thumb_filename)

    log("🎉 완료")
    log(f"   파일명: {filename}")
    log(f"   링크: {link}")
    log(f"   썸네일: {thumb_link}")


if __name__ == "__main__":
    main()
