#!/usr/bin/env python3
"""Create every playlist from fresh Lyria music and a fresh Gemini image.

Prefer existing approved music and Gemini app exports; API generation is explicit opt-in.
"""
from __future__ import annotations

import json
import os
import random
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for entry in (ROOT, ROOT / "scripts"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

import youtube_playlist_maker_legacy as base
from gemini_media_provider import generate_lyria_track, generate_thumbnail
from PIL import Image, ImageDraw, ImageFont

_bank_list = base.list_folder_files
_bank_download = base.download_drive_file
GENERATED_PREFIX = "fresh-lyria:"
_generated_paths: dict[str, str] = {}
_selected_language = ""
_track_languages = []


def metadata(topic, caption, duration_min):
    from youtube_english_metadata import playlist_metadata
    return playlist_metadata(base.CHANNEL_KEY, topic, duration_min)


def balanced_language(counts):
    languages = ["french", "japanese", "spanish", "italian"]
    minimum = min(counts.get(language, 0) for language in languages)
    return random.choice([language for language in languages if counts.get(language, 0) == minimum])


def pick_topic():
    global _selected_language
    path = Path(base.RECENT_TOPICS_FILE)
    state = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    recent = state.get("recent", [])
    if base.CHANNEL_KEY == "globalmusic":
        counts = state.setdefault("romantic_language_counts", {})
        _selected_language = balanced_language(counts)
        counts[_selected_language] = counts.get(_selected_language, 0) + 1
        pool = ["Golden Hour Acoustic Romance", "Soft Songs for a Quiet Cafe",
                "A Sweet Unplugged Evening", "Warm Guitar Love Songs"]
    elif base.CHANNEL_KEY == "kpop":
        _selected_language = "korean"
        pool = ["Korean Acoustic Pop Evening", "Unplugged Korean Love Songs",
                "Soft Korean Acoustic R&B", "Korean Folk Pop for a Quiet Cafe"]
    else:
        _selected_language = ""
        pool = base.CHANNEL_TOPIC_POOLS.get(base.CHANNEL_KEY, base.AUTO_TOPIC_POOL)
    topic = random.choice([value for value in pool if value not in recent] or list(pool))
    state["recent"] = ([topic] + [value for value in recent if value != topic])[:base.RECENT_TOPICS_MEMORY]
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return topic, _selected_language


def _music_prompt(index: int) -> str:
    topic = os.environ.get("TOPIC_KEYWORD", "").strip() or "signature channel mood"
    language = (_track_languages[index - 1] if base.CHANNEL_KEY == "globalmusic" and index <= len(_track_languages)
                else os.environ.get("LANGUAGE_KEYWORD", "").strip() or _selected_language)
    style = {
        "globalmusic": f"a sweet adult female romantic acoustic vocal song in {language or 'French, Japanese, Spanish, or Italian'}",
        "kpop": "an original Korean-language acoustic K-pop song with fresh lyrics",
        "starbucks": "an instrumental cafe jazz and soft piano piece, no vocals",
        "mbb": "an original elegant classical chamber and piano piece, instrumental only",
        "healing": "a slow original ambient nature soundscape led by rain and water, instrumental only",
    }[base.CHANNEL_KEY]
    return (f"Create {style}, approximately three minutes long, inspired by '{topic}'. It must be a new "
            "composition with no quotation of an existing melody, no named artist imitation, and no brand "
            f"references. Keep a clean beginning and ending. Unique production seed: {index}-{random.getrandbits(64):016x}.")


def generate_fresh_tracks(*_args, **_kwargs):
    global _track_languages
    # Prepare a mixed-language playlist, regardless of a single-language calendar label.
    minimum_seconds = int(os.environ.get("PLAYLIST_FRESH_AUDIO_SECONDS", str(70 * 60)))
    requested = max(1, int(os.environ.get("LYRIA_TRACK_COUNT", "20")))
    maximum = max(requested, int(os.environ.get("LYRIA_MAX_TRACKS", "30")))
    from playlist_language_policy import romantic_languages
    _track_languages = romantic_languages(maximum)
    tracks, total = [], 0.0
    for index in range(1, maximum + 1):
        path = Path(base.WORKDIR) / f"fresh_lyria_{index:02d}.mp3"
        base.log(f"   Lyria 새 음악 생성 {index}/{maximum}...")
        generate_lyria_track(_music_prompt(index), path)
        duration = base.get_duration(str(path))
        if duration <= 0:
            raise RuntimeError(f"Lyria track has no playable duration: {path.name}")
        file_id = f"{GENERATED_PREFIX}{index}"
        _generated_paths[file_id] = str(path)
        tracks.append({"id": file_id, "name": path.name, "duration": duration})
        total += duration
        if index >= requested and total >= minimum_seconds:
            break
    if total < minimum_seconds:
        raise RuntimeError(f"Fresh Lyria music is only {total / 60:.1f} minutes; refusing to reuse or loop assets")
    return tracks


def copy_generated(_service, file_id, output_path):
    source = _generated_paths.get(file_id)
    if not source:
        return _bank_download(_service, file_id, output_path)
    shutil.copyfile(source, output_path)


def _thumbnail_prompt(topic: str) -> str:
    # Common layout grammar observed across established 500k+ playlist channels:
    # one memorable scene, restrained palette, and intentional negative space.
    # No specific thumbnail, character, artwork, or brand identity is copied.
    direction = {
        "globalmusic": random.choice(["bright open seaside cafe terrace with turquoise ocean and wide horizon", "sunlit beach cafe with open sea and pale blue sky", "airy garden cafe with flowers and open sky", "bright lakeside terrace with a spacious water view"]) + ", EXACTLY ONE adult male-female couple, two people total, large close-up faces and upper bodies dominating the scene, natural affectionate moment, no other people anywhere; vary cultural background across separate videos, never several couples in one image; airy bright natural lighting and open upper space for one large title",
        "kpop": "modern Korean acoustic listening room, one original adult subject on the right, negative space on the left",
        "starbucks": "cozy independent cafe, one window table and piano, warm restrained palette, negative space on the left",
        "mbb": "elegant classical chamber hall, one grand piano on the right, timeless low-contrast light, negative space on the left",
        "healing": "peaceful rain over a lush forest stream, one clear natural focal point, open misty space on the left",
    }[base.CHANNEL_KEY]
    return (f"Create a completely new original photorealistic source photograph for a music playlist about '{topic}': "
            f"{direction}. Use the proven visual hierarchy of large playlist channels without copying any existing "
            "thumbnail or identifiable character. 16:9, cinematic depth, premium natural color grading, no text, no "
            "logo, no watermark, no trademark, no collage, and no reproduction of an existing image.")


def fresh_image(topic, workdir, service=None):
    if os.environ.get("PLAYLIST_IMAGE_SOURCE", "gemini_app_export") != "gemini_api":
        service = base.get_drive_service()
        items = _bank_list(service, base.THUMBNAIL_FOLDER_ID, base.IMAGE_EXTS, "image/")
        items = [item for item in items if "gemini" in item['name'].lower()]
        if not items:
            raise RuntimeError("WAITING_ASSETS: save an approved Gemini thumbnail export named gemini_* in this channel thumbnail folder")
        raw_path = Path(workdir) / ("gemini_app_export" + Path(random.choice(items)['name']).suffix)
        chosen = random.choice(items)
        _bank_download(service, chosen['id'], str(raw_path))
        with Image.open(raw_path) as image:
            image.verify()
        with Image.open(raw_path) as image:
            if image.width < 1280 or image.height < 720:
                raise RuntimeError("Gemini app thumbnail must be at least 1280x720")
        return [str(raw_path)]
    if os.environ.get("PLAYLIST_PAID_API_ENABLED", "false").lower() != "true":
        raise RuntimeError("Paid image generation is disabled")
    raw_path = Path(workdir) / "fresh_gemini_thumbnail.bin"
    generate_thumbnail(_thumbnail_prompt(topic), raw_path)
    try:
        with Image.open(raw_path) as image:
            image.verify()
        with Image.open(raw_path) as image:
            if image.width < 1280 or image.height < 720:
                raise RuntimeError("Generated thumbnail is smaller than 1280x720")
            suffix = ".jpg" if (image.format or "").lower() in {"jpeg", "jpg"} else ".png"
    except Exception as exc:
        raise RuntimeError("Gemini returned an invalid thumbnail image") from exc
    final_path = raw_path.with_suffix(suffix)
    raw_path.replace(final_path)
    return [str(final_path)]


def benchmark_thumbnail(_channel, image_path, output_path, topic, **_kwargs):
    """Owner's latest requirement: one very large, mobile-readable PLAYLIST label."""
    image = base._resize_cover(Image.open(image_path).convert("RGB"), 1280, 720)
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    font_path = base.ensure_font()
    size=200
    title_font=ImageFont.truetype(font_path,size)
    while draw.textlength('PLAYLIST',font=title_font)>1088:
        size-=2
        title_font=ImageFont.truetype(font_path,size)
    draw.text((644,216),'PLAYLIST',anchor='mm',font=title_font,fill=(0,0,0,160),stroke_width=4)
    draw.text((640,210),'PLAYLIST',anchor='mm',font=title_font,fill='white',stroke_width=1,stroke_fill=(40,30,30,130))
    composed = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    return base._save_thumbnail_capped(composed, output_path)


def make_intro_video(image_path, audio_path, out_path):
    vf=("[0:v]scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,"
        "zoompan=z='1+min(on,71)*0.00025':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1280x720:fps=12,"
        "fade=t=in:st=0:d=1,drawbox=x=0:y=625:w=iw:h=95:color=black@0.30:t=fill[bg];"
        "[1:a]aformat=channel_layouts=mono,showwaves=s=1152x56:mode=cline:rate=12:colors=white:scale=sqrt[wave];"
        "[bg][wave]overlay=64:646:shortest=1,format=yuv420p[v]")
    base.run_ffmpeg(["ffmpeg","-y","-loop","1","-framerate","12","-i",image_path,"-i",audio_path,
                    "-filter_complex",vf,"-map","[v]","-map","1:a","-c:v","libx264","-preset","veryfast",
                    "-tune","stillimage","-crf","20","-threads","2","-c:a","aac","-b:a","192k",
                    "-movflags","+faststart","-shortest",out_path])


def build_fresh_healing(_service, _theme, output_path):
    return base.build_playlist_audio(None, generate_fresh_tracks(), output_path)


def select_music(service, folder_id, exts, mime_prefix):
    if os.environ.get("PLAYLIST_MUSIC_SOURCE", "approved_bank") == "lyria_api":
        if os.environ.get("PLAYLIST_PAID_API_ENABLED", "false").lower() != "true":
            raise RuntimeError("Paid music generation is disabled")
        return generate_fresh_tracks()
    tracks = _bank_list(service, folder_id, exts, mime_prefix)
    from playlist_language_policy import select_bank_tracks
    return select_bank_tracks(tracks, base.CHANNEL_KEY)


def build_hybrid_healing(service, theme, output_path):
    tracks = select_music(service, base.MUSIC_SOURCE_FOLDER_ID, base.AUDIO_EXTS, "audio/")
    return base.build_playlist_audio(service, tracks, output_path)


base.GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
base.pick_auto_topic = pick_topic
base.list_folder_files = select_music
base.download_drive_file = copy_generated
base.filter_tracks_by_language = lambda tracks, _keyword: tracks
base.generate_caption = lambda topic: topic
base.build_healing_theme_audio = build_hybrid_healing
base.fetch_healing_photo = lambda theme, workdir: fresh_image(theme, workdir)[0]
base.build_ai_images = fresh_image
base.generate_youtube_title_description = metadata
base.pick_duration_target = lambda: (50 * 60, 70 * 60)
base.make_channel_thumbnail = benchmark_thumbnail
base.make_static_video = make_intro_video
base.HEALING_THEME_DURATION_SEC = {theme: (50 * 60, 70 * 60) for theme in base.HEALING_THEME_DURATION_SEC}

if __name__ == "__main__":
    base.main()
