#!/usr/bin/env python3
"""Daily 3-5 minute narrated video for the Health Clinic USA / Japan and Seoul_Jisoo1 shopping channels.

Free-only stack: free LLM chain (economy_text) -> Microsoft Edge neural TTS -> Pexels/Pixabay
footage and photos -> ffmpeg (Ken Burns, burned-in subtitles) -> YouTube Data API.
Safety: exact authenticated channel ID must equal the locked UC ID before any upload; one video
per KST day per channel (checked against the channel's uploads); health scripts pass a
claim/dosage gate; shopping scripts may use only facts from config/korea_travel_catalog.json.
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import glob
import json
import os
import random
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
KST = dt.timezone(dt.timedelta(hours=9))
W, H, FPS = 1280, 720, 25
UA = {"User-Agent": "Korea365-ChannelVideo/1.0"}

CHANNELS = {
    "health_usa": {
        "channel_id": "UC91BpNSb4nUwD6jrpthK7FQ", "token_env": "HEALTH_CLINIC_YOUTUBE_REFRESH_TOKEN_EN",
        "lang": "en", "voice": "en-US-AriaNeural", "category": "26", "kind": "health", "offset": 0,
        "name": "Health Clinic USA", "tag": "#HealthClinic #SeniorHealth #HealthyAging",
    },
    "health_japan": {
        "channel_id": "UCC_PcHMv-Uxpr00Pjw_J2Wg", "token_env": "HEALTH_CLINIC_YOUTUBE_REFRESH_TOKEN_JP",
        "lang": "ja", "voice": "ja-JP-NanamiNeural", "category": "26", "kind": "health", "offset": 17,
        "name": "Health_Clinic_Japan", "tag": "#シニア健康 #健康習慣 #サプリメント",
    },
    "shopping": {
        "channel_id": "UCAizx0tPkRSol8sIhanN_QQ", "token_env": "YOUTUBE_OAUTH_REFRESH_TOKEN_SHOPPING_SEOUL_JISOO1",
        "lang": "en", "voice": "en-US-JennyNeural", "category": "19", "kind": "shopping", "offset": 0,
        "name": "Seoul_Jisoo1", "tag": "#Korea #SeoulTravel #KoreaHotels",
    },
}

LENGTH = {"en": (520, 720, "words"), "ja": (1150, 1700, "characters")}
DISCLAIMER = {
    "en": "This video is general education, not medical advice. Supplements are not medicines and do not replace treatment. "
          "Talk with your doctor or pharmacist before starting anything new, especially if you take medication.",
    "ja": "この動画は一般的な健康情報であり、医療上の助言ではありません。サプリメントは医薬品ではなく、治療の代わりにはなりません。"
          "新しく始める前に、特にお薬を飲んでいる方は、医師や薬剤師にご相談ください。",
}
AI_NOTE = {"en": "Narration is a synthetic neural voice. Visuals are licensed stock footage and photos (Pexels, Pixabay).",
           "ja": "ナレーションは合成音声です。映像・写真はライセンスされたストック素材(Pexels, Pixabay)です。"}

BANNED = {
    "en": re.compile(r"(?i)\b(cures?|cured|curing|miracle|guarantee[ds]?|reverses? (?:diabetes|dementia|aging)|"
                     r"replaces? (?:your )?(?:medication|doctor|treatment)|stop taking|no side effects|100% (?:safe|effective))\b"),
    "ja": re.compile(r"(治る|治す|治せ|完治|奇跡|必ず効|薬をやめ|副作用(?:は)?(?:ありません|なし)|100%)"),
}
DOSAGE = re.compile(r"(?i)\b\d+(?:\.\d+)?\s?(?:mg|mcg|µg|iu|grams?|g)\b|\d+\s?(?:ミリグラム|マイクログラム|mg|㎎)")
SHOP_BANNED = re.compile(r"(?i)(\$\s?\d|₩\s?\d|\b\d+\s?(?:usd|krw|won|dollars)\b|\b\d(?:\.\d)?\s?stars?\b|best price|cheapest|discount|% off)")


# ----------------------------------------------------------------- catalog + topic choice
def load_topic(channel: str, date: dt.date, topic_key: str = "") -> dict:
    cfg = CHANNELS[channel]
    if cfg["kind"] == "health":
        topics = json.loads((ROOT / "config/senior_health_topics.json").read_text(encoding="utf-8"))["topics"]
    else:
        topics = json.loads((ROOT / "config/korea_travel_catalog.json").read_text(encoding="utf-8"))["topics"]
    if topic_key:
        return next(t for t in topics if t["key"] == topic_key)
    return topics[(date.toordinal() + cfg["offset"]) % len(topics)]


def affiliate(url: str, kind: str) -> str:
    param = {"booking": ("aid", os.getenv("BOOKING_AID", "")), "agoda": ("cid", os.getenv("AGODA_CID", "")),
             "klook": ("aid", os.getenv("KLOOK_AID", ""))}.get(kind, ("", ""))
    if param[1]:
        return url + ("&" if "?" in url else "?") + f"{param[0]}={quote(param[1])}"
    return url


def shopping_links(topic: dict) -> list[tuple[str, str]]:
    cat = json.loads((ROOT / "config/korea_travel_catalog.json").read_text(encoding="utf-8"))
    tpl, out = cat["link_templates"], []
    for hid in topic.get("items", []):
        h = cat["hotels"][hid]
        q = quote(h["name"] + " Korea")
        out.append((f"{h['name']} on Booking.com", affiliate(tpl["booking"].format(q=q), "booking")))
        out.append((f"{h['name']} on Agoda", affiliate(tpl["agoda"].format(q=q), "agoda")))
    for _ in topic.get("links", []):
        out.append(("Tours, passes, eSIM & transfers (Klook)", affiliate(tpl["klook_korea"].format(q=quote("Korea")), "klook")))
    seen, uniq = set(), []
    for label, url in out:
        if url not in seen:
            seen.add(url)
            uniq.append((label, url))
    return uniq


# ----------------------------------------------------------------- script writing
def build_prompt(channel: str, topic: dict, retry_note: str = "") -> str:
    cfg = CHANNELS[channel]
    lang = cfg["lang"]
    lo, hi, unit = LENGTH[lang]
    language = "English" if lang == "en" else "Japanese (natural, polite spoken Japanese for seniors)"
    if cfg["kind"] == "health":
        name = topic[lang] if lang in topic else topic["en"]
        rules = (
            f"Topic: {name}" + (f" (focus: {topic['focus']})" if topic.get("focus") else "") + f". Type: {topic['kind']}.\n"
            "Audience: adults 60+ and their families. Warm, calm, plain words, short sentences, no jargon without a simple explanation.\n"
            "Cover: what it is, what it is commonly used for, what the general evidence says (mixed or limited where true), who should be careful "
            "(medication interactions such as blood thinners, kidney or liver conditions, pregnancy not relevant), food sources where relevant, "
            "and when to see a doctor. Use cautious wording such as 'may help support' or 'is often used for'.\n"
            "FORBIDDEN: cure/treat/prevent-disease claims, miracle or guarantee language, dosage numbers (no mg/mcg/IU/grams), brand names, "
            "telling people to stop medicines, invented studies, statistics or percentages, personal anecdotes.\n"
        )
    else:
        facts = list(topic.get("facts", []))
        cat = json.loads((ROOT / "config/korea_travel_catalog.json").read_text(encoding="utf-8"))
        for hid in topic.get("items", []):
            h = cat["hotels"][hid]
            facts.append(f"{h['name']} - {h['area']}: {h['note']}")
        rules = (
            f"Topic: {topic['title_hint']}.\nAudience: international travelers planning a trip to Korea. Friendly, practical, upbeat.\n"
            "USE ONLY THESE FACTS (do not add other facts):\n" + "\n".join(f"- {f}" for f in facts) + "\n"
            "You may add generic travel common sense (check opening hours, book early in peak season) but NO prices, ratings, awards, discounts, "
            "years, distances in minutes, or availability claims. Tell viewers to check current rates and availability through the links in the description. "
            "Name hotels exactly as written above.\n"
        )
    return f"""You write narration for a 3-5 minute YouTube video in {language}.
{rules}
Structure: a hook (1 scene), 6-9 content scenes, a short friendly closing (1 scene). 9-12 scenes in total.
Total narration length: {lo}-{hi} {unit}. Each scene is 2-5 sentences of spoken narration (no headings, no bullet marks, no emojis, no stage directions).
For every scene give "visual": 2-4 ENGLISH words to search stock footage (concrete, wholesome, generic: e.g. 'senior couple walking park', 'fish oil capsules'; for Korea travel always name the place, e.g. 'seoul hanok village', 'myeongdong street night', 'busan haeundae beach').
{retry_note}
Return ONLY JSON: {{"title":"<=65 chars, specific and honest, no clickbait, no year","hook":"one sentence summary for the description",
"tags":["5-10 short tags"],"scenes":[{{"narration":"...","visual":"..."}}]}}"""


def count_len(text: str, lang: str) -> int:
    return len(re.findall(r"\w+", text)) if lang == "en" else len(re.sub(r"\s", "", text))


def validate_script(data: dict, channel: str) -> list[str]:
    cfg, problems = CHANNELS[channel], []
    lang = cfg["lang"]
    scenes = data.get("scenes") or []
    if not 8 <= len(scenes) <= 14:
        problems.append(f"scene count {len(scenes)}")
    total = sum(count_len(s.get("narration", ""), lang) for s in scenes)
    lo, hi, unit = LENGTH[lang]
    if not lo * 0.9 <= total <= hi * 1.1:
        problems.append(f"length {total} {unit} outside {lo}-{hi}")
    text = " ".join([data.get("title", "")] + [s.get("narration", "") for s in scenes])
    m = BANNED[lang].search(text)
    if m:
        problems.append(f"banned claim '{m.group(0)}'")
    if cfg["kind"] == "health" and DOSAGE.search(text):
        problems.append("dosage number")
    if cfg["kind"] == "shopping" and SHOP_BANNED.search(text):
        problems.append("price/rating claim")
    if not data.get("title") or len(data["title"]) > 100:
        problems.append("title")
    if any(not s.get("narration") or not s.get("visual") for s in scenes):
        problems.append("empty scene field")
    return problems


def write_script(channel: str, topic: dict) -> dict:
    import economy_text
    note, last = "", []
    for attempt in range(4):
        raw = economy_text.generate_text(build_prompt(channel, topic, note), temperature=0.6)
        m = re.search(r"\{.*\}", raw, re.S)
        try:
            data = json.loads(m.group(0))
        except (AttributeError, ValueError):
            last = ["unparseable JSON"]
            note = "Your last answer was not valid JSON. Return only the JSON object."
            continue
        last = validate_script(data, channel)
        if not last:
            return data
        note = "Fix these problems from your previous attempt: " + "; ".join(last) + "."
        print(f"script attempt {attempt + 1} rejected: {last}", flush=True)
    raise RuntimeError(f"No acceptable script after retries: {last}")


# ----------------------------------------------------------------- media
def pexels_video(query: str, used: set, key: str):
    r = requests.get("https://api.pexels.com/videos/search", headers={"Authorization": key},
                     params={"query": query, "orientation": "landscape", "per_page": 12}, timeout=25)
    r.raise_for_status()
    for v in r.json().get("videos", []):
        if f"pv{v['id']}" in used or not 5 <= v.get("duration", 0) <= 60:
            continue
        files = [f for f in v.get("video_files", []) if f.get("file_type") == "video/mp4" and 1000 <= (f.get("width") or 0) <= 1920]
        if files:
            files.sort(key=lambda f: abs((f["width"] or 0) - 1280))
            return {"id": f"pv{v['id']}", "url": files[0]["link"], "type": "video", "credit": "Pexels"}
    return None


def pexels_photo(query: str, used: set, key: str):
    r = requests.get("https://api.pexels.com/v1/search", headers={"Authorization": key},
                     params={"query": query, "orientation": "landscape", "per_page": 12}, timeout=25)
    r.raise_for_status()
    for p in r.json().get("photos", []):
        if f"pp{p['id']}" not in used and p.get("width", 0) >= 1280:
            return {"id": f"pp{p['id']}", "url": p["src"]["large2x"], "type": "image", "credit": "Pexels"}
    return None


def pixabay_photo(query: str, used: set, key: str):
    r = requests.get("https://pixabay.com/api/", params={"key": key, "q": query, "image_type": "photo", "orientation": "horizontal",
                                                           "safesearch": "true", "min_width": 1280, "per_page": 12}, timeout=25)
    r.raise_for_status()
    for p in r.json().get("hits", []):
        if f"px{p['id']}" not in used:
            return {"id": f"px{p['id']}", "url": p["largeImageURL"], "type": "image", "credit": "Pixabay"}
    return None


def fetch_media(query: str, want_video: bool, used: set, tmp: Path, idx: int, kind: str = ""):
    if kind == "shopping" and not re.search(r"(?i)korea|seoul|busan|jeju|hanok|myeongdong|hongdae|gangnam", query):
        query = "Korea " + query  # generic stock has no Korean context unless asked
    pk, xk = os.getenv("PEXELS_API_KEY", ""), os.getenv("PIXABAY_KEY", "") or os.getenv("PIXABAY_API_KEY", "")
    words = query.split()
    queries = [query] + ([" ".join(words[:2])] if len(words) > 2 else [])
    steps = []
    for q in queries:
        if pk and want_video:
            steps.append((pexels_video, q, pk))
        if pk:
            steps.append((pexels_photo, q, pk))
        if xk:
            steps.append((pixabay_photo, q, xk))
    for fn, q, key in steps:
        try:
            m = fn(q, used, key)
        except requests.RequestException as exc:
            print(f"media source error {fn.__name__}: {type(exc).__name__}", flush=True)
            continue
        if not m:
            continue
        ext = "mp4" if m["type"] == "video" else "jpg"
        path = tmp / f"media_{idx:02d}.{ext}"
        with requests.get(m["url"], headers=UA, timeout=90, stream=True) as resp:
            if resp.status_code != 200:
                continue
            with path.open("wb") as fh:
                for chunk in resp.iter_content(1 << 16):
                    fh.write(chunk)
        if path.stat().st_size < 20_000:
            continue
        used.add(m["id"])
        return {**m, "path": path}
    return None


def font_path(bold: bool = True) -> str | None:
    pats = ["/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/**/NotoSansCJK*-Bold*.ttc", "/usr/share/fonts/**/DejaVuSans-Bold.ttf"]
    for p in pats:
        hits = glob.glob(p, recursive=True)
        if hits:
            return hits[0]
    return None


def fallback_card(text: str, path: Path, seed: int):
    from PIL import Image, ImageDraw, ImageFont
    rnd = random.Random(seed)
    base = [rnd.randint(20, 90) for _ in range(3)]
    img = Image.new("RGB", (1920, 1080), tuple(base))
    d = ImageDraw.Draw(img)
    for y in range(1080):
        c = tuple(min(255, int(b + y / 1080 * 70)) for b in base)
        d.line([(0, y), (1920, y)], fill=c)
    f = ImageFont.truetype(font_path() or "", 86) if font_path() else ImageFont.load_default()
    d.text((960, 540), text[:40], font=f, fill=(255, 255, 255), anchor="mm")
    img.save(path, quality=90)


def run(cmd: list[str]):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed: {r.stderr[-600:]}")
    return r.stdout


def duration(path: Path) -> float:
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)]).strip())


async def _tts(text: str, voice: str, out: Path):
    import edge_tts
    last = None
    for _ in range(4):
        try:
            await edge_tts.Communicate(text, voice, rate="-6%").save(str(out))
            if out.exists() and out.stat().st_size > 2000:
                return
        except Exception as exc:  # network/voice service hiccup
            last = exc
            await asyncio.sleep(3)
    raise RuntimeError(f"TTS failed for voice {voice}: {last}")


def split_chunks(text: str, lang: str) -> list[str]:
    limit = 34 if lang == "en" else 17  # per line; two lines per cue
    sents = [s.strip() for s in re.split(r"(?<=[.!?。！？])\s*", text) if s.strip()]
    chunks = []
    for s in sents:
        if lang == "en":
            words, cur = s.split(), ""
            for w in words:
                if len((cur + " " + w).strip()) > limit * 2 and cur:
                    chunks.append(cur)
                    cur = w
                else:
                    cur = (cur + " " + w).strip()
            if cur:
                chunks.append(cur)
        else:
            parts = re.split(r"(?<=[、，,])", s)
            cur = ""
            for p in parts:
                if len(cur + p) > limit * 2 and cur:
                    chunks.append(cur)
                    cur = p
                else:
                    cur += p
            while len(cur) > limit * 2:
                chunks.append(cur[:limit * 2])
                cur = cur[limit * 2:]
            if cur:
                chunks.append(cur)
    return chunks


def wrap2(text: str, lang: str) -> str:
    limit = 34 if lang == "en" else 17
    if len(text) <= limit:
        return text
    if lang == "en":
        words, a = text.split(), ""
        for i, w in enumerate(words):
            if len((a + " " + w).strip()) > len(text) / 2 + 3 and a:
                return a + "\n" + " ".join(words[i:])
            a = (a + " " + w).strip()
        return text
    mid = len(text) // 2
    return text[:mid] + "\n" + text[mid:]


def srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def make_srt(scene_texts: list[str], durations: list[float], lang: str) -> str:
    out, n, t0 = [], 1, 0.0
    for text, dur in zip(scene_texts, durations):
        chunks = split_chunks(text, lang)
        weights = [max(1, len(re.sub(r"\s", "", c))) for c in chunks]
        total, cur = sum(weights), t0 + 0.15
        usable = max(0.5, dur - 0.5)
        for c, w in zip(chunks, weights):
            span = usable * w / total
            out.append(f"{n}\n{srt_time(cur)} --> {srt_time(cur + span)}\n{wrap2(c, lang)}\n")
            n += 1
            cur += span
        t0 += dur
    return "\n".join(out)


def build_video(channel: str, data: dict, outdir: Path) -> dict:
    cfg = CHANNELS[channel]
    lang = cfg["lang"]
    tmp = outdir / "work"
    tmp.mkdir(parents=True, exist_ok=True)
    scenes = list(data["scenes"])
    if cfg["kind"] == "health":
        scenes.append({"narration": DISCLAIMER[lang], "visual": "doctor consultation senior"})
    used: set = set()
    clips, durs, texts, credits = [], [], [], []
    for i, sc in enumerate(scenes):
        audio = tmp / f"a_{i:02d}.mp3"
        asyncio.run(_tts(sc["narration"], cfg["voice"], audio))
        dur = duration(audio) + 0.45
        media = fetch_media(sc["visual"], want_video=(i % 2 == 0), used=used, tmp=tmp, idx=i, kind=cfg["kind"])
        if media is None:
            card = tmp / f"card_{i:02d}.jpg"
            fallback_card(sc["visual"].title(), card, i)
            media = {"type": "image", "path": card, "id": f"card{i}", "credit": "generated card"}
            print(f"scene {i}: no stock media for '{sc['visual']}', used card", flush=True)
        credits.append({"scene": i, "id": media["id"], "type": media["type"], "credit": media["credit"], "query": sc["visual"]})
        clip = tmp / f"clip_{i:02d}.mp4"
        common = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", "-r", str(FPS),
                  "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-shortest"]
        if media["type"] == "video":
            vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1"
            run(["ffmpeg", "-y", "-stream_loop", "-1", "-i", str(media["path"]), "-i", str(audio), "-t", f"{dur:.2f}",
                 "-vf", vf, "-af", "apad", *common, str(clip)])
        else:
            frames = int(dur * FPS) + 2
            vf = (f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
                  f"zoompan=z='min(zoom+0.0007,1.18)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},setsar=1")
            run(["ffmpeg", "-y", "-i", str(media["path"]), "-i", str(audio), "-t", f"{dur:.2f}", "-vf", vf, "-af", "apad", *common, str(clip)])
        clips.append(clip)
        durs.append(duration(clip))
        texts.append(sc["narration"])
        print(f"scene {i + 1}/{len(scenes)} ok ({durs[-1]:.1f}s, {media['type']})", flush=True)
    listing = tmp / "concat.txt"
    listing.write_text("".join(f"file '{c.name}'\n" for c in clips), encoding="utf-8")
    joined = tmp / "joined.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(joined)])
    srt = outdir / "subtitles.srt"
    srt.write_text(make_srt(texts, durs, lang), encoding="utf-8")
    final = outdir / "video.mp4"
    size = 18 if lang == "en" else 16
    style = (f"FontName=Noto Sans CJK JP,FontSize={size},Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
             f"BackColour=&H80000000,BorderStyle=1,Outline=1.6,Shadow=0.6,MarginV=22,Alignment=2")
    (tmp / "subs.srt").write_text(srt.read_text(encoding="utf-8"), encoding="utf-8")
    burn = subprocess.run(
        ["ffmpeg", "-y", "-i", "joined.mp4", "-vf", f"subtitles=subs.srt:force_style='{style}'", "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "22", "-c:a", "copy", "-movflags", "+faststart", str(final.resolve())], cwd=tmp, capture_output=True, text=True)
    if burn.returncode != 0:
        raise RuntimeError(f"subtitle burn failed: {burn.stderr[-600:]}")
    total = duration(final)
    return {"video_path": str(final), "duration_s": round(total, 1), "credits": credits, "srt": str(srt), "first_media": credits[0]}


def make_thumbnail(title: str, outdir: Path, lang: str):
    from PIL import Image, ImageDraw, ImageFont
    work = outdir / "work"
    src = next(iter(sorted(work.glob("media_00.jpg"))), None)
    if src:
        img = Image.open(src).convert("RGB").resize((W, H))
    else:
        run(["ffmpeg", "-y", "-ss", "2", "-i", str(outdir / "video.mp4"), "-frames:v", "1", str(work / "frame.jpg")])
        img = Image.open(work / "frame.jpg").convert("RGB").resize((W, H))
    shade = Image.new("RGB", (W, H), (0, 0, 0))
    img = Image.blend(img, shade, 0.38)
    d = ImageDraw.Draw(img)
    fp = font_path()
    f = ImageFont.truetype(fp, 78 if lang == "en" else 70) if fp else ImageFont.load_default()
    lines = wrap2(title, lang).split("\n") if len(title) > (30 if lang == "en" else 15) else [title]
    if lang == "en" and len(lines) == 1 and len(title) > 24:
        words = title.split()
        lines = [" ".join(words[:len(words) // 2]), " ".join(words[len(words) // 2:])]
    y = H // 2 - 50 * len(lines)
    for line in lines:
        d.text((W // 2, y), line, font=f, fill=(255, 255, 255), anchor="mm", stroke_width=5, stroke_fill=(0, 0, 0))
        y += 100
    path = outdir / "thumbnail.jpg"
    img.save(path, quality=90)
    return path


# ----------------------------------------------------------------- YouTube
def youtube_service(channel: str):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    cfg = CHANNELS[channel]
    token = os.environ.get(cfg["token_env"], "")
    if not token:
        raise RuntimeError(f"Missing secret {cfg['token_env']}")
    creds = Credentials(token=None, refresh_token=token, token_uri="https://oauth2.googleapis.com/token",
                        client_id=os.environ["YOUTUBE_OAUTH_CLIENT_ID"], client_secret=os.environ["YOUTUBE_OAUTH_CLIENT_SECRET"], scopes=None)
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def preflight(channel: str):
    svc = youtube_service(channel)
    items = svc.channels().list(part="id,contentDetails", mine=True).execute().get("items", [])
    if len(items) != 1 or items[0]["id"] != CHANNELS[channel]["channel_id"]:
        got = [i["id"] for i in items]
        raise RuntimeError(f"Exact-channel check failed for {channel}: expected {CHANNELS[channel]['channel_id']}, got {got}")
    return svc, items[0]["contentDetails"]["relatedPlaylists"]["uploads"]


def already_published_today(svc, uploads_playlist: str, today: dt.date) -> str | None:
    rows = svc.playlistItems().list(part="contentDetails,snippet", playlistId=uploads_playlist, maxResults=15).execute().get("items", [])
    for r in rows:
        stamp = r["contentDetails"].get("videoPublishedAt") or r["snippet"].get("publishedAt", "")
        if not stamp:
            continue
        when = dt.datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(KST).date()
        if when == today:
            return r["contentDetails"]["videoId"]
    return None


def description_for(channel: str, data: dict, topic: dict) -> str:
    cfg = CHANNELS[channel]
    lang = cfg["lang"]
    parts = [data.get("hook", "")]
    if cfg["kind"] == "health":
        parts += ["", DISCLAIMER[lang]]
    else:
        links = shopping_links(topic)
        if links:
            parts += ["", "Links (check current rates and availability):"] + [f"- {l}: {u}" for l, u in links]
            if any(os.getenv(k) for k in ("BOOKING_AID", "AGODA_CID", "KLOOK_AID")):
                parts += ["", "Some links are affiliate links. If you book through them we may earn a commission at no extra cost to you."]
        parts += ["", "Prices, ratings and availability change often; always confirm on the booking site."]
    parts += ["", AI_NOTE[lang], "", cfg["tag"]]
    return "\n".join(parts)[:4900]


def upload(channel: str, svc, outdir: Path, data: dict, topic: dict, privacy: str) -> dict:
    from googleapiclient.http import MediaFileUpload
    from publish_survival_adjective_shorts import wait_for_verified_video
    cfg = CHANNELS[channel]
    body = {
        "snippet": {"title": data["title"][:100], "description": description_for(channel, data, topic),
                    "tags": [t[:30] for t in data.get("tags", [])][:12], "categoryId": cfg["category"],
                    "defaultLanguage": cfg["lang"], "defaultAudioLanguage": cfg["lang"]},
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }
    req = svc.videos().insert(part="snippet,status", body=body,
                              media_body=MediaFileUpload(str(outdir / "video.mp4"), mimetype="video/mp4", resumable=True, chunksize=8 * 1024 * 1024))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    vid = resp["id"]
    video = wait_for_verified_video(svc, vid, cfg["channel_id"], privacy)  # fails closed on wrong channel/privacy
    thumb_ok = True
    try:
        svc.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(outdir / "thumbnail.jpg"), mimetype="image/jpeg")).execute()
    except Exception as exc:  # custom thumbnails need a phone-verified channel; never fail the upload for it
        thumb_ok = False
        print(f"thumbnail not set: {type(exc).__name__}", flush=True)
    receipt = {"video_id": vid, "url": f"https://www.youtube.com/watch?v={vid}", "channel_id": cfg["channel_id"],
               "privacy_status": video["status"]["privacyStatus"], "thumbnail_set": thumb_ok,
               "published_at": dt.datetime.now(dt.timezone.utc).isoformat()}
    (outdir / "publication_receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return receipt


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", required=True, choices=sorted(CHANNELS))
    ap.add_argument("--date", default=dt.datetime.now(KST).date().isoformat())
    ap.add_argument("--topic", default="")
    ap.add_argument("--privacy", choices=("public", "private", "unlisted"), default="private")
    ap.add_argument("--upload", action="store_true", help="upload after exact-channel verification (otherwise build only)")
    ap.add_argument("--force", action="store_true", help="ignore the one-video-per-KST-day guard")
    ap.add_argument("--output-root", default=str(ROOT / "artifacts" / "long-video"))
    a = ap.parse_args()
    date = dt.date.fromisoformat(a.date)
    outdir = Path(a.output_root) / a.channel / a.date
    outdir.mkdir(parents=True, exist_ok=True)
    svc = None
    if a.upload:
        svc, uploads = preflight(a.channel)  # exact channel + write access before spending any time rendering
        if not a.force:
            existing = already_published_today(svc, uploads, date)
            if existing:
                print(f"SKIP: {a.channel} already has video {existing} for KST {a.date}")
                return 0
    topic = load_topic(a.channel, date, a.topic)
    print(f"channel={a.channel} topic={topic.get('key')}", flush=True)
    data = write_script(a.channel, topic)
    built = build_video(a.channel, data, outdir)
    if not 150 <= built["duration_s"] <= 330:
        raise RuntimeError(f"Duration {built['duration_s']}s outside the 3-5 minute window (tolerance 150-330s)")
    make_thumbnail(data["title"], outdir, CHANNELS[a.channel]["lang"])
    manifest = {"channel": a.channel, "date": a.date, "topic": topic, "title": data["title"], "hook": data.get("hook"),
                "tags": data.get("tags"), "scenes": data["scenes"], "description": description_for(a.channel, data, topic), **built}
    (outdir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"BUILT {built['duration_s']}s -> {built['video_path']}", flush=True)
    if a.upload:
        receipt = upload(a.channel, svc, outdir, data, topic, a.privacy)
        print("PUBLISHED", json.dumps(receipt), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
