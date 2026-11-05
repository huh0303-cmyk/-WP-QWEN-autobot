"""Sound-first CAFE HEALING renderer: one calm moving scene, five rotating ambience themes."""
import hashlib
import json
import os
import random
import shutil
import subprocess
from pathlib import Path

import requests
import healing_rain_review as job
from automation_hub.youtube_release import public_allowed, result_url, upload_privacy_status

# One main licensed visual source per upload. The same small set is rotated;
# avoid stitching together a large number of unrelated stock clips.
SOURCE_POOLS = {
    "fire": [6755352, 946600],
    "rain": [13166787, 9632520, 5754996, 32679327],
    "wind": [3027193, 6650237],
    "birds": [30535102, 35475944],
    "temple": [36787646],
}
CATEGORY_ORDER = ("fire", "rain", "wind", "birds", "temple")
HISTORY_LIMIT = 50
BIRD_ASSET = job.ROOT / "assets/playlist-review/forest-birds-cc0.mp3"


def _history_path():
    return Path(os.environ.get("HEALING_THUMBNAIL_HISTORY", job.ROOT / "data/healing_thumbnail_history.json"))


def _category_history_path():
    return Path(os.environ.get("HEALING_CATEGORY_HISTORY", job.ROOT / "data/healing_category_history.json"))


def _read_history(path):
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
        return rows if isinstance(rows, list) else []
    except (OSError, ValueError):
        return []


def choose_mode():
    """Cycle through the five requested themes, recording only verified releases."""
    history = _read_history(_category_history_path())
    completed = [row.get("mode") for row in history if row.get("mode") in CATEGORY_ORDER]
    if not completed:
        return CATEGORY_ORDER[0]
    return CATEGORY_ORDER[(CATEGORY_ORDER.index(completed[-1]) + 1) % len(CATEGORY_ORDER)]


def select_source(mode, seed, history):
    pool = SOURCE_POOLS[mode]
    recent = [int(row.get("source_id", 0)) for row in reversed(history) if row.get("mode") == mode]
    available = [source_id for source_id in pool if source_id not in recent[:min(3, len(pool) - 1)]] or pool
    return available[seed % len(available)]


def select_thumbnail_second(source_id, source_seconds, seed, history):
    upper = max(2, int(source_seconds) - 2)
    candidates = list(range(2, upper + 1))
    used = {(13166787, 3), (18132437, 3)}
    used.update((int(row.get("source_id", 0)), int(row.get("thumbnail_second", -1))) for row in history[-HISTORY_LIMIT:])
    start = seed % len(candidates)
    for offset in range(len(candidates)):
        second = candidates[(start + offset) % len(candidates)]
        if (source_id, second) not in used:
            return second
    return candidates[start]


def _write_audio(path, samples, sample_rate=48000):
    import numpy as np
    from scipy.io import wavfile

    samples = np.asarray(samples, dtype=np.float32)
    peak = float(np.max(np.abs(samples))) if samples.size else 0.0
    if peak > 0:
        samples = samples * min(0.82 / peak, 1.0)
    fade = min(sample_rate * 2, len(samples) // 4)
    if fade:
        ramp = np.linspace(0.0, 1.0, fade, dtype=np.float32)
        samples[:fade] *= ramp
        samples[-fade:] *= ramp[::-1]
    stereo = np.column_stack((samples, samples))
    wavfile.write(str(path), sample_rate, (stereo * 32767).astype(np.int16))


def _make_synthetic_bed(mode, seed, path, seconds=240):
    """Create original, clearly disclosed sound beds without paid generation APIs."""
    import numpy as np
    from scipy.signal import butter, sosfilt

    sr = 48000
    count = sr * seconds
    rng = np.random.default_rng(seed)
    noise = rng.normal(0.0, 1.0, count).astype(np.float32)

    if mode == "wind":
        sos = butter(4, 700, btype="lowpass", fs=sr, output="sos")
        base = sosfilt(sos, noise)
        controls = rng.uniform(0.18, 0.95, int(seconds / 5) + 2)
        envelope = np.interp(np.arange(count), np.arange(len(controls)) * sr * 5, controls)
        audio = base * envelope * 0.12

    elif mode == "rain":
        sos = butter(3, [250, 8500], btype="bandpass", fs=sr, output="sos")
        audio = sosfilt(sos, noise) * 0.055
        # Sparse, very soft droplets add texture without sharp transient peaks.
        for _ in range(seconds * 3):
            start = int(rng.integers(0, count - sr // 20))
            length = int(rng.integers(sr // 100, sr // 25))
            audio[start:start + length] += rng.normal(0, 0.035, length) * np.hanning(length)

    elif mode == "fire":
        sos = butter(3, [90, 7200], btype="bandpass", fs=sr, output="sos")
        audio = sosfilt(sos, noise) * 0.012
        # Random short ember pops; this is original synthesis, not a claimed field recording.
        for _ in range(int(seconds * 1.4)):
            start = int(rng.integers(0, count - sr // 8))
            length = int(rng.integers(sr // 150, sr // 12))
            decay = np.exp(-np.linspace(0, rng.uniform(4, 12), length))
            audio[start:start + length] += rng.normal(0, 0.22, length) * decay

    elif mode == "temple":
        sos = butter(3, 550, btype="lowpass", fs=sr, output="sos")
        audio = sosfilt(sos, noise) * 0.012
        # Soft, widely spaced bronze-like chimes; no sampled commercial bell recording.
        cursor = int(rng.integers(sr * 5, sr * 12))
        while cursor < count - sr * 10:
            length = int(sr * rng.uniform(7, 11))
            t = np.arange(length, dtype=np.float32) / sr
            fundamental = rng.choice([196.0, 220.0, 247.0, 262.0])
            bell = np.zeros(length, dtype=np.float32)
            for multiple, strength, decay in ((1.0, 1.0, 4.8), (2.01, 0.42, 3.2),
                                               (2.76, 0.22, 2.4), (4.08, 0.11, 1.8)):
                bell += strength * np.sin(2 * np.pi * fundamental * multiple * t) * np.exp(-t / decay)
            audio[cursor:cursor + length] += bell * rng.uniform(0.035, 0.055)
            cursor += int(sr * rng.uniform(28, 48))
    else:
        raise ValueError(f"Unsupported healing sound mode: {mode}")

    _write_audio(path, audio)


def record_thumbnail(path, payload):
    rows = _read_history(path)
    rows.append(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(rows[-HISTORY_LIMIT:], ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def record_category(mode, token):
    path = _category_history_path()
    rows = _read_history(path)
    if any(row.get("token") == token for row in rows):
        return
    rows.append({"mode": mode, "token": token, "verified_release": True})
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(rows[-HISTORY_LIMIT:], ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def download(url, path):
    with requests.get(url, stream=True, timeout=90) as response:
        response.raise_for_status()
        with path.open("wb") as output:
            for chunk in response.iter_content(1024 * 1024):
                output.write(chunk)


def configure():
    token = os.environ.get("HEALING_SAMPLE_ID") or os.environ.get("SCHEDULE_ID") or os.environ.get("GITHUB_RUN_ID", "local-preview")
    seed = int(hashlib.sha256(token.encode()).hexdigest()[:16], 16)
    rng = random.Random(seed)
    requested = os.environ.get("HEALING_VARIANT", "sequential")
    mode = choose_mode() if requested == "sequential" else requested
    if mode not in CATEGORY_ORDER:
        raise ValueError(f"Unknown healing preset: {mode}")

    minutes = rng.randint(74, 175)
    job.DURATION = minutes * 60
    job.MARKER = "Review reference: healing-motion-" + token

    titles = {
        "fire": f"Quiet Fireplace | {minutes} Minutes of Soft Crackling Fire Sounds, No Music",
        "rain": f"Rain on Green Leaves | {minutes} Minutes of Peaceful Forest Rain, No Music",
        "wind": f"Forest Breeze | {minutes} Minutes of Gentle Wind Through the Trees",
        "birds": f"Forest Birds | {minutes} Minutes of Natural Birdsong, No Music",
        "temple": f"Quiet Temple Garden | {minutes} Minutes of Soft Bells, Breeze & Birds",
    }
    scenes = {
        "fire": "a close, steady view of glowing firewood and gently moving flames",
        "rain": "rain falling naturally onto green forest leaves",
        "wind": "tree branches and leaves moving gently in a forest breeze",
        "birds": "a quiet woodland scene with birds resting among the trees",
        "temple": "a peaceful Buddhist temple surrounded by green trees",
    }
    sound_notes = {
        "fire": "an original, softly mixed crackling-fire sound bed with irregular ember pops",
        "rain": "an original, gently modulated rain-like sound bed with soft droplet texture",
        "wind": "an original, low, slowly changing wind-like sound bed",
        "birds": "a bundled CC0 forest-bird recording, gently levelled for long listening",
        "temple": "soft, widely spaced original bronze-like chime tones over a quiet bird-and-breeze bed",
    }
    job.TITLE = titles[mode]
    job.DESCRIPTION = f"""Spend {minutes} quiet minutes with {scenes[mode]}. The picture stays simple and uncluttered: one main licensed nature scene, gently joined into a calm continuous view rather than a rapid montage.

The soundscape uses {sound_notes[mode]}. There is no music or narration. Synthesized elements are original sound design, not represented as an uninterrupted field recording. Levels are kept gentle, with no sudden loud effects.

Use this ambience as a quiet background for reading, resting, meditation, or peaceful work. The thumbnail contains no text so the natural scene remains the focus.

Visual source: Pexels, used under the Pexels License. Bird ambience, when used: bundled Freesound CC0 recording. No competitor footage, audio, title, or thumbnail is reused.

{job.MARKER}"""
    return mode, seed, minutes


MODE, SEED, MINUTES = configure()


def render():
    work = job.WORK
    history_path = _history_path()
    history = _read_history(history_path)
    source_id = select_source(MODE, SEED, history)
    source = work / "source.mp4"
    download(f"https://www.pexels.com/download/video/{source_id}/", source)

    source_seconds = float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1", str(source)
    ]))
    end = min(40, int(source_seconds))
    if end < 10:
        raise RuntimeError("Selected nature footage is too short for a smooth scene")
    thumbnail_second = select_thumbnail_second(source_id, source_seconds, SEED, history)
    job.ff("-ss", str(thumbnail_second), "-i", source, "-frames:v", "1",
           "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080",
           work / "thumbnail.jpg")

    # A single main source clip is looped with a one-second dissolve; no busy montage.
    transition = (
        f"[0:v]fps=24,scale=1920:1080:force_original_aspect_ratio=increase,"
        f"crop=1920:1080,setsar=1,split[a][b];"
        f"[a]trim=start=1:end={end},setpts=PTS-STARTPTS[x];"
        f"[b]trim=start=0:end=1,setpts=PTS-STARTPTS[y];"
        f"[x][y]xfade=transition=fade:duration=1:offset={end-2}[v]"
    )
    job.ff("-i", source, "-filter_complex_threads", "1", "-filter_complex", transition,
           "-map", "[v]", "-an", "-c:v", "libx264", "-preset", "fast",
           "-b:v", "2200k", "-maxrate", "2600k", "-bufsize", "5200k",
           "-pix_fmt", "yuv420p", work / "scene.mp4")

    audio_path = work / ("ambience.mp3" if MODE == "birds" else "ambience.wav")
    if MODE == "birds":
        if not BIRD_ASSET.is_file():
            raise RuntimeError("The bundled CC0 forest-bird recording is missing")
        shutil.copyfile(BIRD_ASSET, audio_path)
    else:
        _make_synthetic_bed(MODE, SEED, audio_path)
        if MODE == "temple":
            if not BIRD_ASSET.is_file():
                raise RuntimeError("The bundled CC0 forest-bird recording is missing for temple ambience")
            job.ff("-i", audio_path, "-stream_loop", "-1", "-i", BIRD_ASSET,
                   "-filter_complex", "[0:a]volume=0.88[b];[1:a]volume=0.12[c];"
                                     "[b][c]amix=inputs=2:duration=first:normalize=0[a]",
                   "-map", "[a]", "-t", "240", "-c:a", "pcm_s16le", work / "temple-mix.wav")
            audio_path = work / "temple-mix.wav"

    job.save("synthesis.json", {
        "minutes": MINUTES,
        "mode": MODE,
        "seed": SEED,
        "visual_strategy": "one main Pexels scene with a gentle loop dissolve; no montage",
        "source_id": source_id,
        "source_page": f"https://www.pexels.com/video/{source_id}/",
        "thumbnail_second": thumbnail_second,
        "visual_license": "https://www.pexels.com/license/",
        "bird_asset": "assets/playlist-review/forest-birds-cc0.mp3" if MODE in ("birds", "temple") else None,
        "audio_strategy": "CC0 birds" if MODE == "birds" else "original local sound design",
        "thumbnail_text": False,
        "paid_generation_apis": False,
    })

    tail = f"afade=t=in:d=5,afade=t=out:st={job.DURATION-8}:d=8"
    job.ff("-stream_loop", "-1", "-i", work / "scene.mp4",
           "-stream_loop", "-1", "-i", audio_path,
           "-filter_complex", f"[1:a]loudnorm=I=-25:TP=-3:LRA=8,{tail}[a]",
           "-map", "0:v", "-map", "[a]", "-t", job.DURATION,
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", work / "rain-75.mp4")

    seconds = float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1", str(work / "rain-75.mp4")
    ]))
    if abs(seconds - job.DURATION) > 2:
        raise RuntimeError(f"Rendered duration mismatch: expected {job.DURATION}, got {seconds}")
    job.ff("-ss", "30", "-i", work / "rain-75.mp4", "-t", "20",
           "-c", "copy", work / "preview.mp4")
    record_thumbnail(history_path, {
        "token": job.MARKER.rsplit("-", 1)[-1],
        "mode": MODE,
        "source_id": source_id,
        "thumbnail_second": thumbnail_second,
    })
    print("MOTION_RENDERED", MODE, MINUTES, flush=True)


if __name__ == "__main__":
    job.render = render
    print("SELECTED", MODE, MINUTES, flush=True)
    job.main()
    record_category(MODE, job.MARKER.rsplit("-", 1)[-1])

    receipt = json.loads((job.WORK / "upload.json").read_text())
    video_id = receipt["video_id"]
    result = job.ROOT / os.environ.get("ROOM_RESULT_SOURCE", "artifacts/youtube_playlist_result.json")
    result.parent.mkdir(parents=True, exist_ok=True)
    privacy_status = upload_privacy_status()
    result.write_text(json.dumps({
        "artifact_id": video_id,
        "video_id": video_id,
        "artifact_url": result_url(video_id),
        "studio_url": f"https://studio.youtube.com/video/{video_id}/edit",
        "public_url": f"https://youtu.be/{video_id}",
        "privacy_status": privacy_status,
        "channel_key": "healing",
        "verified_channel_id": receipt["channel_id"],
        "public_allowed": public_allowed(),
        "minutes": MINUTES,
        "variant": MODE,
    }), encoding="utf-8")
