#!/usr/bin/env python3
"""Generate a five-image editorial gallery with SDXL Lightning 4-step."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import requests


API = "https://api.replicate.com/v1"
MODEL = "bytedance/sdxl-lightning-4step"
OUT = Path("output/sdxl-lightning-samples")
PROMPTS = [
    "Photorealistic editorial photo of a Korean family reviewing household finances together at a clean dining table, calculator and plain unmarked papers turned face down, warm natural window light, candid documentary photography, 16:9",
    "Photorealistic editorial photo of a modern apartment exterior in South Korea at golden hour, landscaped walkway, a couple viewing the building from behind, realistic architecture photography, 16:9",
    "Photorealistic editorial photo of a Korean healthcare consultation in a bright modern clinic, doctor listening to an adult patient, natural expressions, discreet documentary photography, 16:9",
    "Photorealistic editorial photo of a traveler walking through a quiet traditional Korean village street with a small suitcase, early morning natural light, authentic travel photography, 16:9",
    "Photorealistic editorial photo of a Korean office worker comparing insurance options at home using a calculator, blank closed laptop and plain desk with no visible writing, evening ambient light, candid lifestyle photography, 16:9",
]
NEGATIVE = (
    "text, letters, words, numbers, writing, labels, captions, documents, forms, "
    "screens, signs, books, packaging, logo, watermark, fake Hangul, Chinese characters, "
    "Japanese characters, random glyphs, distorted hands, extra fingers, low quality"
)


def headers(token: str, wait: bool = False) -> dict[str, str]:
    result = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    if wait:
        result["Prefer"] = "wait=45"
        result["Cancel-After"] = "90s"
    return result


def wait_for(prediction: dict, token: str) -> dict:
    url = (prediction.get("urls") or {}).get("get")
    for _ in range(45):
        if prediction.get("status") in {"succeeded", "failed", "canceled"}:
            return prediction
        time.sleep(2)
        prediction = requests.get(url, headers=headers(token), timeout=20).json()
    return prediction


def first_url(output) -> str:
    if isinstance(output, list) and output:
        item = output[0]
        return item if isinstance(item, str) else item.get("url", "")
    return output if isinstance(output, str) else ""


def main() -> None:
    token = os.environ["REPLICATE_API_TOKEN"]
    OUT.mkdir(parents=True, exist_ok=True)
    model = requests.get(
        f"{API}/models/{MODEL}", headers=headers(token), timeout=20
    )
    model.raise_for_status()
    version = (model.json().get("latest_version") or {}).get("id")
    if not version:
        raise RuntimeError("No current SDXL Lightning version returned by Replicate")

    manifest = []
    for index, prompt in enumerate(PROMPTS, start=1):
        response = requests.post(
            f"{API}/predictions",
            headers=headers(token, wait=True),
            json={
                "version": version,
                "input": {
                    "prompt": prompt,
                    "negative_prompt": NEGATIVE,
                    "width": 1024,
                    "height": 576,
                    "num_outputs": 1,
                    "num_inference_steps": 4,
                    "guidance_scale": 0,
                },
            },
            timeout=65,
        )
        response.raise_for_status()
        prediction = wait_for(response.json(), token)
        if prediction.get("status") != "succeeded":
            raise RuntimeError(f"Sample {index} failed: {prediction.get('error')}")
        image_url = first_url(prediction.get("output"))
        image_response = requests.get(image_url, timeout=60)
        image_response.raise_for_status()
        path = OUT / f"sdxl-lightning-{index:02d}.png"
        path.write_bytes(image_response.content)
        manifest.append(
            {
                "sample": index,
                "model": MODEL,
                "prediction_id": prediction.get("id"),
                "prompt": prompt,
                "metrics": prediction.get("metrics", {}),
                "file": str(path),
            }
        )
        print(f"Saved {path}")

    (OUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
