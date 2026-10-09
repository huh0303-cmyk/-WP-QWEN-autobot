"""Every post gets an image. Free-only fallback chain (Chairman 2026-10-06: "이미지 1, 2, 3 모두 무료로 반드시 넣어라").

Order (all free, no paid API):
  1) Pexels  2) Pixabay  3) Wikimedia Commons (CC0/PD)  -> blogger_free_image.pick_image (relevance-checked, unique photo IDs)
  4) Openverse (CC0/PDM, no key)  5) generated 1:1 topic card (Pillow, cannot fail). No AI-image services (Pollinations removed 2026-10-10).
`ensure_image()` never returns None. The card is a last resort that still names the topic, so it is never "irrelevant".
"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
THEME_COLORS = {"default": ((255, 255, 255), (31, 78, 121)), "health": ((255, 255, 255), (30, 110, 90)),
                "finance": ((255, 255, 255), (60, 60, 110)), "travel": ((255, 255, 255), (20, 100, 140))}


def _font(size: int):
    from PIL import ImageFont
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_card_png(title: str, badge: str = "") -> bytes:
    """1080x1080 (1:1) topic card: solid colour, title wrapped to <=5 lines. Always succeeds."""
    import textwrap
    from PIL import Image, ImageDraw
    W, H = 1080, 1080
    key = "health" if re.search(r"건강|health|medical|의료", badge + title, re.I) else \
          "finance" if re.search(r"보험|금융|finance|invest|insurance|tax", badge + title, re.I) else \
          "travel" if re.search(r"여행|travel|trip", badge + title, re.I) else "default"
    fg, bg = THEME_COLORS[key]
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 14], fill=fg); d.rectangle([0, H - 14, W, H], fill=fg)
    ko = bool(re.search(r"[가-힣]", title))
    lines = textwrap.wrap(re.sub(r"\s+", " ", title).strip() or "Korea", width=12 if ko else 20)[:5]
    f = _font(72); y = (H - len(lines) * 96) // 2 - 10
    for line in lines:
        w = d.textbbox((0, 0), line, font=f)[2]
        d.text(((W - w) // 2, y), line, font=f, fill=fg); y += 96
    if badge:
        fb = _font(30); w = d.textbbox((0, 0), badge, font=fb)[2]
        d.text(((W - w) // 2, H - 70), badge, font=fb, fill=fg)
    buf = io.BytesIO(); img.save(buf, "PNG")
    return buf.getvalue()


def _openverse(query: str):
    r = requests.get("https://api.openverse.org/v1/images/", params={
        "q": query, "license": "cc0,pdm", "page_size": 20, "mature": "false"}, timeout=20,
        headers={"User-Agent": "london-project/1.0"})
    if r.status_code != 200:
        return None
    words = {w for w in re.findall(r"[A-Za-z]{4,}", query.lower())}
    for it in r.json().get("results", []):
        text = f"{it.get('title','')} {' '.join(t.get('name','') for t in it.get('tags') or [])}".lower()
        url = it.get("url") or ""
        if url.startswith("https://") and (not words or sum(w in text for w in words) >= max(1, len(words) // 2)):
            try:
                h = requests.head(url, timeout=15, allow_redirects=True)
                if h.status_code == 200 and h.headers.get("content-type", "").startswith("image/"):
                    return {"url": url, "provider": "Openverse", "id": it.get("id", "")}
            except requests.RequestException:
                continue
    return None


def ensure_image(title: str, queries=(), theme: str = "", asset_key: str = "post", host: bool = True) -> dict:
    """Return {url, provider, alt}. Never None. `host=True` re-hosts the card in the repo (needs GITHUB_REPOSITORY + GH_ASSET_TOKEN)."""
    qs = [q for q in [*queries, theme] if q]
    try:
        import blogger_free_image as free
        found = free.pick_image(qs[0], alternates=qs[1:]) if qs else None
        if found:
            found.setdefault("alt", title)
            return found
    except Exception as exc:  # noqa: BLE001
        print(f"image chain 1-3/5 unavailable: {type(exc).__name__}")
    for q in qs:
        try:
            found = _openverse(q)
            if found:
                print(f"image selected: Openverse {found['id']}")
                found["alt"] = title
                try:
                    from stable_image_hosting import host_permanently  # centre-crops to 1:1
                    found["url"] = host_permanently(found["url"], asset_key=f"openverse-{found['id']}", folder="blogger_images")
                except Exception as exc:  # noqa: BLE001
                    print(f"openverse hosting unavailable: {type(exc).__name__}")
                return found
        except Exception as exc:  # noqa: BLE001
            print(f"openverse unavailable: {type(exc).__name__}")
            break
    data = make_card_png(title, theme)
    url = ""
    if host:
        try:
            from stable_image_hosting import host_bytes
            url = host_bytes(data, asset_key=re.sub(r"[^a-z0-9-]+", "-", asset_key.lower())[:60] or "card")
        except Exception as exc:  # noqa: BLE001
            print(f"card hosting unavailable: {type(exc).__name__}")
    print("image selected: generated topic card")
    return {"url": url, "provider": "GeneratedCard", "id": "card", "alt": title, "png": data}
