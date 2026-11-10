"""Compatibility shim: shared image gateway only; exhausted chain means no image."""
from __future__ import annotations

def ensure_image(title: str, queries=(), theme: str = "", asset_key: str = "post", host: bool = True):
    import replicate_image_provider as provider
    subject = next((str(q).strip() for q in queries if str(q).strip()), str(title or ""))
    url = provider.generate_image_url(subject, theme=theme)
    return {"url": url or "", "provider": provider.last_image_model, "id": "", "alt": title}

def make_card_png(*args, **kwargs):
    raise RuntimeError("No image fallback after the fourth stage")
