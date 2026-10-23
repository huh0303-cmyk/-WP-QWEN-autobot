from __future__ import annotations

import os
from urllib.parse import urlparse

import requests

from .publishing import PublishJob, PublishResult

TISTORY_WRITE_URL = "https://www.tistory.com/apis/post/write"
TISTORY_CATEGORY_LIST_URL = "https://www.tistory.com/apis/category/list"


def _blog_name_from_url(blog_url: str) -> str:
    host = urlparse(blog_url).netloc or blog_url
    return host.split(".")[0]


def _resolve_category_id(blog_name: str, category_name: str, access_token: str) -> str:
    """Best-effort numeric category lookup. Returns "" (no category) on any failure.

    Untested against a live Tistory account — there is no TISTORY_ACCESS_TOKEN
    available in this environment to verify the response shape against. Kept
    fail-open (no category rather than a guessed id) so a lookup miss never
    blocks the actual post.
    """
    if not category_name:
        return ""
    try:
        response = requests.get(
            TISTORY_CATEGORY_LIST_URL,
            params={"access_token": access_token, "output": "json", "blogName": blog_name},
            timeout=15,
        )
        response.raise_for_status()
        items = ((response.json().get("tistory") or {}).get("item") or {}).get("category") or []
        if isinstance(items, dict):
            items = [items]
        for item in items:
            if str(item.get("name", "")).strip() == category_name.strip():
                return str(item.get("id", ""))
    except Exception:
        return ""
    return ""


class TistoryPublisher:
    """Publishes exactly one approved article to one Tistory blog via the
    Tistory Open API (api endpoint under www.tistory.com/apis).

    This is only ever invoked by tistory_approve_publish.py after a signed,
    single-use approval token has verified for this exact job_id — never on
    a schedule and never for more than the one approved article.
    """

    def __init__(self, site_id: str, blog_url: str):
        self.site_id = site_id
        self.blog_url = blog_url
        self.blog_name = _blog_name_from_url(blog_url)

    def publish(self, job: PublishJob, *, category: str = "", image_url: str = "") -> PublishResult:
        errors = job.validate()
        if errors:
            return PublishResult(False, "tistory", self.site_id, job.job_id, "FAILED", error_code="invalid_job", message="; ".join(errors))

        access_token = os.environ.get("TISTORY_ACCESS_TOKEN", "").strip()
        if not access_token:
            return PublishResult(
                False,
                "tistory",
                self.site_id,
                job.job_id,
                "FAILED",
                error_code="missing_credential",
                message="TISTORY_ACCESS_TOKEN is not configured in repository secrets — cannot call the Tistory Open API.",
            )

        content_html = job.content_html
        if image_url:
            content_html = f'<p><img src="{image_url}" alt="{job.title}"></p>' + content_html

        payload = {
            "access_token": access_token,
            "output": "json",
            "blogName": self.blog_name,
            "title": job.title,
            "content": content_html,
            "visibility": "3",  # 3 = publish live (0=private, 1=protected)
            "acceptComment": "1",
        }
        category_id = _resolve_category_id(self.blog_name, category, access_token) if category else ""
        if category_id:
            payload["category"] = category_id
        if job.labels:
            payload["tag"] = ",".join(job.labels)

        try:
            response = requests.post(TISTORY_WRITE_URL, data=payload, timeout=30)
            response.raise_for_status()
            body = response.json()
        except Exception as exc:
            return PublishResult(False, "tistory", self.site_id, job.job_id, "FAILED", error_code="request_failed", message=str(exc))

        tistory = body.get("tistory", {}) if isinstance(body, dict) else {}
        status = str(tistory.get("status", ""))
        if status != "200":
            return PublishResult(
                False,
                "tistory",
                self.site_id,
                job.job_id,
                "FAILED",
                error_code=f"tistory_status_{status or 'unknown'}",
                message=str(tistory.get("error_message") or tistory.get("message") or "Tistory Open API rejected the post."),
                extra={"raw": tistory},
            )

        public_url = str(tistory.get("url", ""))
        return PublishResult(
            True,
            "tistory",
            self.site_id,
            job.job_id,
            "PUBLISHED",
            public_url=public_url,
            remote_id=str(tistory.get("postId", "")),
        )
