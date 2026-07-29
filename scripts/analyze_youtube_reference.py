#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_youtube_reference.py
─────────────────────────────────────────────────────────────
레퍼런스 유튜브 영상 URL을 받아, 영상/오디오/자막을 내려받아 훅 패턴,
제목 패턴, 구성 순서, 영상미(구도/색감/자막 스타일), 나레이션 톤 등
"포맷과 스타일"만 추출해서 요약 리포트를 만든다.

★ 원본 내용을 그대로 베끼는 용도가 아니라, 스타일/구성 참고용 분석이다.
  다운로드한 영상 원본/프레임/대본 원문은 저장소에 남기지 않고
  임시 폴더에서만 쓰고 분석이 끝나면 버린다. 결과는 "패턴 요약"만 남는다.

★ 주의: yt-dlp로 영상을 내려받는 것은 유튜브 이용약관상 비공식 다운로드에
  해당할 수 있다. 개인 리서치/스타일 참고 목적으로만 사용할 것.

사용법:
    python scripts/analyze_youtube_reference.py <유튜브URL> [<유튜브URL2> ...]
    (또는 REFERENCE_URLS 환경변수에 콤마로 구분해서 전달)

필요 환경변수(Secrets):
    GEMINI_API_KEY - 멀티모달(텍스트+이미지+오디오) 분석용

필요 시스템 도구: yt-dlp, ffmpeg, ffprobe
"""

import os
import sys
import json
import base64
import shutil
import subprocess
import requests

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"

WORKDIR = "ref_analysis_tmp"
NUM_FRAMES = 12
NUM_AUDIO_SAMPLES = 3
AUDIO_SAMPLE_SEC = 15


def log(msg):
    print(msg, flush=True)


def run(cmd, timeout=600):
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"명령 실패: {' '.join(cmd)}\n{proc.stderr[-2000:]}")
    return proc.stdout


def get_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


# ════════════════════════════════════════════════════════════
# 1) 다운로드 (영상+오디오+자막)
# ════════════════════════════════════════════════════════════
def download_video(url, out_dir):
    video_path = os.path.join(out_dir, "video.mp4")
    run(["yt-dlp", "-f", "best[height<=720]/best", "-o", video_path,
         "--no-playlist", url], timeout=900)
    if not os.path.exists(video_path):
        # 확장자가 다르게 저장됐을 수 있어 폴더에서 재탐색
        for f in os.listdir(out_dir):
            if f.startswith("video."):
                video_path = os.path.join(out_dir, f)
                break
    return video_path


def download_transcript(url, out_dir):
    base = os.path.join(out_dir, "subs")
    try:
        run(["yt-dlp", "--skip-download", "--write-auto-sub", "--write-sub",
             "--sub-lang", "ko.*,en.*", "--convert-subs", "srt",
             "-o", base, "--no-playlist", url], timeout=300)
    except Exception as e:
        log(f"   ⚠️ 자막 다운로드 실패: {e}")
        return ""

    for f in os.listdir(out_dir):
        if f.startswith("subs") and f.endswith(".srt"):
            with open(os.path.join(out_dir, f), encoding="utf-8", errors="ignore") as fp:
                return fp.read()
    return ""


def srt_to_plain(srt_text, max_chars=6000):
    lines = []
    for line in srt_text.splitlines():
        line = line.strip()
        if not line or line.isdigit() or "-->" in line:
            continue
        lines.append(line)
    text = " ".join(lines)
    return text[:max_chars]


# ════════════════════════════════════════════════════════════
# 2) 프레임/오디오 샘플 추출
# ════════════════════════════════════════════════════════════
def extract_frames(video_path, out_dir, n=NUM_FRAMES):
    duration = get_duration(video_path)
    frame_paths = []
    for i in range(n):
        t = duration * (i + 0.5) / n
        fp = os.path.join(out_dir, f"frame_{i:02d}.jpg")
        run(["ffmpeg", "-y", "-ss", str(t), "-i", video_path,
             "-frames:v", "1", "-q:v", "3", fp], timeout=60)
        if os.path.exists(fp):
            frame_paths.append(fp)
    return frame_paths


def extract_audio_samples(video_path, out_dir, n=NUM_AUDIO_SAMPLES, sec=AUDIO_SAMPLE_SEC):
    duration = get_duration(video_path)
    paths = []
    for i in range(n):
        start = max(duration * (i + 0.5) / n - sec / 2, 0)
        ap = os.path.join(out_dir, f"audio_{i:02d}.mp3")
        run(["ffmpeg", "-y", "-ss", str(start), "-t", str(sec), "-i", video_path,
             "-vn", "-acodec", "libmp3lame", "-b:a", "96k", ap], timeout=60)
        if os.path.exists(ap):
            paths.append(ap)
    return paths


# ════════════════════════════════════════════════════════════
# 3) Gemini 멀티모달 스타일 분석
# ════════════════════════════════════════════════════════════
def build_inline_part(path, mime_type):
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")
    return {"inline_data": {"mime_type": mime_type, "data": data}}


def analyze_style(title, transcript_plain, frame_paths, audio_paths):
    parts = [{"text": f"""아래는 벤치마킹용 유튜브 레퍼런스 영상 분석 요청입니다.
영상 제목: {title}

**중요**: 이 분석은 원본 내용을 그대로 베끼기 위한 게 아니라, "포맷/스타일 패턴"만
추출해서 완전히 다른 주제의 오리지널 콘텐츠를 만들 때 참고하기 위함입니다.
절대 원문 문장을 그대로 옮기지 말고, 패턴을 요약/일반화해서 설명하세요.

아래 순서로 분석해주세요:
1. 제목 패턴 (어떤 구조/공식으로 되어있는지, 일반화된 템플릿으로)
2. 도입부 훅 방식 (질문형/반전형/공포소구 등 어떤 기법을 쓰는지)
3. 전체 구성 순서 (도입-본론-결론이 각각 몇 %쯤 차지하는지, 어떤 순서로 정보를 배치하는지)
4. 나레이션 톤/속도/문체 (오디오 샘플 참고, 존댓말/반말, 격식/구어체, 속도감)
5. 화면 구도/색감/편집 스타일 (프레임 이미지 참고 — 인물 유무, 텍스트 오버레이 위치/폰트 느낌,
   색조, 컷 전환 리듬 추정)
6. 우리 파이프라인에 바로 적용할 수 있는 구체적 개선 제안 3~5개

자막 발췌(참고용, 그대로 인용 최소화):
{transcript_plain[:3000]}
"""}]

    for fp in frame_paths:
        parts.append(build_inline_part(fp, "image/jpeg"))
    for ap in audio_paths:
        parts.append(build_inline_part(ap, "audio/mp3"))

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    r = requests.post(url, json={"contents": [{"parts": parts}]}, timeout=180)
    r.raise_for_status()
    data = r.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


# ════════════════════════════════════════════════════════════
# 메인
# ════════════════════════════════════════════════════════════
def analyze_one(url, idx):
    out_dir = os.path.join(WORKDIR, f"ref_{idx}")
    os.makedirs(out_dir, exist_ok=True)

    log(f"[{idx}] 다운로드 중: {url}")
    video_path = download_video(url, out_dir)
    title = os.path.splitext(os.path.basename(video_path))[0]

    log(f"[{idx}] 자막 추출 중...")
    srt = download_transcript(url, out_dir)
    transcript_plain = srt_to_plain(srt) if srt else "(자막 없음)"

    log(f"[{idx}] 프레임 {NUM_FRAMES}장 추출 중...")
    frame_paths = extract_frames(video_path, out_dir)

    log(f"[{idx}] 오디오 샘플 {NUM_AUDIO_SAMPLES}개 추출 중...")
    audio_paths = extract_audio_samples(video_path, out_dir)

    log(f"[{idx}] Gemini 스타일 분석 중...")
    analysis = analyze_style(url, transcript_plain, frame_paths, audio_paths)

    return {"url": url, "analysis": analysis}


def main():
    if not GEMINI_API_KEY:
        log("❌ GEMINI_API_KEY 없음")
        raise SystemExit(1)

    urls = sys.argv[1:] if len(sys.argv) > 1 else \
        [u.strip() for u in os.environ.get("REFERENCE_URLS", "").split(",") if u.strip()]
    if not urls:
        log("❌ 분석할 유튜브 URL이 없습니다")
        raise SystemExit(1)

    os.makedirs(WORKDIR, exist_ok=True)
    results = []
    for i, url in enumerate(urls, 1):
        try:
            results.append(analyze_one(url, i))
        except Exception as e:
            log(f"⚠️ [{i}] 분석 실패: {e}")
            results.append({"url": url, "error": str(e)})

    with open("youtube_reference_style_report.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    with open("youtube_reference_style_report.md", "w", encoding="utf-8") as f:
        for r in results:
            f.write(f"## {r['url']}\n\n")
            f.write(r.get("analysis", f"(분석 실패: {r.get('error')})"))
            f.write("\n\n---\n\n")

    # 원본 다운로드 파일(영상/프레임/대본)은 남기지 않고 정리
    shutil.rmtree(WORKDIR, ignore_errors=True)

    log("🎉 분석 완료 — youtube_reference_style_report.md 확인하세요")


if __name__ == "__main__":
    main()
