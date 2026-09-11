from __future__ import annotations

import os
import time
from typing import Any

import requests


REPLICATE_API = "https://api.replicate.com/v1"


def _first_url(output: Any) -> str:
    if isinstance(output, str) and output.startswith("http"):
        return output
    if isinstance(output, list):
        for item in output:
            url = _first_url(item)
            if url:
                return url
    if isinstance(output, dict):
        value = output.get("url")
        if isinstance(value, str) and value.startswith("http"):
            return value
    return ""


def generate_flux_image(model: str, brief: str) -> str:
    if model == "none" or not brief.strip():
        return ""
    token = os.environ.get("REPLICATE_API_TOKEN", "").strip()
    if not token:
        raise RuntimeError("REPLICATE_API_TOKEN이 없어 선택한 FLUX 이미지를 생성하지 않았습니다")
    owner, name = model.split("/", 1)
    prompt = (
        f"Photorealistic editorial blog photograph. Subject: {brief.strip()[:800]}. "
        "Authentic human photography, natural anatomy, realistic hands, materials, light and perspective. "
        "Avoid CGI, illustration, plastic skin, malformed fingers, duplicated objects, artificial symmetry, "
        "visible text, captions, logos and watermarks. Professional restrained color grading, 16:9 landscape."
    )
    headers = {
        "Authorization": f"Bearer {token}", "Content-Type": "application/json",
        "Prefer": "wait=45", "Cancel-After": "90s",
    }
    image_input = {"prompt": prompt, "aspect_ratio": "16:9", "output_format": "webp", "output_quality": 85}
    if model != "black-forest-labs/flux-1.1-pro":
        image_input["num_outputs"] = 1
    response = requests.post(
        f"{REPLICATE_API}/models/{owner}/{name}/predictions",
        headers=headers,
        json={"input": image_input},
        timeout=60,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Replicate 이미지 생성 오류 HTTP {response.status_code}: {response.text[:240]}")
    prediction = response.json()
    deadline = time.monotonic() + 90
    while prediction.get("status") not in {"succeeded", "failed", "canceled"}:
        get_url = (prediction.get("urls") or {}).get("get")
        if not get_url or time.monotonic() >= deadline:
            raise RuntimeError("Replicate 이미지 생성 시간이 초과되었습니다")
        time.sleep(2)
        poll = requests.get(get_url, headers={"Authorization": f"Bearer {token}"}, timeout=20)
        poll.raise_for_status()
        prediction = poll.json()
    if prediction.get("status") != "succeeded":
        raise RuntimeError(f"Replicate 이미지 생성 실패: {prediction.get('error') or prediction.get('status')}")
    url = _first_url(prediction.get("output"))
    if not url:
        raise RuntimeError("Replicate 결과에서 이미지 URL을 찾지 못했습니다")
    return url
