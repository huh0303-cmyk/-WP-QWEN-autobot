#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
topik_quiz_shorts.py
─────────────────────────────────────────────────────────────
TOPIK(한국어능력시험) 초급 단어 퀴즈 쇼츠(9:16, 세로, ~60초) 자동 생성기.
sis-korea.com에서 받은 샘플 숏폼(토픽 단어(초급) 카드 + 3지선다 +
정답 공개 + 한국어 여성 내레이션 + 딩 효과음)과 동일한 포맷을 그대로
자동화한다.

카테고리(동물/음식/직업/색깔 등)를 주면 Gemini가 단어 N개 + 오답 2개씩을
뽑아주고, 각 단어에 맞는 플랫 아이콘 스타일 이미지를 생성한 뒤,
"질문 화면 → (딩) → 정답 공개 화면" 카드를 이어붙여 최종 세로 영상을 만든다.

사용법:
    python scripts/topik_quiz_shorts.py "카테고리" [문항수]
    (또는 TOPIC_CATEGORY / NUM_ITEMS 환경변수)
    카테고리를 비우면 Gemini가 무작위로 초급 어휘 카테고리를 고른다.

필요 환경변수(Secrets):
    GEMINI_API_KEY              - 단어/문항 생성 + 이미지 생성(나노바나나)
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

import requests

# Windows 로컬 콘솔(cp949 등)에서 이모지/한글 출력 시 죽지 않도록 UTF-8 강제
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

BRAND_TEXT = os.environ.get("QUIZ_BRAND_TEXT", "서울국제대학교SIS-TOPIK센터")

# 정답 단어(한국어)는 어떤 버전이든 그대로 두고, 질문 문구/헤더만 그 언어로
# 번역해서 "한국어를 배우는 그 나라 학습자"용 버전을 만든다
LANG_CONFIG = {
    "ko": {"name": "한국어", "header": "토픽 단어 (초급)"},
    "ja": {"name": "日本語", "header": "TOPIK単語（初級）"},
    "en": {"name": "English", "header": "TOPIK Words (Beginner)"},
    "es": {"name": "Español", "header": "Palabras TOPIK (Básico)"},
    "zh": {"name": "中文", "header": "TOPIK生词（初级）"},
}

WORKDIR = "topik_quiz_output"
W, H = 1080, 1920

import tempfile as _tempfile

FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/nanumgothic/NanumGothic-Bold.ttf"
FONT_PATH = os.path.join(_tempfile.gettempdir(), "_topik_nanumgothic_bold.ttf")
# 나눔고딕엔 한자 글리프가 없어서 일본어 헤더("TOPIK単語（初級）")용으로 별도 필요
JP_FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/notosansjp/NotoSansJP%5Bwght%5D.ttf"
JP_FONT_PATH = os.path.join(_tempfile.gettempdir(), "_topik_notosansjp.ttf")

PINK_HEADER = (247, 168, 200, 255)
PINK_HIGHLIGHT = (249, 190, 212, 255)
BG_COLOR = (252, 219, 213, 255)
BLACK = (20, 20, 20, 255)


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


def ensure_jp_font():
    if not os.path.exists(JP_FONT_PATH):
        try:
            r = requests.get(JP_FONT_URL, timeout=30)
            r.raise_for_status()
            with open(JP_FONT_PATH, "wb") as f:
                f.write(r.content)
        except Exception:
            return ensure_font()
    return JP_FONT_PATH


# ════════════════════════════════════════════════════════════
# Gemini: 문항 생성 + 이미지 생성
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


def generate_quiz_items(category, n, target_lang="ko"):
    """Gemini에게 TOPIK 초급 수준 단어 n개(카테고리 안에서) + 오답 2개씩을
    JSON으로 받아온다. 카테고리가 비어있으면 Gemini가 무작위로 고른다.
    target_lang이 ko가 아니면, 정답/오답(한국어 단어)은 그대로 두고 question
    (질문 문구)만 그 언어로 번역해서 "그 나라 학습자가 보는 한국어 학습 퀴즈"
    버전을 만든다."""
    cat_instr = (f"카테고리는 '{category}'로 고정." if category.strip()
                 else "카테고리는 동물/음식/채소/직업/색깔/가전제품/교통수단 중 하나를 무작위로 골라라.")
    lang_name = LANG_CONFIG.get(target_lang, LANG_CONFIG["ko"])["name"]
    question_lang_instr = (
        "question은 한국어로." if target_lang == "ko"
        else f"question은 {lang_name}로 번역해서 써줘(그 나라 한국어 학습자가 읽을 질문이므로). "
             f"단, correct/wrong1/wrong2는 가르치려는 한국어 단어이므로 절대 번역하지 말고 한국어 그대로."
    )
    prompt = f"""한국어능력시험(TOPIK) 초급 학습자를 위한 어휘 퀴즈 문항을 {n}개 만들어줘.
{cat_instr} 문항끼리는 서로 다른 단어여야 한다.

각 문항은 다음 형식의 JSON 객체로, 배열 하나에 담아서 응답해줘 (설명 없이 JSON만):
[
  {{
    "question": "무슨 동물이에요?",
    "correct": "독수리",
    "wrong1": "펭귄",
    "wrong2": "캥거루",
    "image_prompt_en": "a bald eagle with spread wings"
  }},
  ...
]

조건:
- correct/wrong1/wrong2는 전부 초급 수준의 쉬운 한국어 명사, 같은 카테고리 안에서 헷갈릴 만한 것들로.
- question은 "무슨 동물이에요?", "이게 뭐예요?", "무슨 직업이에요?" 같은 짧고 쉬운 초급 문형. {question_lang_instr}
- image_prompt_en은 correct 단어를 그림으로 표현할 영어 설명(간단한 명사구, 배경 묘사 없이 그 자체만).
"""
    text = gemini_generate_text(prompt, temperature=1.0)
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    items = json.loads(text.strip())
    random.shuffle(items)
    for it in items:
        it["options"] = [it["correct"], it["wrong1"], it["wrong2"]]
        random.shuffle(it["options"])
        it["correct_index"] = it["options"].index(it["correct"])
    return items


def generate_social_copy(category, items, target_lang="ko"):
    """플랫폼(유튜브/틱톡/인스타/페이스북/쓰레드)에 올릴 제목·설명·해시태그를
    Gemini로 생성한다. 사람이 직접 쓴 것처럼 자연스러운 톤을 요구하고,
    상투적인 AI 말투("Unlock your potential!", 과도한 이모지 나열, 뻔한
    질문형 후킹 등)는 피하도록 명시한다."""
    lang_name = LANG_CONFIG.get(target_lang, LANG_CONFIG["ko"])["name"]
    words = ", ".join(it["correct"] for it in items)
    prompt = f"""너는 한국어 학습 콘텐츠를 운영하는 SNS 담당자다. 아래 단어 퀴즈 쇼츠 영상을
{lang_name}권 시청자에게 올릴 소셜 게시글을 써줘. 다루는 단어: {words} (카테고리: {category or '초급 어휘'}).

조건:
- 문체는 {lang_name}로, 실제 사람이 캐주얼하게 쓴 것처럼. AI가 쓴 티가 나는 상투적 표현
  (예: "Unlock your potential", "Ready to level up?", 이모지 남발, 뻔한 감탄사 나열) 금지.
- 과장 광고 문구, 클릭베이트성 허위 약속 금지.
- youtube_title: 60자 이내
- youtube_description: 2~3문장, 자연스럽게
- short_caption: 틱톡/인스타/페이스북/쓰레드에 공통으로 쓸 짧은 캡션 (2~3문장, 100자 내외)
- hashtags: 5~8개, # 없이 단어만 배열로 (플랫폼에서 조합)

JSON만 응답(설명 없이):
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
def _rounded_rect(draw, box, radius, **kwargs):
    draw.rounded_rectangle(box, radius=radius, **kwargs)


def draw_quiz_card(icon_path, item, idx, total, reveal, out_path, header_text="토픽 단어 (초급)"):
    """reveal=False: 질문 화면(번호 배지만 표시) / reveal=True: 정답 하이라이트 화면"""
    from PIL import Image, ImageDraw, ImageFont

    font_path = ensure_font()

    def F(size):
        return ImageFont.truetype(font_path, size)

    img = Image.new("RGBA", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img, "RGBA")

    # 상단 핑크 헤더 — 언어별로 길이가 달라서 900px 폭에 맞게 폰트 크기 자동 축소.
    # 나눔고딕엔 한자 글리프가 없어서, 헤더에 한자/가나가 섞이면 일본어 폰트로 대체
    _rounded_rect(draw, [90, 60, 990, 270], 45, fill=PINK_HEADER)
    title = header_text
    has_jp = any('぀' <= c <= 'ヿ' or '一' <= c <= '鿿' for c in title)
    header_font_path = ensure_jp_font() if has_jp else font_path
    size = 72
    while size > 30:
        tf = ImageFont.truetype(header_font_path, size)
        tb = draw.textbbox((0, 0), title, font=tf)
        if tb[2] - tb[0] <= 860:
            break
        size -= 4
    draw.text(((W - (tb[2] - tb[0])) // 2, 165 - (tb[1] + tb[3]) // 2), title,
               font=tf, fill=BLACK)

    # 구분선
    draw.line([(90, 305), (990, 305)], fill=BLACK, width=4)

    # 이미지 카드
    card_box = [110, 360, 970, 840]
    _rounded_rect(draw, card_box, 40, fill=(255, 255, 255, 255),
                  outline=BLACK, width=5)
    icon = Image.open(icon_path).convert("RGBA")
    max_w, max_h = 700, 400
    scale = min(max_w / icon.width, max_h / icon.height)
    icon = icon.resize((int(icon.width * scale), int(icon.height * scale)), Image.LANCZOS)
    icon_x = (card_box[0] + card_box[2] - icon.width) // 2
    icon_y = (card_box[1] + card_box[3] - icon.height) // 2
    img.alpha_composite(icon, (icon_x, icon_y))

    if not reveal:
        cx, cy, r = 905, 405, 40
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 255),
                     outline=BLACK, width=4)
        num = str(idx + 1)
        nf = F(44)
        nb = draw.textbbox((0, 0), num, font=nf)
        draw.text((cx - (nb[2] - nb[0]) // 2, cy - (nb[1] + nb[3]) // 2), num,
                   font=nf, fill=BLACK)

    # 질문 문구 — 여기도 한자/가나가 섞이면(일본어 질문) 일본어 폰트로 대체
    question = item["question"]
    q_has_jp = any('぀' <= c <= 'ヿ' or '一' <= c <= '鿿' for c in question)
    qf = ImageFont.truetype(ensure_jp_font(), 58) if q_has_jp else F(58)
    qb = draw.textbbox((0, 0), question, font=qf)
    draw.text(((W - (qb[2] - qb[0])) // 2, 895 - (qb[1] + qb[3]) // 2),
               question, font=qf, fill=BLACK)

    # 보기 A/B/C
    labels = ["A", "B", "C"]
    opt_font = F(52)
    label_font = F(38)
    top = 1010
    pill_h, gap = 140, 45
    for i, opt in enumerate(item["options"]):
        y0 = top + i * (pill_h + gap)
        y1 = y0 + pill_h
        is_correct = reveal and i == item["correct_index"]
        fill = PINK_HIGHLIGHT if is_correct else (255, 255, 255, 255)
        _rounded_rect(draw, [140, y0, 940, y1], 60, fill=fill, outline=BLACK, width=4)
        lcx, lcy, lr = 245, (y0 + y1) // 2, 42
        draw.ellipse([lcx - lr, lcy - lr, lcx + lr, lcy + lr], fill=(255, 255, 255, 255),
                     outline=BLACK, width=3)
        lb = draw.textbbox((0, 0), labels[i], font=label_font)
        draw.text((lcx - (lb[2] - lb[0]) // 2, lcy - (lb[1] + lb[3]) // 2), labels[i],
                   font=label_font, fill=BLACK)
        ob = draw.textbbox((0, 0), opt, font=opt_font)
        draw.text(((W - (ob[2] - ob[0])) // 2 + 40, lcy - (ob[1] + ob[3]) // 2), opt,
                   font=opt_font, fill=BLACK)

    # 하단 브랜드
    bf = F(36)
    bb = draw.textbbox((0, 0), BRAND_TEXT, font=bf)
    draw.text(((W - (bb[2] - bb[0])) // 2, 1840), BRAND_TEXT, font=bf, fill=BLACK)

    img.convert("RGB").save(out_path, "PNG")


# ════════════════════════════════════════════════════════════
# 오디오: TTS + 딩 효과음
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


def make_ding(out_path):
    run_ffmpeg(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=1046:duration=0.35",
                "-af", "afade=t=out:st=0.15:d=0.2,volume=2.0", "-c:a", "aac", out_path])


# ════════════════════════════════════════════════════════════
# 문항 하나 → 클립(질문 정지컷+나레이션 → 딩 → 정답공개 정지컷+나레이션)
# ════════════════════════════════════════════════════════════
def still_clip(image_path, audio_path, out_path):
    dur = get_duration(audio_path)
    run_ffmpeg(["ffmpeg", "-y", "-loop", "1", "-i", image_path, "-i", audio_path,
                "-t", str(dur), "-vf", f"scale={W}:{H},format=yuv420p",
                "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p",
                "-shortest", out_path])
    return dur


def build_item_clip(item, idx, total, workdir, header_text="토픽 단어 (초급)"):
    icon_path = os.path.join(workdir, f"icon_{idx}.png")
    ok = False
    if GEMINI_API_KEY:
        prompt = (f"A simple flat vector clip-art illustration of "
                  f"{item['image_prompt_en']}, isolated on plain white background, "
                  f"cute minimalist icon style, bold clean outlines, bright flat colors, "
                  f"no text, no watermark, no shadow, no gradient")
        for _ in range(3):
            if gemini_generate_image(prompt, icon_path):
                ok = True
                break
    if not ok:
        from PIL import Image
        Image.new("RGB", (600, 400), (200, 200, 200)).save(icon_path)
        log(f"   ⚠️ 문항{idx+1} 이미지 생성 실패 → 플레이스홀더 대체")

    q_frame = os.path.join(workdir, f"q_{idx}.png")
    a_frame = os.path.join(workdir, f"a_{idx}.png")
    draw_quiz_card(icon_path, item, idx, total, reveal=False, out_path=q_frame, header_text=header_text)
    draw_quiz_card(icon_path, item, idx, total, reveal=True, out_path=a_frame, header_text=header_text)

    q_audio = os.path.join(workdir, f"q_audio_{idx}.mp3")
    a_audio = os.path.join(workdir, f"a_audio_{idx}.mp3")
    reveal_text = ", ".join([item["correct"]] * 3)
    if not elevenlabs_tts(item["question"], q_audio):
        make_silence(q_audio.replace(".mp3", ".m4a"), 2.5)
        q_audio = q_audio.replace(".mp3", ".m4a")
    if not elevenlabs_tts(reveal_text, a_audio):
        make_silence(a_audio.replace(".mp3", ".m4a"), 2.5)
        a_audio = a_audio.replace(".mp3", ".m4a")

    ding_path = os.path.join(workdir, "ding.m4a")
    if not os.path.exists(ding_path):
        make_ding(ding_path)

    q_clip = os.path.join(workdir, f"clip_q_{idx}.mp4")
    a_clip = os.path.join(workdir, f"clip_a_{idx}.mp4")
    still_clip(q_frame, q_audio, q_clip)
    still_clip(a_frame, a_audio, a_clip)

    ding_clip = os.path.join(workdir, f"clip_ding_{idx}.mp4")
    still_clip(a_frame, ding_path, ding_clip)

    return [q_clip, ding_clip, a_clip]


def concat_clips(clip_paths, out_path, workdir):
    list_file = os.path.join(workdir, "concat_list.txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for p in clip_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")
    run_ffmpeg(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
                "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", out_path])


# ════════════════════════════════════════════════════════════
# 구글드라이브 업로드 (선택)
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
            service.permissions().create(
                fileId=file_id, body={"type": "anyone", "role": "reader"}
            ).execute()
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

    category = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TOPIC_CATEGORY", "")
    n = int(sys.argv[2]) if len(sys.argv) > 2 else int(os.environ.get("NUM_ITEMS", "5"))
    target_lang = (sys.argv[3] if len(sys.argv) > 3 else os.environ.get("TARGET_LANG", "ko")).strip().lower()
    if target_lang not in LANG_CONFIG:
        target_lang = "ko"
    header_text = LANG_CONFIG[target_lang]["header"]

    os.makedirs(WORKDIR, exist_ok=True)

    log(f"1/3 문항 {n}개 생성 중 (카테고리: {category or '무작위'}, 질문 언어: {target_lang})...")
    items = generate_quiz_items(category, n, target_lang)
    for it in items:
        log(f"   - {it['question']} 정답:{it['correct']} 오답:{it['wrong1']}/{it['wrong2']}")

    log("2/3 문항별 이미지+나레이션+카드 생성 중...")
    all_clips = []
    for idx, item in enumerate(items):
        log(f"   [{idx+1}/{n}] {item['correct']}")
        all_clips.extend(build_item_clip(item, idx, n, WORKDIR, header_text=header_text))

    log("3/3 최종 영상 이어붙이는 중...")
    final_path = os.path.join(WORKDIR, "final.mp4")
    concat_clips(all_clips, final_path, WORKDIR)
    dur = get_duration(final_path)
    log(f"   ✅ 완성: {final_path} ({dur:.1f}초)")

    log("소셜 게시용 제목/캡션 생성 중...")
    try:
        copy = generate_social_copy(category, items, target_lang)
    except Exception as e:
        log(f"   ⚠️ 소셜 카피 생성 실패(무시, 빈 값으로 대체): {e}")
        copy = {"youtube_title": header_text, "youtube_description": "",
                "short_caption": "", "hashtags": ["Korean", "TOPIK", "LearnKorean"]}

    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone(timedelta(hours=9)))

    public_video_url = None
    if all([GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET,
            GOOGLE_OAUTH_REFRESH_TOKEN, GDRIVE_FOLDER_ID]):
        log("업로드 중...")
        service = get_drive_service()
        name = f"topik_quiz_{target_lang}_{now.strftime('%Y%m%d_%H%M%S')}.mp4"
        drive_info = upload_to_drive(service, final_path, GDRIVE_FOLDER_ID, name, make_public=True)
        public_video_url = drive_info.get("directLink")
        log(f"🎉 드라이브 업로드 완료 — {drive_info.get('webViewLink')}")
    else:
        log("드라이브 업로드 설정 없음 — 로컬 파일만 생성됨")

    meta = {
        "lang": target_lang,
        "category": category,
        "created_at": now.isoformat(),
        "video_path": final_path,
        "duration_sec": dur,
        "public_video_url": public_video_url,
        "youtube_title": copy.get("youtube_title", header_text),
        "youtube_description": copy.get("youtube_description", ""),
        "short_caption": copy.get("short_caption", ""),
        "hashtags": copy.get("hashtags", []),
    }
    meta_path = os.path.join(WORKDIR, f"meta_{target_lang}.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    log(f"🎉 완료 — 메타데이터: {meta_path}")


if __name__ == "__main__":
    main()
