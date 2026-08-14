#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
다국어 초급 단어 퀴즈 숏폼 자동 생성기 v4
- 한국어를 원소스로: 매 실행 배치에서 첫 언어가 오늘의 단어(concept) 세트를 정하면
  나머지 언어는 그 세트를 그대로 따라간다(WORKDIR/selected_concepts.json)
- 이미지: canva_assets/(concept) 우선 → 언어 간 공유 캐시(WORKDIR/img_cache) →
  없으면 Wikimedia Commons 검색 + 폴백 카드
- TTS: ElevenLabs(eleven_multilingual_v2, 보이스 1개로 전 언어 커버)
- 효과음: 카운트다운 틱 + 정답 차임 (ffmpeg 합성음, 무료)
- 합성: PIL(프레임 생성) + ffmpeg(인코딩)

v3 변경사항 (디자인 리뉴얼 — 기존 topik_quiz_shorts.py 카드 스타일 참고):
  - 문항마다 배경색/타이머모양/보기모양이 무작위로 바뀌던 것을 없애고, 영상 하나당
    테마(배경+포인트색) 하나로 고정 — 뒤죽박죽 섞여 보이는 "AI가 대충 조립한" 느낌 제거
  - 카드에 그림자 대신 두꺼운 검정 테두리(카툰풍 플랫 디자인)로 통일
  - 보기(선택지)는 캡슐형 + 원형 A/B/C 뱃지로 통일, 정답 공개 시 보기 자체를 강조색으로
    하이라이트(별도 "정답이에요!" 배너 제거로 화면 단순화)
  - 카운트다운은 사진 카드 모서리의 작은 원형 뱃지로 표시(숫자만, 링/바/점 애니메이션 제거)
  - 라틴 문자 언어(en/es/vi) 폰트를 시스템 기본 DejaVu 대신 무료 구글 폰트
    Poppins-ExtraBold로 교체(다운로드 실패 시 자동 폴백)

사용법:
  python3 make_quiz_short_multi.py --lang en --n 5
"""

import os, csv, json, random, argparse, subprocess, urllib.request, urllib.parse, tempfile, hashlib
from PIL import Image, ImageDraw, ImageFont
import requests

try:
    import arabic_reshaper
    from bidi.algorithm import get_display as _bidi_display
except ImportError:
    arabic_reshaper = None
    _bidi_display = None

# 아랍어는 PIL이 문자를 그냥 순서대로만 그려서 글자 연결(shaping)과 방향(RTL)이
# 깨지기 때문에, 화면에 그리기 직전에만 reshape+bidi 처리를 거친다(TTS/데이터
# 원문은 그대로 둬야 하므로 draw 호출부에서만 이 함수를 통과시킨다).
CURRENT_LANG = "en"

def disp(text):
    if CURRENT_LANG == "ar" and arabic_reshaper is not None:
        return _bidi_display(arabic_reshaper.reshape(text))
    return text

def resolve_font(candidates):
    for path in candidates:
        if os.path.exists(path):
            return path
    raise FileNotFoundError(f"사용 가능한 폰트를 찾을 수 없습니다: {candidates}")

LATIN_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
]
CJK_FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
]

# 기본 DejaVu Sans는 딱 봐도 시스템 폰트라 "AI가 대충 만든 티"가 나서, 라틴 문자
# 언어(en/es/vi)는 더 개성 있는 무료 구글 폰트(Poppins ExtraBold, 고정 굵기 정적
# 폰트)를 받아서 대신 쓴다. 다운로드 실패 시에만 DejaVu로 조용히 폴백.
LATIN_HEADLINE_FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-ExtraBold.ttf"
LATIN_HEADLINE_FONT_PATH = os.path.join(tempfile.gettempdir(), "_quiz_poppins_extrabold.ttf")

def ensure_latin_headline_font():
    if not os.path.exists(LATIN_HEADLINE_FONT_PATH):
        try:
            r = requests.get(LATIN_HEADLINE_FONT_URL, timeout=30)
            r.raise_for_status()
            with open(LATIN_HEADLINE_FONT_PATH, "wb") as f:
                f.write(r.content)
        except Exception:
            return None
    return LATIN_HEADLINE_FONT_PATH if os.path.exists(LATIN_HEADLINE_FONT_PATH) else None

# Poppins엔 베트남어 성조 결합 글자(ế/ệ/ả 등) 글리프가 없어서 전부 네모(tofu)로
# 깨진다. 베트남어는 폭넓은 유니코드 커버리지를 가진 Noto Sans(가변 폰트)로 별도 처리.
VI_FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/notosans/NotoSans%5Bwdth,wght%5D.ttf"
VI_FONT_PATH = os.path.join(tempfile.gettempdir(), "_quiz_notosans_vi.ttf")

def ensure_vi_font():
    if not os.path.exists(VI_FONT_PATH):
        try:
            r = requests.get(VI_FONT_URL, timeout=30)
            r.raise_for_status()
            with open(VI_FONT_PATH, "wb") as f:
                f.write(r.content)
        except Exception:
            return None
    return VI_FONT_PATH if os.path.exists(VI_FONT_PATH) else None

# Noto Sans는 키릴 문자(러시아어)도 폭넓게 커버해서 베트남어와 동일한 폰트를
# 재사용한다(ensure_vi_font 이름은 그대로지만 실제로는 두 언어가 공유).

# 아랍어는 Noto Sans에 글리프가 아예 없어서 전용 아랍 문자 폰트가 필요하다.
AR_FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/notosansarabic/NotoSansArabic%5Bwdth,wght%5D.ttf"
AR_FONT_PATH = os.path.join(tempfile.gettempdir(), "_quiz_notosans_arabic.ttf")

def ensure_ar_font():
    if not os.path.exists(AR_FONT_PATH):
        try:
            r = requests.get(AR_FONT_URL, timeout=30)
            r.raise_for_status()
            with open(AR_FONT_PATH, "wb") as f:
                f.write(r.content)
        except Exception:
            return None
    return AR_FONT_PATH if os.path.exists(AR_FONT_PATH) else None

# 태국어는 라틴/키릴/아랍 폰트 어디에도 글리프가 없어서 전용 타이 문자 폰트가 필요하다.
TH_FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/notosansthai/NotoSansThai%5Bwdth,wght%5D.ttf"
TH_FONT_PATH = os.path.join(tempfile.gettempdir(), "_quiz_notosans_thai.ttf")

def ensure_th_font():
    if not os.path.exists(TH_FONT_PATH):
        try:
            r = requests.get(TH_FONT_URL, timeout=30)
            r.raise_for_status()
            with open(TH_FONT_PATH, "wb") as f:
                f.write(r.content)
        except Exception:
            return None
    return TH_FONT_PATH if os.path.exists(TH_FONT_PATH) else None

# ------------------------- 언어별 설정 -------------------------
LANG_CONFIG = {
    "en": {
        "name": "English", "gtts_lang": "en",
        "question_text": "What is this?",
        "font": LATIN_FONT_CANDIDATES,
        "csv": "data/words_en.csv", "brand": "English Basic Words",
        "top_brand": "Survival English",
    },
    "ja": {
        "name": "日本語", "gtts_lang": "ja",
        "question_text": "これは何ですか？",
        "font": CJK_FONT_CANDIDATES,
        "csv": "data/words_ja.csv", "brand": "日本語 基礎単語",
        "top_brand": "Survival Japanese",
    },
    "es": {
        "name": "Español", "gtts_lang": "es",
        "question_text": "¿Qué es esto?",
        "font": LATIN_FONT_CANDIDATES,
        "csv": "data/words_es.csv", "brand": "Español Básico",
        "top_brand": "Survival Spanish",
    },
    "vi": {
        "name": "Tiếng Việt", "gtts_lang": "vi",
        "question_text": "Đây là cái gì?",
        "font": LATIN_FONT_CANDIDATES,
        "csv": "data/words_vi.csv", "brand": "Tiếng Việt Cơ Bản",
        "top_brand": "Survival Vietnamese",
    },
    "ko": {
        "name": "한국어", "gtts_lang": "ko",
        "question_text": "이게 뭐예요?",
        "font": CJK_FONT_CANDIDATES,
        "csv": "data/words_ko.csv", "brand": "TOPIK 초급 단어",
        "top_brand": "KIECA(한국국제교육문화협회)",
    },
    "fr": {
        "name": "Français", "gtts_lang": "fr",
        "question_text": "Qu'est-ce que c'est ?",
        "font": LATIN_FONT_CANDIDATES,
        "csv": "data/words_fr.csv", "brand": "Français de Base",
        "top_brand": "Survival French",
    },
    "de": {
        "name": "Deutsch", "gtts_lang": "de",
        "question_text": "Was ist das?",
        "font": LATIN_FONT_CANDIDATES,
        "csv": "data/words_de.csv", "brand": "Deutsch Grundwortschatz",
        "top_brand": "Survival German",
    },
    "zh": {
        "name": "中文", "gtts_lang": "zh-CN",
        "question_text": "这是什么？",
        "font": CJK_FONT_CANDIDATES,
        "csv": "data/words_zh.csv", "brand": "中文基础词汇",
        "top_brand": "Survival Chinese",
    },
    "ar": {
        "name": "العربية", "gtts_lang": "ar",
        "question_text": "ما هذا؟",
        "font": LATIN_FONT_CANDIDATES,  # ensure_ar_font()가 실패할 때만 쓰이는 폴백
        "csv": "data/words_ar.csv", "brand": "العربية الأساسية",
        "top_brand": "Survival Arabic",
    },
    "ru": {
        "name": "Русский", "gtts_lang": "ru",
        "question_text": "Что это?",
        "font": LATIN_FONT_CANDIDATES,
        "csv": "data/words_ru.csv", "brand": "Базовая лексика",
        "top_brand": "Survival Russian",
    },
    "pt": {
        "name": "Português", "gtts_lang": "pt",
        "question_text": "O que é isto?",
        "font": LATIN_FONT_CANDIDATES,
        "csv": "data/words_pt.csv", "brand": "Português Básico",
        "top_brand": "Survival Portuguese",
    },
    "it": {
        "name": "Italiano", "gtts_lang": "it",
        "question_text": "Cos'è questo?",
        "font": LATIN_FONT_CANDIDATES,
        "csv": "data/words_it.csv", "brand": "Italiano di Base",
        "top_brand": "Survival Italian",
    },
    "th": {
        "name": "ไทย", "gtts_lang": "th",
        "question_text": "นี่คืออะไร",
        "font": LATIN_FONT_CANDIDATES,  # ensure_th_font()가 실패할 때만 쓰이는 폴백
        "csv": "data/words_th.csv", "brand": "คำศัพท์ไทยพื้นฐาน",
        "top_brand": "Survival Thai",
    },
}

W, H = 1080, 1920
FPS = 30
WORKDIR = "build"
ASSETS = "assets"

# CJK(한/일/중) 폰트 - GitHub Actions(Ubuntu, fonts-noto-cjk 설치됨)에선 시스템
# 경로를 바로 쓰고, 그 경로가 없는 환경(로컬 Windows 등)에서는 언어별 무료
# 구글 폰트를 다운로드해서 대체한다 (ensure_vi_font/ensure_ar_font와 동일 패턴).
CJK_FONT_URLS = {
    "ko": ("https://raw.githubusercontent.com/google/fonts/main/ofl/nanumgothic/NanumGothic-ExtraBold.ttf",
           "_quiz_nanumgothic_ko.ttf"),
    "ja": ("https://raw.githubusercontent.com/google/fonts/main/ofl/notosansjp/NotoSansJP%5Bwght%5D.ttf",
           "_quiz_notosans_ja.ttf"),
    "zh": ("https://raw.githubusercontent.com/google/fonts/main/ofl/notosanssc/NotoSansSC%5Bwght%5D.ttf",
           "_quiz_notosans_zh.ttf"),
}

def ensure_cjk_font(lang="ko"):
    for path in CJK_FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    url, fname = CJK_FONT_URLS.get(lang, CJK_FONT_URLS["ko"])
    path = os.path.join(tempfile.gettempdir(), fname)
    if not os.path.exists(path):
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            with open(path, "wb") as f:
                f.write(r.content)
        except Exception:
            return None
    return path if os.path.exists(path) else None

# 영상 하나당 테마(배경색 + 포인트/하이라이트색) 하나를 고정으로 쓴다.
# 문항마다 색이 바뀌면 뒤죽박죽으로 보여서 일부러 통일감을 준다.
THEMES = [
    {"bg": "#8BC34A", "highlight": "#DFF08A"},   # 그린
    {"bg": "#F06292", "highlight": "#FBD3E1"},   # 로즈핑크
    {"bg": "#4FC3F7", "highlight": "#D3EFFD"},   # 스카이블루
    {"bg": "#FFB74D", "highlight": "#FFE3B8"},   # 오렌지
    {"bg": "#BA68C8", "highlight": "#E9CDEE"},   # 퍼플
    {"bg": "#4DB6AC", "highlight": "#C8ECE8"},   # 틸
    {"bg": "#FF8A65", "highlight": "#FFDCC9"},   # 코럴
    {"bg": "#7986CB", "highlight": "#DCE0F7"},   # 인디고
    {"bg": "#AED581", "highlight": "#EAF5D0"},   # 라임
    {"bg": "#FFD54F", "highlight": "#FFF3C4"},   # 앰버
    {"bg": "#D81B60", "highlight": "#F8BBD0"},   # 딥핑크
    {"bg": "#26C6DA", "highlight": "#C7F0F5"},   # 시안
    {"bg": "#9575CD", "highlight": "#E1D5F5"},   # 딥퍼플
    {"bg": "#4DD0E1", "highlight": "#CFF3F7"},   # 터콰이즈
    {"bg": "#FF7043", "highlight": "#FFD9CC"},   # 살몬
    {"bg": "#7E57C2", "highlight": "#DBCEF0"},   # 바이올렛
    {"bg": "#66BB6A", "highlight": "#D2ECD3"},   # 그래스그린
    {"bg": "#FDD835", "highlight": "#FFF6BF"},   # 선플라워옐로
    {"bg": "#42A5F5", "highlight": "#D2E9FD"},   # 블루
    {"bg": "#EC407A", "highlight": "#FBD9E6"},   # 마젠타
]
BLACK = "#141414"

def load_words(csv_path):
    with open(csv_path, encoding="utf-8") as f:
        return list(csv.DictReader(f))

def build_quiz_items(words, n, concepts=None):
    """concepts가 주어지면(다른 언어가 이미 고른 concept 목록) 그 순서/구성 그대로
    이 언어의 단어로 맞춰 뽑는다 — 한국어를 원소스로 나머지 언어를 만들 때
    모든 언어가 같은 단어 세트(예: 사과/바나나/강아지)를 다루게 하기 위함."""
    if concepts:
        by_concept = {w.get("concept", ""): w for w in words}
        chosen = [by_concept[c] for c in concepts if c in by_concept]
        if len(chosen) < len(concepts):
            missing = [c for c in concepts if c not in by_concept]
            print(f"[경고] 이 언어 CSV에 없는 concept {len(missing)}개 스킵: {missing}")
    else:
        pool = words[:]
        random.shuffle(pool)
        chosen = pool[:n]
    items = []
    for w in chosen:
        distractors = [x for x in words if x["category"] == w["category"] and x["word"] != w["word"]]
        if len(distractors) < 2:
            distractors = [x for x in words if x["word"] != w["word"]]
        random.shuffle(distractors)
        opts = [w] + distractors[:2]
        random.shuffle(opts)
        answer_idx = opts.index(w)
        items.append({
            "word": w["word"], "image_query": w["image_query"],
            "concept": w.get("concept", ""),
            "options": [o["word"] for o in opts], "answer_idx": answer_idx,
        })
    return items

def _commons_search(query, out_path):
    api = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": query, "gsrnamespace": 6, "gsrlimit": 10,
        "prop": "imageinfo", "iiprop": "url|mime", "iiurlwidth": 1000,
    }
    url = api + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "SeoulTopikQuizBot/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read().decode("utf-8"))
    pages = data.get("query", {}).get("pages", {})
    for _, page in pages.items():
        info = page.get("imageinfo", [{}])[0]
        mime = info.get("mime", "")
        thumb = info.get("thumburl") or info.get("url")
        if thumb and mime.startswith("image/") and "svg" not in mime:
            try:
                req2 = urllib.request.Request(thumb, headers={"User-Agent": "SeoulTopikQuizBot/1.0"})
                with urllib.request.urlopen(req2, timeout=20) as r2, open(out_path, "wb") as f:
                    f.write(r2.read())
                Image.open(out_path).verify()
                Image.open(out_path).convert("RGB")
                return True
            except Exception:
                continue
    return False

def fetch_commons_image(query, word, out_path, max_attempts=4):
    variants = [query, query.replace(" photo", ""), query.split(" ")[0], word]
    seen = set()
    for attempt in range(max_attempts):
        q = variants[attempt % len(variants)]
        if q in seen:
            continue
        seen.add(q)
        try:
            if _commons_search(q, out_path):
                return True
        except Exception:
            continue
    return False

def make_fallback_card(word, out_path, size=(900, 900)):
    img = Image.new("RGB", size, "#EFEFEF")
    draw = ImageDraw.Draw(img)
    draw.ellipse((size[0]//2-260, size[1]//2-260, size[0]//2+260, size[1]//2+260), fill="#D8D8D8")
    try:
        font = ImageFont.truetype(ensure_cjk_font("ko"), 160)
        ch = word[0] if word else "?"
        bbox = draw.textbbox((0, 0), ch, font=font)
        draw.text(((size[0]-(bbox[2]-bbox[0]))//2, (size[1]-(bbox[3]-bbox[1]))//2-40), ch, font=font, fill="#999999")
    except Exception:
        pass
    img.save(out_path, quality=90)

# ★ 2026-08-14 사용자 지시: 무료 gTTS 대신 ElevenLabs로 교체 — 훨씬 자연스러운
#   음성이 필요하다는 판단. eleven_multilingual_v2 모델은 보이스 하나로 이
#   퀴즈가 다루는 12개 언어를 전부 커버해서 언어별로 다른 보이스를 관리할
#   필요가 없다. 텍스트+보이스 해시로 캐싱해서 같은 단어("사과", "apple" 등)를
#   여러 영상에서 재사용할 때 API 호출을 아낀다(health_clinic의 tts_elevenlabs.py와
#   동일한 캐싱 패턴).
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID_QUIZ") or os.environ.get("ELEVENLABS_VOICE_ID", "")
_TTS_CACHE_DIR = os.path.join(tempfile.gettempdir(), "quiz_tts_cache")
os.makedirs(_TTS_CACHE_DIR, exist_ok=True)


def _ffprobe_duration(path):
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True).stdout.strip())


def tts(text, out_path, gtts_lang=None, slow=False, max_retries=5):
    import time
    if not ELEVENLABS_API_KEY or not ELEVENLABS_VOICE_ID:
        raise RuntimeError("ELEVENLABS_API_KEY / ELEVENLABS_VOICE_ID_QUIZ 환경변수 없음 — TTS 불가")

    cache_key = hashlib.sha256((ELEVENLABS_VOICE_ID + text).encode("utf-8")).hexdigest()[:20]
    cache_path = os.path.join(_TTS_CACHE_DIR, f"{cache_key}.mp3")
    if os.path.exists(cache_path):
        import shutil
        shutil.copyfile(cache_path, out_path)
        return _ffprobe_duration(out_path)

    last_err = None
    for attempt in range(max_retries):
        try:
            resp = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
                headers={"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"},
                json={
                    "text": text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
                },
                timeout=60,
            )
            resp.raise_for_status()
            with open(out_path, "wb") as f:
                f.write(resp.content)
            with open(cache_path, "wb") as f:
                f.write(resp.content)
            return _ffprobe_duration(out_path)
        except Exception as e:
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise last_err

def load_font(path, size, weight=800):
    font = ImageFont.truetype(path, size)
    try:
        # 가변 폰트면 축 이름으로 Weight만 찾아서 굵기 고정(나머지 축은 기본값 유지).
        # 축 순서를 가정하고 [weight]만 넘기면 폭(Width) 등 다른 축에 잘못 적용될 수 있음.
        axes = font.get_variation_axes()
        values = []
        for ax in axes:
            name = ax["name"].decode() if isinstance(ax["name"], bytes) else ax["name"]
            values.append(weight if name.lower() in ("weight", "wght") else ax["default"])
        font.set_variation_by_axes(values)
    except Exception:
        pass  # 정적 폰트면 가변 축이 없어서 예외 발생 -> 조용히 무시
    return font

def rounded_rect(draw, xy, radius, fill=None, outline=None, width=0):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)

def fit_image(img, box_w, box_h):
    """짧은 변 기준으로 확대한 뒤 중앙을 crop해서 항상 box_w x box_h를 정확히 채운다."""
    img = img.convert("RGB")
    ratio = max(box_w / img.width, box_h / img.height)
    new_size = (max(1, int(img.width * ratio)), max(1, int(img.height * ratio)))
    img = img.resize(new_size, Image.LANCZOS)
    left = (img.width - box_w) // 2
    top = (img.height - box_h) // 2
    return img.crop((left, top, left + box_w, top + box_h))

# ------------------------- 레이아웃 상수 -------------------------
HEADER_BOX = (90, 50, 990, 200)
DIVIDER_Y = 232
PIC_BOX_W, PIC_BOX_H = 760, 500
PIC_TOP_Y = 270
QUESTION_Y = 815
OPT_TOP_Y = 940
OPT_H, OPT_GAP = 120, 22
BOTTOM_BRAND_Y = 1850

def draw_header(draw, font_path, brand_text, highlight):
    brand_text = disp(brand_text)
    rounded_rect(draw, HEADER_BOX, 40, fill=highlight)
    size = 68
    while size > 30:
        tf = load_font(font_path, size)
        tb = draw.textbbox((0, 0), brand_text, font=tf)
        if tb[2] - tb[0] <= HEADER_BOX[2] - HEADER_BOX[0] - 80:
            break
        size -= 4
    cx = (HEADER_BOX[0] + HEADER_BOX[2]) // 2
    cy = (HEADER_BOX[1] + HEADER_BOX[3]) // 2
    draw.text((cx - (tb[2]-tb[0])//2, cy - (tb[1]+tb[3])//2), brand_text, font=tf, fill=BLACK)
    draw.line([(HEADER_BOX[0], DIVIDER_Y), (HEADER_BOX[2], DIVIDER_Y)], fill=BLACK, width=4)

def draw_picture_card(img, draw, image_path, countdown=None, font_countdown=None):
    px = (W - PIC_BOX_W) // 2
    py = PIC_TOP_Y
    card_xy = (px, py, px + PIC_BOX_W, py + PIC_BOX_H)
    rounded_rect(draw, card_xy, 40, fill="#FFFFFF", outline=BLACK, width=6)
    if os.path.exists(image_path):
        try:
            pic = Image.open(image_path)
            pic = fit_image(pic, PIC_BOX_W - 30, PIC_BOX_H - 30)
            img.paste(pic, (px + 15, py + 15))
            rounded_rect(draw, card_xy, 40, outline=BLACK, width=6)  # 사진 위로 테두리 다시 그려서 깔끔하게
        except Exception:
            pass
    if countdown is not None:
        cx, cy, r = px + PIC_BOX_W - 60, py + PIC_BOX_H - 60, 46
        draw.ellipse((cx-r, cy-r, cx+r, cy+r), fill="#FFFFFF", outline=BLACK, width=5)
        num = str(countdown)
        nb = draw.textbbox((0, 0), num, font=font_countdown)
        draw.text((cx-(nb[2]-nb[0])//2, cy-(nb[1]+nb[3])//2-6), num, font=font_countdown, fill="#E53935")

def draw_options(draw, options, font_opt, font_label, highlight=None, correct_idx=None):
    for i, opt in enumerate(options):
        opt = disp(opt)
        oy = OPT_TOP_Y + i * (OPT_H + OPT_GAP)
        box = (90, oy, W - 90, oy + OPT_H)
        is_correct = correct_idx is not None and i == correct_idx
        fill_c = highlight if is_correct else "#FFFFFF"
        rounded_rect(draw, box, OPT_H // 2, fill=fill_c, outline=BLACK, width=5 if is_correct else 4)
        lcx, lcy, lr = 175, oy + OPT_H // 2, 40
        draw.ellipse((lcx-lr, lcy-lr, lcx+lr, lcy+lr), fill="#FFFFFF", outline=BLACK, width=3)
        label = chr(65 + i)
        lb = draw.textbbox((0, 0), label, font=font_label)
        draw.text((lcx-(lb[2]-lb[0])//2, lcy-(lb[1]+lb[3])//2), label, font=font_label, fill=BLACK)
        ob = draw.textbbox((0, 0), opt, font=font_opt)
        draw.text((lcx + 90, lcy - (ob[1]+ob[3])//2), opt, font=font_opt, fill=BLACK)

def draw_base_frame(bg_color, cfg, theme, fonts):
    brand_font_path, font_q, font_opt, font_label, font_countdown, font_ko_small = fonts
    img = Image.new("RGB", (W, H), bg_color)
    draw = ImageDraw.Draw(img)
    draw_header(draw, brand_font_path, cfg["brand"], theme["highlight"])
    # top_brand("서울국제대학교" 등)는 항상 한국어라 언어별 폰트가 아니라 한글 폰트로 고정
    bb = draw.textbbox((0, 0), cfg["top_brand"], font=font_ko_small)
    draw.text(((W-(bb[2]-bb[0]))//2, BOTTOM_BRAND_Y), cfg["top_brand"], font=font_ko_small, fill=BLACK)
    return img, draw

def draw_question_frame(item, cfg, theme, image_path, seconds, fonts):
    brand_font_path, font_q, font_opt, font_label, font_countdown, font_ko_small = fonts
    frames = []
    for sec_left in range(seconds, 0, -1):
        img, draw = draw_base_frame(theme["bg"], cfg, theme, fonts)
        draw_picture_card(img, draw, image_path, countdown=sec_left, font_countdown=font_countdown)

        q_text = disp(cfg["question_text"])
        q_bbox = draw.textbbox((0, 0), q_text, font=font_q)
        draw.text(((W - (q_bbox[2]-q_bbox[0])) // 2, QUESTION_Y), q_text, font=font_q, fill=BLACK)

        draw_options(draw, item["options"], font_opt, font_label)
        frames.append(img)
    return frames

def draw_answer_frame(item, cfg, theme, image_path, seconds, fonts):
    brand_font_path, font_q, font_opt, font_label, font_countdown, font_ko_small = fonts
    frames = []
    for _ in range(seconds):
        img, draw = draw_base_frame(theme["bg"], cfg, theme, fonts)
        draw_picture_card(img, draw, image_path)

        q_text = disp(cfg["question_text"])
        q_bbox = draw.textbbox((0, 0), q_text, font=font_q)
        draw.text(((W - (q_bbox[2]-q_bbox[0])) // 2, QUESTION_Y), q_text, font=font_q, fill=BLACK)

        draw_options(draw, item["options"], font_opt, font_label,
                     highlight=theme["highlight"], correct_idx=item["answer_idx"])
        frames.append(img)
    return frames

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", required=True, choices=list(LANG_CONFIG.keys()))
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--question_seconds", type=int, default=5)
    ap.add_argument("--answer_seconds", type=int, default=2)
    ap.add_argument("--out_dir", default="outputs")
    args = ap.parse_args()

    cfg = LANG_CONFIG[args.lang]
    os.makedirs(WORKDIR, exist_ok=True)
    os.makedirs(args.out_dir, exist_ok=True)

    words = load_words(cfg["csv"])

    # ★ 2026-08-14 사용자 지시: 한국어를 원소스로, 나머지 11개 언어는 같은
    #   단어 세트(concept)를 그대로 따라가게 한다 — 언어마다 완전히 다른
    #   단어를 무작위로 뽑던 것을 없앰. 같은 실행 배치(daily_multilang_quiz.yml의
    #   for-loop) 안에서 가장 먼저 도는 언어가 오늘의 concept 목록을 정하고
    #   파일로 남기면, 이후 언어들은 그 파일을 읽어서 그대로 따라간다.
    concepts_path = os.path.join(WORKDIR, "selected_concepts.json")
    if os.path.exists(concepts_path):
        with open(concepts_path, encoding="utf-8") as f:
            concepts = json.load(f)
        items = build_quiz_items(words, args.n, concepts=concepts)
    else:
        items = build_quiz_items(words, args.n)
        with open(concepts_path, "w", encoding="utf-8") as f:
            json.dump([it["concept"] for it in items], f, ensure_ascii=False)

    theme = random.choice(THEMES)  # 영상 전체에서 테마 하나로 고정

    global CURRENT_LANG
    CURRENT_LANG = args.lang

    if args.lang == "ar":
        lang_font_path = ensure_ar_font() or resolve_font(cfg["font"])
    elif args.lang == "th":
        lang_font_path = ensure_th_font() or resolve_font(cfg["font"])
    elif args.lang in ("vi", "ru"):
        # Noto Sans(가변 폰트)가 베트남어 성조 결합기호와 키릴 문자를 둘 다 커버해서 공유
        lang_font_path = ensure_vi_font() or resolve_font(cfg["font"])
    elif cfg["font"] is CJK_FONT_CANDIDATES:
        lang_font_path = ensure_cjk_font(args.lang) or resolve_font(cfg["font"])
    elif cfg["font"] is LATIN_FONT_CANDIDATES:
        lang_font_path = ensure_latin_headline_font() or resolve_font(cfg["font"])
    else:
        lang_font_path = resolve_font(cfg["font"])

    font_q = load_font(lang_font_path, 56)
    font_opt = load_font(lang_font_path, 50)
    font_label = load_font(lang_font_path, 40)
    font_countdown = load_font(lang_font_path, 56)
    font_ko_small = load_font(ensure_cjk_font("ko") or lang_font_path, 38)
    fonts = (lang_font_path, font_q, font_opt, font_label, font_countdown, font_ko_small)

    # 질문 프롬프트 음성 ("이게 뭐예요?" 등) - 언어당 1회만 생성해서 재사용
    question_audio = os.path.join(WORKDIR, f"question_prompt_{args.lang}.mp3")
    tts(cfg["question_text"], question_audio, cfg["gtts_lang"])

    frame_i = 0
    audio_events = []
    cur_time = 0.0

    # ★ 2026-08-14: 이미지는 concept 단위로 언어 간 공유 캐시(WORKDIR/img_cache)에
    #   재사용한다 — "사과" 사진과 "apple" 사진은 어차피 같은 사진이어야 하므로,
    #   한국어 실행에서 받아둔 파일을 나머지 11개 언어가 그대로 복사해 쓴다.
    #   Commons 검색을 언어마다 반복 호출하지 않아 실패 확률(=이미지 누락)도 줄어든다.
    img_cache_dir = os.path.join(WORKDIR, "img_cache")
    os.makedirs(img_cache_dir, exist_ok=True)

    for idx, item in enumerate(items, start=1):
        img_path = os.path.join(WORKDIR, f"img_{args.lang}_{idx}.jpg")
        cache_path = os.path.join(img_cache_dir, f"{item['concept']}.jpg") if item["concept"] else None

        if cache_path and os.path.exists(cache_path):
            Image.open(cache_path).convert("RGB").save(img_path, quality=95)
            ok = True
        else:
            canva_asset = os.path.join("canva_assets", f"{item['concept']}.png")
            if item["concept"] and os.path.exists(canva_asset):
                Image.open(canva_asset).convert("RGB").save(img_path, quality=95)
                ok = True
            else:
                ok = fetch_commons_image(item["image_query"], item["word"], img_path)
            if ok and cache_path:
                Image.open(img_path).convert("RGB").save(cache_path, quality=95)
        if not ok:
            print(f"[정보] 이미지 소싱 실패 -> 폴백 카드 사용: {item['image_query']}")
            make_fallback_card(item["word"], img_path)

        # 정답 단어 음성 (문제 중엔 재생하지 않고, 정답 공개 시점에 3회 반복 재생)
        word_audio = os.path.join(WORKDIR, f"word_{args.lang}_{idx}.mp3")
        word_dur = tts(item["word"], word_audio, cfg["gtts_lang"])

        # 정답 구간 길이: 차임(0.4초) + 단어 3회 반복(간격 0.35초) + 여유 0.6초
        gap = 0.35
        answer_audio_span = 0.4 + (word_dur * 3 + gap * 2) + 0.6
        answer_seconds = max(args.answer_seconds, int(answer_audio_span) + 1)

        q_frames = draw_question_frame(item, cfg, theme, img_path, args.question_seconds, fonts)
        for f in q_frames:
            f.save(os.path.join(WORKDIR, f"frame_{frame_i:05d}.jpg"), quality=90)
            frame_i += 1

        a_frames = draw_answer_frame(item, cfg, theme, img_path, answer_seconds, fonts)
        for f in a_frames:
            f.save(os.path.join(WORKDIR, f"frame_{frame_i:05d}.jpg"), quality=90)
            frame_i += 1

        # 1) 질문 프롬프트 음성 (문항 시작)
        audio_events.append((cur_time + 0.1, question_audio))
        # 2) 5초 카운트다운 틱음
        for s in range(args.question_seconds):
            tick_file = os.path.join(ASSETS, "tick_last.mp3" if s == args.question_seconds-1 else "tick.mp3")
            audio_events.append((cur_time + s, tick_file))
        # 3) 정답 공개: 차임 + 단어 발음 3회 반복
        answer_start = cur_time + args.question_seconds
        audio_events.append((answer_start + 0.05, os.path.join(ASSETS, "correct.mp3")))
        word_t = answer_start + 0.5
        for _ in range(3):
            audio_events.append((word_t, word_audio))
            word_t += word_dur + gap

        cur_time += args.question_seconds + answer_seconds

    concat_list = os.path.join(WORKDIR, "frames.txt")
    with open(concat_list, "w") as f:
        for i in range(frame_i):
            f.write(f"file 'frame_{i:05d}.jpg'\nduration 1\n")
        f.write(f"file 'frame_{frame_i-1:05d}.jpg'\n")

    silent_video = os.path.join(WORKDIR, f"silent_{args.lang}.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
        "-vf", f"fps={FPS},format=yuv420p", "-c:v", "libx264",
        "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:v", "+bitexact",
        "-r", str(FPS), silent_video
    ], check=True, capture_output=True)

    audio_inputs = []
    filter_parts = []
    for i, (t, path) in enumerate(audio_events):
        audio_inputs += ["-i", path]
        filter_parts.append(f"[{i+1}]adelay={int(t*1000)}|{int(t*1000)}[a{i}]")
    amix_inputs = "".join(f"[a{i}]" for i in range(len(audio_events)))
    filter_complex = ";".join(filter_parts) + f";{amix_inputs}amix=inputs={len(audio_events)}:normalize=0,volume=2.0[aout]"

    out_path = os.path.join(args.out_dir, f"quiz_{args.lang}_beginner.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-i", silent_video, *audio_inputs,
        "-filter_complex", filter_complex, "-map", "0:v", "-map", "[aout]",
        "-map_metadata", "-1", "-map_metadata:s:v", "-1", "-map_metadata:s:a", "-1",
        "-fflags", "+bitexact",
        "-c:v", "copy", "-c:a", "aac", "-shortest", out_path
    ], check=True, capture_output=True)

    print(f"완료: {out_path}")

if __name__ == "__main__":
    main()
