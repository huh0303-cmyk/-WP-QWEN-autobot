"""Central FREE-ONLY TTS provider priority for London Project.

Order: Fish Audio S2.1 Pro Free -> local Qwen3-TTS -> Edge TTS ->
optional verified-free provider. Paid providers are intentionally unsupported.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Callable

TTS_PRIORITY = ("fish_audio", "qwen3_tts", "edge_tts", "additional_free")


def _valid_audio(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


def generate_tts(
    text: str,
    output_path: str | Path,
    *,
    language: str = "en",
    fish_generator: Callable | None = None,
    qwen_generator: Callable | None = None,
    additional_free_generator: Callable | None = None,
) -> dict:
    """Generate audio using free providers only, in the policy order.

    Adapter signature: (text, output_path, language) -> truthy on success.
    Fish adapter must explicitly select model 's2.1-pro-free'.
    Qwen adapter must use a locally installed model and reject languages
    that have not been verified for the installed model.
    Additional provider adapter must be verified free before being enabled.
    No paid-provider adapter is accepted by this API.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
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
        voice = voices.get(base_language)
        if not voice:
            errors.append(f"edge_tts: no configured voice for {base_language}")
        else:
            async def save_audio() -> None:
                await edge_tts.Communicate(text, voice).save(str(out))

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

    if additional_free_generator is not None:
        try:
            if additional_free_generator(text, out, language) and _valid_audio(out):
                return {"engine": "additional_free", "path": str(out), "fallback_errors": errors}
            errors.append("additional_free: no valid audio returned")
        except Exception as exc:
            errors.append(f"additional_free: failed ({type(exc).__name__})")
    else:
        errors.append("additional_free: adapter not configured")

    raise RuntimeError("All configured free TTS providers failed: " + "; ".join(errors))
