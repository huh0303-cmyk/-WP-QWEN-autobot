#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
museum_sources.py
─────────────────────────────────────────────────────────────
저작권 없는(퍼블릭도메인/CC0) 실제 미술관 소장품 이미지를 검색+다운로드하는
공용 헬퍼. classic_reads/myth 등 "실제 미술품/유물 사진"이 AI생성 이미지보다
더 어울리는 채널에서 재사용한다. 3개 소스를 합쳐서 쓴다 — 콘텐츠 양과
검색 성공률을 최대화하기 위해(사용자 지시: "컨텐츠 많고 받기 쉬운 것"):

1. Art Institute of Chicago — 키 불필요, 13만+ 소장품, `is_public_domain`
   필드로 저작권 상태 명확. 소스 3개 중 가장 크고 안정적.
2. Met Museum(뉴욕 메트로폴리탄) Open Access — 키 불필요, `isPublicDomain`
   필드 명확.
3. Smithsonian Open Access — data.gov API 키 필요(무료, 즉시발급), CC0만 통과.

NARA(국립문서기록관리청)는 별도로 catalog_api@nara.gov에 이메일로 요청해야
하는 전용 키가 필요해서(=data.gov 키로 안 됨, 2026-08-16 확인) 여기 포함 안 함
— 필요해지면 그 키를 받은 뒤 이 파일에 같은 패턴으로 추가하면 됨.
"""
import os
import re

import requests

DATA_GOV_API_KEY = os.environ.get("DATA_GOV_API_KEY", "")

SI_SEARCH = "https://api.si.edu/openaccess/api/v1.0/search"
AIC_SEARCH = "https://api.artic.edu/api/v1/artworks/search"
AIC_IIIF = "https://www.artic.edu/iiif/2/{image_id}/full/843,/0/default.jpg"
MET_SEARCH = "https://collectionapi.metmuseum.org/public/collection/v1/search"
MET_OBJECT = "https://collectionapi.metmuseum.org/public/collection/v1/objects/{id}"


# ════════════════════════════════════════════════════════════
# 1. Art Institute of Chicago — 키 불필요, 가장 큰 소스
# ════════════════════════════════════════════════════════════
def search_aic_images(query, count):
    params = {"q": query, "fields": "id,title,is_public_domain,image_id", "limit": count * 2}
    try:
        r = requests.get(AIC_SEARCH, params=params, timeout=30)
        r.raise_for_status()
        rows = r.json().get("data", [])
    except Exception:
        return []
    out = []
    for row in rows:
        if len(out) >= count:
            break
        if not row.get("is_public_domain") or not row.get("image_id"):
            continue
        out.append({"title": row.get("title", ""),
                     "image_url": AIC_IIIF.format(image_id=row["image_id"])})
    return out


# ════════════════════════════════════════════════════════════
# 2. Met Museum Open Access — 키 불필요
# ════════════════════════════════════════════════════════════
def search_met_images(query, count):
    try:
        r = requests.get(MET_SEARCH, params={"q": query, "hasImages": "true"}, timeout=30)
        r.raise_for_status()
        ids = (r.json().get("objectIDs") or [])[:count * 2]
    except Exception:
        return []
    out = []
    for obj_id in ids:
        if len(out) >= count:
            break
        try:
            r = requests.get(MET_OBJECT.format(id=obj_id), timeout=20)
            r.raise_for_status()
            d = r.json()
        except Exception:
            continue
        if not d.get("isPublicDomain") or not d.get("primaryImage"):
            continue
        out.append({"title": d.get("title", ""), "image_url": d["primaryImage"]})
    return out


# ════════════════════════════════════════════════════════════
# 3. Smithsonian Open Access — data.gov 키 필요
# ════════════════════════════════════════════════════════════
def search_smithsonian_images(query, count):
    if not DATA_GOV_API_KEY:
        return []
    params = {"q": f"online_media_type:Images AND {query}", "api_key": DATA_GOV_API_KEY, "rows": count * 3}
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
        title = dnr.get("title", {}).get("content", "") if isinstance(dnr.get("title"), dict) else ""
        for m in dnr.get("online_media", {}).get("media", []):
            if m.get("type") != "Images" or (m.get("usage") or {}).get("access") != "CC0":
                continue
            resources = m.get("resources") or []
            best = next((res for res in resources if "High-resolution" in (res.get("label") or "")), None)
            best = best or (resources[0] if resources else None)
            if not best or not best.get("url"):
                continue
            out.append({"title": title, "image_url": best["url"]})
            break
    return out


# ════════════════════════════════════════════════════════════
# 4. 다운로드 + 3소스 통합
# ════════════════════════════════════════════════════════════
def download_image(url, out_path, timeout=60):
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    with open(out_path, "wb") as f:
        f.write(r.content)


_SOURCES = [
    ("aic", search_aic_images),
    ("met", search_met_images),
    ("si", search_smithsonian_images),
]


def fetch_museum_images(query, workdir, count, prefix="museum"):
    """3개 소스를 순서대로 돌면서(콘텐츠 양이 가장 많은 AIC부터) 목표 개수를
    채운다. 한 소스에서 결과가 부족하면 다음 소스로 자동 보충 — 검색 성공률을
    최대화하기 위함(사용자 지시: 콘텐츠 많고 받기 쉬운 것 우선)."""
    paths = []
    for source_name, search_fn in _SOURCES:
        if len(paths) >= count:
            break
        remaining = count - len(paths)
        items = search_fn(query, remaining)
        for i, item in enumerate(items):
            safe = re.sub(r"[^A-Za-z0-9_-]", "_", item["title"])[:40] or f"item{i}"
            out_path = os.path.join(workdir, f"{prefix}_{source_name}_{i}_{safe}.jpg")
            try:
                if not os.path.exists(out_path):
                    download_image(item["image_url"], out_path)
                paths.append(out_path)
            except Exception:
                continue
    return paths


# 하위호환 별칭(기존 코드가 이 이름으로 부르고 있었음).
fetch_smithsonian_images = fetch_museum_images
