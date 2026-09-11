#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ambient_sample_lab.py
─────────────────────────────────────────────────────────────
빗소리/새소리/샘물소리/바람소리/절 풍경소리/목탁소리/성당종소리/
알프스 소 방울소리 등 여러 자연/앰비언스 사운드를 ffmpeg 합성만으로
짧은(기본 60초) 샘플로 만들어서 방향을 미리 들어볼 수 있게 하는 실험용
스크립트. 실제 녹음이 아니라 노이즈 색상/필터/감쇠음 합성이라 새소리나
종소리류는 진짜보다 소박하게 들릴 수 있음 — 톤/방향 결정용.

사용법:
    python scripts/ambient_sample_lab.py [출력폴더] [샘플길이초]
"""

import os
import sys
import random
import subprocess

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def log(msg):
    print(msg, flush=True)


def run_ffmpeg(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg 실패: {' '.join(cmd)}\n{proc.stderr[-1500:]}")


def _decaying_tone_path(freq, ratios, amps, decay_rate, dur, out_path, volume=0.6):
    # decay_rate가 숫자 하나면 모든 배음이 똑같은 속도로 사그라드는데, 실제
    # 종/풍경소리는 상위 배음일수록 훨씬 빨리 죽고 기본음만 따뜻하게 남는다.
    # 전부 같은 속도로 유지하면 높은 배음이 끝까지 남아서 "쨍~" 하고 계속
    # 갈리는 쇳소리로 들린다 — 배음별 감쇠속도를 리스트로도 받을 수 있게 함.
    decay_rates = [decay_rate] * len(ratios) if isinstance(decay_rate, (int, float)) else decay_rate
    terms = [f"{amp}*exp(-{dr}*t)*sin(2*PI*{freq*ratio}*t)"
              for ratio, amp, dr in zip(ratios, amps, decay_rates)]
    expr = "+".join(terms)
    run_ffmpeg(["ffmpeg", "-y", "-f", "lavfi", "-i", f"aevalsrc='{expr}':d={dur}",
                "-af", f"volume={volume}", out_path])


def _chirp_path(f0, f1, dur, decay_rate, out_path, volume=0.5):
    slope = (f1 - f0)
    expr = f"{volume}*exp(-{decay_rate}*t)*sin(2*PI*({f0}+{slope}*t)*t)"
    run_ffmpeg(["ffmpeg", "-y", "-f", "lavfi", "-i", f"aevalsrc='{expr}':d={dur}", out_path])


MAX_SCATTER_EVENTS = 150  # 윈도우 명령줄 길이 제한 방지용 안전 상한


def _scatter_over_bed(bed_path, event_path_or_paths, duration_sec, out_path, min_gap=1.0, max_gap=4.0):
    """짧은 이벤트음(들)을 무작위/불규칙한 간격으로 배경음 위에 흩뿌린다."""
    if isinstance(event_path_or_paths, str):
        event_paths = [event_path_or_paths]
    else:
        event_paths = event_path_or_paths

    delays = []
    t = random.uniform(0.5, max_gap)
    while t < duration_sec - 1.0 and len(delays) < MAX_SCATTER_EVENTS:
        delays.append(int(t * 1000))
        t += random.uniform(min_gap, max_gap)

    inputs = ["-i", bed_path]
    for i in range(len(delays)):
        inputs += ["-i", event_paths[i % len(event_paths)]]

    filter_parts = []
    mix_labels = "[0:a]"
    for i, d in enumerate(delays):
        filter_parts.append(f"[{i+1}:a]adelay={d}|{d}[c{i}]")
        mix_labels += f"[c{i}]"
    filter_parts.append(f"{mix_labels}amix=inputs={len(delays)+1}:duration=first:normalize=0[out]")
    run_ffmpeg(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filter_parts),
                "-map", "[out]", "-c:a", "aac", "-b:a", "192k", out_path])


def _rhythmic_over_bed(bed_path, event_path, duration_sec, interval, out_path, jitter=0.05):
    delays = []
    t = interval
    while t < duration_sec - 0.5 and len(delays) < MAX_SCATTER_EVENTS:
        delays.append(int((t + random.uniform(-jitter, jitter)) * 1000))
        t += interval
    inputs = ["-i", bed_path] + sum([["-i", event_path] for _ in delays], [])
    filter_parts = []
    mix_labels = "[0:a]"
    for i, d in enumerate(delays):
        filter_parts.append(f"[{i+1}:a]adelay={d}|{d}[c{i}]")
        mix_labels += f"[c{i}]"
    filter_parts.append(f"{mix_labels}amix=inputs={len(delays)+1}:duration=first:normalize=0[out]")
    run_ffmpeg(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filter_parts),
                "-map", "[out]", "-c:a", "aac", "-b:a", "192k", out_path])


def make_rain(dur, workdir, out_path):
    # 빗방울 하나하나를 개별 파일로 겹치면(수백 개) 윈도우 명령줄 길이 제한에
    # 걸려서, 대신 서로 배수 아닌 여러 트레몰로 레이어로 "타다닥" 치는 밀도감을
    # 필터만으로 만든다 (짧은 개별 이벤트 오버레이 없이도 충분히 자연스러움).
    run_ffmpeg(["ffmpeg", "-y", "-f", "lavfi", "-i",
                f"anoisesrc=color=white:amplitude=0.35:duration={dur}",
                "-af", "highpass=f=300,lowpass=f=7000,"
                        "tremolo=f=3.7:d=0.15,tremolo=f=5.3:d=0.10,tremolo=f=0.2:d=0.08",
                "-c:a", "aac", "-b:a", "192k", out_path])


def make_birds(dur, workdir, out_path):
    bed = os.path.join(workdir, "_birds_bed.m4a")
    run_ffmpeg(["ffmpeg", "-y", "-f", "lavfi", "-i",
                f"anoisesrc=color=pink:amplitude=0.03:duration={dur}", "-c:a", "aac", bed])
    chirps = []
    for i in range(4):
        p = os.path.join(workdir, f"_bird_chirp_{i}.wav")
        f0 = random.uniform(1800, 2600)
        f1 = f0 + random.uniform(1500, 3000)
        _chirp_path(f0, f1, 0.15, 9, p, volume=0.5)
        chirps.append(p)
    _scatter_over_bed(bed, chirps, dur, out_path, min_gap=0.8, max_gap=2.5)


def make_stream(dur, workdir, out_path):
    bed = os.path.join(workdir, "_stream_bed.m4a")
    run_ffmpeg(["ffmpeg", "-y", "-f", "lavfi", "-i",
                f"anoisesrc=color=pink:amplitude=0.28:duration={dur}",
                "-af", "bandpass=f=1200:width_type=h:w=2200,"
                        "tremolo=f=1.3:d=0.18,tremolo=f=2.1:d=0.12",
                "-c:a", "aac", bed])
    plink = os.path.join(workdir, "_stream_plink.wav")
    _decaying_tone_path(1400, [1, 1.5], [0.5, 0.3], 14, 0.2, plink, volume=0.25)
    _scatter_over_bed(bed, plink, dur, out_path, min_gap=0.6, max_gap=1.8)


def make_thunderstorm(dur, workdir, out_path):
    """무거운 비 배경 위에 가끔(25~75초 간격) 천둥(크랙+낮은 우르릉거림)이 치는
    폭풍우 사운드. 2026-08-16 사용자 요청("번개천둥있는것도")."""
    bed = os.path.join(workdir, "_storm_bed.m4a")
    run_ffmpeg(["ffmpeg", "-y", "-f", "lavfi", "-i",
                f"anoisesrc=color=white:amplitude=0.4:duration={dur}",
                "-af", "highpass=f=250,lowpass=f=8000,"
                        "tremolo=f=4.1:d=0.18,tremolo=f=6.7:d=0.12,tremolo=f=0.15:d=0.1",
                "-c:a", "aac", "-b:a", "192k", bed])

    thunder = os.path.join(workdir, "_thunder_crack.wav")
    # 날카로운 크랙(임팩트)과 낮게 우르릉대는 럼블 두 레이어를 합성해 천둥 한 번을 만든다.
    run_ffmpeg(["ffmpeg", "-y",
                "-f", "lavfi", "-i", "anoisesrc=color=white:amplitude=1.0:duration=0.35",
                "-f", "lavfi", "-i", "anoisesrc=color=brown:amplitude=1.0:duration=4.5",
                "-filter_complex",
                "[0:a]highpass=f=800,lowpass=f=4000,afade=t=out:st=0.03:d=0.32,volume=0.9[crack];"
                "[1:a]lowpass=f=120,tremolo=f=7:d=0.5,tremolo=f=2.3:d=0.4,"
                "afade=t=in:st=0:d=0.3,afade=t=out:st=3.5:d=1.0,volume=0.7[rumble];"
                "[crack][rumble]amix=inputs=2:duration=longest:normalize=0[out]",
                "-map", "[out]", thunder])

    _scatter_over_bed(bed, thunder, dur, out_path, min_gap=25.0, max_gap=75.0)


def make_wind(dur, workdir, out_path):
    run_ffmpeg(["ffmpeg", "-y", "-f", "lavfi", "-i",
                f"anoisesrc=color=brown:amplitude=0.32:duration={dur}",
                "-af", "bandpass=f=500:width_type=h:w=900,"
                        "tremolo=f=0.15:d=0.3,tremolo=f=0.23:d=0.2",
                "-c:a", "aac", "-b:a", "192k", out_path])


def make_temple_chime(dur, workdir, out_path):
    bed = os.path.join(workdir, "_chime_bed.m4a")
    run_ffmpeg(["ffmpeg", "-y", "-f", "lavfi", "-i",
                f"anoisesrc=color=brown:amplitude=0.06:duration={dur}",
                "-af", "bandpass=f=500:width_type=h:w=900,tremolo=f=0.12:d=0.2",
                "-c:a", "aac", bed])
    chime = os.path.join(workdir, "_chime_tone.wav")
    # 상위 배음(2.76배/5.4배)을 기본음보다 훨씬 빨리 죽여서 "쨍" 하고 밝게
    # 시작했다가 금방 따뜻한 기본음만 남게 — 예전엔 셋 다 같은 속도(2.2)로
    # 감쇠해서 날카로운 5940Hz대 배음이 3초 내내 안 죽고 쇳소리로 들렸음.
    _decaying_tone_path(1100, [1, 2.76, 5.4], [0.5, 0.18, 0.07], [1.6, 4.5, 8.0], 3.0, chime, volume=0.5)
    _scatter_over_bed(bed, chime, dur, out_path, min_gap=2.5, max_gap=6.0)


def make_moktak(dur, workdir, out_path):
    bed = os.path.join(workdir, "_moktak_bed.m4a")
    run_ffmpeg(["ffmpeg", "-y", "-f", "lavfi", "-i",
                f"anoisesrc=color=pink:amplitude=0.02:duration={dur}", "-c:a", "aac", bed])
    knock = os.path.join(workdir, "_moktak_knock.wav")
    run_ffmpeg(["ffmpeg", "-y", "-f", "lavfi", "-i", "anoisesrc=color=white:amplitude=1.0:duration=0.12",
                "-af", "bandpass=f=550:width_type=h:w=500,afade=t=out:st=0.02:d=0.1,volume=0.6",
                knock])
    _rhythmic_over_bed(bed, knock, dur, interval=0.62, out_path=out_path, jitter=0.03)


def make_cathedral_bell(dur, workdir, out_path):
    bed = os.path.join(workdir, "_bell_bed.m4a")
    run_ffmpeg(["ffmpeg", "-y", "-f", "lavfi", "-i",
                f"anoisesrc=color=brown:amplitude=0.03:duration={dur}", "-c:a", "aac", bed])
    bell = os.path.join(workdir, "_bell_tone.wav")
    _decaying_tone_path(190, [1, 1.5, 2.4, 3.1], [0.5, 0.3, 0.2, 0.12], 0.9, 6.0, bell, volume=0.6)
    _scatter_over_bed(bed, bell, dur, out_path, min_gap=6.0, max_gap=14.0)


def make_alpine_cowbell(dur, workdir, out_path):
    bed = os.path.join(workdir, "_cowbell_bed.m4a")
    run_ffmpeg(["ffmpeg", "-y", "-f", "lavfi", "-i",
                f"anoisesrc=color=pink:amplitude=0.03:duration={dur}", "-c:a", "aac", bed])
    clanks = []
    for i in range(3):
        p = os.path.join(workdir, f"_cowbell_clank_{i}.wav")
        base = random.uniform(500, 650)
        _decaying_tone_path(base, [1, 1.8, 2.35], [0.5, 0.35, 0.25], 7, 0.5, p, volume=0.5)
        clanks.append(p)
    _scatter_over_bed(bed, clanks, dur, out_path, min_gap=0.7, max_gap=2.2)


SOUND_LIBRARY = {
    "rain": ("빗소리", make_rain),
    "birds": ("새소리", make_birds),
    "stream": ("샘물소리", make_stream),
    "wind": ("바람소리", make_wind),
    "temple_chime": ("절_풍경소리", make_temple_chime),
    "moktak": ("목탁소리", make_moktak),
    "cathedral_bell": ("성당종소리", make_cathedral_bell),
    "alpine_cowbell": ("알프스_소방울소리", make_alpine_cowbell),
}


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else "ambient_output/samples"
    dur = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
    os.makedirs(outdir, exist_ok=True)

    for key, (label, fn) in SOUND_LIBRARY.items():
        out_path = os.path.join(outdir, f"{key}_{label}.m4a")
        log(f"만드는 중: {label} ({dur:.0f}초)...")
        fn(dur, outdir, out_path)
        log(f"   ✅ {out_path}")


if __name__ == "__main__":
    main()
