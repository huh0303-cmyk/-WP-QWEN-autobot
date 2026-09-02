#!/usr/bin/env python3
"""AI visual inspection and hard alignment gates for knowledge-channel footage."""
from __future__ import annotations

import json
import mimetypes
import os
from pathlib import Path


def _strip_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


def inspect_and_filter_clips(topic, clips, workdir, run_ffmpeg, log, min_score=75):
    """Inspect three real frames from every clip and reject unrelated footage."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required for visual-footage alignment review")
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    accepted = []
    for index, clip in enumerate(clips):
        duration = max(float(clip.get("duration", 1)), 1.0)
        frames = []
        for frame_no, ratio in enumerate((0.2, 0.5, 0.8), 1):
            frame = Path(workdir) / f"alignment_frame_{index}_{frame_no}.jpg"
            run_ffmpeg([
                "ffmpeg", "-y", "-ss", str(max(0.2, duration * ratio)), "-i", clip["path"],
                "-frames:v", "1", "-q:v", "3", str(frame),
            ])
            frames.append(frame)
        prompt = f"""Inspect this actual archival-video frame. The planned documentary topic is:
{topic}

Archive metadata title: {clip.get('title', '')}
Archive metadata description: {clip.get('description', '')}

Return JSON only:
{{"visual_summary":"literal visible people, objects, place and action across all three frames",
  "shot_sequence":["opening visible action","middle visible action","closing visible action"],
  "era_cues":"visible period clues or unknown",
  "relevance_score":0,
  "reason":"brief evidence-based reason"}}

Score relevance from 0 to 100. Do not infer that the image is relevant merely from
the metadata. Judge what is visibly on screen. Generic or unrelated filler scores below 65.
"""
        contents = [
            types.Part.from_bytes(data=frame.read_bytes(), mime_type="image/jpeg")
            for frame in frames
        ]
        contents.append(prompt)
        response = client.models.generate_content(
            model=os.getenv("KNOWLEDGE_VISION_MODEL", "gemini-2.5-flash"),
            contents=contents,
        )
        analysis = json.loads(_strip_json(response.text or ""))
        score = int(analysis.get("relevance_score", 0))
        clip["visual_analysis"] = analysis
        log(f"   visual check {index + 1}: {score}/100 — {analysis.get('visual_summary', '')[:100]}")
        if score >= min_score:
            accepted.append(clip)
    if len(accepted) < 2:
        raise RuntimeError(
            f"Visual relevance gate failed: only {len(accepted)}/{len(clips)} clips scored {min_score}+"
        )
    return accepted


def verify_narration_alignment(topic, clips, narration, generate_text, min_score=90):
    """Fail before rendering when narration and inspected footage remain mismatched."""
    evidence = "\n".join(
        f"{i + 1}. {clip.get('visual_analysis', {}).get('visual_summary', '')}; "
        f"sequence={clip.get('visual_analysis', {}).get('shot_sequence', [])}"
        for i, clip in enumerate(clips)
    )
    prompt = f"""Act as a strict documentary continuity editor.
Topic: {topic}

Actual clip order, based on AI inspection of real frames:
{evidence}

Narration:
{narration[:12000]}

Judge whether the narration progresses through the same subjects in the same order.
Penalize generic narration, invented visuals, wrong people/periods, or long passages with
no matching footage. Return JSON only:
{{"alignment_score":0,"mismatches":["..."],"verdict":"PASS or FAIL"}}
"""
    result = json.loads(_strip_json(generate_text(prompt, temperature=0.1)))
    score = int(result.get("alignment_score", 0))
    if score < min_score or str(result.get("verdict", "")).upper() != "PASS":
        raise RuntimeError(
            f"Narration/footage alignment gate failed: {score}/100; "
            f"{result.get('mismatches', [])}"
        )
    return result
