"""
2단계 (영상): TTS 오디오 + 도입부(첫 4장, 각 6초 켄번즈 클립) + 본편(나머지 이미지 전부 켄번즈,
              나레이션에 맞춰 자주 컷 전환) + 화자 타임라인 기반 정밀 자막(SRT, 크고 굵게 번인)을
              합쳐 최종 MP4를 만듭니다.

ffmpeg를 직접 호출하는 방식입니다 (moviepy보다 이 환경에서 훨씬 빠르고 안정적으로 검증됨).
"""
import glob
import json
import os
import re
import subprocess
import tempfile

import requests

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")
VIDEO_SIZE = (1280, 720)
INTRO_CLIP_COUNT = 4            # 도입부에 쓸 이미지 수 (각각 켄번즈 클립으로)
INTRO_CLIP_DURATION_SEC = 6.0   # 도입부 클립 1개당 길이
MIN_IMAGE_DURATION_SEC = 3.0    # 본편에서 이미지 1장이 화면에 남는 최소 시간 (너무 빨리 안 바뀌게)

FONT_PATH_LATIN = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_PATH_CJK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"


def _run(cmd: list, timeout: int = 280):
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 명령 실패: {' '.join(cmd)}\n{result.stderr[-2000:]}")
    return result


def _ffprobe_duration(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, timeout=30,
    )
    return float(result.stdout.strip())


def _fetch_from_pexels(keyword: str, out_path: str) -> bool:
    headers = {"Authorization": PEXELS_API_KEY}
    r = requests.get(
        "https://api.pexels.com/v1/search", headers=headers,
        params={"query": keyword, "per_page": 1, "orientation": "landscape"}, timeout=30,
    )
    if r.status_code != 200:
        return False
    photos = r.json().get("photos", [])
    if not photos:
        return False
    url = photos[0]["src"]["large2x"]
    img = requests.get(url, timeout=60)
    with open(out_path, "wb") as f:
        f.write(img.content)
    return True


def _fetch_from_pixabay(keyword: str, out_path: str) -> bool:
    if not PIXABAY_API_KEY:
        return False
    r = requests.get(
        "https://pixabay.com/api/",
        params={"key": PIXABAY_API_KEY, "q": keyword, "per_page": 3,
                "image_type": "photo", "orientation": "horizontal", "safesearch": "true"},
        timeout=30,
    )
    if r.status_code != 200:
        return False
    hits = r.json().get("hits", [])
    if not hits:
        return False
    url = hits[0]["largeImageURL"]
    img = requests.get(url, timeout=60)
    with open(out_path, "wb") as f:
        f.write(img.content)
    return True


def _fetch_images(keywords: list, out_dir: str) -> list:
    """Pexels 우선 검색, 실패하면 Pixabay로 자동 폴백."""
    paths = []
    for i, kw in enumerate(keywords):
        path = os.path.join(out_dir, f"{i:02d}_{re.sub(r'[^a-z0-9]+', '_', kw.lower())}.jpg")
        try:
            if _fetch_from_pexels(kw, path):
                paths.append(path)
                continue
        except Exception as e:
            print(f"[Video] Pexels 실패 ('{kw}'): {e}")

        try:
            if _fetch_from_pixabay(kw, path):
                print(f"[Video] '{kw}' → Pixabay로 대체 성공")
                paths.append(path)
                continue
        except Exception as e:
            print(f"[Video] Pixabay도 실패 ('{kw}'): {e}")

        print(f"[Video] 경고: '{kw}' 이미지를 찾지 못해 건너뜀 (Pexels/Pixabay 둘 다 실패)")

    if not paths:
        raise RuntimeError("배경 이미지를 하나도 가져오지 못했습니다. Pexels/Pixabay API 키를 확인하세요.")
    return paths


def _build_kenburns_clip(image_path: str, duration_sec: float, out_path: str, variant: int = 0):
    """이미지 1장을 켄번즈(천천히 줌인/줌아웃 + 살짝 팬) 애니메이션 클립으로 변환 (무료, ffmpeg zoompan).
    variant로 줌 방향/팬 방향을 살짝씩 바꿔서 이미지가 많아도 단조롭지 않게 한다."""
    w, h = VIDEO_SIZE
    fps = 25
    frames = max(int(duration_sec * fps), 1)
    zoom_rate = 0.0012 + (variant % 3) * 0.0003

    zoom_in = variant % 2 == 0
    if zoom_in:
        zexpr = f"if(lte(zoom,1.0),1.0,min(zoom+{zoom_rate},1.16))"
    else:
        zexpr = f"if(lte(zoom,1.0),1.16,max(zoom-{zoom_rate},1.0))"

    pans = [
        ("iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),                        # 중앙
        ("0", "ih/2-(ih/zoom/2)"),                                        # 좌→
        ("iw-(iw/zoom)", "ih/2-(ih/zoom/2)"),                             # →우
        ("iw/2-(iw/zoom/2)", "0"),                                        # 위→
    ]
    px, py = pans[variant % len(pans)]

    _run([
        "ffmpeg", "-y", "-loop", "1", "-i", image_path, "-t", str(duration_sec),
        "-vf", (
            f"scale={w*2}:{h*2},"
            f"zoompan=z='{zexpr}':x='{px}':y='{py}':d={frames}:s={w}x{h}:fps={fps}"
        ),
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        out_path,
    ])


def _timeline_to_srt(timeline: list, srt_path: str, max_words_per_cue: int = 8):
    """화자 타임라인(ms 단위)을 SRT 자막 파일로 변환. 자막 줄을 8단어 단위로 쪼갬."""
    def ms_to_srt_time(ms):
        ms = int(ms)
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        s, ms = divmod(ms, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def chunk_words(text, max_words):
        words = text.split()
        return [" ".join(words[i:i + max_words]) for i in range(0, len(words), max_words)]

    lines = []
    idx = 1
    for seg in timeline:
        chunks = chunk_words(seg["text"], max_words_per_cue)
        total_chars = sum(len(c) for c in chunks) or 1
        t = seg["start_ms"]
        for c in chunks:
            dur = max(int(seg["duration_ms"] * (len(c) / total_chars)), 800)
            start, end = t, t + dur
            lines.append(f"{idx}\n{ms_to_srt_time(start)} --> {ms_to_srt_time(end)}\n{c}\n")
            idx += 1
            t = end

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return idx - 1


def _burn_subtitles(video_in: str, srt_path: str, video_out: str, lang: str):
    """시니어 채널용 큼직하고 가독성 높은 자막 번인 (흰 글씨 + 두꺼운 검은 테두리 + 그림자)."""
    font_name = "DejaVu Sans Bold" if lang == "en" else "Noto Sans CJK Black"
    style = (
        f"FontName={font_name},Bold=1,FontSize=38,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H80000000,"
        "BorderStyle=1,Outline=4,Shadow=2,Alignment=2,MarginV=60"
    )
    _run([
        "ffmpeg", "-y", "-i", video_in,
        "-vf", f"subtitles={srt_path}:force_style='{style}'",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24", "-c:a", "copy",
        video_out,
    ])


def build_video(
    script_text: str,
    scene_keywords: str,
    audio_path: str,
    timeline: list,
    lang: str,
    out_path: str,
) -> str:
    """
    최종 MP4 생성 파이프라인:
    1) Pexels/Pixabay에서 장면별 이미지 다수 확보 (스크립트당 45~60개 키워드 → 이미지 다수)
    2) 첫 INTRO_CLIP_COUNT(4)장 → 각각 INTRO_CLIP_DURATION_SEC(6초) 켄번즈 클립 → 도입부
    3) 나머지 이미지 전부 → 켄번즈 클립 (남은 시간을 이미지 수만큼 균등 분할, 나레이션 흐름에 맞춰
       자주 컷 전환되도록 함 — 정지 슬라이드쇼가 아니라 이미지 하나하나가 다 살아 움직임)
    4) 모든 클립 이어붙이기 → 오디오 합성 (정확히 오디오 길이로 클리핑)
    5) 타임라인 기반 SRT 생성 → 시니어용 큰 굵은 글씨로 번인
    """
    total_duration = _ffprobe_duration(audio_path)
    keywords = [k.strip() for k in scene_keywords.split(",") if k.strip()] or ["senior healthy lifestyle"]

    with tempfile.TemporaryDirectory() as tmp:
        print(f"[Video] Pexels/Pixabay 이미지 다운로드 중... (키워드 {len(keywords)}개)")
        images = _fetch_images(keywords, tmp)
        print(f"[Video] 이미지 {len(images)}장 확보")

        intro_images = images[:INTRO_CLIP_COUNT]
        main_images = images[INTRO_CLIP_COUNT:] or images  # 이미지가 부족하면 재사용

        clip_paths = []

        print(f"[Video] 도입부 클립 {len(intro_images)}개(각 {INTRO_CLIP_DURATION_SEC:.0f}초, 켄번즈) 생성 중...")
        intro_total = 0.0
        for i, img in enumerate(intro_images):
            clip_path = os.path.join(tmp, f"intro_{i:02d}.mp4")
            _build_kenburns_clip(img, INTRO_CLIP_DURATION_SEC, clip_path, variant=i)
            clip_paths.append(clip_path)
            intro_total += INTRO_CLIP_DURATION_SEC

        remaining_duration = max(total_duration - intro_total, 1.0)
        n_main = max(len(main_images), 1)
        per_image = max(remaining_duration / n_main, MIN_IMAGE_DURATION_SEC)
        # per_image가 최소값에 걸려 합계가 남은 시간을 넘길 수 있으니, 넘는 만큼은 마지막 클립에서 흡수
        print(f"[Video] 본편 클립 {n_main}개(이미지당 약 {per_image:.1f}초, 켄번즈) 생성 중... "
              f"— 나레이션에 맞춰 자주 전환됨")
        for i, img in enumerate(main_images):
            clip_path = os.path.join(tmp, f"main_{i:03d}.mp4")
            _build_kenburns_clip(img, per_image, clip_path, variant=INTRO_CLIP_COUNT + i)
            clip_paths.append(clip_path)

        print(f"[Video] 클립 {len(clip_paths)}개 이어붙이는 중...")
        join_list = os.path.join(tmp, "join.txt")
        with open(join_list, "w") as f:
            for p in clip_paths:
                f.write(f"file '{p}'\n")
        combined = os.path.join(tmp, "combined.mp4")
        _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", join_list, "-c", "copy", combined])

        print("[Video] 오디오 합성 중...")
        with_audio = os.path.join(tmp, "with_audio.mp4")
        _run([
            "ffmpeg", "-y", "-i", combined, "-i", audio_path, "-t", f"{total_duration:.2f}",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", with_audio,
        ])

        print("[Video] 자막(SRT) 생성 중...")
        srt_path = os.path.join(tmp, "captions.srt")
        n_cues = _timeline_to_srt(timeline, srt_path)
        print(f"[Video] 자막 큐 {n_cues}개 생성됨")

        print("[Video] 자막 번인 중 (최종 인코딩)...")
        _burn_subtitles(with_audio, srt_path, out_path, lang)

    print(f"[Video] 완료: {out_path}")
    return out_path
