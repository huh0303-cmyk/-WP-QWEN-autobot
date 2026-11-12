#!/usr/bin/env python3
"""Isolated, upload-free TODAY IN HISTORY longform renderer.

Input: reviewed JSON manifest + local rights-cleared stills + already aligned narration
audio. No paid API calls, YouTube uploads, or mutations of existing Shorts workflows.
This is a finishing/quality gate, NOT a research or TTS generator.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import tempfile
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

FPS = 24
WIDTH, HEIGHT = 1920, 1080
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def execute(*args):
    p = subprocess.run(args, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(f"{args[0]} failed: {p.stderr[-1500:]}")
    return p.stdout.strip()


def duration(path):
    return float(execute("ffprobe", "-v", "error", "-show_entries",
                         "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)))


def stamp(seconds):
    millis = round(seconds * 1000)
    hours, millis = divmod(millis, 3600000)
    minutes, millis = divmod(millis, 60000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def validate(manifest, root, demo=False):
    errors = []
    if manifest.get("channel_key") != "history" or manifest.get("language") != "en":
        errors.append("History channel and English narration are mandatory")
    if manifest.get("upload_visibility") != "private":
        errors.append("Only PRIVATE upload can be considered after external review")
    try:
        d = date.fromisoformat(manifest["episode_date"])
    except (KeyError, ValueError, TypeError):
        return ["Explicit ISO episode_date is required"]
    events = manifest.get("events", [])
    if len(events) != 2:
        errors.append("Exactly two events required")
    else:
        dates = []
        for event in events:
            try:
                event_date = date.fromisoformat(event["date"])
                dates.append(event_date)
                if (event_date.month, event_date.day) != (d.month, d.day):
                    errors.append("Event calendar day mismatch")
            except (KeyError, ValueError, TypeError):
                errors.append("Invalid event date")
            if len(event.get("fact_sources", [])) < 1:
                errors.append("Event requires verified factual source URL")
        if dates != sorted(dates, reverse=True):
            errors.append("Events must be newest first")
    scenes = manifest.get("scenes", [])
    if not demo and not 40 <= len(scenes) <= 60:
        errors.append("Production requires 40-60 distinct visual scenes")
    if demo and len(scenes) < 2:
        errors.append("Demo requires at least two scenes")
    seen = set()
    running = 0.0
    for i, shot in enumerate(scenes):
        try:
            image = (root / shot["image"]).resolve()
            audio = (root / shot["audio"]).resolve()
            if not image.is_relative_to(root.resolve()) or not audio.is_relative_to(root.resolve()):
                raise ValueError("media path escapes manifest directory")
            if not image.is_file() or not audio.is_file():
                raise ValueError("missing image/audio")
            if not shot.get("source_url") or not shot.get("rights_basis"):
                raise ValueError("source URL and item-specific rights basis required")
            if not demo:
                if shot.get("event_date") not in [e.get("date") for e in events]:
                    raise ValueError("scene event_date must match one of the verified events")
                if not shot.get("visible_content") or not shot.get("narration_excerpt"):
                    raise ValueError("visible content and narration-to-visual mapping are required")
                if "example.org" in shot["source_url"]:
                    raise ValueError("placeholder source URLs are not accepted")
            digest = hashlib.sha256(image.read_bytes()).hexdigest()
            if digest in seen:
                raise ValueError("duplicate still image")
            seen.add(digest)
            length = duration(audio)
            if length <= 0.25 or not math.isfinite(length):
                raise ValueError("invalid narration audio")
            captions = shot.get("captions", [])
            if not captions:
                raise ValueError("timestamped narration captions required")
            last_end = 0
            for cap in captions:
                start, end = float(cap["start"]), float(cap["end"])
                caption = cap["text"].strip()
                if not 0 <= start < end <= length + 0.15 or start < last_end:
                    raise ValueError("captions out of range, reversed or overlapping")
                if not caption or len(caption.split()) > 6 or "\n" in caption:
                    raise ValueError("caption must be one line, 1-6 English words")
                last_end = end
            running += length
        except (KeyError, ValueError, OSError, RuntimeError) as exc:
            errors.append(f"scene {i + 1}: {exc}")
    if not demo and not 12 * 60 <= running <= 18 * 60:
        errors.append(f"Production narration must run 12-18 min (actual {running:.1f}s)")
    return errors


def create_srt(scenes, root, out):
    lines, offset, index = [], 0.0, 1
    for shot in scenes:
        for cap in shot["captions"]:
            lines.extend([str(index), f"{stamp(offset + cap['start'])} --> {stamp(offset + cap['end'])}",
                          cap["text"].strip(), ""])
            index += 1
        offset += duration(root / shot["audio"])
    out.write_text("\n".join(lines), encoding="utf-8")


def thumbnail_variants(manifest, root, out):
    label = date.fromisoformat(manifest["episode_date"]).strftime("%B %d").upper()
    title = str(manifest.get("thumbnail_title", "THIS DAY IN HISTORY")).upper().strip()
    if len(title.split()) > 6:
        raise ValueError("Thumbnail headline must be 6 words or fewer")
    scenes = manifest["scenes"]
    for n, idx in enumerate((0, len(scenes) // 2, len(scenes) - 1), start=1):
        with Image.open(root / scenes[idx]["image"]) as source:
            im = ImageOps.fit(source.convert("RGB"), (1280, 720))
        overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        draw.rectangle((0, 0, 1280, 720), fill=(0, 0, 0, 110 if n == 2 else 90))
        font_date = ImageFont.truetype(FONT, 118)
        font_title = ImageFont.truetype(FONT, 65)
        draw.text((70, 80), label, font=font_date, fill=(255, 218, 67),
                  stroke_width=4, stroke_fill=(0, 0, 0))
        # Restrict line widths for mobile previews
        words, lines, current = title.split(), [], ""
        for word in words:
            probe = f"{current} {word}".strip()
            if draw.textbbox((0, 0), probe, font=font_title)[2] > 1120 and current:
                lines.append(current)
                current = word
            else:
                current = probe
        lines.append(current)
        if len(lines) > 2:
            raise ValueError("Thumbnail headline exceeds two lines")
        for j, line in enumerate(lines):
            draw.text((76, 405 + j * 88), line, font=font_title, fill="white",
                      stroke_width=3, stroke_fill="black")
        im = Image.alpha_composite(im.convert("RGBA"), overlay).convert("RGB")
        im.save(out / f"thumbnail_{n}.jpg", quality=90)


def render(manifest, root, out, demo=False):
    problems = validate(manifest, root, demo)
    if problems:
        raise ValueError("; ".join(problems))
    out.mkdir(parents=True, exist_ok=True)
    scenes = manifest["scenes"]
    create_srt(scenes, root, out / "captions.srt")
    thumbnail_variants(manifest, root, out)
    w, h = (640, 360) if demo else (WIDTH, HEIGHT)
    with tempfile.TemporaryDirectory(prefix="history-render-") as tmp:
        parts = []
        for i, shot in enumerate(scenes):
            src = root / shot["image"]
            aud = root / shot["audio"]
            seconds = duration(aud)
            frames = math.ceil(seconds * FPS)
            target = Path(tmp) / f"clip-{i:03}.mp4"
            # Each still gently moves; motion alternates per shot.
            zoom = ("min(zoom+0.0007,1.15)" if i % 2 == 0
                    else "if(eq(on,0),1.15,max(zoom-0.0007,1.0))")
            filt = (f"scale={w*2}:{h*2}:force_original_aspect_ratio=increase,"
                    f"crop={w*2}:{h*2},"
                    f"zoompan=z='{zoom}':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':"
                    f"d=1:s={w}x{h}:fps={FPS},format=yuv420p")
            execute("ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(src),
                    "-i", str(aud), "-vf", filt, "-frames:v", str(frames),
                    "-c:v", "libx264", "-preset", "ultrafast" if demo else "veryfast",
                    "-c:a", "aac", "-b:a", "128k", "-shortest", str(target))
            parts.append(target)
        concat = Path(tmp) / "concat.txt"
        concat.write_text("".join(f"file '{p}'\n" for p in parts), encoding="utf-8")
        joined = Path(tmp) / "joined.mp4"
        execute("ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                "-i", str(concat), "-c", "copy", str(joined))
        subtitle_path = (out / "captions.srt").resolve()
        execute("ffmpeg", "-y", "-loglevel", "error", "-i", str(joined),
                "-vf", f"subtitles={subtitle_path}:force_style='FontSize={16 if demo else 23},"
                f"Outline=2,MarginV={38 if demo else 90},Alignment=2'",
                "-c:v", "libx264", "-preset", "ultrafast" if demo else "veryfast",
                "-c:a", "copy", str(out / "review.mp4"))
    report = {"status": "rendered_for_review_not_uploaded",
              "episode_date": manifest["episode_date"],
              "scenes": len(scenes), "duration_seconds": duration(out / "review.mp4"),
              "thumbnails": 3, "caption_file": "captions.srt", "upload_performed": False}
    (out / "review_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("manifest", type=Path)
    p.add_argument("--output", type=Path, default=Path("artifacts/history_pilot"))
    p.add_argument("--demo", action="store_true", help="Permits short synthetic QA fixture, NEVER uploads")
    p.add_argument("--check-only", action="store_true")
    args = p.parse_args()
    root = args.manifest.resolve().parent
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    problems = validate(data, root, args.demo)
    if problems:
        raise SystemExit("\n".join(problems))
    if args.check_only:
        print("Manifest preflight passed. This is not proof of rights or factual accuracy.")
    else:
        print(json.dumps(render(data, root, args.output, args.demo), indent=2))


if __name__ == "__main__":
    main()
