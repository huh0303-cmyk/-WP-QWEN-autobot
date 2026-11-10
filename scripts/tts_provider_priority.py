"""Central FREE-ONLY TTS provider priority for London Project.

Order: Fish Audio S2.1 Pro Free -> local Qwen3-TTS -> Edge TTS.
Paid providers are intentionally unsupported.
"""
from __future__ import annotations

import asyncio
import os
import shlex
import hashlib
import json
import random
import subprocess
from pathlib import Path
from typing import Callable

TTS_PRIORITY = ("fish_audio", "qwen3_tts", "edge_tts")

# Six approved narrator slots per channel: three male, three female.
# Provider-specific IDs must be configured and verified, never fabricated.
VOICE_ROLES = ("male_news_1", "male_documentary_2", "male_news_3",
               "female_news_1", "female_documentary_2", "female_news_3")
EDGE_VOICES = {
    "ko": ("ko-KR-HyunsuNeural", "ko-KR-InJoonNeural", "ko-KR-BongJinNeural",
           "ko-KR-SunHiNeural", "ko-KR-JiMinNeural", "ko-KR-SeoHyeonNeural"),
    "en": ("en-US-GuyNeural", "en-US-DavisNeural", "en-US-ChristopherNeural",
           "en-US-AriaNeural", "en-US-JennyNeural", "en-US-MichelleNeural"),
}
def choose_narrator(channel: str, language: str = "ko", history_path: str | Path | None = None) -> dict:
    """Choose one of six roles, avoiding last two when persistent history is available."""
    history = Path(history_path or os.getenv("TTS_VOICE_HISTORY_PATH", "data/tts_voice_history.json"))
    key = channel + ":" + language.lower().split("-")[0]
    try:
        state = json.loads(history.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    recent = state.get(key, [])[-2:]
    eligible = [i for i in range(6) if i not in recent] or list(range(6))
    index = random.SystemRandom().choice(eligible)
    state[key] = (state.get(key, []) + [index])[-20:]
    history.parent.mkdir(parents=True, exist_ok=True)
    history.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    base = language.lower().split("-")[0]
    edge_pool = EDGE_VOICES.get(base)
    edge_voice = edge_pool[index] if edge_pool else None
    return {"index": index, "role": VOICE_ROLES[index], "edge_voice": edge_voice,
            "fish_voice_id": os.getenv(f"FISH_VOICE_{base.upper()}_{index + 1}", "").strip(),
            "qwen_voice": os.getenv(f"QWEN_VOICE_{base.upper()}_{index + 1}", "").strip()}

def shorts_audio_filter() -> str:
    """1.2x speed, subtle brightening and loudness control for narrated Shorts."""
    return "atempo=1.2,highpass=f=90,treble=g=2:f=3500,loudnorm=I=-16:TP=-1.5:LRA=9"

def render_shorts_audio(input_path: str | Path, output_path: str | Path) -> Path:
    """Postprocess any successful provider uniformly; fail closed on bad output."""
    source, dest = Path(input_path), Path(output_path)
    if not verify_audio(source):
        raise RuntimeError("Invalid TTS source audio")
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(source),
        "-af", shorts_audio_filter(), "-c:a", "libmp3lame", "-q:a", "2", str(dest)],
        check=True, capture_output=True, timeout=180)
    if not verify_audio(dest):
        raise RuntimeError("Invalid processed Shorts audio")
    return dest

def verify_audio(path: str | Path, minimum_seconds: float = 0.4) -> bool:
    """Reject missing, corrupt or implausibly short files using ffprobe."""
    out = Path(path)
    if not out.is_file() or out.stat().st_size < 1000:
        return False
    try:
        p = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
            "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(out)],
            capture_output=True, text=True, timeout=20, check=True)
        return float(p.stdout.strip()) >= minimum_seconds
    except (OSError, ValueError, subprocess.SubprocessError):
        return False


def _valid_audio(path: Path) -> bool:
    return verify_audio(path)


def local_qwen3_tts(text: str, output_path: str | Path, language: str) -> bool:
    """Optional local Qwen3-TTS adapter. Disabled unless a command is configured.

    QWEN3_TTS_COMMAND is an executable plus arguments; placeholders:
    {text_file}, {output_file}, {language}. No shell is invoked.
    The command must use a locally installed model, not a paid API.
    """
    command = os.getenv("QWEN3_TTS_COMMAND", "").strip()
    if not command:
        return False
    out = Path(output_path)
    source = out.with_suffix(out.suffix + ".qwen-input.txt")
    source.write_text(text, encoding="utf-8")
    try:
        args = [
            part.replace("{text_file}", str(source))
                .replace("{output_file}", str(out))
                .replace("{language}", language)
            for part in shlex.split(command)
        ]
        if not args:
            return False
        subprocess.run(args, check=True, timeout=180, capture_output=True)
        return _valid_audio(out)
    finally:
        source.unlink(missing_ok=True)


def generate_tts(
    text: str,
    output_path: str | Path,
    *,
    language: str = "en",
    fish_generator: Callable | None = None,
    qwen_generator: Callable | None = None,
    edge_voice: str | None = None,
    edge_pitch: str = "+0Hz",
    channel: str | None = None,
    narrator: dict | None = None,
) -> dict:
    """Generate audio using free providers only, in the policy order.

    Adapter signature: (text, output_path, language) -> truthy on success.
    Fish adapter must explicitly select model 's2.1-pro-free'.
    Qwen adapter must use a locally installed model and reject languages
    that have not been verified for the installed model.
    No paid-provider adapter is accepted by this API.
    """
    if narrator is None and channel:
        narrator = choose_narrator(channel, language)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if qwen_generator is None:
        qwen_generator = local_qwen3_tts
    errors: list[str] = []

    for name, generator in (
        ("fish_audio", fish_generator),
        ("qwen3_tts", qwen_generator),
    ):
        if generator is None:
            errors.append(f"{name}: adapter not configured")
            continue
        try:
            if generator(text, out, language) and _valid_audio(out):
                return {"engine": name, "path": str(out), "fallback_errors": errors}
            errors.append(f"{name}: no valid audio returned")
        except Exception as exc:
            errors.append(f"{name}: failed ({type(exc).__name__})")

    try:
        import edge_tts

        base_language = language.lower().split("-")[0]
        voices = {
            "ko": "ko-KR-SunHiNeural",
            "ja": "ja-JP-NanamiNeural",
            "zh": "zh-CN-XiaoxiaoNeural",
            "vi": "vi-VN-HoaiMyNeural",
            "en": "en-US-AriaNeural",
            "es": "es-ES-ElviraNeural",
            "fr": "fr-FR-DeniseNeural",
            "de": "de-DE-KatjaNeural",
            "it": "it-IT-ElsaNeural",
            "th": "th-TH-PremwadeeNeural",
        }
        voice = edge_voice or (narrator or {}).get("edge_voice") or voices.get(base_language)
        if not voice:
            errors.append(f"edge_tts: no configured voice for {base_language}")
        else:
            async def save_audio() -> None:
                await edge_tts.Communicate(text, voice, pitch=edge_pitch).save(str(out))

            try:
                asyncio.get_running_loop()
            except RuntimeError:
                asyncio.run(save_audio())
            else:
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    pool.submit(asyncio.run, save_audio()).result()
            if _valid_audio(out):
                return {"engine": "edge_tts", "path": str(out), "fallback_errors": errors}
            errors.append("edge_tts: no valid audio returned")
    except Exception as exc:
        errors.append(f"edge_tts: failed ({type(exc).__name__})")

    raise RuntimeError("All configured free TTS providers failed: " + "; ".join(errors))
