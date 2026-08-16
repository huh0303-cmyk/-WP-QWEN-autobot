#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
healing_ambient_longform.py
─────────────────────────────────────────────────────────────
ambient_sample_lab.py의 make_stream/make_temple_chime/make_rain은 원래
60초 미리듣기용이라, 이벤트음(빗방울 외 물방울/풍경소리 등)을 무작위 간격으로
흩뿌리는 _scatter_over_bed가 최대 150개까지만 배치한다(윈도우 커맨드라인
길이 제한 때문). 70~90분짜리를 그대로 요청하면 앞쪽 몇 분만 이벤트음이 있고
나머지는 밋밋한 배경음만 남는다.

그래서 스트림/풍경소리는 이벤트 밀도가 유지되는 짧은 세그먼트(수 분)를
여러 개 만들어 이어붙이는 방식으로 전체 길이를 채운다. 빗소리는 이벤트
오버레이 없이 필터만으로 합성되므로 원하는 길이로 한 번에 만들어도 된다.

사용법:
    python scripts/healing_ambient_longform.py <rain|stream|temple_chime|thunderstorm> <출력경로.mp3> [목표분]
"""
import os
import sys
import glob
import random
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ambient_sample_lab as lab

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

WORKDIR = "healing_longform_work"

# 사운드별로 이벤트 밀도를 안전하게 유지할 수 있는 세그먼트 길이(초).
# (세그먼트길이 / 평균간격) < 150 이 되도록 여유있게 잡음.
SEGMENT_SEC = {
    "stream": 130,
    "temple_chime": 480,
    "thunderstorm": 600,
}


def log(msg):
    print(msg, flush=True)


def run_ffmpeg(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg 실패: " + " ".join(cmd) + "\n" + proc.stderr[-2000:])


def concat_segments(seg_paths, out_path):
    list_file = os.path.join(WORKDIR, "_concat_list.txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for p in seg_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")
    run_ffmpeg(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
                "-c", "copy", out_path])


def _finalize(raw_path, out_path):
    """기존 원곡 폴더 컨벤션(.mp3)과 실제 컨테이너를 맞추기 위해, 내부적으로는
    aac/m4a로 만들고 최종 산출물만 요청받은 확장자에 맞게 트랜스코딩한다."""
    if out_path.lower().endswith(".mp3") and not raw_path.lower().endswith(".mp3"):
        run_ffmpeg(["ffmpeg", "-y", "-i", raw_path, "-c:a", "libmp3lame", "-b:a", "192k", out_path])
    elif os.path.abspath(raw_path) != os.path.abspath(out_path):
        run_ffmpeg(["ffmpeg", "-y", "-i", raw_path, "-c", "copy", out_path])


def build(sound_key, out_path, minutes):
    os.makedirs(WORKDIR, exist_ok=True)
    duration_sec = minutes * 60
    raw_path = os.path.join(WORKDIR, f"_raw_{sound_key}_{random.randint(0,999999)}.m4a")

    if sound_key == "rain":
        log(f"빗소리 {minutes:.0f}분 합성 중 (세그먼트 없이 한 번에)...")
        lab.make_rain(duration_sec, WORKDIR, raw_path)
        _finalize(raw_path, out_path)
        return

    if sound_key not in SEGMENT_SEC:
        raise ValueError(f"지원하지 않는 사운드: {sound_key}")

    fn = {"stream": lab.make_stream, "temple_chime": lab.make_temple_chime,
          "thunderstorm": lab.make_thunderstorm}[sound_key]
    seg_len = SEGMENT_SEC[sound_key]
    n_segments = max(1, round(duration_sec / seg_len))
    log(f"{sound_key} {minutes:.0f}분 목표 -> {n_segments}개 세그먼트(~{seg_len}초씩)로 분할 생성...")

    seg_paths = []
    for i in range(n_segments):
        seg_path = os.path.join(WORKDIR, f"_seg_{sound_key}_{i:03d}.m4a")
        fn(seg_len, WORKDIR, seg_path)
        seg_paths.append(seg_path)
        log(f"   세그먼트 {i+1}/{n_segments} 완료")

    log("세그먼트 이어붙이는 중...")
    concat_segments(seg_paths, raw_path)
    _finalize(raw_path, out_path)


def main():
    if len(sys.argv) < 3:
        log("사용법: python scripts/healing_ambient_longform.py <rain|stream|temple_chime> <출력경로> [목표분]")
        raise SystemExit(1)
    sound_key = sys.argv[1]
    out_path = sys.argv[2]
    minutes = float(sys.argv[3]) if len(sys.argv) > 3 else random.uniform(70, 90)
    build(sound_key, out_path, minutes)
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                           "-of", "default=noprint_wrappers=1:nokey=1", out_path],
                          capture_output=True, text=True).stdout.strip()
    log(f"✅ 완료: {out_path} ({float(dur)/60:.1f}분)")


if __name__ == "__main__":
    main()
