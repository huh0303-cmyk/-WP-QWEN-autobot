"""Generate deterministic, high-contrast favicons for the five Tistory rooms."""

from pathlib import Path

from PIL import Image, ImageDraw


OUT = Path(__file__).resolve().parents[1] / "assets" / "tistory_favicons"


def canvas(color: str):
    image = Image.new("RGBA", (64, 64), color)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((2, 2, 61, 61), radius=14, outline="#ffffff", width=3)
    return image, draw


def save(name: str, image: Image.Image):
    OUT.mkdir(parents=True, exist_ok=True)
    image.save(OUT / f"{name}.ico", format="ICO", sizes=[(16, 16), (32, 32), (64, 64)])


def main():
    # Property/finance: house roof and doorway.
    image, d = canvas("#1457D9")
    d.polygon([(14, 31), (32, 15), (50, 31)], fill="white")
    d.rounded_rectangle((19, 29, 45, 51), radius=3, fill="white")
    d.rectangle((29, 38, 36, 51), fill="#1457D9")
    save("finance-housing", image)

    # Insurance: protective shield with check.
    image, d = canvas("#6D28D9")
    d.polygon([(32, 12), (50, 19), (47, 39), (32, 52), (17, 39), (14, 19)], fill="white")
    d.line([(23, 32), (29, 39), (42, 25)], fill="#6D28D9", width=5, joint="curve")
    save("insurance", image)

    # Health: universally legible medical cross.
    image, d = canvas("#059669")
    d.rounded_rectangle((26, 14, 38, 50), radius=3, fill="white")
    d.rounded_rectangle((14, 26, 50, 38), radius=3, fill="white")
    save("health", image)

    # Life information: document with verified check.
    image, d = canvas("#EA580C")
    d.rounded_rectangle((17, 12, 47, 52), radius=5, fill="white")
    d.line([(23, 23), (41, 23)], fill="#EA580C", width=3)
    d.line([(23, 30), (37, 30)], fill="#EA580C", width=3)
    d.line([(24, 40), (29, 45), (40, 35)], fill="#EA580C", width=4, joint="curve")
    save("life", image)

    # Korea travel: map pin and center point.
    image, d = canvas("#DC2626")
    d.ellipse((17, 10, 47, 40), fill="white")
    d.polygon([(20, 31), (32, 54), (44, 31)], fill="white")
    d.ellipse((26, 19, 38, 31), fill="#DC2626")
    save("travel", image)


if __name__ == "__main__":
    main()
