#!/usr/bin/env python3
"""Build pronunciation-first vocabulary Shorts for each Survival language channel.

The target-language neural voice is mandatory. A language fails closed when its
configured voice cannot be produced; it is never replaced with another language.
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import math
import random
import hashlib
import shutil
import subprocess
import sys
import os
from dataclasses import dataclass
from pathlib import Path

import edge_tts
import requests
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
PAIR_PATH = ROOT / "config" / "survival_adjective_pairs.json"
CHANNEL_PATH = ROOT / "config" / "survival_language_channels.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "youtube" / "language-adjectives"
WIDTH, HEIGHT = 1080, 1920


@dataclass(frozen=True)
class LanguageProfile:
    code: str
    label: str
    voice: str
    locale: str
    accent: tuple[int, int, int]


LANGUAGES = {
    "ko": LanguageProfile("ko", "KOREAN / TOPIK", "ko-KR-SunHiNeural", "ko-KR", (85, 109, 255)),
    "en": LanguageProfile("en", "ENGLISH SURVIVAL", "en-US-JennyNeural", "en-US", (12, 173, 125)),
    "ja": LanguageProfile("ja", "JAPANESE SURVIVAL", "ja-JP-NanamiNeural", "ja-JP", (236, 72, 93)),
    "zh": LanguageProfile("zh", "CHINESE SURVIVAL", "zh-CN-XiaoxiaoNeural", "zh-CN", (235, 77, 75)),
    "vi": LanguageProfile("vi", "VIETNAMESE SURVIVAL", "vi-VN-HoaiMyNeural", "vi-VN", (255, 153, 46)),
    "es": LanguageProfile("es", "SPANISH SURVIVAL", "es-ES-ElviraNeural", "es-ES", (255, 193, 7)),
    "fr": LanguageProfile("fr", "FRENCH SURVIVAL", "fr-FR-DeniseNeural", "fr-FR", (44, 123, 229)),
    "de": LanguageProfile("de", "GERMAN SURVIVAL", "de-DE-KatjaNeural", "de-DE", (120, 83, 190)),
    "it": LanguageProfile("it", "ITALIAN SURVIVAL", "it-IT-ElsaNeural", "it-IT", (0, 150, 136)),
    "pt": LanguageProfile("pt", "PORTUGUESE SURVIVAL", "pt-BR-FranciscaNeural", "pt-BR", (46, 125, 50)),
}


def run(command: list[str]) -> None:
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def ffprobe_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        check=True,
        text=True,
        capture_output=True,
    )
    return float(result.stdout.strip())


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def select_pair(target_date: dt.date, pair_id: str | None) -> dict:
    catalog = load_json(PAIR_PATH)
    pairs = catalog["pairs"]
    if pair_id:
        for pair in pairs:
            if pair["id"] == pair_id:
                return pair
        raise ValueError(f"Unknown pair id: {pair_id}")

    # The previous category-first selector cycled through only THREE noun
    # lessons while the catalog had 30 adjective lessons. This silently
    # repeated noun content every six days (sun-moon, book-phone, water-coffee).
    # Build one deterministic 33-lesson cycle from the entire catalog and
    # spread the smaller category across the cycle. No pair repeats until
    # every catalog entry has been used once.
    adjectives = [row for row in pairs if row.get("category", "adjective") != "noun"]
    nouns = [row for row in pairs if row.get("category", "adjective") == "noun"]
    if not adjectives or not nouns:
        raise RuntimeError("Vocabulary catalog must contain adjective and noun lessons")
    ordered = list(adjectives)
    # Insert nouns at evenly spaced positions rather than clustering them.
    for index, noun in enumerate(nouns):
        position = round((index + 1) * (len(adjectives) + 1) / (len(nouns) + 1))
        ordered.insert(min(position, len(ordered)), noun)

    anchor_date = dt.date(2026, 10, 5)
    release_index = (target_date - anchor_date).days
    return ordered[release_index % len(ordered)]


def channel_map() -> dict[str, dict]:
    rows = load_json(CHANNEL_PATH)["languages"]
    result = {row["language_code"]: row for row in rows}
    if set(result) != set(LANGUAGES):
        raise RuntimeError("Language registry and production profiles do not match exactly")
    ids = [row["channel_id"] for row in rows]
    if len(ids) != len(set(ids)) or any(not value.startswith("UC") or len(value) != 24 for value in ids):
        raise RuntimeError("Language registry contains a missing or duplicate exact channel ID")
    return result


def font_candidates(bold: bool) -> list[Path]:
    if bold:
        names = [
            Path("C:/Windows/Fonts/malgunbd.ttf"),
            Path("C:/Windows/Fonts/arialbd.ttf"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ]
    else:
        names = [
            Path("C:/Windows/Fonts/malgun.ttf"),
            Path("C:/Windows/Fonts/arial.ttf"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        ]
    return names


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for path in font_candidates(bold):
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    raise RuntimeError("A Unicode font is required to render the language cards")


def centered(draw: ImageDraw.ImageDraw, text: str, y: int, selected_font, fill, max_width: int = 900) -> None:
    current = selected_font
    while current.size > 42:
        box = draw.textbbox((0, 0), text, font=current)
        if box[2] - box[0] <= max_width:
            break
        current = font(current.size - 6, bold=True)
    box = draw.textbbox((0, 0), text, font=current)
    draw.text(((WIDTH - (box[2] - box[0])) / 2, y), text, font=current, fill=fill)


def pronunciation(pair: dict, code: str, word: str) -> str:
    overrides = pair.get("pronunciations", {}).get(code)
    if overrides:
        return overrides[pair[code].index(word)]
    if code == "ko":
        from hangul_romanize import Transliter
        from hangul_romanize.rule import academic
        return Transliter(academic).translit(word)
    if code == "ja":
        from pykakasi import kakasi
        return " ".join(item["hepburn"] for item in kakasi().convert(word))
    if code == "zh":
        from pypinyin import Style, lazy_pinyin
        return " ".join(lazy_pinyin(word, style=Style.TONE))
    return word


def card_background(profile: LanguageProfile, category: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (WIDTH, HEIGHT), (7, 12, 27))
    draw = ImageDraw.Draw(image)
    for y in range(HEIGHT):
        strength = y / HEIGHT
        base = tuple(int(7 + strength * channel * 0.16) for channel in profile.accent)
        draw.line((0, y, WIDTH, y), fill=base)
    draw.rounded_rectangle((68, 86, WIDTH - 68, HEIGHT - 92), radius=54, outline=profile.accent, width=5)
    draw.text((84, 116), profile.label, font=font(39, True), fill=(226, 232, 240))
    draw.rounded_rectangle((82, 181, 430, 245), radius=30, fill=profile.accent)
    label = "ADJECTIVES" if category == "adjective" else "NOUNS"
    draw.text((112, 193), f"VOCABULARY  •  {label}", font=font(25, True), fill=(255, 255, 255))
    return image, draw


def make_card(path: Path, profile: LanguageProfile, word: str, reading: str, meaning: str, count: int | None,
              counterpart: str = "", counterpart_reading: str = "", counterpart_meaning: str = "",
              mode: str = "repeat", category: str = "adjective") -> None:
    image, draw = card_background(profile, category)
    if mode == "intro":
        centered(draw, "TODAY'S PAIR", 480, font(62, True), (220, 226, 238))
        centered(draw, word, 670, font(112, True), (255, 255, 255))
        draw.rounded_rectangle((160, 1030, 920, 1190), radius=80, fill=profile.accent)
        centered(draw, "LISTEN  -  REPEAT", 1070, font(46, True), (255, 255, 255))
    elif mode == "outro":
        # Use the final card as a study recap, not generic praise. The learner
        # sees both the target spelling and the accessible Latin reading/gloss.
        centered(draw, "TODAY'S WORDS", 420, font(58, True), (220, 226, 238))
        centered(draw, word, 610, font(88, True), profile.accent)
        centered(draw, f"{reading}   •   {meaning}", 760, font(52, True), (255, 255, 255))
        centered(draw, counterpart, 970, font(88, True), profile.accent)
        centered(draw, f"{counterpart_reading}   •   {counterpart_meaning}", 1120, font(52, True), (255, 255, 255))
    elif mode == "contrast":
        centered(draw, word, 580, font(112, True), (255, 255, 255))
        centered(draw, counterpart, 930, font(112, True), profile.accent)
        centered(draw, "ONE MORE TIME", 1300, font(45, True), (220, 226, 238))
    else:
        centered(draw, "LISTEN, THEN SAY IT", 405, font(48, True), (220, 226, 238))
        centered(draw, word, 650, font(150, True), (255, 255, 255))
        centered(draw, reading, 950, font(62, True), profile.accent)
        centered(draw, f"MEANING  {meaning.upper()}", 1115, font(48, True), (220, 226, 238))
        if count is not None:
            centered(draw, f"{count} / 5", 1335, font(54, True), (220, 226, 238))
            x0, gap = 372, 84
            for index in range(5):
                fill = profile.accent if index < count else (57, 67, 88)
                draw.ellipse((x0 + index * gap, 1465, x0 + index * gap + 42, 1507), fill=fill)
    draw.text((84, 1765), "Hear it. Pause. Say it out loud.", font=font(34), fill=(186, 195, 211))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, quality=95)


async def synthesize(text: str, profile: LanguageProfile, output: Path) -> str:
    """Fish Audio S2.1 Pro Free first; free native-locale Edge TTS only if Fish fails."""
    api_key = os.getenv("FISH_AUDIO_API_KEY", "").strip()
    fish_error = "FISH_AUDIO_API_KEY not configured"
    if api_key:
        try:
            response = requests.post(
                "https://api.fish.audio/v1/tts",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "model": "s2.1-pro-free",
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg",
                },
                json={"text": text, "format": "mp3"},
                timeout=120,
            )
            if response.ok and len(response.content) > 1000 and not response.content.lstrip().startswith(b"{"):
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(response.content)
                print(f"TTS_ENGINE=fish_audio model=s2.1-pro-free language={profile.code} bytes={output.stat().st_size}", flush=True)
                return "Fish Audio S2.1 Pro Free"
            fish_error = f"Fish Audio HTTP {response.status_code}; invalid audio={len(response.content) <= 1000 or response.content.lstrip().startswith(b'{')}"
        except Exception as exc:
            fish_error = f"Fish Audio request failed ({type(exc).__name__})"
    print(f"TTS_FALLBACK language={profile.code} reason={fish_error}; provider=edge_tts", flush=True)
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            await edge_tts.Communicate(text, profile.voice, rate="-8%", pitch="+0Hz").save(str(output))
            if output.exists() and output.stat().st_size > 1000:
                print(f"TTS_ENGINE=edge_tts voice={profile.voice} language={profile.code} bytes={output.stat().st_size}", flush=True)
                return "Microsoft Edge TTS (free fallback)"
        except Exception as exc:
            last_error = exc
        await asyncio.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Both Fish Audio and free native voice generation failed for {profile.code}/{profile.voice}: {last_error}; {fish_error}")


def quote_concat(path: Path) -> str:
    return str(path.resolve()).replace("'", "'\\''")


def make_fixed_audio(source: Path, output: Path, duration: float) -> None:
    run([
        "ffmpeg", "-y", "-i", str(source), "-af", f"apad=pad_dur={duration},atrim=0:{duration}",
        "-ar", "44100", "-ac", "2", "-c:a", "aac", "-b:a", "160k", str(output),
    ])


def make_silence(output: Path, duration: float) -> None:
    run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", str(duration),
        "-c:a", "aac", "-b:a", "160k", str(output),
    ])


def build_video(workdir: Path, timeline: list[tuple[Path, Path, float]], output: Path) -> None:
    slides = workdir / "slides.txt"
    audio = workdir / "audio.txt"
    slides.write_text(
        "".join(f"file '{quote_concat(image)}'\nduration {duration:.3f}\n" for image, _, duration in timeline)
        + f"file '{quote_concat(timeline[-1][0])}'\n",
        encoding="utf-8",
    )
    audio.write_text("".join(f"file '{quote_concat(track)}'\n" for _, track, _ in timeline), encoding="utf-8")
    silent_video = workdir / "silent.mp4"
    full_audio = workdir / "full.m4a"
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(slides),
        "-vf", f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
        "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-an", str(silent_video),
    ])
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(audio), "-c", "copy", str(full_audio)])
    run([
        "ffmpeg", "-y", "-i", str(silent_video), "-i", str(full_audio), "-c:v", "copy", "-c:a", "aac",
        "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(output),
    ])


async def build_language(target_date: dt.date, pair: dict, code: str, channel: dict, output_root: Path) -> dict:
    profile = LANGUAGES[code]
    words = pair[code]
    meaning_code = "ko" if code == "en" else "en"
    meanings = pair[meaning_code]
    readings = [pronunciation(pair, code, word) for word in words]
    destination = output_root / target_date.isoformat() / code
    workdir = destination / "work"
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    raw_a, raw_b = workdir / "word_a.mp3", workdir / "word_b.mp3"
    engine_a = await synthesize(words[0], profile, raw_a)
    engine_b = await synthesize(words[1], profile, raw_b)
    engines_used = sorted(set([engine_a, engine_b]))
    # Stable per date/language/pair randomization varies pacing while keeping reruns reproducible.
    seed_text = f"{target_date.isoformat()}|{code}|{pair['id']}"
    seed = int(hashlib.sha256(seed_text.encode("utf-8")).hexdigest()[:16], 16)
    rng = random.Random(seed)
    # Wider, natural-looking pacing: vary the intro/outro and each spoken card.
    # The seeded RNG makes a rerun for the same date deterministic, but different
    # dates/pairs produce visibly different total durations instead of a 0:29 template.
    intro_duration = round(rng.uniform(1.1, 2.8), 2)
    outro_duration = round(rng.uniform(1.3, 3.2), 2)
    word_durations = [round(rng.uniform(1.8, 4.0), 2) for _ in range(10)]
    # YouTube displays rounded seconds. Avoid the conspicuous 0:29 duration
    # even if the randomized timing happens to land in the 28.5–29.5s window.
    planned_duration = intro_duration + outro_duration + sum(word_durations)
    if 28.5 <= planned_duration < 29.5:
        adjustable = next((i for i, value in enumerate(word_durations) if value <= 2.8), None)
        if adjustable is not None:
            word_durations[adjustable] = round(word_durations[adjustable] + 1.1, 2)
        else:
            adjustable = next(i for i, value in enumerate(word_durations) if value >= 3.0)
            word_durations[adjustable] = round(word_durations[adjustable] - 1.1, 2)
    audio_tracks = []
    for index, duration in enumerate(word_durations):
        letter = "a" if index % 2 == 0 else "b"
        source = raw_a if letter == "a" else raw_b
        track = workdir / f"word_{letter}_{index + 1}.m4a"
        make_fixed_audio(source, track, duration)
        audio_tracks.append(track)
    intro_audio, outro_audio = workdir / "intro.m4a", workdir / "outro.m4a"
    make_silence(intro_audio, intro_duration)
    make_silence(outro_audio, outro_duration)

    intro = workdir / "intro.png"
    outro = workdir / "outro.png"
    category = pair.get("category", "adjective")
    make_card(intro, profile, f"{words[0]}  /  {words[1]}", "", "", None, mode="intro", category=category)
    make_card(
        outro, profile, words[0], readings[0], meanings[0], None,
        counterpart=words[1], counterpart_reading=readings[1],
        counterpart_meaning=meanings[1], mode="outro", category=category,
    )
    timeline: list[tuple[Path, Path, float]] = [(intro, intro_audio, intro_duration)]
    duration_index = 0
    for index in range(1, 6):
        for letter, word, reading, meaning in (
            ("a", words[0], readings[0], meanings[0]),
            ("b", words[1], readings[1], meanings[1]),
        ):
            card = workdir / f"{letter}_{index}.png"
            make_card(card, profile, word, reading, meaning, index, category=category)
            duration = word_durations[duration_index]
            timeline.append((card, audio_tracks[duration_index], duration))
            duration_index += 1
    timeline.append((outro, outro_audio, outro_duration))

    output = destination / f"{target_date.isoformat()}_{code}_{pair['id']}.mp4"
    build_video(workdir, timeline, output)
    duration = ffprobe_duration(output)
    if not 22 <= duration <= 48:
        raise RuntimeError(f"Unexpected randomized Short duration for {code}: {duration}")
    if category == "noun":
        glosses = meanings if code == "en" else pair["en"]
        title = f"{words[0]} ({readings[0]}) • {words[1]} ({readings[1]}) | {glosses[0]} • {glosses[1]} #Shorts"
    elif code in {"ko", "ja", "zh"}:
        title = f"{words[0]} ({readings[0]}) vs {words[1]} ({readings[1]}) | {pair['en'][0]} vs {pair['en'][1]} #Shorts"
    else:
        title = f"{words[0]} vs {words[1]} | Listen & Repeat 5x #Shorts"
    manifest = {
        "date": target_date.isoformat(),
        "language_code": code,
        "language_label": profile.label,
        "pair_id": pair["id"],
        "category": category,
        "words": words,
        "pronunciations": readings,
        "meanings": meanings,
        "voice_provider": engines_used,
        "voice": profile.voice,
        "voice_locale": profile.locale,
        "synthetic_voice_disclosure": "native-locale neural voice; not a recorded human speaker",
        "repeat_each_word": 5,
        "channel_id": channel["channel_id"],
        "series_name": channel["series_name"],
        "video_path": str(output.resolve()),
        "duration_seconds": round(duration, 3),
        "duration_policy": "date-language-pair-seeded randomized slide timing; 1.8-4.0s per word repetition, randomized intro/outro",
        "title": title,
        # Stable semantic key lets the publisher recognize the same lesson
        # even when a rerun generates a different date or video file.
        "content_key": f"{code}:{pair['id']}",
        "description": (
            f"{words[0]} ({readings[0]}) means {meanings[0]}; {words[1]} ({readings[1]}) means {meanings[1]}. "
            f"Short {category} pronunciation practice: listen, pause, and repeat each word aloud. "
            f"Lesson ID: {pair['id']} | Content key: {code}:{pair['id']}. #languagelearning #Shorts"
        ),
        "tags": ["language learning", "pronunciation", "listen and repeat", pair["id"], f"lesson-{pair['id']}", f"content-{code}-{pair['id']}", "Shorts"],
        "publication_status": "generated_not_uploaded",
    }
    manifest_path = destination / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


async def async_main(args: argparse.Namespace) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise RuntimeError("ffmpeg and ffprobe are required")
    target_date = dt.date.fromisoformat(args.date)
    pair = select_pair(target_date, args.pair_id)
    registry = channel_map()
    codes = list(LANGUAGES) if args.languages == "all" else [value.strip() for value in args.languages.split(",") if value.strip()]
    invalid = sorted(set(codes) - set(LANGUAGES))
    if invalid:
        raise ValueError(f"Unknown languages: {invalid}")
    output_root = Path(args.output_root).resolve()
    manifests = []
    for code in codes:
        print(f"BUILD {code}: {pair[code][0]} / {pair[code][1]} ({LANGUAGES[code].voice})", flush=True)
        manifests.append(await build_language(target_date, pair, code, registry[code], output_root))
        if not args.keep_work:
            shutil.rmtree(output_root / target_date.isoformat() / code / "work", ignore_errors=True)
    batch = {
        "date": target_date.isoformat(),
        "pair_id": pair["id"],
        "category": pair.get("category", "adjective"),
        "requested_languages": codes,
        "completed_languages": [row["language_code"] for row in manifests],
        "count": len(manifests),
        "publication_status": "generated_not_uploaded",
        "items": manifests,
    }
    batch_path = output_root / target_date.isoformat() / "batch_manifest.json"
    batch_path.write_text(json.dumps(batch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "complete", "batch_manifest": str(batch_path), "count": len(manifests)}, ensure_ascii=False))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=dt.date.today().isoformat())
    parser.add_argument("--pair-id")
    parser.add_argument("--languages", default="all", help="all or comma-separated language codes")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--keep-work", action="store_true", help="Keep intermediate cards and render files for debugging")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(async_main(parse_args())))
