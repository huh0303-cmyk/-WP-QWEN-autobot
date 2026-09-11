#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mbb_composer_playlist.py
─────────────────────────────────────────────────────────────
MBB(모짜르트클래식) 채널용 영상을 "작품 단위"로 하나씩 만든다 — 한 작곡가의
서로 다른 곡들(교향곡/현악사중주/서곡 등)을 한 영상에 몰아 붙이지 않고,
같은 작품의 악장들만 이어붙여 별도 영상으로 낸다 (예: 베토벤 교향곡 3번은
그것대로 한 편, 코리올란 서곡은 그것대로 한 편). 위키미디어 커먼즈의
퍼블릭도메인 초상화 위에 작곡가 이름을 크게, 그 바로 아래 곡명을 중간
크기로 얹은 배경에 오디오 반응 파형을 겹친다.

사용법:
    python scripts/mbb_composer_playlist.py [mozart|bach|beethoven|all]
    (기본값: all)

입출력 폴더는 구글드라이브 데스크톱 앱으로 마운트된 "플리채널/모짜르트클래식"
폴더를 그대로 사용한다 — 원곡(mp3)/썸네일(초상화 png)/완성(결과 mp4) 하위폴더.
"""

import os
import re
import sys
import glob
import shutil
import subprocess
import datetime

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE = (r"G:\.shortcut-targets-by-id\14FPgjTeXjJ3H1dCLn7sbMLRy9PhMacw_"
        r"\플리채널\모짜르트_바흐_베트벤클래식")
AUDIO_DIR = os.path.join(BASE, "원곡")
THUMB_DIR = os.path.join(BASE, "썸네일")
OUT_DIR = os.path.join(BASE, "완성")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
WORKDIR = os.path.join(REPO_ROOT, "mbb_work")
PORTRAIT_DIR = os.path.join(WORKDIR, "portraits")
FONT_PATH = os.path.join(REPO_ROOT, "playlist_output", "_playfair.ttf")
# ffmpeg drawtext의 fontfile 인자가 비ASCII 경로(레포 경로의 'ドキュメント')를 못 읽는
# 문제가 있어 ASCII 전용 임시 경로에 폰트를 복사해두고 그쪽을 사용한다.
_FONT_ASCII_PATH = r"C:\Users\huh03\AppData\Local\Temp\claude\C--Users-huh03-OneDrive--------GitHub--WP-QWEN-autobot\20ad6185-83da-487f-9a7d-f4643f691e82\scratchpad\_playfair.ttf"
if os.path.exists(_FONT_ASCII_PATH):
    FONT_PATH = _FONT_ASCII_PATH

VIDEO_W, VIDEO_H = 1920, 1080
TRACK_GAP_SEC = 1.2  # 악장 사이 무음 간격 — 뚝뚝 끊기는 느낌 방지

COMPOSERS = [
    {"name": "Mozart", "prefix": "WolfgangAmadeusMozart",
     "portrait": "mozart_krafft.jpg"},
    {"name": "Bach", "prefix": "JohannSebastianBach",
     "portrait": "bach_haussmann.jpg"},
    {"name": "Beethoven", "prefix": "LudwigVanBeethoven",
     "portrait": "beethoven_stieler.jpg"},
]


def log(msg):
    print(msg, flush=True)


def run_ffmpeg(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg 실패: " + " ".join(cmd) + "\n" + proc.stderr[-3000:])


def humanize_piece_name(s):
    s = re.sub(r'([A-G])(Flat|Sharp)?(Major|Minor)', r' \1 \2 \3 ', s)
    s = re.sub(r'Bwv\.(\d)', r'BWV \1', s, flags=re.I)
    s = re.sub(r'(No|Op|K)\.(?=\d)', r'\1. ', s)
    s = re.sub(r'(?<=[a-zA-Z])(?=[0-9])', ' ', s)
    s = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def get_piece_key(filepath, composer_name):
    """같은 작품(교향곡/사중주/서곡 등)에 속한 악장들을 묶는 키.
    바흐 골드베르크 변주곡은 32트랙 전체가 하나의 순환곡이라 통째로 하나의
    작품 취급한다. 베토벤/모차르트는 파일명이
    '{작곡가}-{작품명}-{두자리 악장번호}-{악장이름}.mp3' 또는 악장 구분이
    없는 단일곡은 '{작곡가}-{작품명}.mp3' 형태라, 접두어를 뗀 뒤 순수
    숫자 세그먼트가 나오기 전까지를 작품명으로 본다."""
    stem = os.path.splitext(os.path.basename(filepath))[0]
    parts = stem.split('-')[1:]  # 작곡가 접두어 제거
    if composer_name == "Bach":
        return "GoldbergVariationsBwv.988"
    key_parts = []
    for p in parts:
        if p.isdigit():
            break
        key_parts.append(p)
    return "-".join(key_parts) if key_parts else stem


def get_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, check=True,
        encoding="utf-8", errors="replace",
    )
    return float(out.stdout.strip())


def _cover_crop(img, w, h):
    from PIL import Image
    sw, sh = img.size
    scale = max(w / sw, h / sh)
    nw, nh = int(sw * scale + 0.5), int(sh * scale + 0.5)
    img = img.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - w) // 2, (nh - h) // 2
    return img.crop((left, top, left + w, top + h))


def _gradient_band(w, h, band_h, max_alpha):
    from PIL import Image, ImageDraw
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for i in range(band_h):
        frac = i / band_h
        alpha = int(max_alpha * frac)
        y = h - band_h + i
        d.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))
    return overlay


def _fit_font(draw, text, font_path, max_w, start_size, min_size=18):
    from PIL import ImageFont
    size = start_size
    font = ImageFont.truetype(font_path, size)
    while size > min_size:
        font = ImageFont.truetype(font_path, size)
        bbox = draw.textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= max_w:
            break
        size -= 4
    return font


def _render_titled_portrait(portrait_img, composer_name, piece_title, w, h, show_subtitle=True,
                             title_y_frac=0.74, subtitle_gap_frac=0.035):
    from PIL import Image, ImageDraw, ImageFilter

    img = _cover_crop(portrait_img, w, h).convert("RGBA")
    img = Image.alpha_composite(img, _gradient_band(w, h, int(h * 0.46), 175))
    draw = ImageDraw.Draw(img, "RGBA")

    # 작곡가 이름 — 제일 크게, 중앙
    title = composer_name.upper()
    max_w = int(w * 0.88)
    font = _fit_font(draw, title, FONT_PATH, max_w, int(h * 0.30))
    bbox = draw.textbbox((0, 0), title, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (w - tw) // 2
    ty = int(h * title_y_frac) - th - bbox[1]

    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).text((tx + 4, ty + 6), title, font=font, fill=(0, 0, 0, 200))
    shadow = shadow.filter(ImageFilter.GaussianBlur(7))
    img = Image.alpha_composite(img, shadow)
    draw = ImageDraw.Draw(img, "RGBA")
    draw.text((tx, ty), title, font=font, fill=(255, 255, 255, 255))

    label_font = _fit_font(draw, "P L A Y L I S T", FONT_PATH, max_w, max(int(font.size * 0.22), 18))
    label = "P L A Y L I S T"
    lb = draw.textbbox((0, 0), label, font=label_font)
    lw = lb[2] - lb[0]
    draw.text(((w - lw) // 2, ty - int(font.size * 0.34)), label,
               font=label_font, fill=(255, 255, 255, 225))

    # 곡명 부제 — 작곡가 이름 바로 아래, 중간 크기 (썸네일에만 고정 표기;
    # 영상 배경에는 안 넣고 대신 재생 중 왼쪽으로 흐르는 자막으로 별도 처리)
    if show_subtitle:
        sub_font = _fit_font(draw, piece_title, FONT_PATH, max_w, int(h * 0.062), min_size=16)
        sb = draw.textbbox((0, 0), piece_title, font=sub_font)
        sw_, sh_ = sb[2] - sb[0], sb[3] - sb[1]
        sx = (w - sw_) // 2
        # 주의: sy 기준점은 ty+th(단순 텍스트 높이)가 아니라 ty+bbox[3](작곡가 이름의
        # 실제 시각적 하단)이어야 한다. bbox[1](상단 오프셋)이 0이 아닌 폰트가 많아서
        # ty+th를 쓰면 그 차이(bbox[1])만큼 위로 밀려 이름 글자와 곡명이 겹쳤었음.
        sy = ty + bbox[3] + int(h * subtitle_gap_frac)

        sub_shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(sub_shadow).text((sx + 3, sy + 4), piece_title, font=sub_font, fill=(0, 0, 0, 190))
        sub_shadow = sub_shadow.filter(ImageFilter.GaussianBlur(5))
        img = Image.alpha_composite(img, sub_shadow)
        draw = ImageDraw.Draw(img, "RGBA")
        draw.text((sx, sy), piece_title, font=sub_font, fill=(255, 255, 255, 235))

    return img.convert("RGB")


def make_thumbnails(portrait_path, composer_name, piece_title, out_bg_path, out_thumb_path):
    from PIL import Image
    portrait = Image.open(portrait_path).convert("RGB")
    # 영상 배경(bg): 곡명 없이 — 재생 중 스크롤 자막으로 대체.
    # 작곡가 이름을 화면 하단(0.74)이 아니라 중상단(0.48)에 배치 — build_video()의
    # 파형바(bar_y)와 스크롤 자막(title_y)이 화면 하단 쪽에 있어서, 이름을 기본
    # 위치(0.74)에 두면 이름 텍스트 하단이 스크롤 자막과 겹쳐 보이는 문제가 있었음.
    # 0.52도 여유가 부족하다는 피드백(2026-08-12)을 받아 0.48로 한 번 더 올려서
    # 이름 하단과 캡션바 사이 간격을 눈에 띄게 넉넉히 뒀다 — 절대 다시 낮추지 말 것.
    _render_titled_portrait(portrait, composer_name, piece_title, VIDEO_W, VIDEO_H,
                             show_subtitle=False, title_y_frac=0.48).save(out_bg_path, "PNG")
    # 썸네일: 곡명 고정 표기. 작곡가 이름을 더 위로(0.58) 올리고 곡명과의 간격을
    # 넓혀서(0.06) 곡명 자막이 프레임 하단에 눌리거나 잘 안 보이던 문제를 해결.
    _render_titled_portrait(portrait, composer_name, piece_title, 1280, 720,
                             show_subtitle=True, title_y_frac=0.58,
                             subtitle_gap_frac=0.06).save(out_thumb_path, "PNG")


def group_composer_tracks(prefix, composer_name):
    """작곡가의 모든 mp3를 작품별로 묶는다. 손상된(다운로드 실패 등) 트랙은
    건너뛰고 경고만 남긴다 — 한 트랙 때문에 전체 작업이 죽지 않도록."""
    candidates = sorted(glob.glob(os.path.join(AUDIO_DIR, prefix + "*.mp3")))
    if not candidates:
        raise RuntimeError(f"{prefix} 트랙을 찾을 수 없습니다: {AUDIO_DIR}")

    pieces = {}  # piece_key -> [(path, duration), ...]  (등장 순서 유지)
    order = []
    for f in candidates:
        try:
            dur = get_duration(f)
            if dur < 1.0:
                raise ValueError(f"재생시간 {dur:.2f}초 — 오디오로 보기 어려움")
        except Exception as e:
            log(f"   ⚠️ 손상된 트랙 스킵: {os.path.basename(f)} ({e})")
            continue
        key = get_piece_key(f, composer_name)
        if key not in pieces:
            pieces[key] = []
            order.append(key)
        pieces[key].append((f, dur))

    if not pieces:
        raise RuntimeError(f"{prefix}의 모든 트랙이 손상되어 있습니다: {AUDIO_DIR}")
    return [(key, pieces[key]) for key in order]


def concat_piece_audio(files, out_path):
    cmd = ["ffmpeg", "-y"]
    n = 0
    for i, (f, _dur) in enumerate(files):
        cmd += ["-i", f]
        n += 1
        if i < len(files) - 1:
            cmd += ["-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={TRACK_GAP_SEC}"]
            n += 1
    if n == 1:
        shutil.copy(files[0][0], out_path)
        return
    filter_complex = "".join(f"[{i}:a:0]" for i in range(n)) + f"concat=n={n}:v=0:a=1[outa]"
    cmd += ["-filter_complex", filter_complex, "-map", "[outa]",
            "-c:a", "aac", "-b:a", "192k", out_path]
    run_ffmpeg(cmd)


def _ffmpeg_text_escape(s):
    return s.replace("\\", "\\\\").replace("'", "\\'")


def build_video(bg_png, audio_path, out_path, duration, piece_title):
    """정지 배경(초상화+작곡가명) 위에 오디오 반응 파형을 겹치고, 그 위에
    곡명을 왼쪽으로 계속 흐르는 스크롤 자막으로 재생 내내 띄운다."""
    wave_w, wave_h = 1200, 220
    bar_w, bar_h = wave_w + 80, wave_h + 60
    bar_y = VIDEO_H - bar_h - 90
    title_y = bar_y - 64
    # 곡명 자막 전용 배경 바 — 초상화 배경이 밝을 때도 흰 글씨가 묻히지 않도록
    # 파형바와 같은 톤의 반투명 검정 바를 자막 줄 높이만큼 따로 깔아준다.
    title_bar_h = 60
    title_bar_y = title_y - 14
    # 절대경로를 그대로 쓰면 드라이브 문자 뒤 콜론(C:)이 ffmpeg 필터 파서의
    # key=value 구분자와 충돌해서 깨진다(실제 테스트로 확인) — run_ffmpeg가 항상
    # 저장소 루트를 cwd로 실행되므로 상대경로로 바꾸면 콜론과 비-ASCII 경로
    # (레포 경로의 'ドキュメント') 문제를 한 번에 피할 수 있다.
    try:
        font_file = os.path.relpath(FONT_PATH).replace("\\", "/")
    except ValueError:
        font_file = FONT_PATH.replace("\\", "/")
    scroll_speed = 90  # px/sec
    text = _ffmpeg_text_escape(piece_title)
    filter_complex = (
        f"[1:a]showwaves=s={wave_w}x{wave_h}:mode=cline:colors=white@0.85:rate=25,"
        f"format=rgba[wave];"
        f"[0:v]drawbox=x=(iw-{bar_w})/2:y={bar_y}:w={bar_w}:h={bar_h}:"
        f"color=black@0.35:t=fill,"
        f"drawbox=x=(iw-{bar_w})/2:y={title_bar_y}:w={bar_w}:h={title_bar_h}:"
        f"color=black@0.4:t=fill[bg0];"
        f"[bg0][wave]overlay=x=(W-w)/2:y={bar_y + (bar_h - wave_h) // 2}[bgwave];"
        f"[bgwave]drawtext=fontfile='{font_file}':text='{text}':"
        f"fontsize=40:fontcolor=white:borderw=2:bordercolor=black@0.9:"
        f"x='w-mod(({scroll_speed})*t,w+tw)':y={title_y}[vout]"
    )
    run_ffmpeg([
        "ffmpeg", "-y",
        "-loop", "1", "-i", bg_png,
        "-i", audio_path,
        "-filter_complex", filter_complex,
        "-map", "[vout]", "-map", "1:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p", "-shortest",
        "-map_metadata", "-1", "-fflags", "+bitexact",
        "-flags:v", "+bitexact", "-flags:a", "+bitexact",
        "-t", str(duration),
        out_path,
    ])


def slugify(s):
    return re.sub(r'[^A-Za-z0-9]+', '', s)


def main():
    os.makedirs(WORKDIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)

    target = (sys.argv[1] if len(sys.argv) > 1 else "all").strip().lower()
    composers = COMPOSERS if target == "all" else [
        c for c in COMPOSERS if c["name"].lower() == target]
    if not composers:
        log(f"❌ 알 수 없는 작곡가: {target} (mozart/bach/beethoven/all 중 하나)")
        raise SystemExit(1)

    today = datetime.date.today().isoformat()

    for c in composers:
        name = c["name"]
        log(f"=== {name} 작품별 영상 제작 시작 ===")
        portrait_path = os.path.join(PORTRAIT_DIR, c["portrait"])

        piece_groups = group_composer_tracks(c["prefix"], name)
        log(f"   {len(piece_groups)}개 작품 발견")

        for piece_key, files in piece_groups:
            piece_title = humanize_piece_name(piece_key)
            slug = slugify(piece_key)
            log(f"   --- {piece_title} ({len(files)}악장) ---")

            bg_png = os.path.join(WORKDIR, f"{name}_{slug}_bg.png")
            thumb_png = os.path.join(WORKDIR, f"{name}_{slug}_thumb.png")
            make_thumbnails(portrait_path, name, piece_title, bg_png, thumb_png)

            audio_path = os.path.join(WORKDIR, f"{name}_{slug}_audio.m4a")
            concat_piece_audio(files, audio_path)
            dur = get_duration(audio_path)

            final_path = os.path.join(OUT_DIR, f"{today}-claude-{name}-{slug}.mp4")
            log(f"      인코딩 중... ({dur/60:.1f}분)")
            build_video(bg_png, audio_path, final_path, dur, piece_title)
            log(f"      ✅ 완성: {final_path}")

            final_thumb_path = os.path.join(OUT_DIR, f"{today}-claude-{name}-{slug}_thumbnail.png")
            shutil.copy(thumb_png, final_thumb_path)
            shutil.copy(thumb_png, os.path.join(THUMB_DIR, f"{today}-claude-{name}-{slug}_thumbnail.png"))

    log("🎉 전체 완료")


if __name__ == "__main__":
    main()
