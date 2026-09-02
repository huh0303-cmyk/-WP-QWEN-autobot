"""Generate deterministic square identity marks for WordPress and Tistory sites."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "site_logos"
SIZE = 512

PALETTES = {
    "health": ("#047857", "#10B981"), "skin": ("#BE185D", "#F472B6"),
    "travel": ("#C2410C", "#F97316"), "finance": ("#1D4ED8", "#60A5FA"),
    "insurance": ("#6D28D9", "#A78BFA"), "law": ("#7C2D12", "#D97706"),
    "study": ("#1E40AF", "#38BDF8"), "job": ("#0F766E", "#2DD4BF"),
    "news": ("#991B1B", "#EF4444"), "tech": ("#312E81", "#818CF8"),
    "world": ("#0369A1", "#22D3EE"), "wedding": ("#9D174D", "#FB7185"),
    "invest": ("#166534", "#84CC16"), "crypto": ("#92400E", "#FBBF24"),
    "default": ("#0F172A", "#2563EB"),
}


def classify(name: str, url: str) -> str:
    value = f"{name} {url}".lower()
    for key, words in {
        "health": ("health", "medical"), "skin": ("skin", "olive"),
        "travel": ("trip", "travel"), "finance": ("finance", "real estate"),
        "insurance": ("insurance",), "law": ("law", "tax"),
        "study": ("study", "sis", "kieca", "ksa"), "job": ("job", "visa"),
        "news": ("news", "journal", "신문"), "tech": ("tech",),
        "world": ("world", "korea365"), "wedding": ("wedding",),
        "invest": ("invest",), "crypto": ("crypto",),
    }.items():
        if any(word in value for word in words):
            return key
    return "default"


def initials(name: str) -> str:
    cleaned = name.replace("&", " ").replace("-", " ")
    words = [word for word in cleaned.split() if word.lower() not in {"korea", "in", "the"}]
    if not words:
        words = cleaned.split()
    letters = "".join(word[0] for word in words if word and word[0].isascii()).upper()
    return (letters or "K")[:2]


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in ("C:/Windows/Fonts/arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def make(mark: str, colors: tuple[str, str], destination: Path) -> None:
    image = Image.new("RGB", (SIZE, SIZE), colors[0])
    draw = ImageDraw.Draw(image)
    draw.ellipse((-90, 260, 330, 680), fill=colors[1])
    draw.ellipse((300, -120, 610, 190), fill=colors[1])
    draw.rounded_rectangle((30, 30, 481, 481), radius=116, outline="white", width=20)
    face = font(190 if len(mark) == 2 else 230)
    box = draw.textbbox((0, 0), mark, font=face)
    draw.text(((SIZE - (box[2] - box[0])) / 2, (SIZE - (box[3] - box[1])) / 2 - box[1]), mark, font=face, fill="white")
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, "PNG", optimize=True)


def main() -> None:
    registry = json.loads((ROOT / "config" / "automation_hub_sites.json").read_text(encoding="utf-8"))
    for site in registry["sites"]:
        if site.get("platform") == "wordpress":
            kind = classify(site["name"], site["url"])
            make(initials(site["name"]), PALETTES[kind], OUT / "wordpress" / f"{site['site_id']}.png")
    tistory = json.loads((ROOT / "config" / "tistory_portfolio.json").read_text(encoding="utf-8"))
    for site in tistory["sites"]:
        kind = classify(site["title"], site["url"])
        make(initials(site["title"]), PALETTES[kind], OUT / "tistory" / f"{site['site_id']}.png")


if __name__ == "__main__":
    main()
