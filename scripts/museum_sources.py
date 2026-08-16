#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
museum_sources.py
─────────────────────────────────────────────────────────────
스미소니언 박물관 Open Access API에서 CC0(저작권 없음 확정) 소장품 이미지를
검색+다운로드하는 공용 헬퍼. classic_reads/myth 등 "실제 미술품/유물 사진"이
AI생성 이미지보다 더 어울리는 채널에서 재사용한다.

data.gov API 키 하나로 스미소니언 접근 가능(무료, 즉시 발급).
NARA(국립문서기록관리청)는 별도로 catalog_api@nara.gov에 이메일로 요청해야
하는 전용 키가 필요해서(=data.gov 키로 안 됨, 2026-08-16 확인) 여기 포함 안 함
— 필요해지면 그 키를 받은 뒤 이 파일에 같은 패턴으로 추가하면 됨.
"""
import os
import re

import requests

SI_SEARCH = "https://api.si.edu/openaccess/api/v1.0/search"
DATA_GOV_API_KEY = os.environ.get("DATA_GOV_API_KEY", "")


def search_smithsonian_images(query, count=6):
    """CC0로 확인된 이미지 소장품만 반환. 각 항목: title, image_url, width, height."""
    if not DATA_GOV_API_KEY:
        return []
    params = {
        "q": f"online_media_type:Images AND {query}",
        "api_key": DATA_GOV_API_KEY,
        "rows": count * 3,
    }
    try:
        r = requests.get(SI_SEARCH, params=params, timeout=30)
        r.raise_for_status()
        rows = r.json().get("response", {}).get("rows", [])
    except Exception:
        return []

    out = []
    for row in rows:
        if len(out) >= count:
            break
        dnr = row.get("content", {}).get("descriptiveNonRepeating", {})
        media_items = dnr.get("online_media", {}).get("media", [])
        title = dnr.get("title", {}).get("content", "") if isinstance(dnr.get("title"), dict) else ""
        for m in media_items:
            if m.get("type") != "Images":
                continue
            if (m.get("usage") or {}).get("access") != "CC0":
                continue
            resources = m.get("resources") or []
            best = next((res for res in resources if "High-resolution" in (res.get("label") or "")), None)
            best = best or (resources[0] if resources else None)
            if not best or not best.get("url"):
                continue
            out.append({"title": title, "image_url": best["url"],
                        "width": best.get("width"), "height": best.get("height")})
            break
    return out


def download_image(url, out_path, timeout=60):
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    with open(out_path, "wb") as f:
        f.write(r.content)


def fetch_smithsonian_images(query, workdir, count, prefix="museum"):
    """검색+다운로드까지 한 번에. 반환값은 로컬 파일 경로 리스트(실패한 항목은 스킵)."""
    items = search_smithsonian_images(query, count)
    paths = []
    for i, item in enumerate(items):
        safe = re.sub(r"[^A-Za-z0-9_-]", "_", item["title"])[:40] or f"item{i}"
        out_path = os.path.join(workdir, f"{prefix}_{i}_{safe}.jpg")
        try:
            if not os.path.exists(out_path):
                download_image(item["image_url"], out_path)
            paths.append(out_path)
        except Exception:
            continue
    return paths
