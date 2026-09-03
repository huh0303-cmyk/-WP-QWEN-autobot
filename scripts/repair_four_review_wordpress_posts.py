#!/usr/bin/env python3
"""Repair the four WordPress review-list posts and verify their public SEO fields."""
from __future__ import annotations

import html
import json
import os
import re
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "four-wordpress-review-repair.json"
USER = os.environ.get("WP_USER", "huh0303@gmail.com").strip()

TARGETS = [
    {
        "site": "https://ksa-korea.org",
        "post_id": 825,
        "secret": "KSAKOREAORG",
        "title": "해외 이수자 학생부대체서식: 대학별 서류·번역·공증 준비법",
        "description": "해외 이수자의 학생부대체서식 준비 절차를 대학별 요구사항, 성적·활동 증빙, 번역과 공증, 제출 일정 순서로 정리했습니다.",
    },
    {
        "site": "https://krealestate365.com",
        "post_id": 564,
        "secret": "KREALESTATE365COM",
        "title": "Renting or Buying in Korea: Deposits, Contracts and Property Checks",
        "description": "Compare renting and buying in Korea with practical checks for deposits, contracts, registration records, agent fees and the steps that protect your housing decision.",
    },
    {
        "site": "https://ktech365.com",
        "post_id": 4659,
        "secret": "KTECH365COM",
        "title": "South Korea Tech Entry: AI, Chips, R&D and Partnership Priorities",
        "description": "Understand South Korea's technology landscape through AI, semiconductors, research funding, startup programs and practical partnership checks before entering the market.",
    },
    {
        "site": "https://jobinkorea365.com",
        "post_id": 997,
        "secret": "JOBINKOREA365COM",
        "title": "Working in Korea: Visa Eligibility, Contract Costs and Job-Search Plan",
        "description": "Plan a Korean job search with clear checks for visa eligibility, contract terms, relocation costs, hiring documents and realistic steps from application to employment.",
    },
]


def plain(value: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", value or "")).strip()


def main() -> None:
    results = []
    for target in TARGETS:
        password = os.environ[target["secret"]].strip()
        endpoint = f"{target['site']}/wp-json/wp/v2/posts/{target['post_id']}"
        before = requests.get(endpoint, auth=(USER, password), params={"context": "edit"}, timeout=30)
        before.raise_for_status()
        old = before.json()
        old_content = old.get("content", {}).get("raw", "")
        old_images = re.findall(r'''(?is)<img\b[^>]*\bsrc=["']([^"']+)["']''', old_content)

        updated = requests.post(endpoint, auth=(USER, password), json={
            "title": target["title"],
            "excerpt": target["description"],
            "meta": {"rank_math_description": target["description"]},
            "status": "publish",
        }, timeout=30)
        updated.raise_for_status()

        public = requests.get(endpoint, params={"context": "view"}, timeout=30)
        public.raise_for_status()
        post = public.json()
        new_content = post.get("content", {}).get("rendered", "")
        new_images = re.findall(r'''(?is)<img\b[^>]*\bsrc=["']([^"']+)["']''', new_content)
        actual_title = plain(post.get("title", {}).get("rendered", ""))
        actual_description = post.get("meta", {}).get("rank_math_description", "")
        if actual_title != target["title"] or actual_description != target["description"]:
            raise RuntimeError(f"public SEO verification failed for {target['site']}")
        if old_images != new_images:
            raise RuntimeError(f"image preservation verification failed for {target['site']}")
        results.append({
            "site": target["site"],
            "post_id": target["post_id"],
            "status": post.get("status"),
            "link": post.get("link"),
            "old_title": plain(old.get("title", {}).get("raw", "")),
            "new_title": actual_title,
            "description": actual_description,
            "description_length": len(actual_description),
            "images_preserved": True,
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"posts": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"repaired": len(results), "published": sum(x["status"] == "publish" for x in results), "images_preserved": all(x["images_preserved"] for x in results)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
