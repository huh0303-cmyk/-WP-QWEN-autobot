"""
3단계: 썸네일 생성.
구독자 50만+ 건강/시니어 채널 벤치마킹 결과를 따른 스타일:
- 실사진 배경(Pexels, 없으면 Pixabay) + 좌측 어둡게 그라데이션(텍스트 가독성)
- 굵은 산세리프 + 흰 글씨 + 두꺼운 검은 외곽선(하이라이트 색은 노랑/빨강), 3줄 이내
- Claude가 뽑은 대본의 [TITLE]을 3줄로 자동 분해해 넣음
- 실존 인물/특정 병원 로고는 쓰지 않음 (스톡 사진만 사용)
"""
import os
from io import BytesIO

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1280, 720
CJK_FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
LATIN_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
CJK_INDEX = {"kr": 1, "jp": 0}

COLOR_YELLOW = (255, 214, 40)
COLOR_RED = (255, 55, 55)
COLOR_WHITE = (255, 255, 255)

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")


def _fetch_background_photo(keyword: str) -> "Image.Image | None":
    """벤치마킹 결과: 스톡 일러스트보다 실사진 배경이 클릭률이 훨씬 높음. Pexels 우선, 실패 시 Pixabay."""
    try:
        r = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": keyword, "per_page": 1, "orientation": "landscape"}, timeout=30,
        )
        photos = r.json().get("photos", []) if r.status_code == 200 else []
        if photos:
            img_bytes = requests.get(photos[0]["src"]["large2x"], timeout=60).content
            return Image.open(BytesIO(img_bytes)).convert("RGB")
    except Exception as e:
        print(f"[Thumbnail] Pexels 배경 실패: {e}")

    if PIXABAY_API_KEY:
        try:
            r = requests.get(
                "https://pixabay.com/api/",
                params={"key": PIXABAY_API_KEY, "q": keyword, "per_page": 3,
                        "image_type": "photo", "orientation": "horizontal", "safesearch": "true"},
                timeout=30,
            )
            hits = r.json().get("hits", []) if r.status_code == 200 else []
            if hits:
                img_bytes = requests.get(hits[0]["largeImageURL"], timeout=60).content
                return Image.open(BytesIO(img_bytes)).convert("RGB")
        except Exception as e:
            print(f"[Thumbnail] Pixabay 배경 실패: {e}")

    return None


def _get_font(lang: str, size: int):
    if lang == "en":
        return ImageFont.truetype(LATIN_FONT, size)
    return ImageFont.truetype(CJK_FONT, size, index=CJK_INDEX.get(lang, 1))


def _draw_outlined_text(draw, pos, text, font, fill, outline_w=8, outline_fill="black"):
    x, y = pos
    for dx in range(-outline_w, outline_w + 1, 2):
        for dy in range(-outline_w, outline_w + 1, 2):
            if dx * dx + dy * dy <= outline_w * outline_w:
                draw.text((x + dx, y + dy), text, font=font, fill=outline_fill)
    draw.text((x, y), text, font=font, fill=fill)
    return draw.textbbox((x, y), text, font=font)


def _draw_generic_hospital_building(draw, base_x=760, base_y=720):
    """완전 범용 병원 건물 실루엣 (특정 병원/로고 아님)."""
    building_w, building_h = 520, 560
    top = base_y - building_h
    draw.rectangle([base_x, top, base_x + building_w, base_y], fill=(20, 34, 48, 255))
    draw.rectangle([base_x + 40, top + 40, base_x + building_w - 40, base_y], fill=(26, 44, 60, 255))

    cols, rows = 6, 8
    margin = 70
    gap_x = (building_w - margin * 2) / cols
    gap_y = (building_h - margin) / rows
    win_w, win_h = gap_x * 0.55, gap_y * 0.5
    lit_pattern = {(1, 2), (3, 2), (0, 4), (4, 4), (2, 5), (5, 6), (1, 7), (3, 7)}
    for r in range(rows):
        for c in range(cols):
            wx = base_x + margin + c * gap_x
            wy = top + margin + r * gap_y
            lit = (c, r) in lit_pattern
            color = (255, 224, 130, 230) if lit else (60, 80, 100, 180)
            draw.rectangle([wx, wy, wx + win_w, wy + win_h], fill=color)

    cross_cx, cross_cy = base_x + building_w / 2, top - 55
    badge_r = 46
    draw.ellipse([cross_cx - badge_r, cross_cy - badge_r, cross_cx + badge_r, cross_cy + badge_r], fill=(255, 255, 255, 255))
    bar_w, bar_h = 44, 14
    draw.rectangle([cross_cx - bar_w / 2, cross_cy - bar_h / 2, cross_cx + bar_w / 2, cross_cy + bar_h / 2], fill=COLOR_RED)
    draw.rectangle([cross_cx - bar_h / 2, cross_cy - bar_w / 2, cross_cx + bar_h / 2, cross_cy + bar_w / 2], fill=COLOR_RED)

    draw.polygon(
        [(base_x + 150, base_y), (base_x + building_w - 150, base_y),
         (base_x + building_w - 110, base_y - 60), (base_x + 190, base_y - 60)],
        fill=(35, 55, 75, 255),
    )


def _split_title_into_lines(title: str, lang: str) -> list:
    """
    대본의 [TITLE]을 3줄로 자동 분해하고 색상(노랑/흰/빨강)을 배정.
    이미 대본에 콜론/구두점으로 나뉘어 있으면 그 기준으로, 아니면 단어 수 기준으로 3등분.
    """
    words = title.replace(",", " ").split()
    if len(words) < 3:
        return [(title, COLOR_YELLOW)]

    n = len(words)
    third = max(1, n // 3)
    line1 = " ".join(words[:third])
    line2 = " ".join(words[third: third * 2])
    line3 = " ".join(words[third * 2:])
    colors = [COLOR_YELLOW, COLOR_WHITE, COLOR_RED]
    return [(l, c) for l, c in zip([line1, line2, line3], colors) if l]


def generate_thumbnail(title: str, main_keyword: str, lang: str, out_path: str, kicker: str = None) -> str:
    print(f"[Thumbnail] 배경 실사진 검색 중... (키워드: {main_keyword})")
    photo = _fetch_background_photo(main_keyword)

    if photo:
        print("[Thumbnail] 실사진 배경으로 생성 중 (벤치마킹 스타일)...")
        pw, ph = photo.size
        scale = max(W / pw, H / ph)
        photo = photo.resize((int(pw * scale) + 1, int(ph * scale) + 1))
        left = (photo.width - W) // 2
        top = (photo.height - H) // 2
        img = photo.crop((left, top, left + W, top + H))
        # 살짝 어둡게(콘트라스트) + 약한 블러로 텍스트 배경 정리
        img = img.filter(ImageFilter.GaussianBlur(radius=0.6))
    else:
        print("[Thumbnail] 실사진을 못 구해 기본 배경으로 대체...")
        img = Image.new("RGB", (W, H), (8, 16, 24))
        top_c, bot_c = (10, 22, 32), (4, 8, 14)
        for y in range(H):
            t = y / H
            c = tuple(int(top_c[i] * (1 - t) + bot_c[i] * t) for i in range(3))
            ImageDraw.Draw(img).line([(0, y), (W, y)], fill=c)
        draw = ImageDraw.Draw(img, "RGBA")
        _draw_generic_hospital_building(draw)

    # 좌측(텍스트 들어갈 자리)을 어둡게 그라데이션 — 실사진 위에서도 글씨 가독성 확보
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for x in range(0, 900):
        alpha = int(190 * (1 - x / 900))
        od.line([(x, 0), (x, H)], fill=(2, 4, 8, alpha))
    # 하단도 살짝 어둡게 (브랜드 바 가독성)
    for y in range(H - 90, H):
        alpha = int(150 * ((y - (H - 90)) / 90))
        od.line([(0, y), (W, y)], fill=(2, 4, 8, alpha))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img, "RGBA")

    y_cursor = 130
    if kicker:
        kf = _get_font(lang, 32)
        draw.text((64, 92), kicker, font=kf, fill=(210, 210, 210, 255))

    lines = _split_title_into_lines(title, lang)
    for text, color in lines:
        size = 96 if lang != "en" else 74
        font = _get_font(lang, size)
        bbox = _draw_outlined_text(draw, (60, y_cursor), text, font, color, outline_w=8)
        y_cursor = bbox[3] + 16

    draw.rectangle([0, H - 14, W, H], fill=COLOR_RED)
    logo_prefix = {"kr": "건강채널", "en": "HEALTH CHANNEL", "jp": "健康チャンネル"}.get(lang, "HEALTH CHANNEL")
    prefix_font = _get_font(lang, 26)
    brand_font = ImageFont.truetype(LATIN_FONT, 38)
    prefix_bbox = draw.textbbox((0, 0), logo_prefix, font=prefix_font)
    brand_bbox = draw.textbbox((0, 0), "Health Clinic", font=brand_font)
    prefix_w = prefix_bbox[2] - prefix_bbox[0]
    brand_w = brand_bbox[2] - brand_bbox[0]
    brand_x = W - 40 - brand_w
    prefix_x = brand_x - 14 - prefix_w
    draw.text((prefix_x, 24), logo_prefix, font=prefix_font, fill=(220, 220, 220, 235))
    draw.text((brand_x, 16), "Health Clinic", font=brand_font, fill=(255, 255, 255, 250))

    img.save(out_path, quality=94)
    print(f"[Thumbnail] 완료: {out_path}")
    return out_path
