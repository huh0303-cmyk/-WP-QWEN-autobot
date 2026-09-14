"""Offline preflight for Today in History. Does not generate or upload media."""
import argparse
import json
import random
from datetime import date
from pathlib import Path

APPROVED_VOICES = ("Brian", "George", "Daniel", "Bill")


def choose_voice(previous=None, rng=None):
    """Persist the returned name with the episode; reuse it for every retry/segment."""
    return (rng or random.SystemRandom()).choice(
        [name for name in APPROVED_VOICES if name != previous]
    )


def validate_episode(plan):
    errors = []
    try:
        day = date.fromisoformat(plan.get("episode_date", ""))
    except (TypeError, ValueError):
        return ["episode_date must be an explicit ISO date"]
    if plan.get("channel_key") != "history":
        errors.append("channel_key must be history")
    if plan.get("language") != "en":
        errors.append("English narration and captions required")
    if plan.get("voice_name") not in APPROVED_VOICES:
        errors.append("Use an approved stock narrator")
    if plan.get("date_label") != f"{day.strftime('%B').upper()} {day.day}":
        errors.append("date_label must emphasize episode month and day")
    if plan.get("date_is_primary") is not True:
        errors.append("Month/day must dominate historical year visually")
    events = plan.get("events", [])
    if not isinstance(events, list) or not events:
        return errors + ["At least one verified event is required"]
    dates = []
    for index, event in enumerate(events):
        prefix = f"event {index + 1}: "
        try:
            event_day = date.fromisoformat(event.get("date", ""))
            dates.append(event_day)
            if (event_day.month, event_day.day) != (day.month, day.day):
                errors.append(prefix + "event is not on episode month/day")
        except (TypeError, ValueError):
            errors.append(prefix + "valid event date required")
        if not event.get("fact_sources"):
            errors.append(prefix + "fact source URLs required")
        if not event.get("narration"):
            errors.append(prefix + "scene-grounded narration required")
        scenes = event.get("scenes", [])
        if not scenes:
            errors.append(prefix + "matched scenes required")
        for scene in scenes:
            if scene.get("kind") not in ("archival_video", "archival_image", "explanatory_animation"):
                errors.append(prefix + "declare the visual type")
            if not all(scene.get(k) for k in ("source", "rights_basis", "visible_content", "narration_excerpt")):
                errors.append(prefix + "source, rights and scene-to-narration mapping required")
            if scene.get("kind") == "explanatory_animation" and not scene.get("on_screen_label"):
                errors.append(prefix + "label explanatory animation")
    if dates != sorted(dates, reverse=True):
        errors.append("Events must run newest to oldest")
    # These attestations require actual human/automated media review, not LLM guesses.
    for field in ("rights_review_passed", "audio_file_verified", "caption_sync_checked", "visual_alignment_checked"):
        if plan.get(field) is not True:
            errors.append(field + " required before upload readiness")
    if plan.get("upload_visibility") != "private":
        errors.append("Automated pipeline uploads private; public release is a separate decision")
    return errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    args = parser.parse_args()
    errors = validate_episode(json.loads(Path(args.manifest).read_text(encoding="utf-8")))
    print(json.dumps({"ready": not errors, "errors": errors}, indent=2))
    raise SystemExit(bool(errors))
