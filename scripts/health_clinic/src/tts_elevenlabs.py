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

FISH_AUDIO_API_KEY = os.getenv("FISH_AUDIO_API_KEY", "").strip()

CACHE_DIR = "/tmp/vita150_tts_cache"
FISH_CACHE_DIR = os.path.join(CACHE_DIR, "fish_s2_1_pro_free_v2")
EDGE_CACHE_DIR = os.path.join(CACHE_DIR, "edge_tts_v2")
os.makedirs(FISH_CACHE_DIR, exist_ok=True)
os.makedirs(EDGE_CACHE_DIR, exist_ok=True)

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


def _tts_single(text: str, voice_id: str, lang: str, speaker: str) -> str:
    """Use Fish Audio for Japanese; keep provider caches strictly separated."""
    normalized_lang = lang.split("-")[0].lower()
    is_japanese = normalized_lang in ("ja", "jp")

    fish_hash = hashlib.sha256(
        ("fish-audio-s2.1-pro-free-v2|" + lang + "|" + speaker + "|" + text).encode("utf-8")
    ).hexdigest()[:20]
    fish_path = os.path.join(FISH_CACHE_DIR, f"{fish_hash}.mp3")
    if os.path.exists(fish_path) and os.path.getsize(fish_path) > 1000:
        print(f"[TTS_ENGINE] fish_audio_cache model=s2.1-pro-free lang={lang} speaker={speaker}")
        return fish_path

    fish_error = None
    if FISH_AUDIO_API_KEY:
        try:
            resp = requests.post(
                "https://api.fish.audio/v1/tts",
                headers={"Authorization": f"Bearer {FISH_AUDIO_API_KEY}", "model": "s2.1-pro-free",
                         "Content-Type": "application/json", "Accept": "audio/mpeg"},
                json={"text": text, "format": "mp3"}, timeout=180,
            )
            if resp.ok and len(resp.content) > 1000 and not resp.content.lstrip().startswith(b"{"):
                with open(fish_path, "wb") as f:
                    f.write(resp.content)
                print(f"[TTS_ENGINE] fish_audio model=s2.1-pro-free lang={lang} speaker={speaker} bytes={len(resp.content)}")
                return fish_path
            fish_error = f"HTTP {resp.status_code}"
        except Exception as exc:
            fish_error = type(exc).__name__
    else:
        fish_error = "FISH_AUDIO_API_KEY unavailable"

    # Japanese narration must never silently change provider.
    if is_japanese:
        raise RuntimeError(
            f"Japanese Health Clinic requires Fish Audio s2.1-pro-free; {fish_error}. "
            "Generation stopped before using another TTS provider."
        )

    edge_hash = hashlib.sha256(
        ("edge-tts-v2|" + lang + "|" + speaker + "|" + text).encode("utf-8")
    ).hexdigest()[:20]
    edge_path = os.path.join(EDGE_CACHE_DIR, f"{edge_hash}.mp3")
    if os.path.exists(edge_path) and os.path.getsize(edge_path) > 1000:
        print(f"[TTS_ENGINE] edge_tts_cache lang={lang} speaker={speaker}")
        return edge_path

    voices = {
        "ko": ("ko-KR-SunHiNeural", "ko-KR-InJoonNeural"),
        "en": ("en-US-AriaNeural", "en-US-GuyNeural"),
        "vi": ("vi-VN-HoaiMyNeural", "vi-VN-NamMinhNeural"),
        "zh": ("zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural"),
        "es": ("es-ES-ElviraNeural", "es-ES-AlvaroNeural"),
        "fr": ("fr-FR-DeniseNeural", "fr-FR-HenriNeural"),
        "de": ("de-DE-KatjaNeural", "de-DE-ConradNeural"),
        "it": ("it-IT-ElsaNeural", "it-IT-DiegoNeural"),
        "pt": ("pt-BR-FranciscaNeural", "pt-BR-AntonioNeural"),
    }
    pair = voices.get(normalized_lang)
    if not pair:
        raise RuntimeError(f"No configured free Edge TTS voice for language={lang}.")
    voice = pair[0] if speaker == "A" else pair[1]
    import asyncio
    import edge_tts
    asyncio.run(edge_tts.Communicate(text, voice).save(edge_path))
    if not os.path.exists(edge_path) or os.path.getsize(edge_path) <= 1000:
        raise RuntimeError(f"Edge TTS failed for {lang}/{speaker}.")
    print(f"[TTS_ENGINE] edge_tts voice={voice} lang={lang} speaker={speaker} bytes={os.path.getsize(edge_path)}")
    return edge_path


def synthesize_dialogue_with_timeline(script_text: str, lang: str):
    """
    2인 대화체 대본을 화자별로 나눠 합성 후 하나의 mp3로 병합.
    반환값: (final_mp3_path, timeline)
      timeline: [{"speaker": "A", "text": "...", "start_ms": int, "duration_ms": int}, ...]
    """
    lang_cfg = LANGUAGES[lang]
    voice_map = {"A": "A", "B": "B"}

    segments = parse_dialogue(script_text)
    if not segments:
        raise ValueError("대본에서 읽을 텍스트를 찾지 못했습니다.")

    used_speakers = {s for s, _ in segments}

    print(f"[TTS] {len(segments)}개 대사 세그먼트 합성 시작 (화자: {sorted(used_speakers)})")
    combined = AudioSegment.silent(duration=0)
    silence = AudioSegment.silent(duration=SILENCE_BETWEEN_TURNS_MS)
    timeline = []
    cursor = 0

    for i, (speaker, text) in enumerate(segments):
        mp3_path = _tts_single(text, voice_map[speaker], lang, speaker)
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
