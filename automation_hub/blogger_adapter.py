from __future__ import annotations

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
        try:
            response = self.session.post(
                endpoint,
                params={"isDraft": str(not job.publish_now).lower()},
                headers={"Authorization": f"Bearer {self.access_token}"},
                json={"kind": "blogger#post", "title": job.title, "content": job.content_html, "labels": job.labels},
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
            return PublishResult(True, "blogger", self.site_id, job.job_id, "drafted", remote_id=remote_id, message="Blogger draft created")
        verification = verify_publication(public_url, job.title, site_url=self.site_url, attempts=3)
        if not verification.ok:
            return PublishResult(False, "blogger", self.site_id, job.job_id, "verification_failed", public_url=public_url, remote_id=remote_id, error_code=verification.error_code, message=verification.error_message)
        return PublishResult(True, "blogger", self.site_id, job.job_id, "published", public_url=verification.final_url, remote_id=remote_id)

