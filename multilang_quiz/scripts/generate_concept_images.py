#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data/words_*.csv가 공유하는 concept(단어카드 사진) 전체를 Gemini 이미지 생성으로
한 번에 깔끔하게 (재)생성해서 canva_assets/{concept}.png로 저장하는 일회성 스크립트.

기존 canva_assets/의 일부 이미지가 Canva 템플릿 목업(문구/워터마크 박힘)이라 전부
같은 스타일(텍스트 없음, 플랫/사실적 사진, 배경 깔끔)로 통일해서 다시 만든다.

사용법:
    python3 scripts/generate_concept_images.py            # 전체 30개 재생성
    python3 scripts/generate_concept_images.py --only-missing  # 없는 것만 생성

필요 환경변수: GEMINI_API_KEY
"""
import os, sys, csv, json, base64, argparse, glob
import requests

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_IMAGE_MODELS = ["gemini-2.5-flash-image", "gemini-2.5-flash-image-preview"]
ASSETS_DIR = "canva_assets"


def log(msg):
    print(msg, flush=True)


def gemini_generate_image(prompt, out_path):
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    for model in GEMINI_IMAGE_MODELS:
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{model}:generateContent?key={GEMINI_API_KEY}")
        try:
            r = requests.post(url, json=body, timeout=90)
            if r.status_code != 200:
                continue
            data = r.json()
            parts = data["candidates"][0]["content"]["parts"]
            for part in parts:
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and inline.get("data"):
                    with open(out_path, "wb") as f:
                        f.write(base64.b64decode(inline["data"]))
                    return True
        except Exception as e:
            log(f"   ⚠️ {model} 실패(무시): {e}")
            continue
    return False


def load_concepts():
    """모든 언어 CSV에서 (concept -> 참고용 image_query) 맵을 만든다.
    5개 언어가 같은 concept 집합을 공유하므로 순서만 유지해 중복 제거."""
    seen = {}
    for csv_path in sorted(glob.glob("data/words_*.csv")):
        with open(csv_path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                c = row.get("concept", "").strip()
                if c and c not in seen:
                    seen[c] = row.get("image_query", c)
    return seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only-missing", action="store_true",
                     help="이미 canva_assets/에 있는 concept는 건너뛰기")
    args = ap.parse_args()

    if not GEMINI_API_KEY:
        log("❌ GEMINI_API_KEY 없음")
        raise SystemExit(1)

    os.makedirs(ASSETS_DIR, exist_ok=True)
    concepts = load_concepts()
    log(f"총 {len(concepts)}개 concept 확인됨")

    ok, fail = [], []
    for concept, query in concepts.items():
        out_path = os.path.join(ASSETS_DIR, f"{concept}.png")
        if args.only_missing and os.path.exists(out_path):
            continue

        prompt = (
            f"A clean, simple real photograph of a single {query}, isolated on a plain "
            f"light gray or white studio background, centered composition, soft natural "
            f"lighting, no text, no watermark, no logo, no caption, no marketing copy, "
            f"no props, no border, no frame, just the object itself, product-photography style"
        )
        success = False
        for attempt in range(3):
            if gemini_generate_image(prompt, out_path):
                success = True
                break
        if success:
            log(f"✅ {concept} -> {out_path}")
            ok.append(concept)
        else:
            log(f"❌ {concept} 생성 실패")
            fail.append(concept)

    log(f"완료 — 성공 {len(ok)} / 실패 {len(fail)}")
    if fail:
        log(f"실패 목록: {', '.join(fail)}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
