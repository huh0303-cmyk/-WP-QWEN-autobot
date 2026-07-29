#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
youtube_video_pipeline.py
──────────────────────────────────────────────────────────────────
주제어 입력 → 10분 대본 생성 → 이미지 10장 프롬프트/생성 →
1~10번 이미지 전부 팬줌(Ken Burns) 동영상 변환(나레이션 길이에 맞춤) →
ElevenLabs TTS 나레이션 → 자막(SRT) 생성 → 시니어용 큰글씨 썸네일(PNG) →
썸네일+본편 결합 최종 mp4 완성 → 구글드라이브 업로드 → 이메일 통보

사용법:
    python scripts/youtube_video_pipeline.py "주제어"
    (또는 환경변수 VIDEO_TOPIC 로 전달)

필요 환경변수(Secrets):
    GEMINI_API_KEY              - 대본/이미지프롬프트/이미지(나노바나나) 생성
    ELEVENLABS_API_KEY          - TTS 나레이션
    ELEVENLABS_VOICE_ID         - (선택) 보이스 ID, 기본값 있음
    GMAIL_APP_PASSWORD          - 완료 알림 메일 발송용 (huh0303@gmail.com)
    GOOGLE_OAUTH_CLIENT_ID      - 구글드라이브 업로드용 OAuth 클라이언트 ID
    GOOGLE_OAUTH_CLIENT_SECRET  - 구글드라이브 업로드용 OAuth 클라이언트 시크릿
    GOOGLE_OAUTH_REFRESH_TOKEN  - 구글드라이브 업로드용 OAuth 리프레시 토큰
                                  (서비스 계정은 개인 드라이브에 업로드 시 저장공간
                                  할당량이 없어 실패하므로, 실제 사용자 계정 OAuth로 업로드)
    GDRIVE_FOLDER_ID            - 업로드 대상 드라이브 폴더 ID

필요 시스템 도구: ffmpeg, ffprobe (GitHub Actions ubuntu-latest에 기본 포함)
"""

import os
import sys
import re
import time
import base64
import textwrap
import subprocess

import requests

# Windows 로컬 콘솔(cp949 등)에서 이모지/한글 출력 시 죽지 않도록 UTF-8 강제
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ════════════════════════════════════════════════════════════
# 설정
# ════════════════════════════════════════════════════════════
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_TEXT_MODEL = "gemini-2.5-flash"
GEMINI_IMAGE_MODELS = ["gemini-2.5-flash-image", "gemini-2.5-flash-image-preview"]  # 나노바나나

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID") or "21m00Tcm4TlvDq8ikWAM"
ELEVENLABS_MODEL = "eleven_multilingual_v2"

GMAIL_USER = "huh0303@gmail.com"
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
GOOGLE_OAUTH_REFRESH_TOKEN = os.environ.get("GOOGLE_OAUTH_REFRESH_TOKEN", "")
GDRIVE_FOLDER_ID = os.environ.get("GDRIVE_FOLDER_ID", "")

WORKDIR = "yt_output"
NUM_IMAGES = 10
VIDEO_W, VIDEO_H = 1920, 1080
FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/nanumgothic/NanumGothic-Bold.ttf"
FONT_PATH = "/tmp/_yt_nanumgothic_bold.ttf"


def log(msg):
    print(msg, flush=True)


# ════════════════════════════════════════════════════════════
# 0) 공통 유틸
# ════════════════════════════════════════════════════════════
def ensure_font():
    if not os.path.exists(FONT_PATH):
        r = requests.get(FONT_URL, timeout=30)
        r.raise_for_status()
        with open(FONT_PATH, "wb") as f:
            f.write(r.content)
    return FONT_PATH


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
# 1) 대본 생성 (Gemini)
# ════════════════════════════════════════════════════════════
def gemini_generate_text(prompt, temperature=0.9):
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{GEMINI_TEXT_MODEL}:generateContent?key={GEMINI_API_KEY}")
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature}}
    r = requests.post(url, json=body, timeout=60)
    r.raise_for_status()
    data = r.json()
    candidates = data.get("candidates") or []
    if not candidates or not candidates[0].get("content", {}).get("parts"):
        reason = candidates[0].get("finishReason") if candidates else data.get("promptFeedback")
        raise RuntimeError(f"Gemini 응답에 콘텐츠가 없습니다 (finishReason/피드백: {reason})")
    return candidates[0]["content"]["parts"][0]["text"]


def generate_script(topic, style_reference=""):
    style_block = ""
    if style_reference.strip():
        style_block = f"""
아래는 참고할 레퍼런스 영상의 "포맷/스타일 패턴 분석" 요약입니다.
내용을 그대로 베끼지 말고, 이 패턴(훅 방식/구성 순서/톤)만 참고해서
완전히 새로운 오리지널 대본을 쓰세요:
{style_reference[:4000]}
"""
    prompt = f"""당신은 유튜브 나레이션 대본 작가입니다.
주제: "{topic}"
{style_block}
약 10분 분량(한국어 기준 약 1500~1700자, 자연스러운 구어체)의
유튜브 방송용 나레이션 대본을 작성하세요.

규칙:
- 도입(훅) - 본론 - 마무리 구조로 정확히 10개 문단
- 각 문단 앞에 "###1###" ~ "###10###" 마커를 붙이고, 마커 외 다른 텍스트는 넣지 마세요
- 각 문단은 15~20초 분량(문장 3~5개)으로 균등하게
- 과장된 클릭베이트 표현, 가짜 자격/전문가 사칭 금지
"""
    text = gemini_generate_text(prompt)
    segments = []
    for m in re.finditer(r'###(\d+)###\s*(.*?)(?=###\d+###|$)', text, re.DOTALL):
        body = m.group(2).strip()
        if body:
            segments.append(body)

    if len(segments) < NUM_IMAGES:
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
        segments = paragraphs

    # 정확히 10개로 맞추기 (모자라면 마지막 문단 재분할, 넘치면 자르기)
    while len(segments) < NUM_IMAGES and any(len(s) > 20 for s in segments):
        longest_idx = max(range(len(segments)), key=lambda i: len(segments[i]))
        s = segments[longest_idx]
        mid = len(s) // 2
        split_at = s.rfind(".", 0, mid)
        split_at = split_at + 1 if split_at != -1 else mid
        left, right = s[:split_at].strip(), s[split_at:].strip()
        if left and right:
            segments[longest_idx:longest_idx + 1] = [left, right]
        else:
            break
    # 그래도 모자라면(응답이 지나치게 짧았던 경우) 주제 기반 채움 문구로 패딩
    while len(segments) < NUM_IMAGES:
        segments.append(f"{topic}에 대해 조금 더 살펴보겠습니다.")
    segments = segments[:NUM_IMAGES]

    return segments, text


# ════════════════════════════════════════════════════════════
# 2) 이미지 프롬프트 생성 (Gemini)
# ════════════════════════════════════════════════════════════
IMAGE_STYLE_SUFFIX = (
    ", 16:9 widescreen landscape framing, horizontal composition filling the "
    "entire frame edge to edge, candid real-life photo taken on a good camera, "
    "natural lighting, realistic texture and detail, no illustration or 3D render "
    "look, no text, no watermark, no logos"
)


def generate_image_prompts(topic, segments, style_reference=""):
    joined = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(segments))
    style_block = ""
    if style_reference.strip():
        style_block = f"""
참고할 레퍼런스 영상의 영상미 스타일 분석(구도/색감/편집 톤)도 반영하세요
(내용 복제 아님, 스타일만 참고):
{style_reference[:2000]}
"""
    prompt = f"""다음은 "{topic}"에 대한 유튜브 대본 10개 문단입니다.
{joined}
{style_block}
각 문단에 어울리는 유튜브 영상용 이미지 생성 프롬프트를 영어로 10개 작성하세요.
- 반드시 16:9 가로(와이드스크린) 구도로 명시할 것 — 인물/사물이 정중앙에 작게 몰리지 않고
  프레임 전체를 채우는 가로 구도
- 실제 카메라로 찍은 듯한 사실적인 사진 스타일(생성형 티가 나는 매끈한 일러스트/렌더 느낌 금지),
  자극적이지 않고 안전한 이미지
- 각 줄은 "1. ..." 형식의 번호로 시작
- 텍스트/워터마크/로고 없이, 유튜브 콘텐츠 정책에 위배되지 않는 이미지
"""
    text = gemini_generate_text(prompt)
    prompts = [m.group(1).strip() + IMAGE_STYLE_SUFFIX for m in
               re.finditer(r'^\s*\d+[\.\)]\s*(.+)$', text, re.MULTILINE)]
    while len(prompts) < NUM_IMAGES:
        prompts.append(f"{topic}, photorealistic photo, safe for work" + IMAGE_STYLE_SUFFIX)
    return prompts[:NUM_IMAGES]


# ════════════════════════════════════════════════════════════
# 3) 이미지 생성 (Gemini 2.5 Flash Image / 나노바나나)
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


def make_placeholder_image(out_path, text=""):
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (VIDEO_W, VIDEO_H), (30, 30, 34))
    if text:
        draw = ImageDraw.Draw(img)
        font = _get_font(48)
        draw.text((60, VIDEO_H // 2 - 24), text[:40], font=font, fill="white")
    img.save(out_path, "PNG")


# ════════════════════════════════════════════════════════════
# 4) ElevenLabs TTS
# ════════════════════════════════════════════════════════════
def elevenlabs_tts(text, out_path):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {"xi-api-key": ELEVENLABS_API_KEY,
               "Content-Type": "application/json", "Accept": "audio/mpeg"}
    body = {"text": text, "model_id": ELEVENLABS_MODEL,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
    r = requests.post(url, headers=headers, json=body, timeout=90)
    r.raise_for_status()
    with open(out_path, "wb") as f:
        f.write(r.content)


# ════════════════════════════════════════════════════════════
# 5) 이미지 → 동영상 (팬줌 / 정지컷)
# ════════════════════════════════════════════════════════════
def make_kenburns_clip(image_path, out_path, duration, fps=25):
    frames = max(int(duration * fps), 1)
    vf = (f"scale=2560:-1,zoompan=z='min(zoom+0.0012,1.25)':d={frames}:"
          f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={VIDEO_W}x{VIDEO_H}:fps={fps},"
          f"format=yuv420p")
    run_ffmpeg(["ffmpeg", "-y", "-loop", "1", "-i", image_path, "-vf", vf,
                "-r", str(fps), "-t", str(duration), "-c:v", "libx264",
                "-pix_fmt", "yuv420p", out_path])


def make_still_clip_with_silence(image_path, out_path, duration, fps=25):
    vf = (f"scale={VIDEO_W}:{VIDEO_H}:force_original_aspect_ratio=decrease,"
          f"pad={VIDEO_W}:{VIDEO_H}:(ow-iw)/2:(oh-ih)/2,format=yuv420p")
    run_ffmpeg(["ffmpeg", "-y", "-loop", "1", "-i", image_path,
                "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-vf", vf, "-r", str(fps), "-t", str(duration),
                "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", "-shortest", out_path])


def concat_stream_copy(clip_paths, out_path):
    list_file = os.path.join(WORKDIR, "concat_list.txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for p in clip_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")
    run_ffmpeg(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
                "-c", "copy", out_path])


def concat_reencode(inputs, out_path):
    cmd = ["ffmpeg", "-y"]
    for p in inputs:
        cmd += ["-i", p]
    n = len(inputs)
    filter_complex = "".join(f"[{i}:v:0][{i}:a:0]" for i in range(n)) + f"concat=n={n}:v=1:a=1[outv][outa]"
    cmd += ["-filter_complex", filter_complex, "-map", "[outv]", "-map", "[outa]",
            "-c:v", "libx264", "-c:a", "aac", out_path]
    run_ffmpeg(cmd)


def concat_audio_reencode(audio_paths, out_path):
    cmd = ["ffmpeg", "-y"]
    for p in audio_paths:
        cmd += ["-i", p]
    n = len(audio_paths)
    filter_complex = "".join(f"[{i}:a:0]" for i in range(n)) + f"concat=n={n}:v=0:a=1[outa]"
    cmd += ["-filter_complex", filter_complex, "-map", "[outa]", out_path]
    run_ffmpeg(cmd)


def mux_video_audio(video_path, audio_path, out_path):
    run_ffmpeg(["ffmpeg", "-y", "-i", video_path, "-i", audio_path,
                "-c:v", "copy", "-c:a", "aac", "-shortest", out_path])


# ════════════════════════════════════════════════════════════
# 6) 자막 (SRT) 생성 + 굽기
# ════════════════════════════════════════════════════════════
def _srt_time(seconds):
    ms_total = int(round(seconds * 1000))
    h, rem = divmod(ms_total, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_srt(segments, durations, out_path):
    lines = []
    t = 0.0
    for i, (text, dur) in enumerate(zip(segments, durations), 1):
        start, end = t, t + dur
        wrapped = "\n".join(textwrap.wrap(text, width=38)[:2]) or text[:76]
        lines.append(f"{i}\n{_srt_time(start)} --> {_srt_time(end)}\n{wrapped}\n")
        t = end
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def burn_subtitles(video_path, srt_path, out_path):
    srt_escaped = os.path.abspath(srt_path).replace("\\", "/").replace(":", "\\:")
    style = "FontName=NanumGothic,FontSize=26,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=2"
    run_ffmpeg(["ffmpeg", "-y", "-i", video_path,
                "-vf", f"subtitles='{srt_escaped}':force_style='{style}'",
                "-c:a", "copy", out_path])


# ════════════════════════════════════════════════════════════
# 7) 썸네일 (시니어용 큰 글씨, PNG)
# ════════════════════════════════════════════════════════════
_FONT_CACHE = {}


def _get_font(size):
    if size in _FONT_CACHE:
        return _FONT_CACHE[size]
    from PIL import ImageFont
    ensure_font()
    font = ImageFont.truetype(FONT_PATH, size)
    _FONT_CACHE[size] = font
    return font


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


def make_thumbnail(image_path, title, out_path, w=1280, h=720):
    from PIL import Image, ImageDraw

    img = _resize_cover(Image.open(image_path).convert("RGB"), w, h)
    lines = textwrap.wrap(title, width=10)[:3]
    font = _get_font(88)

    bar_h = 110 * len(lines) + 50
    overlay = Image.new("RGBA", (w, bar_h), (0, 0, 0, 165))
    crop = img.crop((0, h - bar_h, w, h)).convert("RGBA")
    blended = Image.alpha_composite(crop, overlay).convert("RGB")
    img.paste(blended, (0, h - bar_h))

    draw = ImageDraw.Draw(img)
    y = h - bar_h + 25
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font, stroke_width=8)
        tw = bbox[2] - bbox[0]
        x = (w - tw) // 2
        draw.text((x, y), line, font=font, fill="white", stroke_width=8, stroke_fill="black")
        y += 105

    img.save(out_path, "PNG")


# ════════════════════════════════════════════════════════════
# 8) 구글드라이브 업로드
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


def upload_to_drive(file_path, folder_id):
    """큰 파일도 안정적으로 올라가도록 청크 단위 업로드 + 재시도 처리.
    (파일 전체를 한 번에 보내면 도중 짧은 네트워크 끊김에도 통째로 실패함)"""
    import time
    from googleapiclient.http import MediaFileUpload

    service = get_drive_service()
    metadata = {"name": os.path.basename(file_path), "parents": [folder_id]}
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
# 9) 이메일 알림
# ════════════════════════════════════════════════════════════
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


# ════════════════════════════════════════════════════════════
# 메인 파이프라인
# ════════════════════════════════════════════════════════════
def load_style_reference():
    """STYLE_REFERENCE 환경변수(텍스트 그대로) 우선, 없으면 레퍼런스 분석기가
    남긴 youtube_reference_style_report.md 파일이 있으면 그걸 사용."""
    text = os.environ.get("STYLE_REFERENCE", "")
    if text.strip():
        return text
    default_path = "youtube_reference_style_report.md"
    if os.path.exists(default_path):
        with open(default_path, encoding="utf-8") as f:
            return f.read()
    return ""


def main():
    topic = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("VIDEO_TOPIC", "")
    if not topic:
        log("❌ 주제어가 없습니다. (인자 1개 또는 VIDEO_TOPIC 환경변수)")
        sys.exit(1)

    style_reference = load_style_reference()

    required = {"GEMINI_API_KEY": GEMINI_API_KEY, "ELEVENLABS_API_KEY": ELEVENLABS_API_KEY,
                "GMAIL_APP_PASSWORD": GMAIL_APP_PASSWORD,
                "GOOGLE_OAUTH_CLIENT_ID": GOOGLE_OAUTH_CLIENT_ID,
                "GOOGLE_OAUTH_CLIENT_SECRET": GOOGLE_OAUTH_CLIENT_SECRET,
                "GOOGLE_OAUTH_REFRESH_TOKEN": GOOGLE_OAUTH_REFRESH_TOKEN,
                "GDRIVE_FOLDER_ID": GDRIVE_FOLDER_ID}
    missing = [k for k, v in required.items() if not v]
    if missing:
        log(f"❌ 환경변수 누락: {missing}")
        sys.exit(1)

    os.makedirs(WORKDIR, exist_ok=True)
    ensure_font()
    log(f"🎬 주제: {topic}")
    if style_reference.strip():
        log("   📎 레퍼런스 스타일 참고자료 적용됨")

    log("1/8 대본 생성 중...")
    segments, full_script = generate_script(topic, style_reference)
    log(f"   -> {len(segments)}개 문단 생성 완료")

    log("2/8 이미지 프롬프트 생성 중...")
    img_prompts = generate_image_prompts(topic, segments, style_reference)
    for i, p in enumerate(img_prompts, 1):
        log(f"   [{i:02d}] {p}")

    log("3/8 이미지 10장 생성 중 (나노바나나)...")
    image_paths = []
    for i, p in enumerate(img_prompts, 1):
        path = os.path.join(WORKDIR, f"image_{i:02d}.png")
        ok = False
        for attempt in range(3):
            try:
                if gemini_generate_image(p, path):
                    ok = True
                    break
            except Exception as e:
                log(f"   ⚠️ image_{i:02d} 시도{attempt + 1} 실패: {e}")
            time.sleep(2)
        if not ok:
            make_placeholder_image(path, text=f"{topic} #{i}")
            log(f"   ⚠️ image_{i:02d} 생성 실패 → 플레이스홀더 대체")
        else:
            log(f"   ✅ image_{i:02d}.png")
        image_paths.append(path)

    log("4/8 나레이션(ElevenLabs TTS) 생성 중...")
    audio_paths, durations = [], []
    for i, seg in enumerate(segments, 1):
        apath = os.path.join(WORKDIR, f"seg_{i:02d}.mp3")
        elevenlabs_tts(seg, apath)
        dur = get_duration(apath)
        audio_paths.append(apath)
        durations.append(dur)
        log(f"   ✅ seg_{i:02d}.mp3 ({dur:.1f}초)")

    log("5/8 이미지 → 동영상 변환 중 (1~10번 전부 팬줌, 나레이션/자막 길이에 맞춤)...")
    clip_paths = []
    for i, (img, dur) in enumerate(zip(image_paths, durations), 1):
        cpath = os.path.join(WORKDIR, f"clip_{i:02d}.mp4")
        make_kenburns_clip(img, cpath, duration=dur)
        clip_paths.append(cpath)
        log(f"   ✅ clip_{i:02d}.mp4")

    log("6/8 영상+음성 결합 및 자막 삽입 중...")
    video_only = os.path.join(WORKDIR, "video_only.mp4")
    concat_stream_copy(clip_paths, video_only)

    full_audio = os.path.join(WORKDIR, "narration_full.mp3")
    concat_audio_reencode(audio_paths, full_audio)

    muxed = os.path.join(WORKDIR, "muxed.mp4")
    mux_video_audio(video_only, full_audio, muxed)

    srt_path = os.path.join(WORKDIR, "subtitles.srt")
    build_srt(segments, durations, srt_path)
    subtitled = os.path.join(WORKDIR, "with_subs.mp4")
    burn_subtitles(muxed, srt_path, subtitled)

    log("7/8 썸네일 생성 및 최종 mp4 결합 중...")
    thumb_title = topic if len(topic) <= 24 else topic[:24]
    thumb_path = os.path.join(WORKDIR, "thumbnail.png")
    make_thumbnail(image_paths[0], thumb_title, thumb_path)

    intro_clip = os.path.join(WORKDIR, "thumb_intro.mp4")
    make_still_clip_with_silence(thumb_path, intro_clip, duration=2.5)

    final_video = os.path.join(WORKDIR, "final.mp4")
    concat_reencode([intro_clip, subtitled], final_video)
    log(f"   ✅ 최종 영상: {final_video}")

    log("8/8 구글드라이브 업로드 + 이메일 발송 중...")
    video_link, _ = upload_to_drive(final_video, GDRIVE_FOLDER_ID)
    thumb_link, _ = upload_to_drive(thumb_path, GDRIVE_FOLDER_ID)

    send_email(
        f"✅ [자동생성] 유튜브 영상 완성 - {topic}",
        f"주제: {topic}\n\n"
        f"최종 영상(Drive): {video_link}\n"
        f"썸네일(Drive): {thumb_link}\n\n"
        f"── 전체 대본 ──\n{full_script}"
    )

    log("🎉 전체 파이프라인 완료")
    log(f"   영상: {video_link}")
    log(f"   썸네일: {thumb_link}")


if __name__ == "__main__":
    main()
