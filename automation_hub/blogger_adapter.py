from __future__ import annotations

import html
from typing import Any

import requests

from .public_verifier import verify_publication
from .publishing import PublishJob, PublishResult


class BloggerPublisher:
    """Publish through Google's supported Blogger v3 API."""

    def __init__(self, site_id: str, blog_id: str, access_token: str, *, site_url: str = "", session: Any = requests):
        self.site_id = site_id
        self.blog_id = blog_id
        self.access_token = access_token
        self.site_url = site_url
        self.session = session

    def publish(self, job: PublishJob) -> PublishResult:
        errors = job.validate()
        if errors:
            return PublishResult(False, "blogger", self.site_id, job.job_id, "failed", error_code="invalid_job", message="; ".join(errors))
        if not self.blog_id or not self.access_token:
            return PublishResult(False, "blogger", self.site_id, job.job_id, "auth_required", error_code="missing_blogger_credentials", message="Blogger blog ID and OAuth token are required")

        endpoint = f"https://www.googleapis.com/blogger/v3/blogs/{self.blog_id}/posts"
        marker = f"automation-job:{job.job_id}"
        marked_content = f"<!-- {html.escape(marker)} -->{job.content_html}"
        try:
            # Blogger has no idempotency-key header.  Persist a hidden stable
            # job marker in the draft and look for it before every retry.  A
            # worker crash after POST but before the Sheet update therefore
            # returns the already-created draft instead of making a duplicate.
            existing = self.session.get(
                endpoint,
                params={"status": ["draft", "live", "scheduled"], "view": "ADMIN",
                        "fetchBodies": "true", "maxResults": 50},
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=30,
            )
            if isinstance(existing.status_code, int) and existing.status_code != 200:
                return PublishResult(
                    False, "blogger", self.site_id, job.job_id, "failed",
                    error_code=f"blogger_preflight_http_{existing.status_code}",
                    message="Blogger idempotency preflight failed; draft creation was not attempted",
                )
            if existing.status_code == 200:
                for item in existing.json().get("items", []):
                    if marker not in str(item.get("content", "")):
                        continue
                    remote_id = str(item.get("id", ""))
                    review_url = f"https://www.blogger.com/blog/post/edit/{self.blog_id}/{remote_id}"
                    return PublishResult(
                        True, "blogger", self.site_id, job.job_id, "drafted",
                        public_url=review_url, remote_id=remote_id,
                        message="Existing Blogger draft recovered by stable job marker; no duplicate created",
                        extra={"idempotent_recovery": True,
                               "search_description": job.search_description,
                               "search_description_ui_required": True},
                    )
            response = self.session.post(
                endpoint,
                params={"isDraft": str(not job.publish_now).lower()},
                headers={"Authorization": f"Bearer {self.access_token}"},
                # Blogger API v3's Post resource does not expose the editor's
                # Search description field. Sending an invented customMetaData
                # property is silently ignored, so never claim that it saved.
                json={"kind": "blogger#post", "title": job.title, "content": marked_content,
                      "labels": job.labels},
                timeout=30,
            )
            if response.status_code not in {200, 201}:
                return PublishResult(False, "blogger", self.site_id, job.job_id, "failed", error_code=f"blogger_http_{response.status_code}", message=response.text[:500])
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            return PublishResult(False, "blogger", self.site_id, job.job_id, "failed", error_code="blogger_request_error", message=str(exc)[:500])

        public_url = payload.get("url", "")
        remote_id = str(payload.get("id", ""))
        if not job.publish_now:
            review_url = f"https://www.blogger.com/blog/post/edit/{self.blog_id}/{remote_id}"
            return PublishResult(
                True, "blogger", self.site_id, job.job_id, "drafted",
                public_url=review_url, remote_id=remote_id,
                message="Blogger draft created; Search description must be saved in the editor before manual publish",
                extra={"search_description": job.search_description, "search_description_ui_required": True},
            )
        verification = verify_publication(public_url, job.title, site_url=self.site_url, attempts=3)
        if not verification.ok:
            return PublishResult(False, "blogger", self.site_id, job.job_id, "verification_failed", public_url=public_url, remote_id=remote_id, error_code=verification.error_code, message=verification.error_message)
        return PublishResult(True, "blogger", self.site_id, job.job_id, "published", public_url=verification.final_url, remote_id=remote_id)
