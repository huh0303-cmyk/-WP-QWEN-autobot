#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
breakdown_other_lang.py
sort_suno_tracks.py가 "other" 폴더로 분류한 곡들의 실제 감지 언어를
집계해서 보여준다 (파일을 옮기지 않고 카운트만).

사용법:
    python scripts/breakdown_other_lang.py "G:\\내 드라이브\\Suno_음악_원곡다운로드\\sorted\\other"
"""
import os
import sys
from collections import Counter

AUDIO_EXT = (".mp3", ".wav", ".m4a", ".flac")


def main():
    if len(sys.argv) < 2:
        print("사용법: python scripts/breakdown_other_lang.py <other폴더경로>")
        raise SystemExit(1)

    from faster_whisper import WhisperModel

    src_dir = sys.argv[1]
    files = sorted(f for f in os.listdir(src_dir) if f.lower().endswith(AUDIO_EXT))
    print(f"총 {len(files)}개 분석 중...")

    model = WhisperModel("tiny", device="cpu", compute_type="int8")
    counts = Counter()

    for i, fname in enumerate(files, 1):
        path = os.path.join(src_dir, fname)
        try:
            _, info = model.transcribe(path, beam_size=1, vad_filter=True)
            counts[info.language] += 1
        except Exception:
            counts["ERROR"] += 1
        if i % 50 == 0:
            print(f"  ...{i}/{len(files)}")

    print("\n언어별 개수:")
    for lang, n in counts.most_common():
        print(f"  {lang}: {n}개")


if __name__ == "__main__":
    main()
