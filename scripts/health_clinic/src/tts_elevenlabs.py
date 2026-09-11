"""
2단계 (음성): [A]/[B] 태그로 구분된 2인 대화체 대본을 ElevenLabs로 합성.
화자가 바뀔 때마다 다른 voice_id로 TTS 호출 후, 하나의 오디오 트랙으로 이어붙입니다.

synthesize_dialogue_with_timeline()은 각 대사의 시작/길이(ms)를 함께 반환합니다.
이 타임라인은 video_builder.py에서 정확한 자막(SRT) 타이밍을 만드는 데 사용됩니다.
"""
import hashlib
import os
import re

import requests
from pydub import AudioSegment

from config import LANGUAGES

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

CACHE_DIR = "/tmp/vita150_tts_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

SPEAKER_TAG_RE = re.compile(r"^\[(A|B)\]\s*(.*)$")
SILENCE_BETWEEN_TURNS_MS = 350


def parse_dialogue(script_text: str):
    """
    [A]/[B] 태그가 붙은 대본을 (speaker, text) 세그먼트 목록으로 파싱.
    같은 화자가 연속되면 한 세그먼트로 합침 (API 호출 수 절약).
    태그가 전혀 없으면 전부 화자 A로 처리 (단일 화자 대본 호환).
    """
    segments = []
    current_speaker = None
    current_lines = []

    for raw_line in script_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        m = SPEAKER_TAG_RE.match(line)
        if m:
            speaker, text = m.group(1), m.group(2).strip()
        else:
            speaker, text = current_speaker or "A", line

        if speaker != current_speaker:
            if current_speaker is not None:
                segments.append((current_speaker, " ".join(current_lines)))
            current_speaker, current_lines = speaker, [text]
        else:
            current_lines.append(text)

    if current_speaker is not None:
        segments.append((current_speaker, " ".join(current_lines)))
    return segments


def _tts_single(text: str, voice_id: str) -> str:
    """텍스트 한 덩어리를 하나의 mp3로 합성 (캐시 적용)."""
    text_hash = hashlib.sha256((voice_id + text).encode("utf-8")).hexdigest()[:16]
    out_path = os.path.join(CACHE_DIR, f"{text_hash}.mp3")
    if os.path.exists(out_path):
        return out_path

    resp = requests.post(
        API_URL.format(voice_id=voice_id),
        headers={"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"},
        json={
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        },
        timeout=180,
    )
    resp.raise_for_status()
    with open(out_path, "wb") as f:
        f.write(resp.content)
    return out_path


def synthesize_dialogue_with_timeline(script_text: str, lang: str):
    """
    2인 대화체 대본을 화자별로 나눠 합성 후 하나의 mp3로 병합.
    반환값: (final_mp3_path, timeline)
      timeline: [{"speaker": "A", "text": "...", "start_ms": int, "duration_ms": int}, ...]
    """
    lang_cfg = LANGUAGES[lang]
    voice_a = os.getenv(lang_cfg["voice_id_a_env"])
    voice_b = os.getenv(lang_cfg["voice_id_b_env"])
    voice_map = {"A": voice_a, "B": voice_b}

    segments = parse_dialogue(script_text)
    if not segments:
        raise ValueError("대본에서 읽을 텍스트를 찾지 못했습니다.")

    used_speakers = {s for s, _ in segments}
    missing = [s for s in used_speakers if not voice_map.get(s)]
    if missing:
        env_names = [lang_cfg["voice_id_a_env"] if s == "A" else lang_cfg["voice_id_b_env"] for s in missing]
        raise ValueError(f"{lang} 채널의 다음 음성이 .env에 설정되지 않았습니다: {env_names}")

    print(f"[TTS] {len(segments)}개 대사 세그먼트 합성 시작 (화자: {sorted(used_speakers)})")
    combined = AudioSegment.silent(duration=300)
    silence = AudioSegment.silent(duration=SILENCE_BETWEEN_TURNS_MS)
    timeline = []
    cursor = 300

    for i, (speaker, text) in enumerate(segments):
        mp3_path = _tts_single(text, voice_map[speaker])
        clip = AudioSegment.from_mp3(mp3_path)
        timeline.append({"speaker": speaker, "text": text, "start_ms": cursor, "duration_ms": len(clip)})
        combined += clip + silence
        cursor += len(clip) + SILENCE_BETWEEN_TURNS_MS
        print(f"  [{i+1}/{len(segments)}] 화자 {speaker} 합성 완료 ({len(text)}자, {len(clip)/1000:.1f}초)")

    script_hash = hashlib.sha256(script_text.encode("utf-8")).hexdigest()[:12]
    final_path = os.path.join(CACHE_DIR, f"dialogue_{lang}_{script_hash}.mp3")
    combined.export(final_path, format="mp3")
    print(f"[TTS] 전체 병합 완료: {final_path} (총 {len(combined) / 1000:.1f}초)")
    return final_path, timeline


# 하위 호환용 별칭
def synthesize(script_text: str, lang: str) -> str:
    path, _ = synthesize_dialogue_with_timeline(script_text, lang)
    return path


def synthesize_dialogue(script_text: str, lang: str) -> str:
    path, _ = synthesize_dialogue_with_timeline(script_text, lang)
    return path
