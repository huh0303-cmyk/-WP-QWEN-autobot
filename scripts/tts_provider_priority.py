"""Central TTS provider priority for London Project video pipelines.

Priority: Fish Audio (if configured) -> free Edge TTS -> ElevenLabs (last resort).
Providers are attempted sequentially. A successful earlier provider prevents any
later provider from being called. No credentials are logged.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Callable

TTS_PRIORITY = ("fish_audio", "edge_tts", "elevenlabs")


def generate_tts(text: str, output_path: str | Path, *, language: str = "en",
                 fish_generator: Callable | None = None,
                 elevenlabs_generator: Callable | None = None) -> dict:
    """Generate audio in priority order; provider adapters may be injected for testing.

    fish_generator signature: (text, output_path, language) -> truthy on success.
    elevenlabs_generator signature: (text, output_path, language) -> truthy on success.
    Edge TTS uses the installed edge-tts package and a language-appropriate voice.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    errors = []

    if fish_generator is None:
        # Only attempt Fish Audio when explicitly configured; API details are kept
        # inside a provider adapter rather than guessing voice IDs or logging secrets.
        if os.getenv("FISH_AUDIO_API_KEY", "").strip():
            errors.append("fish_audio configured but no adapter supplied")
        else:
            errors.append("fish_audio not configured")
    else:
        try:
            if fish_generator(text, out, language) and out.exists() and out.stat().st_size > 0:
                return {"engine": "fish_audio", "path": str(out), "fallback_errors": errors}
            errors.append("fish_audio returned no audio")
        except Exception as exc:
            errors.append(f"fish_audio failed: {type(exc).__name__}")

    # Edge TTS is free and must be tried before any paid provider.
    try:
        import edge_tts
        voice = {
            "ko": "ko-KR-SunHiNeural",
            "ja": "ja-JP-NanamiNeural",
            "zh": "zh-CN-XiaoxiaoNeural",
            "vi": "vi-VN-HoaiMyNeural",
        }.get(language.lower().split("-")[0], "en-US-AriaNeural")
        asyncio.run(edge_tts.Communicate(text, voice).save(str(out)))
        if out.exists() and out.stat().st_size > 0:
            return {"engine": "edge_tts", "path": str(out), "fallback_errors": errors}
        errors.append("edge_tts returned no audio")
    except Exception as exc:
        errors.append(f"edge_tts failed: {type(exc).__name__}")

    # Paid provider is last and only reached after both free paths failed.
    if elevenlabs_generator is not None:
        try:
            if elevenlabs_generator(text, out, language) and out.exists() and out.stat().st_size > 0:
                return {"engine": "elevenlabs", "path": str(out), "fallback_errors": errors}
            errors.append("elevenlabs returned no audio")
        except Exception as exc:
            errors.append(f"elevenlabs failed: {type(exc).__name__}")

    raise RuntimeError("All configured TTS providers failed: " + "; ".join(errors))
