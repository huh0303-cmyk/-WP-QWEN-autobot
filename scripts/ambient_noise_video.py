#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ambient_noise_video.py
─────────────────────────────────────────────────────────────
백색소음/힐링 사운드 장르(예: "명문대 도서관 백색소음", 수면/집중용 앰비언스)
장시간(수십분~수시간) 영상을 자동 생성한다. 실제 녹음이 아니라 여러 색상의
노이즈를 겹치고 불규칙한 변화를 줘서 "기계적으로 들리는 단조로운 노이즈"
티가 최대한 안 나게 만든다.

사용법:
    python scripts/ambient_noise_video.py "주제" [분]
    (또는 TOPIC_KEYWORD / DURATION_MIN 환경변수)

필요 환경변수(Secrets):
    GEMINI_API_KEY - 배경 이미지 생성(선택, 없으면 단색 배경으로 폴백)

필요 시스템 도구: ffmpeg, ffprobe
"""

import os
import sys
import random
import base64
import subprocess

import requests

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_IMAGE_MODELS = ["gemini-2.5-flash-image", "gemini-2.5-flash-image-preview"]

WORKDIR = "ambient_output"
VIDEO_W, VIDEO_H = 1920, 1080


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


def gemini_generate_image(prompt, out_path):
    print("BLOCKED: legacy automated image generation is disabled")
    return False
    # 2026-08-22: 무료(Gemini) 우선, 실패하면 OpenAI 유료 폴백(사용자 지시
    # "이미지도 돈안드는것 최우선" — curio_longform.py와 동일 원칙).
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

    try:
        from openai_text import openai_available, openai_generate_image
        if openai_available() and openai_generate_image(prompt, out_path):
            return True
    except ImportError:
        pass
    return False


def build_ambient_noise(duration_sec, out_path, workdir):
    """도서관/서재 백색소음: 브라운+핑크 노이즈를 겹쳐서 기본 톤을 만들고,
    서로 배수 관계가 아닌 두 개의 아주 느린 트레몰로를 곱해 "일정 주기로
    반복되는" 티가 안 나는 자연스러운 숨쉬기를 만든다. 그 위에 불규칙한
    간격으로 아주 작은 '페이지 넘기는' 느낌의 미세한 틱 소리를 흩뿌려서
    완전히 균일한 기계음처럼 들리지 않게 한다."""
    base = os.path.join(workdir, "_ambient_base.m4a")
    run_ffmpeg([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"anoisesrc=color=brown:amplitude=0.20:duration={duration_sec}",
        "-f", "lavfi", "-i", f"anoisesrc=color=pink:amplitude=0.07:duration={duration_sec}",
        "-filter_complex",
        "[0:a][1:a]amix=inputs=2:duration=first:normalize=0,"
        "tremolo=f=0.1:d=0.08,tremolo=f=0.13:d=0.06[out]",
        "-map", "[out]", "-c:a", "aac", base,
    ])

    click = os.path.join(workdir, "_ambient_click.wav")
    run_ffmpeg([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anoisesrc=color=white:amplitude=1.0:duration=0.08",
        "-af", "afade=t=out:st=0.02:d=0.06,volume=0.16", click,
    ])

    n_ticks = max(4, int(duration_sec / 50))
    max_delay_ms = max(int(duration_sec * 1000) - 3000, 3000)
    delays = sorted(random.sample(range(2000, max_delay_ms), min(n_ticks, max_delay_ms // 2000)))

    inputs = ["-i", base]
    for _ in delays:
        inputs += ["-i", click]

    filter_parts = []
    mix_labels = "[0:a]"
    for i, d in enumerate(delays):
        filter_parts.append(f"[{i+1}:a]adelay={d}|{d}[c{i}]")
        mix_labels += f"[c{i}]"
    filter_parts.append(f"{mix_labels}amix=inputs={len(delays)+1}:duration=first:normalize=0[out]")
    filter_complex = ";".join(filter_parts)

    run_ffmpeg([
        "ffmpeg", "-y", *inputs,
        "-filter_complex", filter_complex,
        "-map", "[out]", "-c:a", "aac", "-b:a", "192k", out_path,
    ])


def make_kenburns_clip(image_path, out_path, duration, fps=25):
    frames = max(int(duration * fps), 1)
    vf = (f"scale=2560:-1,zoompan=z='min(zoom+0.00008,1.06)':d={frames}:"
          f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={VIDEO_W}x{VIDEO_H}:fps={fps},"
          f"format=yuv420p")
    run_ffmpeg(["ffmpeg", "-y", "-loop", "1", "-i", image_path, "-vf", vf,
                "-r", str(fps), "-t", str(duration), "-c:v", "libx264",
                "-pix_fmt", "yuv420p", out_path])


def main():
    topic = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TOPIC_KEYWORD", "명문대 도서관")
    minutes = float(sys.argv[2]) if len(sys.argv) > 2 else float(os.environ.get("DURATION_MIN", "70"))
    duration_sec = minutes * 60

    os.makedirs(WORKDIR, exist_ok=True)

    log(f"1/3 배경 이미지 생성 중 (주제: {topic})...")
    bg_path = os.path.join(WORKDIR, "bg.png")
    ok = False
    if GEMINI_API_KEY:
        prompt = (f"A cozy, warmly lit old gothic-revival collegiate library reading room, "
                  f"generic ivy-league aesthetic (not a specific real-world landmark), tall "
                  f"wooden bookshelves, soft afternoon light through tall windows, empty "
                  f"reading tables with brass lamps, real photograph, not a painting, not "
                  f"illustration, cinematic wide 16:9, no text, no people, no watermark. "
                  f"Mood: {topic}")
        for _ in range(3):
            if gemini_generate_image(prompt, bg_path):
                ok = True
                break
    if not ok:
        from PIL import Image
        Image.new("RGB", (1920, 1080), (40, 30, 20)).save(bg_path)
        log("   ⚠️ 이미지 생성 실패 → 단색 배경 대체")

    log(f"2/3 백색소음 {minutes:.0f}분 합성 중...")
    audio_path = os.path.join(WORKDIR, "ambient_audio.m4a")
    build_ambient_noise(duration_sec, audio_path, WORKDIR)

    log("3/3 영상 조립 중...")
    visual_path = os.path.join(WORKDIR, "visual.mp4")
    make_kenburns_clip(bg_path, visual_path, duration_sec)
    final_path = os.path.join(WORKDIR, "final.mp4")
    run_ffmpeg(["ffmpeg", "-y", "-i", visual_path, "-i", audio_path,
                "-c:v", "copy", "-c:a", "aac", "-shortest", final_path])

    log(f"✅ 완료: {final_path} ({get_duration(final_path)/60:.1f}분)")


if __name__ == "__main__":
    main()
