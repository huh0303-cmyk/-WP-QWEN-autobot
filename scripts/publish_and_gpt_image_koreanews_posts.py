#!/usr/bin/env python3
"""2026-08-21 사용자 지시 — koreanews365.com의 특정 34개 비공개 글(과거
색인이력 7개 + SEO80점 이상 27개)을 공개 전환하고, 대표이미지(featured
image)가 없는 글은 GPT(gpt-image-1)로 생성해서 채운다."""
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import requests  # noqa: E402
from openai_text import openai_available, openai_generate_image  # noqa: E402

SITE = "https://koreanews365.com"
USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
PW = os.getenv("KOREANEWS365COM", "").strip()

# 2026-08-21 1차 실행에서 34건 전부 공개전환은 이미 성공. 대표이미지만
# 실패한 15건 재시도용으로 목록 축소(나머지 19건은 이미 이미지 있거나
# 신규생성 완료됨). 호출 사이 텀이 전혀 없어서 OpenAI 이미지 생성 RPM
# 한도에 걸린 것으로 보여 이번엔 간격을 둔다.
POST_IDS = [
    3387, 4017, 4016, 3395, 3785, 4101, 4012, 3408, 3380,
    4104, 4103, 4100, 4013, 3415, 3327,
]
IMAGE_CALL_DELAY_SEC = 15


def api(method, path, **kwargs):
    r = requests.request(method, f"{SITE}/wp-json/wp/v2/{path}", auth=(USER, PW),
                          timeout=90, **kwargs)
    r.raise_for_status()
    return r.json() if r.content else {}


def strip_tags(html):
    return re.sub(r"<[^>]+>", " ", html or "").strip()


def make_image(post_id, title):
    workdir = "/tmp/kn365_gpt_images" if os.name != "nt" else os.getcwd()
    os.makedirs(workdir, exist_ok=True)
    out_path = os.path.join(workdir, f"post_{post_id}.png")
    prompt = (
        f"A clean, realistic editorial news photograph illustrating the story: "
        f"\"{title}\". Documentary photojournalism style, natural lighting, "
        f"no text, no watermark, no logos."
    )
    ok = openai_generate_image(prompt, out_path, size="1536x1024")
    return out_path if ok else None


def upload_media(path, title):
    with open(path, "rb") as f:
        data = f.read()
    r = requests.post(f"{SITE}/wp-json/wp/v2/media", auth=(USER, PW), timeout=90,
                       headers={"Content-Disposition": f'attachment; filename="{os.path.basename(path)}"',
                                "Content-Type": "image/png"},
                       data=data)
    r.raise_for_status()
    media = r.json()
    media_id = media["id"]
    requests.post(f"{SITE}/wp-json/wp/v2/media/{media_id}", auth=(USER, PW), timeout=30,
                  json={"alt_text": title[:120]})
    return media_id


def main():
    if not PW:
        raise SystemExit("Missing KOREANEWS365COM secret")
    if not openai_available():
        raise SystemExit("OPENAI_API_KEY 없음 — GPT 이미지 생성 불가")

    published = image_filled = image_skipped_existing = image_failed = 0
    for pid in POST_IDS:
        try:
            post = api("GET", f"posts/{pid}", params={"context": "edit",
                        "_fields": "id,title,featured_media,status"})
        except Exception as e:
            print(f"[{pid}] 조회 실패: {e}")
            continue

        title = post["title"]["raw"]

        if post.get("status") != "publish":
            api("POST", f"posts/{pid}", json={"status": "publish"})
            published += 1
            print(f"[{pid}] 공개 전환됨 — {title}")
        else:
            print(f"[{pid}] 이미 공개 상태 — {title}")

        if post.get("featured_media"):
            image_skipped_existing += 1
            print(f"    대표이미지 이미 있음(id={post['featured_media']}), 스킵")
            continue

        time.sleep(IMAGE_CALL_DELAY_SEC)
        img_path = make_image(pid, title)
        if not img_path:
            image_failed += 1
            print(f"    ⚠️ GPT 이미지 생성 실패")
            continue
        media_id = upload_media(img_path, title)
        api("POST", f"posts/{pid}", json={"featured_media": media_id})
        image_filled += 1
        print(f"    ✅ GPT 이미지 생성+설정 완료(media_id={media_id})")

    print(f"\n완료: 공개전환 {published}건 / GPT이미지 신규설정 {image_filled}건 / "
          f"기존이미지 유지 {image_skipped_existing}건 / 이미지실패 {image_failed}건 "
          f"(총 {len(POST_IDS)}건 처리)")


if __name__ == "__main__":
    main()
