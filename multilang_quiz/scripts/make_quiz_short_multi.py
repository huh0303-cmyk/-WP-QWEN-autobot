#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
다국어 초급 단어 퀴즈 숏폼 자동 생성기 (무료 파이프라인) v2
- 대상 언어: en(영어) / ja(일본어) / es(스페인어) / vi(베트남어)
- 이미지: Wikimedia Commons API (무료, 키 불필요) + 재시도 + 폴백 카드
- TTS: gTTS (무료, 구글 번역 TTS)
- 효과음: 카운트다운 틱 + 정답 차임 (ffmpeg 합성음, 무료)
- 합성: PIL(프레임 생성) + ffmpeg(인코딩)

v2 변경사항 (사용자 피드백 반영):
  - 카운트다운 5초 기본값, 숫자를 항상 크게 표시(스타일 무관)
  - 초당 틱 효과음 + 정답 시 차임 효과음 추가
  - 상단 고정 브랜드 바 "서울국제대학교" 추가
  - 이미지 소싱 재시도(쿼리 변형) + 실패 시 폴백 카드(빈 화면 방지)

사용법:
  python3 make_quiz_short_multi.py --lang en --n 5
"""

import os, csv, json, random, argparse, subprocess, urllib.request, urllib.parse
from PIL import Image, ImageDraw, ImageFont
from gtts import gTTS

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

# ------------------------- 언어별 설정 -------------------------
LANG_CONFIG = {
    "en": {
        "name": "English", "gtts_lang": "en",
        "question_text": "What is this?", "correct_text": "Correct!",
        "font": LATIN_FONT_CANDIDATES,
        "csv": "data/words_en.csv", "brand": "English Basic Words",
        "top_brand": "서울국제대학교",
    },
    "ja": {
        "name": "日本語", "gtts_lang": "ja",
        "question_text": "これは何ですか？", "correct_text": "正解！",
        "font": CJK_FONT_CANDIDATES,
        "csv": "data/words_ja.csv", "brand": "日本語 基礎単語",
        "top_brand": "서울국제대학교",
    },
    "es": {
        "name": "Español", "gtts_lang": "es",
        "question_text": "¿Qué es esto?", "correct_text": "¡Correcto!",
        "font": LATIN_FONT_CANDIDATES,
        "csv": "data/words_es.csv", "brand": "Español Básico",
        "top_brand": "서울국제대학교",
    },
    "vi": {
        "name": "Tiếng Việt", "gtts_lang": "vi",
        "question_text": "Đây là cái gì?", "correct_text": "Chính xác!",
        "font": LATIN_FONT_CANDIDATES,
        "csv": "data/words_vi.csv", "brand": "Tiếng Việt Cơ Bản",
        "top_brand": "서울국제대학교",
    },
    "ko": {
        "name": "한국어", "gtts_lang": "ko",
        "question_text": "이게 뭐예요?", "correct_text": "정답이에요!",
        "font": CJK_FONT_CANDIDATES,
        "csv": "data/words_ko.csv", "brand": "TOPIK 초급 단어",
        "top_brand": "TOPIK어휘(초급)",
    },
}

W, H = 1080, 1920
FPS = 30
WORKDIR = "build"
ASSETS = "assets"
BADGE_COLORS = ["#FFD6E8", "#E4D6FF", "#D6F0FF", "#D6FFE4", "#FFF0D6", "#D6FFF7",
                "#FFE0C2", "#E0FFE0", "#F0D6FF", "#D6E4FF", "#FFF5B8", "#C2F5E9"]
TIMER_STYLES = ["ring", "bar", "dots"]
OPTION_STYLES = ["rounded", "pill", "square"]
KO_FONT = resolve_font(CJK_FONT_CANDIDATES)

def next_bg_color(prev_color):
    """직전 문항과 겹치지 않게 매번 배경색을 바꿔서 반환."""
    choices = [c for c in BADGE_COLORS if c != prev_color]
    return random.choice(choices)

def load_words(csv_path):
    with open(csv_path, encoding="utf-8") as f:
        return list(csv.DictReader(f))

def build_quiz_items(words, n):
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
        font = ImageFont.truetype(KO_FONT, 160)
        ch = word[0] if word else "?"
        bbox = draw.textbbox((0, 0), ch, font=font)
        draw.text(((size[0]-(bbox[2]-bbox[0]))//2, (size[1]-(bbox[3]-bbox[1]))//2-40), ch, font=font, fill="#999999")
    except Exception:
        pass
    img.save(out_path, quality=90)

def tts(text, out_path, gtts_lang, slow=False, max_retries=5):
    import time
    last_err = None
    for attempt in range(max_retries):
        try:
            gTTS(text, lang=gtts_lang, slow=slow).save(out_path)
            return float(subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", out_path],
                capture_output=True, text=True).stdout.strip())
        except Exception as e:
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise last_err

def load_font(path, size):
    return ImageFont.truetype(path, size)

def rounded_rect(draw, xy, radius, fill, outline=None, width=0):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)

def fit_image(img, box_w, box_h):
    img = img.convert("RGB")
    ratio = min(box_w / img.width, box_h / img.height)
    new_size = (max(1, int(img.width * ratio)), max(1, int(img.height * ratio)))
    return img.resize(new_size, Image.LANCZOS)

def draw_top_bar(draw, font_top, top_brand):
    rounded_rect(draw, (0, 0, W, 130), 0, fill="#1B2A4A")
    bbox = draw.textbbox((0, 0), top_brand, font=font_top)
    draw.text(((W-(bbox[2]-bbox[0]))//2, 34), top_brand, font=font_top, fill="#FFFFFF")

# 사진 카드 크기/위치 - 사진과 보기(선택지) 사이 여백을 좁히기 위해 컴팩트하게 조정
PIC_BOX_W, PIC_BOX_H = 760, 600
PIC_TOP_Y = 300

def draw_picture_card(img, draw, image_path):
    if os.path.exists(image_path):
        try:
            pic = Image.open(image_path)
            pic = fit_image(pic, PIC_BOX_W, PIC_BOX_H)
            px = (W - pic.width) // 2
            py = PIC_TOP_Y
            rounded_rect(draw, (px - 30, py - 30, px + pic.width + 30, py + pic.height + 30), 40, fill="#FFFFFF")
            img.paste(pic, (px, py))
        except Exception:
            pass

def draw_question_frame(idx, total, item, cfg, bg_color, timer_style, option_style, image_path, seconds, fonts):
    frames = []
    font_q, font_opt, font_badge, font_top, font_timer_num = fonts

    for sec_left in range(seconds, 0, -1):
        img = Image.new("RGB", (W, H), bg_color)
        draw = ImageDraw.Draw(img)
        draw_top_bar(draw, font_top, cfg["top_brand"])

        badge_txt = f"{idx}/{total}"
        rounded_rect(draw, (W - 190, 150, W - 40, 220), 25, fill="#FFFFFF")
        bbox = draw.textbbox((0, 0), badge_txt, font=font_badge)
        draw.text((W - 115 - (bbox[2]-bbox[0])//2, 160), badge_txt, font=font_badge, fill="#333333")

        q_bbox = draw.textbbox((0, 0), cfg["question_text"], font=font_q)
        draw.text(((W - (q_bbox[2]-q_bbox[0])) // 2, 200), cfg["question_text"], font=font_q, fill="#222222")

        draw_picture_card(img, draw, image_path)

        cx, cy = W // 2, 1050
        r = 70
        if timer_style == "ring":
            draw.ellipse((cx-r, cy-r, cx+r, cy+r), outline="#DDDDDD", width=14)
            angle = 360 * (sec_left / seconds)
            draw.arc((cx-r, cy-r, cx+r, cy+r), -90, -90+angle, fill="#FF5A5A", width=14)
        elif timer_style == "bar":
            bar_w = 560
            draw.rounded_rectangle((cx-bar_w//2, cy+r-24, cx+bar_w//2, cy+r+16), 20, fill="#DDDDDD")
            fill_w = int(bar_w * (sec_left/seconds))
            draw.rounded_rectangle((cx-bar_w//2, cy+r-24, cx-bar_w//2+fill_w, cy+r+16), 20, fill="#FF5A5A")
            draw.ellipse((cx-r, cy-r, cx+r, cy+r), fill="#FFFFFF", outline="#FF5A5A", width=6)
        else:
            for i in range(seconds):
                dot_x = cx - (seconds*36)//2 + i*36
                color = "#FF5A5A" if i < sec_left else "#DDDDDD"
                draw.ellipse((dot_x-10, cy+r, dot_x+10, cy+r+20), fill=color)
            draw.ellipse((cx-r, cy-r, cx+r, cy+r), fill="#FFFFFF", outline="#FF5A5A", width=6)

        t_bbox = draw.textbbox((0, 0), str(sec_left), font=font_timer_num)
        draw.text((cx-(t_bbox[2]-t_bbox[0])//2, cy-(t_bbox[3]-t_bbox[1])//2-14), str(sec_left),
                   font=font_timer_num, fill="#FF3B3B")

        opt_y = 1180
        opt_h = 120
        gap = 22
        for i, opt in enumerate(item["options"]):
            oy = opt_y + i*(opt_h+gap)
            box = (90, oy, W-90, oy+opt_h)
            if option_style == "pill":
                rounded_rect(draw, box, opt_h//2, fill="#FFFFFF", outline="#333333", width=4)
            elif option_style == "square":
                draw.rectangle(box, fill="#FFFFFF", outline="#333333", width=4)
            else:
                rounded_rect(draw, box, 24, fill="#FFFFFF", outline="#333333", width=4)
            label = chr(65+i)
            draw.text((130, oy+opt_h//2-28), label, font=font_opt, fill="#888888")
            o_bbox = draw.textbbox((0,0), opt, font=font_opt)
            draw.text((240, oy+opt_h//2-(o_bbox[3]-o_bbox[1])//2-8), opt, font=font_opt, fill="#222222")

        frames.append(img)
    return frames

def draw_answer_frame(idx, total, item, cfg, bg_color, option_style, image_path, seconds, fonts):
    frames = []
    font_q, font_opt, font_badge, font_top, font_correct = fonts

    for _ in range(seconds):
        img = Image.new("RGB", (W, H), bg_color)
        draw = ImageDraw.Draw(img)
        draw_top_bar(draw, font_top, cfg["top_brand"])

        q_bbox = draw.textbbox((0, 0), cfg["question_text"], font=font_q)
        draw.text(((W - (q_bbox[2]-q_bbox[0])) // 2, 200), cfg["question_text"], font=font_q, fill="#222222")

        draw_picture_card(img, draw, image_path)

        c_bbox = draw.textbbox((0,0), cfg["correct_text"], font=font_correct)
        rounded_rect(draw, (W//2-(c_bbox[2]-c_bbox[0])//2-40, 990, W//2+(c_bbox[2]-c_bbox[0])//2+40, 1080), 30, fill="#4CAF50")
        draw.text((W//2-(c_bbox[2]-c_bbox[0])//2, 1010), cfg["correct_text"], font=font_correct, fill="#FFFFFF")

        opt_y = 1180
        opt_h = 120
        gap = 22
        for i, opt in enumerate(item["options"]):
            oy = opt_y + i*(opt_h+gap)
            box = (90, oy, W-90, oy+opt_h)
            is_correct = (i == item["answer_idx"])
            fill_c = "#D6FFE4" if is_correct else "#FFFFFF"
            outline_c = "#4CAF50" if is_correct else "#CCCCCC"
            if option_style == "pill":
                rounded_rect(draw, box, opt_h//2, fill=fill_c, outline=outline_c, width=5 if is_correct else 3)
            elif option_style == "square":
                draw.rectangle(box, fill=fill_c, outline=outline_c, width=5 if is_correct else 3)
            else:
                rounded_rect(draw, box, 24, fill=fill_c, outline=outline_c, width=5 if is_correct else 3)
            label = chr(65+i)
            draw.text((130, oy+opt_h//2-28), label, font=font_opt, fill="#888888")
            o_bbox = draw.textbbox((0,0), opt, font=font_opt)
            draw.text((240, oy+opt_h//2-(o_bbox[3]-o_bbox[1])//2-8), opt, font=font_opt, fill="#222222")

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
    items = build_quiz_items(words, args.n)

    lang_font_path = resolve_font(cfg["font"])
    font_q = load_font(lang_font_path, 56)
    font_opt = load_font(lang_font_path, 50)
    font_badge = load_font(lang_font_path, 38)
    font_top = load_font(KO_FONT, 52)
    font_timer_num = load_font(lang_font_path, 84)
    font_correct = load_font(lang_font_path, 60)

    q_fonts = (font_q, font_opt, font_badge, font_top, font_timer_num)
    a_fonts = (font_q, font_opt, font_badge, font_top, font_correct)

    # 질문 프롬프트 음성 ("이게 뭐예요?" 등) - 언어당 1회만 생성해서 재사용
    question_audio = os.path.join(WORKDIR, f"question_prompt_{args.lang}.mp3")
    q_prompt_dur = tts(cfg["question_text"], question_audio, cfg["gtts_lang"])

    frame_i = 0
    audio_events = []
    cur_time = 0.0
    prev_bg_color = None

    for idx, item in enumerate(items, start=1):
        bg_color = next_bg_color(prev_bg_color)
        prev_bg_color = bg_color
        timer_style = random.choice(TIMER_STYLES)
        option_style = random.choice(OPTION_STYLES)

        img_path = os.path.join(WORKDIR, f"img_{args.lang}_{idx}.jpg")
        canva_asset = os.path.join("canva_assets", f"{item['concept']}.png")
        if item["concept"] and os.path.exists(canva_asset):
            Image.open(canva_asset).convert("RGB").save(img_path, quality=95)
            ok = True
        else:
            ok = fetch_commons_image(item["image_query"], item["word"], img_path)
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

        q_frames = draw_question_frame(idx, len(items), item, cfg, bg_color, timer_style, option_style, img_path, args.question_seconds, q_fonts)
        for f in q_frames:
            f.save(os.path.join(WORKDIR, f"frame_{frame_i:05d}.jpg"), quality=90)
            frame_i += 1

        a_frames = draw_answer_frame(idx, len(items), item, cfg, bg_color, option_style, img_path, answer_seconds, a_fonts)
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
