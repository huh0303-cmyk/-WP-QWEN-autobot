"""Render rights-safe Seoul Journal parliament thumbnail templates.

The renderer never fetches photographs. Editors must pass locally reviewed images,
so a missing image becomes an explicit placeholder instead of an unlicensed face.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


NAVY = (7, 20, 42)
CYAN = (0, 231, 255)
WHITE = (255, 255, 255)
RED = (232, 46, 55)
GRAY = (76, 85, 101)


def font(size: int) -> ImageFont.FreeTypeFont:
    candidates = (
        Path("C:/Windows/Fonts/malgunbd.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
        Path("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"),
    )
    return ImageFont.truetype(str(next(path for path in candidates if path.exists())), size)


def cover(image_path: Path | None, size: tuple[int, int], label: str) -> Image.Image:
    if image_path:
        return ImageOps.fit(Image.open(image_path).convert("RGB"), size, centering=(0.5, 0.35))
    image = Image.new("RGB", size, GRAY)
    draw = ImageDraw.Draw(image)
    message = f"권리 확인 사진\n{label}"
    bounds = draw.multiline_textbbox((0, 0), message, font=font(max(24, size[1] // 17)), align="center")
    draw.multiline_text(
        ((size[0] - (bounds[2] - bounds[0])) / 2, (size[1] - (bounds[3] - bounds[1])) / 2),
        message,
        font=font(max(24, size[1] // 17)),
        fill=(220, 225, 232),
        align="center",
        spacing=10,
    )
    return image


def fitted_text(draw: ImageDraw.ImageDraw, text: str, max_width: int, start: int, minimum: int) -> tuple[ImageFont.FreeTypeFont, int]:
    size = start
    while size > minimum and draw.textlength(text, font=font(size)) > max_width:
        size -= 2
    return font(size), size


def render_landscape(
    output: Path,
    headline_top: str,
    headline_bottom: str,
    duration: str,
    badge: str,
    images: list[Path],
) -> None:
    width, height = 1280, 720
    canvas = Image.new("RGB", (width, height), NAVY)
    draw = ImageDraw.Draw(canvas)

    face_top = 72
    face_height = 405
    count = min(3, max(1, len(images)))
    slot_width = width // count
    for index in range(count):
        source = images[index] if index < len(images) else None
        canvas.paste(cover(source, (slot_width, face_height), f"인물 {index + 1}"), (index * slot_width, face_top))
    draw.rectangle((0, 0, width, face_top), fill=NAVY)
    draw.rectangle((0, 448, width, height), fill=(3, 12, 27))
    draw.rectangle((0, 448, 13, height), fill=RED)

    # Small, channel-owned identity rather than a copied broadcaster bug.
    draw.rounded_rectangle((22, 15, 176, 57), radius=9, fill=WHITE)
    draw.text((37, 21), "서울저널", font=font(25), fill=NAVY)
    draw.rounded_rectangle((194, 16, 360, 57), radius=8, fill=RED)
    badge_font, _ = fitted_text(draw, badge, 140, 24, 18)
    draw.text((208, 22), badge, font=badge_font, fill=WHITE)

    top_font, top_size = fitted_text(draw, headline_top, 1190, 76, 46)
    bottom_font, _ = fitted_text(draw, headline_bottom, 1190, 80, 48)
    draw.text((38, 466), headline_top, font=top_font, fill=WHITE, stroke_width=5, stroke_fill=(0, 0, 0))
    draw.text((38, 466 + top_size + 7), headline_bottom, font=bottom_font, fill=CYAN, stroke_width=5, stroke_fill=(0, 0, 0))

    duration_font = font(27)
    duration_box = draw.textbbox((0, 0), duration, font=duration_font)
    duration_width = duration_box[2] - duration_box[0]
    draw.rounded_rectangle((width - duration_width - 44, height - 50, width - 14, height - 12), radius=7, fill=(0, 0, 0))
    draw.text((width - duration_width - 29, height - 48), duration, font=duration_font, fill=WHITE)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, quality=95)


def render_short(
    output: Path,
    headline_top: str,
    headline_bottom: str,
    duration: str,
    badge: str,
    images: list[Path],
) -> None:
    width, height = 1080, 1920
    canvas = Image.new("RGB", (width, height), NAVY)
    draw = ImageDraw.Draw(canvas)
    face_top, face_height = 160, 1030
    count = min(2, max(1, len(images)))
    slot_width = width // count
    for index in range(count):
        source = images[index] if index < len(images) else None
        canvas.paste(cover(source, (slot_width, face_height), f"인물 {index + 1}"), (index * slot_width, face_top))
    draw.rectangle((0, 0, width, face_top), fill=NAVY)
    draw.rectangle((0, 1140, width, height), fill=(3, 12, 27))
    draw.rectangle((0, 1140, 16, height), fill=RED)
    draw.rounded_rectangle((28, 39, 245, 112), radius=12, fill=WHITE)
    draw.text((50, 51), "서울저널", font=font(39), fill=NAVY)
    draw.rounded_rectangle((268, 41, 520, 112), radius=11, fill=RED)
    badge_font, _ = fitted_text(draw, badge, 220, 38, 28)
    draw.text((288, 53), badge, font=badge_font, fill=WHITE)
    top_font, top_size = fitted_text(draw, headline_top, 980, 92, 54)
    bottom_font, _ = fitted_text(draw, headline_bottom, 980, 100, 56)
    draw.text((50, 1205), headline_top, font=top_font, fill=WHITE, stroke_width=6, stroke_fill=(0, 0, 0))
    draw.text((50, 1205 + top_size + 22), headline_bottom, font=bottom_font, fill=CYAN, stroke_width=6, stroke_fill=(0, 0, 0))
    draw.rounded_rectangle((815, 1810, 1045, 1880), radius=12, fill=(0, 0, 0))
    draw.text((845, 1820), duration, font=font(39), fill=WHITE)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, quality=95)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--headline-top", default="“그 답변 책임질 수 있습니까?”")
    parser.add_argument("--headline-bottom", default="재질문에 회의장 술렁")
    parser.add_argument("--duration", default="13:00")
    parser.add_argument("--badge", default="국회 질의")
    parser.add_argument("--image", type=Path, action="append", default=[])
    args = parser.parse_args()
    render_landscape(args.output_dir / "seoul-journal-thumbnail-16x9.jpg", args.headline_top, args.headline_bottom, args.duration, args.badge, args.image)
    render_short(args.output_dir / "seoul-journal-thumbnail-9x16.jpg", args.headline_top, args.headline_bottom, "0:59", args.badge, args.image)


if __name__ == "__main__":
    main()
