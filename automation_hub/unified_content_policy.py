"""London Project unified content policy enforcement.

All platform adapters should call validate_content() before publishing and
record_publish_result() after the platform returns an id/url.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config" / "LONDON_PROJECT_UNIFIED_CONTENT_POLICY_20261114.json"


def load_policy() -> dict[str, Any]:
    with POLICY_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def body_char_count(html: str) -> int:
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = re.sub(r"\s+", " ", text).strip()
    return len(text)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_content(*, title: str, html: str, language: str, image_count: int = 0,
                    image_alt_texts: Iterable[str] = (), prior_titles: Iterable[str] = (),
                    similar_content_score: float | None = None) -> dict[str, Any]:
    policy = load_policy()
    length = body_char_count(html)
    errors: list[str] = []
    if not policy["length"]["min_chars"] <= length <= policy["length"]["max_chars"]:
        errors.append(f"body_char_count_out_of_range:{length}")
    if image_count > policy["images"]["max_images"]:
        errors.append("more_than_one_image")
    if image_count and any(not str(alt).strip() for alt in image_alt_texts):
        errors.append("missing_image_alt")
    if any(title.strip().casefold() == t.strip().casefold() for t in prior_titles):
        errors.append("duplicate_title")
    if re.search(r"\b20\d{2}\b", title):
        errors.append("year_in_title")
    if similar_content_score is not None and similar_content_score >= policy["seo"]["similarity_threshold"]:
        errors.append("content_similarity_too_high")
    chain_key = "ko" if language.lower().startswith(("ko", "kr")) else "en"
    return {
        "ok": not errors,
        "errors": errors,
        "body_char_count": length,
        "language": chain_key,
        "policy_version": policy["version"],
        "validated_at": datetime.now(timezone.utc).isoformat(),
    }


def record_publish_result(*, result_path: str | Path, post_id: str | int | None,
                          url: str | None, selected_model: str | None,
                          model_attempts: list[str], validation: dict[str, Any],
                          image_provider: str | None = None, image_url: str | None = None,
                          image_duplicate_check: str = "not_run",
                          image_failure_reason: str | None = None) -> None:
    record = {
        "post_id": post_id, "url": url, "selected_model": selected_model,
        "model_attempts": model_attempts, "body_char_count": validation.get("body_char_count"),
        "image_provider": image_provider, "image_url": image_url,
        "image_duplicate_check": image_duplicate_check,
        "image_failure_reason": image_failure_reason,
        "validation_result": validation,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    destination = Path(result_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
