#!/usr/bin/env python3
"""Backfill missing K-Health365 SEO scores using the repo's transparent heuristic.

Important: this is an internal estimate, NOT Rank Math's native editor-side score.
It only replaces blank/"None"/non-numeric values for the explicitly listed posts.
"""
from __future__ import annotations

import html
import json
import os
import re
from pathlib import Path

import requests

SITE = "https://k-health365.com"
WP_USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
PASSWORD = os.getenv("KHEALTH365COM", "").strip()
POST_IDS = [7367, 6988, 7365, 7364, 7363]
OUT = Path("artifacts/khealth-seo-score-backfill.json")


def plain(value: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value or "")).split())


def char_count(body: str) -> int:
    return len(plain(body).replace(" ", "").replace("\n", ""))


def estimated_score(title: str, body: str, description: str, focus: str) -> tuple[int, dict]:
    """Use the existing repository audit rubric; this is not Rank Math's own algorithm."""
    chars = char_count(body)
    score = 0
    reasons = {}
    if chars >= 3500:
        score += 30
        reasons["body_length"] = 30
    elif chars >= 2500:
        score += 22
        reasons["body_length"] = 22
    elif chars >= 2000:
        score += 14
        reasons["body_length"] = 14
    elif chars >= 1500:
        score += 8
        reasons["body_length"] = 8
    else:
        reasons["body_length"] = 0

    title_points = 12 if title and 15 <= len(title) <= 55 else 0
    score += title_points
    reasons["title_length"] = title_points

    desc_points = 15 if len(description) >= 100 else (5 if description else 0)
    score += desc_points
    reasons["meta_description"] = desc_points

    focus_points = 10 if focus else 0
    score += focus_points
    reasons["focus_keyword"] = focus_points

    h2 = len(re.findall(r"<h2[\s>]", body, re.IGNORECASE))
    h2_points = 12 if h2 >= 4 else (6 if h2 >= 2 else 0)
    score += h2_points
    reasons["h2_structure"] = h2_points

    tables = len(re.findall(r"<table[\s>]", body, re.IGNORECASE))
    table_points = 8 if tables >= 1 else 0
    score += table_points
    reasons["table"] = table_points

    lists = len(re.findall(r"<ul[\s>]", body, re.IGNORECASE))
    list_points = 5 if lists >= 2 else 0
    score += list_points
    reasons["lists"] = list_points

    numbers = len(re.findall(r"\d+[\.,]?\d*\s*(?:%|명|만|원|mmHg|mg)", body))
    number_points = 8 if numbers >= 5 else 0
    score += number_points
    reasons["specific_data"] = number_points

    reasons["body_chars"] = chars
    reasons["h2_count"] = h2
    reasons["table_count"] = tables
    reasons["list_count"] = lists
    reasons["specific_data_count"] = numbers
    return min(score, 100), reasons


def api(method: str, route: str, **kwargs):
    response = requests.request(
        method, f"{SITE}/wp-json/wp/v2/{route}", auth=(WP_USER, PASSWORD),
        timeout=40, **kwargs,
    )
    response.raise_for_status()
    return response.json()


def main() -> int:
    if not PASSWORD:
        raise SystemExit("KHEALTH365COM secret is required")
    report = {"site": SITE, "score_type": "repository_heuristic_not_native_rank_math", "posts": [], "failed": []}
    for post_id in POST_IDS:
        try:
            post = api("GET", f"posts/{post_id}", params={"context": "edit"})
            title = plain((post.get("title") or {}).get("rendered", ""))
            body_obj = post.get("content") or {}
            body = body_obj.get("rendered", "") if isinstance(body_obj, dict) else str(body_obj)
            meta = post.get("meta") or {}
            focus_raw = str(meta.get("rank_math_focus_keyword") or "").strip()
            # Rank Math's focus keyword is a single phrase; older automation stored comma lists.
            focus = next((part.strip() for part in focus_raw.split(",") if part.strip()), "")
            description = str(meta.get("rank_math_description") or "").strip()
            old_score = str(meta.get("rank_math_seo_score") or "").strip()
            try:
                int(float(old_score))
                valid_score = old_score not in ("", "None", "none", "null")
            except (ValueError, TypeError):
                valid_score = False

            row = {
                "id": post_id, "title": title, "old_score": old_score,
                "focus_before": focus_raw, "focus_after": focus,
                "score_updated": False,
            }
            if valid_score:
                row["score"] = int(float(old_score))
                row["note"] = "existing numeric score retained"
                report["posts"].append(row)
                continue

            score, details = estimated_score(title, body, description, focus)
            meta_update = {"rank_math_seo_score": str(score)}
            if focus and focus != focus_raw:
                meta_update["rank_math_focus_keyword"] = focus
            api("POST", f"posts/{post_id}", json={"meta": meta_update})

            saved = api("GET", f"posts/{post_id}", params={"context": "edit"})
            saved_meta = saved.get("meta") or {}
            saved_score = str(saved_meta.get("rank_math_seo_score") or "").strip()
            if saved_score != str(score):
                raise RuntimeError(f"score verification failed: expected {score}, got {saved_score!r}")
            if focus and str(saved_meta.get("rank_math_focus_keyword") or "").strip() != focus:
                raise RuntimeError("focus keyword verification failed")
            row.update({"score": score, "score_updated": True, "score_breakdown": details,
                        "focus_verified": True, "note": "heuristic estimate; not native Rank Math recalculation"})
            report["posts"].append(row)
        except Exception as exc:
            report["failed"].append({"id": post_id, "error": f"{type(exc).__name__}: {str(exc)[:250]}"})

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "target_count": len(POST_IDS),
        "updated": sum(1 for row in report["posts"] if row.get("score_updated")),
        "retained_existing": sum(1 for row in report["posts"] if row.get("note") == "existing numeric score retained"),
        "failed": len(report["failed"]),
        "scores": [{"id": row["id"], "score": row.get("score"), "updated": row.get("score_updated")} for row in report["posts"]],
        "score_type": report["score_type"],
    }, ensure_ascii=False))
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
