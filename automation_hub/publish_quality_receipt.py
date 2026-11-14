"""Shared publish receipt and deterministic quality gate for every platform.

Call before publication and persist receipt only after platform returns an ID/URL.
Never log API keys, prompt bodies, or credentials.
"""
from __future__ import annotations
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from automation_hub.editorial_readability import visible_length, MIN_CHARS, MAX_CHARS

def publish_quality_receipt(*, platform, site, title, article_html, language,
                            text_model, image_source=None, image_url=None,
                            duplicate_title=False, duplicate_body=False,
                            duplicate_image=False, publication_id=None,
                            publication_url=None):
    count = visible_length(article_html)
    problems = []
    if not MIN_CHARS <= count <= MAX_CHARS:
        problems.append("ARTICLE_LENGTH_BLOCKED")
    if not text_model or not text_model.startswith("gemini-"):
        problems.append("TEXT_MODEL_POLICY_FAIL")
    if duplicate_title: problems.append("DUPLICATE_TITLE")
    if duplicate_body: problems.append("DUPLICATE_BODY")
    if duplicate_image: problems.append("DUPLICATE_IMAGE")
    if image_source and image_source not in ("pexels", "pixabay", "bytonylee/sdxl-turbo", "black-forest-labs/flux-schnell"):
        problems.append("IMAGE_SOURCE_POLICY_FAIL")
    if not re.search(r'<h2\b', article_html, re.I): problems.append("MISSING_H2")
    if not re.search(r'faq|frequently asked|자주 묻는', article_html, re.I):
        problems.append("MISSING_FAQ")
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform, "site": site, "title": title,
        "language": language, "character_count": count,
        "required_range": [MIN_CHARS, MAX_CHARS],
        "text_model": text_model, "image_source": image_source,
        "image_fingerprint": hashlib.sha256((image_url or "").encode()).hexdigest() if image_url else None,
        "duplicate_checks": {"title": duplicate_title, "body": duplicate_body, "image": duplicate_image},
        "status": "PASS" if not problems else "BLOCKED", "issues": problems,
        "publication_id": publication_id, "publication_url": publication_url,
    }

def save_receipt(receipt, output_dir="artifacts/publish-receipts"):
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    name = hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest()[:20]
    output = path / (name + ".json")
    output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    return output
