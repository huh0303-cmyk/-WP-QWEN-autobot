#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
archive_footage_longform.py
─────────────────────────────────────────────────────────────
american_archive / history(_today) / invention / silent_era / retro_reels
5개 채널 공용 파이프라인. nasa_archive_longform.py와 같은 원칙 — AI 생성
영상 대신 Internet Archive(archive.org, 무료·키 불필요)에서 실제 퍼블릭도메인
영상을 검색+다운로드해 짜깁기하고, 그 위에 Gemini 사실기반 나레이션
(ElevenLabs TTS) + 큰 번인자막을 입힌다. 썸네일도 실제 다운로드한 프레임 사용.

퍼블릭도메인 검증 원칙(채널마다 다름, CHANNEL_ARCHIVE_CONFIG 참고):
- Prelinger Archives(collection:prelinger)는 기증 조건 자체가 전량 퍼블릭도메인이라
  개별 licenseurl 없이도 안전(invention, retro_reels).
- 그 외(american_archive, history, silent_era)는 검색 시점에 licenseurl이 명시적으로
  "publicdomain"인 항목만 통과시킨다 — archive.org는 저작권 있는 업로드도 섞여 있어서
  Prelinger처럼 컬렉션 전체를 신뢰할 수 없음.
- silent_era는 추가로 1929년 이전 작품이면 licenseurl이 없어도 허용(미국 저작권법상
  95년 보호기간이 지나 자동으로 퍼블릭도메인인 게 법적으로 확실하기 때문).

myth(신화)와 science(과학상식)는 이 파이프라인 대상이 아니다 — 실존하는 "실제 영상
자료"가 애초에 없는 주제라 억지로 아카이브를 끼워맞추면 안 됨. 계속 curio_longform.py
(Gemini 이미지 기반) 그대로 사용.

사용법(curio_longform.py와 동일한 인자 순서 — 워크플로우 재사용 가능):
    python scripts/archive_footage_longform.py "<주제>" en "" <channel_key>
    예: python scripts/archive_footage_longform.py "Charlie Chaplin and The Tramp" en "" silent_era
"""
import os
import re
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests  # noqa: E402

from curio_longform import (  # noqa: E402
    gemini_generate_text, get_duration, run_ffmpeg, _strip_json_fence,
    log, GEMINI_API_KEY, ensure_thumbnail_font,
)
from classic_reads_longform import (  # noqa: E402
    build_narration_track, write_srt, mux_final, _save_thumbnail_capped,
)
from nasa_archive_longform import (  # noqa: E402
    normalize_clip, build_visual_track, extract_hero_frame, W, H,
)

IA_SEARCH = "https://archive.org/advancedsearch.php"
IA_METADATA = "https://archive.org/metadata"
LOC_SEARCH = "https://www.loc.gov/collections/national-screening-room/"
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

CHANNEL_ARCHIVE_CONFIG = {
    "american_archive": {"collections": None, "require_pd_license": True, "max_year": None,
                          "domain": "American history told through public archival footage"},
    "history": {"collections": None, "require_pd_license": True, "max_year": None,
                "domain": "on-this-day historical events"},
    "invention": {"collections": ["prelinger"], "require_pd_license": False, "max_year": None,
                  "domain": "the history of inventions, shown through real vintage footage"},
    "silent_era": {"collections": None, "require_pd_license": True, "max_year": 1929,
                    "domain": "classic silent films and the early days of cinema"},
    "retro_reels": {"collections": ["prelinger"], "require_pd_license": False, "max_year": None,
                     "domain": "nostalgic 20th-century pop culture, shown through real vintage footage"},
}


# ════════════════════════════════════════════════════════════
# 1. Internet Archive 검색 + 퍼블릭도메인 필터 + 다운로드
# ════════════════════════════════════════════════════════════
def _build_query(topic, cfg):
    q = f'({topic}) AND mediatype:(movies)'
    if cfg["collections"]:
        coll = " OR ".join(f"collection:{c}" for c in cfg["collections"])
        q += f" AND ({coll})"
    if cfg["require_pd_license"]:
        q += ' AND licenseurl:(*publicdomain*)'
    return q


_STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "was", "were",
    "his", "her", "its", "into", "over", "under", "about", "when", "how",
    "why", "what", "who", "which", "became", "become", "becomes", "first",
    "day", "the", "and",
}


def _extract_keywords(topic):
    """검색 결과가 실제로 주제와 관련 있는지 확인하기 위한 핵심 단어 추출.
    2026-08-21 사고: 릴리번스 검증 없이 archive.org 전문검색 결과를 그대로
    받아쓰다 보니 "Hawaii becomes the" 검색에 Baywatch/사탕광고/감옥 다큐 같은
    완전 무관한 영상이 섞여 들어감(느슨한 단어 매칭이라 "the" 하나로도 걸림).
    제목/연도/날짜 숫자 등 topic의 고유명사·핵심어가 최소 하나는 클립 제목이나
    설명에 실제로 들어있어야 통과시킨다."""
    words = re.findall(r"[A-Za-z']+|\d+", topic)
    keywords = set()
    for w in words:
        wl = w.lower()
        if wl in _STOPWORDS or len(w) < 3:
            continue
        keywords.add(wl)
    return keywords


def _is_relevant(doc, keywords):
    if not keywords:
        return True
    haystack = f"{doc.get('title') or ''} {doc.get('description') or ''}".lower()
    return any(kw in haystack for kw in keywords)


def search_archive_org(topic, cfg, count, max_retries=3):
    """2026-08-17: 여러 채널이 짧은 간격으로 동시에 검색하면 archive.org가
    가끔 정상 JSON이 아닌 응답(과부하/일시 오류)을 줘서 KeyError로 전체가
    죽는 사고가 있었음 — 재시도 + 안전한 폴백으로 방어."""
    q = _build_query(topic, cfg)
    params = {
        "q": q, "rows": count, "output": "json",
        "fl[]": ["identifier", "title", "year", "licenseurl", "description"],
    }
    for attempt in range(max_retries):
        try:
            r = requests.get(IA_SEARCH, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            docs = data.get("response", {}).get("docs")
            if docs is not None:
                break
            log(f"   ⚠️ archive.org 응답 형식 이상(response 없음) — 재시도({attempt + 1}/{max_retries})")
        except Exception as e:
            log(f"   ⚠️ archive.org 검색 실패({e}) — 재시도({attempt + 1}/{max_retries})")
        docs = []
        if attempt < max_retries - 1:
            import time as _time
            _time.sleep(5 * (attempt + 1))
    else:
        log("   ⚠️ archive.org 검색 계속 실패 — 이번 시도는 결과 없음으로 처리")
    # licenseurl이 없어도 1929년 이전(법적으로 확실한 PD)이면 통과시킨다(silent_era 등).
    max_year = cfg.get("max_year")
    out = []
    for d in docs:
        year = d.get("year")
        try:
            year = int(year) if year else None
        except (TypeError, ValueError):
            year = None
        has_pd_license = "publicdomain" in (d.get("licenseurl") or "")
        legally_pd_by_age = max_year is not None and year is not None and year <= max_year
        if cfg["require_pd_license"] and not (has_pd_license or legally_pd_by_age):
            continue
        out.append(d)
    return out


def _best_ia_file(files, identifier):
    """h.264/MPEG4 mp4 우선, 너무 큰 원본은 피한다(CI 다운로드 속도)."""
    candidates = [f for f in files if f.get("format", "").lower() in ("h.264", "mpeg4")]
    if not candidates:
        candidates = [f for f in files if f.get("name", "").lower().endswith(".mp4")]
    if not candidates:
        return None
    candidates.sort(key=lambda f: int(f.get("size") or 0))
    for f in candidates:
        size = int(f.get("size") or 0)
        if size and size < 400 * 1024 * 1024:  # 400MB 미만 우선
            return f["name"]
    return candidates[0]["name"]


def download_file(url, out_path, timeout=180):
    r = requests.get(url, stream=True, timeout=timeout)
    r.raise_for_status()
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=1 << 16):
            f.write(chunk)


# ════════════════════════════════════════════════════════════
# 1b. 미국 의회도서관(Library of Congress) National Screening Room —
#     Internet Archive를 보조하는 2차 소스. 컬렉션 자체가 작아서(검색어당
#     결과가 몇 개 안 됨) 주력 소스로는 안 쓰지만, 사용자가 명시적으로
#     "미의회도서관에서"라고 지시했으므로 매번 같이 시도해서 실제로
#     섞어 쓴다. 항목마다 rights 상태가 다를 수 있어 access_restricted/
#     download_restricted 플래그가 False인 것만 사용한다.
# ════════════════════════════════════════════════════════════
def search_loc(query, count):
    try:
        r = requests.get(LOC_SEARCH, params={"fo": "json", "q": query, "c": count}, timeout=30)
        r.raise_for_status()
        return (r.json().get("results") or [])[:count]
    except Exception as e:
        log(f"   ⚠️ LOC 검색 실패({query}): {e}")
        return []


def fetch_loc_clip_info(item_url):
    if not item_url:
        return None
    try:
        r = requests.get(item_url, params={"fo": "json"}, timeout=30)
        r.raise_for_status()
        d = r.json()
    except Exception:
        return None
    item = d.get("item", {}) or {}
    if item.get("access_restricted"):
        return None
    resources = d.get("resources") or []
    if not resources:
        return None
    res = resources[0]
    if res.get("download_restricted"):
        return None
    video_url = res.get("video")
    if not video_url:
        return None
    return {"video_url": video_url, "title": item.get("title", ""),
            "date": item.get("date") or "", "identifier": item_url}


def fetch_loc_clips(query, workdir, n_target=4):
    docs = search_loc(query, n_target * 2)
    clips = []
    for d in docs:
        if len(clips) >= n_target:
            break
        info = fetch_loc_clip_info(d.get("id", ""))
        if not info:
            continue
        safe_name = re.sub(r"[^A-Za-z0-9_-]", "_", info["identifier"])[-60:]
        raw_path = os.path.join(workdir, f"raw_loc_{safe_name}.mp4")
        try:
            if not os.path.exists(raw_path):
                download_file(info["video_url"], raw_path)
            dur = get_duration(raw_path)
            if dur < 3:
                continue
            clips.append({
                "path": raw_path, "title": info["title"], "duration": dur,
                "identifier": f"LOC:{info['identifier']}",
                "year": info["date"][:4] if info["date"] else "",
                "description": "",
            })
        except Exception as e:
            log(f"   ⚠️ LOC 다운로드 실패({info['identifier']}): {e}")
            continue
    return clips


# 채널별 도메인만으로 재검색할 때 쓸 단순 키워드(구체적 주제로 결과가 없을 때의 폴백).
_FALLBACK_QUERY = {
    "american_archive": "American history newsreel",
    "history": "historical newsreel documentary",
    "invention": "invention technology history",
    "silent_era": "silent film",
    "retro_reels": "vintage advertisement 1950s",
}


def fetch_archive_clips(topic, channel_key, workdir, n_target=40):
    """실제 영상을 반드시 확보하는 게 우선이라(사용자 지시: 짧아도, 흑백이어도
    상관없음), 특정 주제로 결과가 없으면 점점 검색 범위를 넓혀서 재시도한다:
    1) 정확한 주제 그대로 검색
    2) 주제에서 핵심 단어만 남겨 재검색
    3) 채널 도메인 공통 키워드로 재검색(사실상 무조건 결과가 나오는 폴백).

    2026-08-18 사고: n_target이 8이었는데 클립당 최대 22초(CLIP_TRIM_SECONDS)라
    8분 나레이션 채우려면 같은 8개를 2.5바퀴나 돌려써서 눈에 띄게 반복 재생됨
    (History Today 영상, 사용자가 "계속 반복된다"고 지적). 20으로 올려 반복을
    거의 없애거나 최소화."""
    cfg = CHANNEL_ARCHIVE_CONFIG[channel_key]

    attempts = [topic]
    core_words = " ".join(topic.split()[:3])
    if core_words and core_words != topic:
        attempts.append(core_words)
    attempts.append(_FALLBACK_QUERY.get(channel_key, channel_key))

    # 2026-08-21: topic/core_words 단계는 주제와 실제로 무관한 결과(느슨한 텍스트
    # 매칭 때문에 Baywatch, 사탕광고, 감옥 다큐 같은 게 섞여 들어옴)를 걸러내야
    # 함 — 클립 제목/설명에 주제 핵심어가 하나도 없으면 버린다. 마지막 단계인
    # 채널 도메인 폴백 쿼리(_FALLBACK_QUERY)는 애초에 주제-불특정 범용 키워드라
    # 이 필터를 적용하면 안 됨(항상 걸러져서 빈 결과가 됨).
    keywords = _extract_keywords(topic)
    docs = []
    used_query = None
    for i, q in enumerate(attempts):
        is_fallback_tier = (i == len(attempts) - 1)
        found = search_archive_org(q, cfg, n_target * 3)
        if not is_fallback_tier:
            before = len(found)
            found = [d for d in found if _is_relevant(d, keywords)]
            if before and not found:
                log(f"   (검색은 됐지만 주제와 무관한 결과뿐이라 버림: \"{q}\", {before}건 전부 제외)")
        if found:
            docs = found
            used_query = q
            break
        log(f"   (검색 결과 없음: \"{q}\" — 범위를 넓혀 재시도)")
    if not docs:
        return []
    if used_query != topic:
        log(f"   ℹ️ 정확한 주제로는 못 찾아서 \"{used_query}\"로 대체 검색함")

    clips = []
    for d in docs:
        if len(clips) >= n_target:
            break
        identifier = d.get("identifier")
        if not identifier:
            continue
        try:
            meta = requests.get(f"{IA_METADATA}/{identifier}", timeout=30).json()
        except Exception:
            continue
        fname = _best_ia_file(meta.get("files", []), identifier)
        if not fname:
            continue
        asset_url = f"https://archive.org/download/{identifier}/{fname}"
        safe_name = re.sub(r"[^A-Za-z0-9_-]", "_", identifier)[:60]
        raw_path = os.path.join(workdir, f"raw_{safe_name}.mp4")
        try:
            if not os.path.exists(raw_path):
                download_file(asset_url, raw_path)
            dur = get_duration(raw_path)
            if dur < 3:
                continue
            clips.append({
                "path": raw_path, "title": d.get("title", ""), "duration": dur,
                "identifier": identifier, "year": d.get("year", ""),
                "description": (d.get("description") or "")[:300] if isinstance(d.get("description"), str) else "",
            })
        except Exception as e:
            log(f"   ⚠️ 다운로드 실패({identifier}): {e}")
            continue

    # 미의회도서관(LOC) National Screening Room도 항상 같이 시도해서 섞는다
    # (Internet Archive만으로 충분해도 사용자가 명시적으로 요청한 소스라 매번 시도).
    if len(clips) < n_target:
        loc_clips = fetch_loc_clips(used_query, workdir, n_target=n_target - len(clips))
        if loc_clips:
            log(f"   + LOC(미의회도서관)에서 {len(loc_clips)}개 클립 추가 확보")
        clips.extend(loc_clips)

    return clips


# ════════════════════════════════════════════════════════════
# 2. 대본 + 메타데이터 (사실기반)
# ════════════════════════════════════════════════════════════
def generate_script(topic, channel_key, clips):
    domain = CHANNEL_ARCHIVE_CONFIG[channel_key]["domain"]
    clip_notes = "\n".join(
        f"- {c['title']} ({c['year'] or 'year unknown'}): {c['description']}" for c in clips
    )
    prompt = f"""You are writing a narration script for a ~14-minute YouTube documentary
video about: "{topic}". This channel's domain is: {domain}. The video uses real
public-domain archival footage (not AI-generated visuals).

Real archival clips that will play under this narration (ground your script in
real, well-documented facts — reference what these clips likely show, but do
not invent specific details not backed by well-known public facts):
---
{clip_notes[:3000]}
---

Write "narration": ~1900-2000 words, English, engaging documentary tone (a good
history/culture YouTuber, not a dry lecture). Hook in the first two sentences.
Structure: hook -> context -> core interesting facts/story -> a surprising or
lesser-known detail -> a memorable closing line. Do not fabricate quotes or
specific statistics beyond well-established public knowledge.

Also write "title_hint": a short natural phrase capturing the video's angle.

Respond with JSON only, no explanation, no markdown fences:
{{"narration": "...", "title_hint": "..."}}
"""
    text = gemini_generate_text(prompt, temperature=0.85)
    return json.loads(_strip_json_fence(text))


def generate_youtube_metadata(topic, channel_key, narration):
    prompt = f"""You are writing the YouTube title and description for a documentary
video about "{topic}", on a channel using real public-domain archival footage
(Internet Archive / Prelinger Archives).

Narration script:
---
{narration[:6000]}
---

Write:
1. "title": a warm, friendly, curiosity-driven YouTube title, under 100
   characters — like a real person who loves this topic sharing it with you,
   not a clickbait template. No ALL CAPS spam, no emoji-stuffing, no lies.
2. "description": around 1000 characters (not bytes), always in English.
   - Open with 2-3 sentences on why this moment/topic matters, plain natural
     prose (no "In this video, we will explore..." or similar AI-sounding
     opener).
   - A short paragraph pulling out 3-5 concrete facts actually in the script.
   - Mention the footage is real public-domain archival footage.
   - One natural sentence inviting people to subscribe for more.
   - End with 4-6 relevant hashtags on the last line.

Respond with JSON only, no explanation, no markdown fences:
{{"title": "...", "description": "..."}}
"""
    text = gemini_generate_text(prompt, temperature=0.8)
    return json.loads(_strip_json_fence(text))


# ════════════════════════════════════════════════════════════
# 3. 썸네일 — 실제 다운로드 프레임 + 채널별 브랜드 태그
# ════════════════════════════════════════════════════════════
_BRAND_TAG = {
    "american_archive": "REAL ARCHIVAL FOOTAGE",
    "history": "REAL ARCHIVAL FOOTAGE",
    "invention": "REAL VINTAGE FOOTAGE",
    "silent_era": "PUBLIC DOMAIN SILENT FILM",
    "retro_reels": "REAL VINTAGE FOOTAGE",
}


def build_thumbnail(topic, channel_key, hero_frame_path, workdir):
    from PIL import Image, ImageDraw, ImageFont, ImageEnhance

    def crop_resize(img, w, h):
        ratio = img.width / img.height
        target_ratio = w / h
        if ratio > target_ratio:
            new_h = img.height
            new_w = int(new_h * target_ratio)
            left = (img.width - new_w) // 2
            img = img.crop((left, 0, left + new_w, new_h))
        else:
            new_w = img.width
            new_h = int(new_w / target_ratio)
            top = (img.height - new_h) // 2
            img = img.crop((0, top, new_w, top + new_h))
        return img.resize((w, h), Image.LANCZOS)

    def text_with_outline(draw, cx, y, text, font, fill, outline, ow=10):
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        x = cx - w // 2 - bbox[0]
        for dx in range(-ow, ow + 1, 3):
            for dy in range(-ow, ow + 1, 3):
                if dx * dx + dy * dy <= ow * ow:
                    draw.text((x + dx, y + dy), text, font=font, fill=outline)
        draw.text((x, y), text, font=font, fill=fill)

    def wrap(draw, text, font, max_width, max_lines=2):
        words = text.split()
        lines, cur = [], ""
        for w in words:
            trial = (cur + " " + w).strip()
            if draw.textbbox((0, 0), trial, font=font)[2] <= max_width:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines[:max_lines]

    TW, TH = 1280, 720
    UPSCALE = (5120, 2880)
    font_path = ensure_thumbnail_font("en", DATA_DIR)

    img = crop_resize(Image.open(hero_frame_path).convert("RGB"), TW, TH)
    img = ImageEnhance.Contrast(img).enhance(1.15)
    canvas = img.copy()

    overlay = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rectangle([0, TH - 260, TW, TH], fill=(0, 0, 0, 165))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(canvas)

    WHITE, YELLOW, BLACK = (255, 255, 255), (255, 214, 0), (0, 0, 0)
    title_font = ImageFont.truetype(font_path, 62)
    lines = wrap(draw, topic.upper(), title_font, TW - 100)
    y = TH - 240
    for line in lines:
        text_with_outline(draw, TW // 2, y, line, title_font, YELLOW, BLACK, 10)
        y += 72

    tag_font = ImageFont.truetype(font_path, 30)
    text_with_outline(draw, TW // 2, TH - 45, _BRAND_TAG.get(channel_key, "REAL ARCHIVAL FOOTAGE"),
                       tag_font, WHITE, BLACK, 5)

    canvas = canvas.resize(UPSCALE, Image.LANCZOS)
    out_path = os.path.join(workdir, "thumbnail.png")
    canvas.save(out_path, quality=95)
    return _save_thumbnail_capped(canvas, out_path)


# ════════════════════════════════════════════════════════════
# 4. 메인
# ════════════════════════════════════════════════════════════
def main():
    if not GEMINI_API_KEY:
        log("❌ GEMINI_API_KEY 없음")
        raise SystemExit(1)

    topic = sys.argv[1] if len(sys.argv) > 1 else ""
    lang = (sys.argv[2] if len(sys.argv) > 2 else "en").strip().lower()
    channel_key = sys.argv[4] if len(sys.argv) > 4 else ""
    if not topic or channel_key not in CHANNEL_ARCHIVE_CONFIG:
        log(f"❌ 사용법: python archive_footage_longform.py \"주제\" en \"\" <channel_key>"
            f" (channel_key: {list(CHANNEL_ARCHIVE_CONFIG)})")
        raise SystemExit(1)

    workdir = os.path.join("curio_longform_output", channel_key, lang)
    os.makedirs(workdir, exist_ok=True)

    log(f"1/6 Internet Archive에서 실제 퍼블릭도메인 클립 검색+다운로드 중 (주제: {topic})...")
    clips = fetch_archive_clips(topic, channel_key, workdir)
    if not clips:
        log("❌ 이 주제로 사용 가능한 퍼블릭도메인 클립을 하나도 못 찾음 — 주제를 바꿔서 재시도 필요")
        raise SystemExit(1)
    log(f"   {len(clips)}개 클립 확보 (전부 퍼블릭도메인 검증됨)")

    log("2/6 사실기반 대본 생성 중...")
    data = generate_script(topic, channel_key, clips)
    narration = data["narration"]
    with open(os.path.join(workdir, "script.json"), "w", encoding="utf-8") as f:
        json.dump({"topic": topic, "clips": clips, **data}, f, ensure_ascii=False, indent=2)
    log(f"   나레이션 {len(narration.split())}단어")

    log("2.5/6 유튜브 제목/설명 생성 중...")
    yt_meta = generate_youtube_metadata(topic, channel_key, narration)
    log(f"   제목: {yt_meta['title']}")

    log("3/6 나레이션 TTS + 캡션 타이밍 생성 중...")
    audio_path, srt_entries, total_dur = build_narration_track(narration, workdir)
    log(f"   총 나레이션 길이: {total_dur/60:.1f}분")
    srt_path = os.path.join(workdir, "captions.srt")
    write_srt(srt_entries, srt_path)

    log("4/6 실제 아카이브 클립으로 영상 트랙 조립 중 (트림+정규화+순환)...")
    visual_path = build_visual_track(clips, total_dur, workdir)

    log("5/6 영상+오디오 합성 중...")
    final_path = os.path.join(workdir, "final.mp4")
    mux_final(visual_path, audio_path, srt_path, final_path, workdir)
    dur = get_duration(final_path)
    log(f"   ✅ 영상 완성: {final_path} ({dur/60:.1f}분)")

    log("6/6 썸네일 생성 중 (실제 프레임 사용)...")
    hero_frame = os.path.join(workdir, "hero_frame.jpg")
    extract_hero_frame(clips[0]["path"], hero_frame, at_sec=min(1.0, clips[0]["duration"] / 3))
    thumb_path = build_thumbnail(topic, channel_key, hero_frame, workdir)
    log(f"   ✅ 썸네일 완성: {thumb_path}")

    meta = {
        "topic": topic,
        "lang": lang,
        "channel_key": channel_key,
        "duration_sec": dur,
        "video_path": final_path,
        "thumbnail_path": thumb_path,
        "title": yt_meta["title"],
        "description": yt_meta["description"],
        "source_clips": [{"identifier": c["identifier"], "title": c["title"]} for c in clips],
    }
    with open(os.path.join(workdir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    log(f"🎉 완료 — {workdir}/meta.json")


if __name__ == "__main__":
    main()
