#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_concept_images.py
─────────────────────────────────────────────────────────────
canva_assets/{concept}.png 30장 전부가 실제로 그 단어를 정확히 보여주는지
Gemini Vision으로 하나씩 확인하는 안전망. 발행 전에 한 번 돌려서 "동상인데
House" 같은 사고를 사전에 잡아낸다.

사용법: python3 scripts/verify_concept_images.py
필요 환경변수: GEMINI_API_KEY
"""
import os
import sys
import glob
import time
from google import genai
from google.genai import types

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL = "gemini-2.5-flash-lite"
ASSETS_DIR = "canva_assets"


def log(msg):
    print(msg, flush=True)


def verify_one(concept, image_path):
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    prompt = (
        f"Does this image clearly and unambiguously show a '{concept}'? "
        f"This is a flashcard for a language-learning app, so a young beginner "
        f"must be able to recognize the object at a glance. "
        f"Answer with exactly one word first, YES or NO, then a dash and a short "
        f"(under 12 words) reason. Example: NO - looks like a statue, not a house"
    )
    for attempt in range(3):
        try:
            resp = client.models.generate_content(
                model=MODEL,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                    prompt,
                ],
                config={"temperature": 0.0, "max_output_tokens": 40},
            )
            text = (resp.text or "").strip()
            ok = text.upper().startswith("YES")
            return ok, text
        except Exception as e:
            err = str(e).lower()
            if "429" in err or "quota" in err:
                time.sleep(15)
                continue
            time.sleep(5)
    return None, "verification failed after retries"


def main():
    if not GEMINI_API_KEY:
        log("GEMINI_API_KEY 없음")
        raise SystemExit(1)

    files = sorted(glob.glob(os.path.join(ASSETS_DIR, "*.png")))
    if not files:
        log(f"{ASSETS_DIR}/ 에 이미지가 없습니다")
        raise SystemExit(1)

    log(f"총 {len(files)}개 이미지 확인 시작\n")
    passed, failed, unknown = [], [], []

    for path in files:
        concept = os.path.splitext(os.path.basename(path))[0]
        ok, reason = verify_one(concept, path)
        if ok is True:
            passed.append(concept)
            log(f"  OK   {concept:12s} - {reason}")
        elif ok is False:
            failed.append((concept, reason))
            log(f"  FAIL {concept:12s} - {reason}")
        else:
            unknown.append(concept)
            log(f"  ??   {concept:12s} - {reason}")
        time.sleep(0.3)

    log("\n" + "=" * 60)
    log(f"통과 {len(passed)} / 실패 {len(failed)} / 확인불가 {len(unknown)} (총 {len(files)}개)")
    if failed:
        log("\n재생성이 필요한 이미지:")
        for concept, reason in failed:
            log(f"  - {concept}: {reason}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
