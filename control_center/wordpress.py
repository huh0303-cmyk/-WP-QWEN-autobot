from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Any

import requests

from .registry import WordPressSite
from .images import generate_flux_image


WP_USER = os.environ.get("WP_USER", "huh0303@gmail.com")


@dataclass(frozen=True, slots=True)
class DraftResult:
    post_id: str
    edit_url: str
    preview_url: str
    recovered: bool = False


def credential_health(site: WordPressSite) -> str:
    return "ready" if site.secret_name and os.environ.get(site.secret_name, "").strip() else "missing"


def deterministic_slug(job_id: str, keyword: str) -> str:
    digest = hashlib.sha256(f"{job_id}:{keyword}".encode("utf-8")).hexdigest()[:16]
    return f"k365-review-{digest}"


def create_draft(site: WordPressSite, *, job_id: str, keyword: str, article: dict[str, Any]) -> DraftResult:
    password = os.environ.get(site.secret_name, "").strip()
    if not password:
        raise RuntimeError(f"{site.secret_name} 인증정보가 없어 원격 작업을 시작하지 않았습니다")
    auth = (WP_USER, password)
    slug = deterministic_slug(job_id, keyword)
    endpoint = f"{site.url}/wp-json/wp/v2/posts"

    existing = requests.get(
        endpoint,
        auth=auth,
        params={"slug": slug, "status": "any", "context": "edit", "per_page": 1},
        timeout=30,
    )
    if existing.status_code == 200 and existing.json():
        post = existing.json()[0]
        if post.get("status") != "draft":
            raise RuntimeError(f"동일 작업의 기존 글 상태가 draft가 아닙니다: {post.get('status')}")
        post_id = str(post["id"])
        return DraftResult(post_id, f"{site.url}/wp-admin/post.php?post={post_id}&action=edit", post.get("link", ""), True)

    featured_media = 0
    content_html = article["content_html"]
    image_queries = article.get("image_queries") or []
    image_model = article.get("image_model", "none")
    if image_model != "none" and image_queries:
        image_alt = f"{str(image_queries[0]).strip()} 관련 장면"
        prior_media = requests.get(
            f"{site.url}/wp-json/wp/v2/media", auth=auth,
            params={"slug": slug, "context": "edit", "per_page": 1}, timeout=30,
        )
        media_data = prior_media.json()[0] if prior_media.status_code == 200 and prior_media.json() else None
        if not media_data:
            image_url = generate_flux_image(image_model, str(image_queries[0]))
            image_response = requests.get(image_url, timeout=45)
            image_response.raise_for_status()
            media = requests.post(
                f"{site.url}/wp-json/wp/v2/media", auth=auth,
                headers={"Content-Disposition": f'attachment; filename="{slug}.webp"', "Content-Type": "image/webp"},
                data=image_response.content, timeout=60,
            )
            if media.status_code not in {200, 201}:
                raise RuntimeError(f"WordPress 이미지 업로드 실패 HTTP {media.status_code}: {media.text[:240]}")
            media_data = media.json()
        featured_media = int(media_data["id"])
        source_url = media_data.get("source_url", "")
        requests.post(
            f"{site.url}/wp-json/wp/v2/media/{featured_media}", auth=auth,
            json={"alt_text": image_alt}, timeout=30,
        )
        if source_url:
            content_html = f'<figure><img src="{source_url}" alt="{image_alt}"></figure>' + content_html

    payload: dict[str, Any] = {
        "title": article["title"],
        "slug": slug,
        "content": content_html,
        "excerpt": article["meta_description"],
        "status": "draft",
        "comment_status": "closed",
        "ping_status": "closed",
        "meta": {"rank_math_description": article["meta_description"], "control_center_job_id": job_id},
    }
    if featured_media:
        payload["featured_media"] = featured_media
    response = requests.post(endpoint, auth=auth, json=payload, timeout=45)
    if response.status_code not in {200, 201}:
        # An unknown network outcome is recovered by the deterministic slug on retry.
        raise RuntimeError(f"WordPress 초안 생성 실패 HTTP {response.status_code}: {response.text[:300]}")
    post = response.json()
    if post.get("status") != "draft":
        raise RuntimeError(f"WordPress가 안전하지 않은 상태를 반환했습니다: {post.get('status')}")
    post_id = str(post["id"])
    return DraftResult(post_id, f"{site.url}/wp-admin/post.php?post={post_id}&action=edit", post.get("link", ""))
