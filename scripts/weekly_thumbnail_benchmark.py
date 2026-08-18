#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
weekly_thumbnail_benchmark.py
─────────────────────────────────────────────────────────────
플리채널 5개 각각에 대해, 그 장르에서 실제로 잘 나가는(구독자 50만~100만+)
유튜브 채널의 제목/썸네일 패턴을 참고해서 매주 새 썸네일 5장씩 만들어
각 채널의 "썸네일" 구글드라이브 폴더에 올린다.

이미지 생성 AI(크레딧 필요)는 안 쓰고, Pexels 무료 스톡사진 API + PIL 텍스트
합성만으로 만든다(무인 자동화라 로그인 필요한 서비스는 못 씀). 유튜브
벤치마킹은 YouTube Data API로 장르별 상위 영상을 조회해 제목 패턴을 참고한다.

사용법:
    python scripts/weekly_thumbnail_benchmark.py [channel_key]
    (기본값: all — 5개 채널 전부)

필요 환경변수(Secrets):
    GOOGLE_OAUTH_CLIENT_ID/SECRET/REFRESH_TOKEN  - 드라이브 업로드용
    YOUTUBE_API_KEY                              - 벤치마킹 채널/영상 조회용
    PEXELS_API_KEY (또는 PEXELS_KEY)             - 무료 스톡사진
    GMAIL_APP_PASSWORD                            - 완료 알림 메일(선택)
"""
import os
import sys
import random
import subprocess
import requests

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
GOOGLE_OAUTH_REFRESH_TOKEN = os.environ.get("GOOGLE_OAUTH_REFRESH_TOKEN", "")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
PEXELS_KEY = os.environ.get("PEXELS_API_KEY") or os.environ.get("PEXELS_KEY", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
GMAIL_USER = "huh0303@gmail.com"

WORKDIR = "weekly_thumb_work"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(SCRIPT_DIR, "..", "playlist_output", "_nanum.ttf")
SERIF_FONT_PATH = os.path.join(SCRIPT_DIR, "..", "playlist_output", "_playfair.ttf")
ROOT_FOLDER_NAME = "플리채널"

# style: block_pop(K-pop) / script_elegant(로맨틱) / stacked_serif(클래식) /
#        minimal_caption(힐링) / block_bold(카페) — 오늘 세션에서 검증된 장르별 포맷
CHANNELS = [
    {"key": "kpop", "folder": "K-pop", "style": "block_pop",
     "queries": ["neon city night portrait", "seoul street night lights", "colorful concert lights crowd"],
     "titles": ["K-POP VIBES", "PLAYLIST", "NIGHT DRIVE MIX", "UPBEAT PLAYLIST", "CHILL K-POP"]},
    {"key": "romantic", "folder": "로맨틱글로벌음악", "style": "script_elegant",
     "queries": ["romantic couple sunset", "candlelight dinner date", "romantic travel golden hour"],
     "titles": ["Playlist", "Love Songs", "Romantic Mix", "For You", "Slow Dance"]},
    {"key": "mbb", "folder": "모짜르트_바흐_베트벤클래식", "style": "stacked_serif",
     "queries": ["classical piano concert hall", "violin close up vintage", "orchestra symphony stage lights"],
     "titles": ["RELAXING MUSIC", "CLASSICAL FOCUS", "PIANO ONLY", "STUDY CLASSICAL", "ORCHESTRA MIX"]},
    {"key": "healing", "folder": "힐링", "style": "minimal_caption",
     "queries": ["rain window forest", "calm foggy lake morning", "peaceful nature meditation"],
     "titles": ["Deep Sleep", "Rain Ambience", "Forest Calm", "Meditation", "Quiet Morning"]},
    {"key": "cafe", "folder": "스타벅스_카페음악", "style": "block_bold",
     "queries": ["coffee shop cozy interior", "jazz cafe warm light window", "coffee cup rain window"],
     "titles": ["COFFEE SHOP MUSIC", "CAFE JAZZ", "WORK & FOCUS", "MORNING CAFE", "RELAXING JAZZ"]},
]

STYLE_COLORS = {
    "block_pop": [(255, 20, 130), (0, 220, 255)],
    "block_bold": [(255, 196, 0), (255, 138, 61), (255, 255, 255)],
}


def log(msg):
    print(msg, flush=True)


def run_cmd(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError("실패: " + " ".join(cmd) + "\n" + proc.stderr[-1500:])


def get_drive_service():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    creds = Credentials(
        token=None, refresh_token=GOOGLE_OAUTH_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_OAUTH_CLIENT_ID, client_secret=GOOGLE_OAUTH_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    return build("drive", "v3", credentials=creds)


def find_folder(service, name, parent_id=None):
    q = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        q += f" and '{parent_id}' in parents"
    resp = service.files().list(q=q, fields="files(id,name)").execute()
    files = resp.get("files", [])
    if not files:
        raise RuntimeError(f"폴더를 찾을 수 없음: {name} (parent={parent_id})")
    return files[0]["id"]


def upload_to_drive(service, file_path, folder_id, name):
    from googleapiclient.http import MediaFileUpload
    metadata = {"name": name, "parents": [folder_id]}
    media = MediaFileUpload(file_path, resumable=False)
    service.files().create(body=metadata, media_body=media, fields="id").execute()


def fetch_pexels_photo(query, out_path, exclude_urls):
    if not PEXELS_KEY:
        return False
    try:
        r = requests.get(
            f"https://api.pexels.com/v1/search?query={requests.utils.quote(query)}&per_page=15&orientation=landscape",
            headers={"Authorization": PEXELS_KEY}, timeout=15,
        )
        photos = r.json().get("photos", [])
        random.shuffle(photos)
        for p in photos:
            url = p.get("src", {}).get("large2x") or p.get("src", {}).get("large", "")
            if url and url not in exclude_urls:
                img_data = requests.get(url, timeout=20).content
                with open(out_path, "wb") as f:
                    f.write(img_data)
                exclude_urls.add(url)
                return True
    except Exception as e:
        log(f"   ⚠️ Pexels 조회 실패({query}): {e}")
    return False


def benchmark_top_titles(query):
    """YouTube Data API로 해당 장르 상위 영상 제목 몇 개를 로그로 남긴다(참고용,
    구독자 50만+ 채널만 필터). 실패해도 전체 파이프라인은 계속 진행."""
    if not YOUTUBE_API_KEY:
        return []
    try:
        r = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={"part": "snippet", "q": query, "type": "video", "order": "viewCount",
                    "maxResults": 5, "key": YOUTUBE_API_KEY}, timeout=15,
        )
        items = r.json().get("items", [])
        channel_ids = [it["snippet"]["channelId"] for it in items]
        if not channel_ids:
            return []
        r2 = requests.get(
            "https://www.googleapis.com/youtube/v3/channels",
            params={"part": "statistics", "id": ",".join(channel_ids), "key": YOUTUBE_API_KEY}, timeout=15,
        )
        stats = {c["id"]: int(c["statistics"].get("subscriberCount", 0)) for c in r2.json().get("items", [])}
        results = []
        for it in items:
            subs = stats.get(it["snippet"]["channelId"], 0)
            if subs >= 500_000:
                results.append((it["snippet"]["title"], subs))
        return results
    except Exception as e:
        log(f"   ⚠️ 벤치마킹 조회 실패({query}): {e}")
        return []


def cover_crop(img, w, h):
    from PIL import Image
    sw, sh = img.size
    scale = max(w / sw, h / sh)
    nw, nh = int(sw * scale + 0.5), int(sh * scale + 0.5)
    img = img.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - w) // 2, (nh - h) // 2
    return img.crop((left, top, left + w, top + h))


def gradient_band(w, h, band_h, max_alpha):
    from PIL import Image, ImageDraw
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for i in range(band_h):
        alpha = int(max_alpha * (i / band_h))
        d.line([(0, h - band_h + i), (w, h - band_h + i)], fill=(0, 0, 0, alpha))
    return overlay


def compose_thumbnail(photo_path, title, style, out_path, w=1280, h=720):
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    img = cover_crop(Image.open(photo_path).convert("RGB"), w, h).convert("RGBA")
    draw = ImageDraw.Draw(img, "RGBA")

    if style == "minimal_caption":
        img = Image.alpha_composite(img, gradient_band(w, h, int(h * 0.28), 130))
        draw = ImageDraw.Draw(img, "RGBA")
        font = ImageFont.truetype(FONT_PATH, 46)
        bbox = draw.textbbox((0, 0), title, font=font)
        draw.text((36, h - (bbox[3] - bbox[1]) - 34), title, font=font, fill=(255, 255, 255, 240))
        img.convert("RGB").save(out_path, "PNG")
        return

    if style == "stacked_serif":
        img = Image.alpha_composite(img, gradient_band(w, h, int(h * 0.5), 165))
        draw = ImageDraw.Draw(img, "RGBA")
        size = 78
        font = ImageFont.truetype(SERIF_FONT_PATH, size)
        max_w = int(w * 0.88)
        bbox = draw.textbbox((0, 0), title, font=font)
        while bbox[2] - bbox[0] > max_w and size > 34:
            size -= 4
            font = ImageFont.truetype(SERIF_FONT_PATH, size)
            bbox = draw.textbbox((0, 0), title, font=font)
        tx = (w - (bbox[2] - bbox[0])) // 2
        ty = int(h * 0.78) - bbox[3]
        shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).text((tx + 3, ty + 5), title, font=font, fill=(0, 0, 0, 200))
        img = Image.alpha_composite(img, shadow.filter(ImageFilter.GaussianBlur(6)))
        draw = ImageDraw.Draw(img, "RGBA")
        draw.text((tx, ty), title, font=font, fill=(255, 255, 255, 255))
        img.convert("RGB").save(out_path, "PNG")
        return

    if style == "script_elegant":
        img = Image.alpha_composite(img, gradient_band(w, h, int(h * 0.35), 140))
        draw = ImageDraw.Draw(img, "RGBA")
        font = ImageFont.truetype(SERIF_FONT_PATH, 88)
        bbox = draw.textbbox((0, 0), title, font=font)
        tx, ty = 60, h - (bbox[3] - bbox[1]) - 60
        draw.text((tx, ty), title, font=font, fill=(255, 240, 225, 255))
        img.convert("RGB").save(out_path, "PNG")
        return

    # block_pop / block_bold: 굵은 컬러 텍스트(오늘 카페/K-pop 벤치마킹 스타일)
    colors = STYLE_COLORS.get(style, [(255, 255, 255)])
    color = random.choice(colors)
    img = Image.alpha_composite(img, gradient_band(w, h, int(h * 0.4), 150))
    draw = ImageDraw.Draw(img, "RGBA")
    size = 96
    font = ImageFont.truetype(FONT_PATH, size)
    max_w = int(w * 0.9)
    bbox = draw.textbbox((0, 0), title, font=font)
    while bbox[2] - bbox[0] > max_w and size > 40:
        size -= 4
        font = ImageFont.truetype(FONT_PATH, size)
        bbox = draw.textbbox((0, 0), title, font=font)
    tx = (w - (bbox[2] - bbox[0])) // 2
    ty = int(h * 0.72) - bbox[3]
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).text((tx + 3, ty + 4), title, font=font, fill=(0, 0, 0, 210))
    img = Image.alpha_composite(img, shadow.filter(ImageFilter.GaussianBlur(5)))
    draw = ImageDraw.Draw(img, "RGBA")
    draw.text((tx, ty), title, font=font, fill=color + (255,))
    img.convert("RGB").save(out_path, "PNG")


def process_channel(service, root_id, ch, today):
    key, folder_name, style = ch["key"], ch["folder"], ch["style"]
    log(f"=== [{key}] {folder_name} ===")

    channel_folder_id = find_folder(service, folder_name, root_id)
    thumb_folder_id = find_folder(service, "썸네일", channel_folder_id)

    for q in ch["queries"]:
        hits = benchmark_top_titles(q)
        for title, subs in hits[:2]:
            log(f"   벤치마크 참고: \"{title}\" ({subs:,}구독)")

    exclude_urls = set()
    uploaded = 0
    for i, title in enumerate(ch["titles"], 1):
        query = ch["queries"][i % len(ch["queries"])]
        photo_path = os.path.join(WORKDIR, f"{key}_{i:02d}_photo.jpg")
        if not fetch_pexels_photo(query, photo_path, exclude_urls):
            log(f"   ⚠️ {i}번 사진 확보 실패, 스킵")
            continue
        out_path = os.path.join(WORKDIR, f"{key}_{i:02d}_thumb.png")
        compose_thumbnail(photo_path, title, style, out_path)
        upload_to_drive(service, out_path, thumb_folder_id, f"{today}-weekly-{key}-{i:02d}.png")
        uploaded += 1
        log(f"   ✅ {i}/5 업로드 완료 ({title})")

    return uploaded


def send_summary_email(results):
    if not GMAIL_APP_PASSWORD:
        return
    import smtplib
    from email.mime.text import MIMEText
    body = "\n".join(f"- {k}: {v}장 업로드" for k, v in results.items())
    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = "[플리채널] 주간 썸네일 벤치마킹 완료"
    msg["From"] = GMAIL_USER
    msg["To"] = GMAIL_USER
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as s:
            s.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            s.sendmail(GMAIL_USER, [GMAIL_USER], msg.as_string())
    except Exception as e:
        log(f"⚠️ 이메일 발송 실패(무시): {e}")


def main():
    import datetime
    missing = [k for k, v in {
        "GOOGLE_OAUTH_CLIENT_ID": GOOGLE_OAUTH_CLIENT_ID,
        "GOOGLE_OAUTH_CLIENT_SECRET": GOOGLE_OAUTH_CLIENT_SECRET,
        "GOOGLE_OAUTH_REFRESH_TOKEN": GOOGLE_OAUTH_REFRESH_TOKEN,
    }.items() if not v]
    if missing:
        log(f"❌ 환경변수 누락: {missing}")
        raise SystemExit(1)
    if not PEXELS_KEY:
        log("❌ PEXELS_API_KEY(또는 PEXELS_KEY) 없음 — 무료 스톡사진을 못 가져옵니다")
        raise SystemExit(1)

    os.makedirs(WORKDIR, exist_ok=True)
    target = (sys.argv[1] if len(sys.argv) > 1 else "all").strip().lower()
    channels = CHANNELS if target == "all" else [c for c in CHANNELS if c["key"] == target]
    if not channels:
        log(f"❌ 알 수 없는 채널: {target}")
        raise SystemExit(1)

    service = get_drive_service()
    root_id = find_folder(service, ROOT_FOLDER_NAME)
    today = datetime.date.today().isoformat()

    results = {}
    for ch in channels:
        results[ch["key"]] = process_channel(service, root_id, ch, today)

    send_summary_email(results)
    log("🎉 전체 완료: " + ", ".join(f"{k}={v}" for k, v in results.items()))


if __name__ == "__main__":
    main()
