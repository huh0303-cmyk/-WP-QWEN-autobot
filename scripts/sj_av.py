#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Audio + subtitle helpers for the Seoul Journal Shorts pipeline.

* Rotating narrators: 3 male + 3 female Edge voices, one picked at random per video.
* Sentence-by-sentence synthesis: every sentence is a separate clip whose real length is
  measured with ffprobe, so word times are measured, never estimated or drifted.
* ASS subtitle writer for libass: bold outlined text, one highlighted word, short fades.
"""
import asyncio, os, random, re, subprocess, sys, time
from pathlib import Path

# Documentary / news-narrator tuned (slightly slower, slightly lower). Change freely.
# Override at run time with SEOUL_JOURNAL_VOICE=<voice name | male | female>.
VOICE_ROSTER = [
    {"voice": "ko-KR-InJoonNeural",             "gender": "male",   "tone": "documentary_deep", "rate": "+8%", "pitch": "-4Hz"},
    {"voice": "ko-KR-HyunsuMultilingualNeural", "gender": "male",   "tone": "news_clear",       "rate": "+8%", "pitch": "-2Hz"},
    {"voice": "en-US-BrianMultilingualNeural",  "gender": "male",   "tone": "narrator_calm",    "rate": "+8%", "pitch": "-2Hz"},
    {"voice": "ko-KR-SunHiNeural",              "gender": "female", "tone": "anchor",           "rate": "+8%", "pitch": "-2Hz"},
    {"voice": "en-US-AvaMultilingualNeural",    "gender": "female", "tone": "narrator_warm",    "rate": "+8%", "pitch": "-1Hz"},
    {"voice": "en-US-EmmaMultilingualNeural",   "gender": "female", "tone": "documentary_clear", "rate": "+8%", "pitch": "-2Hz"},
]

PAUSE_SENTENCE = 0.18   # silence after the last word of a sentence
PAUSE_PARAGRAPH = 0.38  # silence after the last sentence of a paragraph
PAUSE_END = 0.30


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"{cmd[0]} failed: {r.stderr[-400:]}")
    return r


def _duration(path):
    r = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)])
    return float(r.stdout.strip())



def _speech_bounds(wav_path):
    """Measure where real sound starts/ends in a clip (silencedetect), so word times
    are anchored to actual audio instead of the TTS engine's reported offsets."""
    r = subprocess.run(["ffmpeg","-v","info","-i",str(wav_path),"-af","silencedetect=noise=-38dB:d=0.04","-f","null","-"],
                       capture_output=True, text=True)
    total = _duration(wav_path)
    starts = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", r.stderr)]
    lead = ends[0] if (starts and starts[0] <= 0.02 and ends) else 0.0
    tail_start = total
    if starts and (len(starts) > len(ends) or (ends and starts[-1] > ends[-1])):
        tail_start = starts[-1]
    elif starts and ends and abs(ends[-1] - total) < 0.05:
        tail_start = starts[-1]
    return max(0.0, lead), min(total, max(tail_start, lead + 0.2))


def _fit_words(words, lead, speech_end):
    """Linearly map engine word times onto the measured speech window."""
    raw_start = min(w["start"] for w in words)
    raw_end = max(w["end"] for w in words)
    span = max(0.05, raw_end - raw_start)
    win = max(0.05, speech_end - lead)
    out = []
    for w in words:
        a = lead + (w["start"] - raw_start) * win / span
        b = lead + (w["end"] - raw_start) * win / span
        out.append({"text": w["text"], "start": a, "end": max(b, a + 0.03)})
    return out


def split_units(text):
    """Narration -> [(sentence, 'sent'|'para')]. Slices keep every letter of the narration."""
    units = []
    for para in re.split(r"\n\s*\n", text.strip()):
        para = " ".join(para.split())
        parts = [p.strip() for p in re.split(r"(?<=[.!?。！？])\s+", para) if p.strip()]
        for i, part in enumerate(parts):
            units.append((part, "para" if i == len(parts) - 1 else "sent"))
    return units


async def _edge_unit(text, voice, rate, pitch):
    import edge_tts
    audio = bytearray()
    words = []
    async for ch in edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, boundary="WordBoundary").stream():
        if ch["type"] == "audio":
            audio += ch["data"]
        elif ch["type"] == "WordBoundary":
            start = float(ch["offset"]) / 10_000_000
            words.append({"text": ch["text"], "start": start, "end": start + float(ch["duration"]) / 10_000_000})
    return bytes(audio), words


def _synthesize_with(voice, units, out_dir, work, log):
    fitted = []
    segments = []
    cursor = 0.0
    for i, (unit, kind) in enumerate(units):
        audio = words = None
        for attempt in range(3):
            try:
                audio, words = asyncio.run(_edge_unit(unit, voice["voice"], voice["rate"], voice["pitch"]))
                if len(audio) >= 1500 and words:
                    break
                audio = None
            except Exception:
                if attempt == 2:
                    raise
            time.sleep(1.5 * (attempt + 1))
        if not audio:
            raise RuntimeError(f"sentence {i} returned no audio/word events")
        mp3 = work / f"u{i:02d}.mp3"
        wav = work / f"u{i:02d}.wav"
        mp3.write_bytes(audio)
        _run(["ffmpeg", "-y", "-v", "error", "-i", str(mp3), "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(wav)])
        raw_len = _duration(wav)
        lead, speech_end = _speech_bounds(wav)
        words = _fit_words(words, lead, speech_end)
        last_end = min(speech_end, raw_len)
        pause = PAUSE_END if i == len(units) - 1 else (PAUSE_PARAGRAPH if kind == "para" else PAUSE_SENTENCE)
        target = last_end + pause
        fit = work / f"u{i:02d}_fit.wav"
        # Pad or trim so each sentence is exactly "speech + chosen pause" long.
        _run(["ffmpeg", "-y", "-v", "error", "-i", str(wav), "-af", f"apad=whole_dur={target:.4f},atrim=0:{target:.4f}",
              "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(fit)])
        fit_len = _duration(fit)
        for w in words:
            segments.append({"text": w["text"], "start": round(cursor + w["start"], 3), "end": round(cursor + min(w["end"], fit_len), 3)})
        cursor += fit_len
        fitted.append(fit)
    listing = work / "concat.txt"
    listing.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in fitted), encoding="utf-8")
    mp3_out = out_dir / "voice.mp3"
    _run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(listing),
          "-c:a", "libmp3lame", "-b:a", "192k", str(mp3_out)])
    final_len = _duration(mp3_out)
    if abs(final_len - cursor) > 0.25:
        raise RuntimeError(f"assembled audio {final_len:.2f}s differs from timeline {cursor:.2f}s")
    return {"voice": voice["voice"], "gender": voice["gender"], "tone": voice["tone"],
            "segments": segments, "timeline_seconds": round(cursor, 3), "audio_seconds": round(final_len, 3), "sentences": len(units)}


def synthesize_roster_voice(text, out_dir, log=print):
    """Random narrator from the 3M/3F roster. Writes voice.mp3 + tts-timeline.json to out_dir."""
    import json
    out_dir = Path(out_dir)
    work = out_dir / "voice-parts"
    work.mkdir(parents=True, exist_ok=True)
    units = split_units(text)
    if not units:
        raise RuntimeError("empty narration")
    forced = os.getenv("SEOUL_JOURNAL_VOICE", "").strip().casefold()
    pool = [v for v in VOICE_ROSTER if forced and forced in (v["voice"].casefold(), v["gender"])] or list(VOICE_ROSTER)
    random.shuffle(pool)
    errors = []
    for voice in pool:
        try:
            result = _synthesize_with(voice, units, out_dir, work, log)
            (out_dir / "tts-timeline.json").write_text(json.dumps(
                {"engine": "edge_sentence_timed", "voice": result["voice"], "gender": result["gender"],
                 "segments": result["segments"]}, ensure_ascii=False, indent=2), encoding="utf-8")
            return result
        except Exception as exc:
            errors.append(f"{voice['voice']}:{type(exc).__name__}:{str(exc)[:90]}")
            log("VOICE_FAILED " + errors[-1])
    raise RuntimeError("all roster voices failed: " + " | ".join(errors))


# ---------------------------------------------------------------- subtitles (ASS)

HIGHLIGHT = "&H00D7FF&"   # BGR -> warm yellow
WHITE = "&HFFFFFF&"


def _t(sec):
    cs = int(round(max(0.0, sec) * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _esc(s):
    return s.replace("\\", "").replace("{", "(").replace("}", ")")


def _layout(words, max_line):
    items = []
    line_len = 0
    for w in words:
        raw = w["text"]
        vis = _esc(raw.strip())
        if not vis:
            continue
        if line_len and line_len + len(vis) > max_line:
            items[-1]["sep"] = "\\N"
            line_len = 0
        space = raw[-1:].isspace()
        items.append({"vis": vis, "sep": " " if space else "", "start": float(w["start"]), "end": float(w["end"])})
        line_len += len(vis) + (1 if space else 0)
    if items:
        items[-1]["sep"] = ""
    return items


def write_ass(cues, path, font=None, size=62, max_line=14, y=1290):
    font = font or os.getenv("SEOUL_JOURNAL_SUB_FONT") or ("Malgun Gothic" if sys.platform.startswith("win") else "Noto Sans CJK KR")
    header = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,"
        "ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\n"
        f"Style: Cap,{font},{size},&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,7,3,5,60,60,0,1\n\n"
        "[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
    )
    events = []
    for ci, cue in enumerate(cues):
        words = cue.get("words") or [{"text": cue["text"], "start": cue["start"], "end": cue["end"]}]
        items = _layout(words, max_line)
        if not items:
            continue
        next_start = cues[ci + 1]["start"] if ci + 1 < len(cues) else cue["end"] + 1.0
        for k, it in enumerate(items):
            last = k == len(items) - 1
            st = cue["start"] if k == 0 else it["start"]
            en = min(cue["end"] + 0.15, next_start) if last else items[k + 1]["start"]
            if en <= st + 0.03:
                en = st + 0.05
            body = ""
            for j, x in enumerate(items):
                if j == k:
                    body += "{\\1c" + HIGHLIGHT + "}" + x["vis"] + "{\\1c" + WHITE + "}" + x["sep"]
                else:
                    body += x["vis"] + x["sep"]
            fade = "\\fad(90,0)" if k == 0 and not last else ("\\fad(0,70)" if last and k else ("\\fad(90,70)" if last else ""))
            events.append(f"Dialogue: 0,{_t(st)},{_t(en)},Cap,,0,0,0,,{{\\an5\\pos(540,{y}){fade}}}{body}")
    Path(path).write_text(header + "\n".join(events) + "\n", encoding="utf-8-sig")
    return len(events)
