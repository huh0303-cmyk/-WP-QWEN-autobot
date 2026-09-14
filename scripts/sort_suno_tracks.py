#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sort_suno_tracks.py
─────────────────────────────────────────────────────────────
Suno로 만든 mp3 수백~수천 곡이 보컬 언어(한국어/독일어/일본어 등)와
연주곡(instrumental)이 섞여 있을 때, 사람이 일일이 안 들어봐도 되게
자동으로 분류해서 폴더별로 복사해주는 일회성 로컬 도구.

원리: faster-whisper(무료 오픈소스 음성인식 모델, tiny 사이즈)로 각 파일
앞부분을 인식해서 - 보컬(가사)이 감지되면 그 언어로, 감지 안 되면
instrumental로 분류한다. API 키/비용 없음, 전부 로컬에서 실행됨.

사용법:
    pip install faster-whisper
    python scripts/sort_suno_tracks.py "G:\\내 드라이브\\suno_tracks"

결과: <입력폴더>/sorted/{instrumental, korean, german, japanese, other}/
      에 파일을 복사(원본은 그대로 둠).
"""
import os
import sys
import shutil

LANG_MAP = {
    "ko": "korean", "de": "german", "ja": "japanese", "en": "english",
    "vi": "vietnamese", "ru": "russian", "it": "italian", "fr": "french",
    "zh": "chinese", "es": "spanish",
}
AUDIO_EXT = (".mp3", ".wav", ".m4a", ".flac")


def log(msg):
    print(msg, flush=True)


def main():
    if len(sys.argv) < 2:
        log("사용법: python scripts/sort_suno_tracks.py <입력폴더>")
        raise SystemExit(1)

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        log("먼저 설치: pip install faster-whisper")
        raise SystemExit(1)

    src_dir = sys.argv[1]
    out_dir = os.path.join(src_dir, "sorted")

    files = sorted(f for f in os.listdir(src_dir) if f.lower().endswith(AUDIO_EXT))
    if not files:
        log(f"{src_dir}에 오디오 파일이 없습니다.")
        return

    log(f"총 {len(files)}개 파일 분석 시작 (tiny 모델 로딩 중...)")
    model = WhisperModel("tiny", device="cpu", compute_type="int8")

    counts = {}
    for i, fname in enumerate(files, 1):
        path = os.path.join(src_dir, fname)
        try:
            # vad_filter=True: 음성 구간(VAD)이 없으면 segments가 비어있음 -> 연주곡 신호
            segments, info = model.transcribe(path, beam_size=1, vad_filter=True)
            has_speech = next(segments, None) is not None
            lang, prob = info.language, info.language_probability
        except Exception as e:
            log(f"  [{i}/{len(files)}] {fname}: 분석 실패({e}) -> other")
            has_speech, lang, prob = False, None, 0.0

        if not has_speech or prob < 0.5:
            category = "instrumental"
        else:
            category = LANG_MAP.get(lang, "other")

        dest_dir = os.path.join(out_dir, category)
        os.makedirs(dest_dir, exist_ok=True)
        shutil.copy2(path, os.path.join(dest_dir, fname))
        counts[category] = counts.get(category, 0) + 1
        log(f"  [{i}/{len(files)}] {fname} -> {category}"
            + (f" (lang={lang}, {prob:.2f})" if has_speech else ""))

    log("\n완료 — 결과: " + out_dir)
    for cat, n in sorted(counts.items(), key=lambda x: -x[1]):
        log(f"  {cat}: {n}개")


if __name__ == "__main__":
    main()
