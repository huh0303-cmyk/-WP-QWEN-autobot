#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_image_relevance.py
─────────────────────────────────────────────────────────────
27개 사이트 전체 발행글을 대상으로, 본문에 들어간 이미지가 글 주제와
실제로 관련 있는지 Gemini Vision으로 하나하나 판정한다.

읽기 전용(공개 REST 데이터만 사용, 사이트 인증 불필요) — 실제 삭제는
이 스크립트가 만든 image_audit_manifest.json을 apply_image_audit.py가
읽어서 각 사이트 비밀번호로 수행한다. (판정과 쓰기를 분리해 조사 단계는
언제든 안전하게 재실행 가능하게 함)
"""
import os
import re
import sys
import json
import time
import requests

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from concurrent.futures import ThreadPoolExecutor, as_completed
from google import genai
from google.genai import types

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL = "gemini-2.5-flash-lite"
MODEL_FALLBACK = "gemini-2.5-flash"

SITES = [
    "https://k-health365.com", "https://koreamedicaltour.com", "https://koreainvest365.com",
    "https://ki-korea.com", "https://koreainsurance365.com", "https://kfinance365.com",
    "https://koreataxnlaw.com", "https://koreacrypto365.com", "https://krealestate365.com",
    "https://ktech365.com", "https://kskin365.com", "https://oliveyoungkorea.com",
    "https://kworld365.com", "https://k-trip365.com", "https://k-visa365.com",
    "https://koreawedding365.com", "https://kstudy365.com", "https://studyinkorea365.com",
    "https://kieca-korea.org", "https://ksa-korea.org", "https://sis-korea.com",
    "https://jobkorea365.com", "https://jobinkorea365.com", "https://jobkoreaglobal.com",
    "https://korea365.org", "https://koreanews365.com", "https://theseouljournal.com",
]

FIGURE_IMG_RE = re.compile(
    r'<figure\b[^>]*>.*?<img[^>]+src="([^"]+)"[^>]*>.*?</figure>',
    re.IGNORECASE | re.DOTALL,
)

MANIFEST_PATH = "image_audit_manifest.json"
PROGRESS_PATH = "image_audit_progress.log"
_model_state = {"current": MODEL}


def log(msg):
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    try:
        with open(PROGRESS_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    try:
        print(line, flush=True)
    except Exception:
        try:
            print(line.encode("ascii", "replace").decode("ascii"), flush=True)
        except Exception:
            pass


def get_all_posts(site):
    posts = []
    page = 1
    while True:
        try:
            r = requests.get(
                f"{site}/wp-json/wp/v2/posts",
                params={"per_page": 100, "page": page, "status": "publish",
                        "_fields": "id,link,title,meta,content"},
                timeout=30,
            )
        except Exception as e:
            log(f"  ⚠️ {site} page{page} 요청 오류: {e}")
            break
        if r.status_code != 200:
            break
        items = r.json()
        if not isinstance(items, list) or not items:
            break
        posts.extend(items)
        if len(items) < 100:
            break
        page += 1
    return posts


def download_image(url):
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        ctype = r.headers.get("Content-Type", "")
        if r.status_code == 200 and ctype.startswith("image"):
            return r.content, ctype.split(";")[0].strip()
    except Exception:
        pass
    return None, None


def classify_image(image_bytes, mime_type, title, keyword):
    prompt = (
        "You are QA-checking whether a stock photo actually matches a blog article's topic.\n"
        f"Article title: {title}\n"
        f"Article focus keyword/subject: {keyword}\n"
        "Look at the attached image. Does it visually and topically relate to this SPECIFIC "
        "subject (not just a vaguely-similar generic photo of the same broad category)? "
        "Respond with exactly one word first, RELEVANT or MISMATCH, then a dash and a short "
        "(under 12 words) reason. Example: MISMATCH - generic office photo, article is about diabetes"
    )
    for attempt in range(3):
        try:
            resp = client.models.generate_content(
                model=_model_state["current"],
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    prompt,
                ],
                config={"temperature": 0.0, "max_output_tokens": 60},
            )
            text = (resp.text or "").strip()
            verdict = "MISMATCH" if text.upper().startswith("MISMATCH") else "RELEVANT"
            return verdict, text
        except Exception as e:
            err = str(e).lower()
            if "429" in err or "quota" in err:
                if _model_state["current"] != MODEL_FALLBACK:
                    _model_state["current"] = MODEL_FALLBACK
                time.sleep(20)
                continue
            time.sleep(5)
    return "UNKNOWN", "classification failed after retries"


def process_post(site, post):
    found = []
    content = post.get("content", {}).get("rendered", "") or ""
    title = re.sub(r"<[^>]+>", "", post.get("title", {}).get("rendered", "") or "")
    meta = post.get("meta", {}) or {}
    keyword = (meta.get("rank_math_focus_keyword") or "").split(",")[0].strip() or title

    urls = FIGURE_IMG_RE.findall(content)
    for u in urls:
        img_bytes, mime = download_image(u)
        if not img_bytes:
            continue
        verdict, reason = classify_image(img_bytes, mime, title, keyword)
        if verdict in ("MISMATCH", "UNKNOWN"):
            found.append({
                "site": site, "post_id": post["id"], "link": post.get("link", ""),
                "title": title, "keyword": keyword, "image_url": u,
                "verdict": verdict, "reason": reason,
            })
        time.sleep(0.2)
    return found


def main():
    manifest = []
    total_posts = 0
    for site in SITES:
        posts = get_all_posts(site)
        total_posts += len(posts)
        log(f"[{site}] {len(posts)}개 글 조사 시작")
        site_flagged = 0
        with ThreadPoolExecutor(max_workers=5) as ex:
            futs = {ex.submit(process_post, site, p): p for p in posts}
            for fut in as_completed(futs):
                try:
                    res = fut.result()
                except Exception as e:
                    log(f"  ⚠️ 글 처리 오류: {e}")
                    continue
                if res:
                    manifest.extend(res)
                    site_flagged += len(res)
        with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        log(f"[{site}] 완료 - 무관 이미지 {site_flagged}건 발견 (누적 {len(manifest)}건)")

    log("=" * 60)
    log(f"전체 {total_posts}개 글 조사 완료. 무관 이미지 {len(manifest)}건 → {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
