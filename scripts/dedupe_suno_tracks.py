#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dedupe_suno_tracks.py
─────────────────────────────────────────────────────────────
Suno에서 대량 다운받은 mp3 중 "제목만 다르고 실제로는 같은 곡"인 중복을
오디오 내용 자체(Chromaprint 지문)로 찾아낸다. 제목/파일명은 전혀 신뢰하지
않는다.

안전 설계: 절대 파일을 삭제하지 않는다. 중복으로 판정된 곡들 중 비트레이트가
가장 높은(음질이 가장 좋은) 파일만 원래 자리에 남기고, 나머지는
<입력폴더>/_duplicates_review/ 로 "이동"만 한다. 실제 삭제는 그 폴더를
직접 확인한 뒤 사람이 판단해서 지우는 것을 권장한다.

필요 프로그램:
    - ffmpeg / ffprobe (이미 설치돼 있다고 가정)
    - fpcalc (Chromaprint) - https://github.com/acoustid/chromaprint/releases
      에서 운영체제에 맞는 걸 받아서 PATH에 추가하거나, --fpcalc 옵션으로
      실행파일 경로를 직접 지정

    pip install pyacoustid

사용법:
    python scripts/dedupe_suno_tracks.py "폴더경로" [--threshold 0.95] [--fpcalc "C:\\tools\\fpcalc.exe"]
"""
import os
import sys
import shutil
import argparse
import subprocess
from collections import defaultdict

AUDIO_EXT = (".mp3", ".wav", ".m4a", ".flac")


def log(msg):
    print(msg, flush=True)


def get_duration_bitrate(ffprobe_path, path):
    out = subprocess.run(
        [ffprobe_path, "-v", "error", "-show_entries",
         "format=duration,bit_rate", "-of",
         "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    lines = out.stdout.strip().splitlines()
    duration = float(lines[0]) if len(lines) > 0 and lines[0] else 0.0
    bitrate = int(lines[1]) if len(lines) > 1 and lines[1].isdigit() else 0
    return duration, bitrate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--threshold", type=float, default=0.95,
                     help="0~1, 높을수록 더 엄격하게(완전히 같은 곡만) 중복 판정 (기본 0.95)")
    ap.add_argument("--fpcalc", default="fpcalc",
                     help="fpcalc 실행파일 경로 (기본: PATH에서 찾음)")
    ap.add_argument("--ffprobe", default="ffprobe")
    args = ap.parse_args()

    try:
        import acoustid
    except ImportError:
        log("먼저 설치: pip install pyacoustid")
        raise SystemExit(1)

    files = sorted(f for f in os.listdir(args.folder) if f.lower().endswith(AUDIO_EXT))
    if not files:
        log(f"{args.folder}에 오디오 파일이 없습니다.")
        return
    log(f"총 {len(files)}개 파일 지문(fingerprint) 추출 중...")

    info = {}  # fname -> {duration, bitrate, fp}
    for i, fname in enumerate(files, 1):
        path = os.path.join(args.folder, fname)
        try:
            duration, encoded_fp = acoustid.fingerprint_file(path, force_fpcalc=True)
            _, bitrate = get_duration_bitrate(args.ffprobe, path)
            info[fname] = {"duration": duration, "bitrate": bitrate, "fp": encoded_fp}
        except Exception as e:
            log(f"  [{i}/{len(files)}] {fname}: 지문 추출 실패({e}) -> 건너뜀")
        if i % 50 == 0:
            log(f"  ...{i}/{len(files)} 처리됨")

    # 재생시간이 비슷한 것들끼리만 묶어서 비교(전부 O(n^2) 하면 느림).
    # 진짜 같은 곡이면 재생시간도 거의 같을 수밖에 없음.
    buckets = defaultdict(list)
    for fname, d in info.items():
        buckets[round(d["duration"])].append(fname)

    log("중복 그룹 탐색 중...")
    visited = set()
    groups = []
    fnames_sorted = list(info.keys())
    for fname in fnames_sorted:
        if fname in visited:
            continue
        dur = round(info[fname]["duration"])
        candidates = buckets[dur] + buckets.get(dur - 1, []) + buckets.get(dur + 1, [])
        group = [fname]
        visited.add(fname)
        for other in candidates:
            if other == fname or other in visited:
                continue
            try:
                score = acoustid.compare_fingerprints(
                    (info[fname]["duration"], info[fname]["fp"]),
                    (info[other]["duration"], info[other]["fp"]),
                )
            except Exception:
                score = 0.0
            if score >= args.threshold:
                group.append(other)
                visited.add(other)
        if len(group) > 1:
            groups.append(group)

    if not groups:
        log("중복으로 의심되는 곡이 없습니다.")
        return

    review_dir = os.path.join(args.folder, "_duplicates_review")
    os.makedirs(review_dir, exist_ok=True)

    log(f"\n중복 그룹 {len(groups)}개 발견 — 음질(비트레이트) 가장 좋은 것만 남기고 나머지는 "
        f"{review_dir} 로 이동합니다 (삭제 아님, 직접 확인 후 지우세요).")
    total_moved = 0
    for group in groups:
        group.sort(key=lambda f: info[f]["bitrate"], reverse=True)
        keep, drop = group[0], group[1:]
        log(f"\n[유지] {keep} ({info[keep]['bitrate']//1000 if info[keep]['bitrate'] else '?'}kbps)")
        for fname in drop:
            src = os.path.join(args.folder, fname)
            dst = os.path.join(review_dir, fname)
            shutil.move(src, dst)
            total_moved += 1
            log(f"  [이동] {fname} ({info[fname]['bitrate']//1000 if info[fname]['bitrate'] else '?'}kbps) -> _duplicates_review/")

    log(f"\n완료 — 중복 그룹 {len(groups)}개, 이동된 파일 {total_moved}개.")
    log(f"'{review_dir}' 폴더를 확인해서 문제 없으면 직접 삭제해주세요.")


if __name__ == "__main__":
    main()
