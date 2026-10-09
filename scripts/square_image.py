"""1:1 (square) normalisation for every blog image (Chairman 2026-10-10: 사진은 전부 가로 1 : 세로 1).

`to_square_jpeg(data)` centre-crops to a square and resizes to SIZE x SIZE. If Pillow or the bytes are
unusable it returns None so callers can fall back to the untouched original instead of failing a publish.
"""
from __future__ import annotations

import io

SIZE = 1080


def to_square_jpeg(data: bytes, size: int = SIZE):
    try:
        from PIL import Image, ImageOps
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img).convert("RGB")
        w, h = img.size
        side = min(w, h)
        left, top = (w - side) // 2, (h - side) // 2
        img = img.crop((left, top, left + side, top + side))
        if side != size:
            img = img.resize((size, size), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=88, optimize=True)
        return buf.getvalue()
    except Exception:  # noqa: BLE001 - never block a publish on image post-processing
        return None
